from base64 import b64encode
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def rounded_book():
    return (ROOT / 'sample_data/rounded.csv').read_bytes()


def rounded_payload(book):
    return {'book_base64': b64encode(book).decode()}


def test_rounded_run_reports_signoff_blocked(client, rounded_book):
    report = client.post('/api/runs', json=rounded_payload(rounded_book)).json()
    assert report['book']['rounding'] == {'enabled': True, 'ok': 3, 'hold': 1, 'over': 1, 'signable': False}
    by_key = {row['key']: row for row in report['book']['rows']}
    assert by_key['00102']['code'] == 'TOL_HOLD'
    assert by_key['00104']['code'] == 'TOL_OVER'


def test_review_confirm_blocked_while_band_crosses_tolerance(client, rounded_book):
    run_id = client.post('/api/runs', json=rounded_payload(rounded_book)).json()['manifest']['run_id']
    blocked = client.post(f'/api/review/{run_id}',
                          json={'version': 0, 'decision': '确认', 'note': '按显示值签'})
    assert (blocked.status_code, blocked.json()['code']) == (422, 'REVIEW_ROUNDED')
    # 退回仍可登记，交班不留空
    returned = client.post(f'/api/review/{run_id}',
                           json={'version': 0, 'decision': '退回', 'note': '舍入区间跨允差，等精测'})
    assert returned.status_code == 200 and returned.json()['version'] == 1


def test_late_precision_book_reopens_signoff_and_keeps_old_conclusion(client, rounded_book):
    hold = client.post('/api/runs', json=rounded_payload(rounded_book)).json()
    hold_id = hold['manifest']['run_id']
    exact = client.post('/api/runs', json={}).json()
    exact_id = exact['manifest']['run_id']
    assert hold_id != exact_id
    # 原舍入批次及其依据仍可查
    old = client.get(f'/api/runs/{hold_id}').json()
    assert old['book']['rounding']['hold'] == 1
    # 精测外账按原办法核对，确认不再被舍入闸门拦截
    allowed = client.post(f'/api/review/{exact_id}',
                          json={'version': 0, 'decision': '确认', 'note': '精测已到，逐笔核对'})
    assert allowed.status_code == 200
    assert len(client.get('/api/runs').json()) == 2


def test_same_precision_book_rerun_does_not_add_run(client):
    first = client.post('/api/runs', json={}).json()['manifest']['run_id']
    second = client.post(f'/api/runs/{first}/replay').json()['manifest']['run_id']
    assert first == second and len(client.get('/api/runs').json()) == 1


def test_export_carries_rounded_evidence(client, rounded_book):
    run_id = client.post('/api/runs', json=rounded_payload(rounded_book)).json()['manifest']['run_id']
    proof = client.get(f'/api/export/{run_id}').json()
    row = next(row for row in proof['reconciliation']['rows'] if row['key'] == '00102')
    assert row['code'] == 'TOL_HOLD' and row['delta_min'] == '-1.500' and row['delta_max'] == '-0.500'
    assert proof['reconciliation']['rounding']['signable'] is False


def test_rounded_sample_endpoint(client):
    response = client.get('/api/samples/rounded')
    assert response.status_code == 200 and '舍入步长'.encode() in response.content
