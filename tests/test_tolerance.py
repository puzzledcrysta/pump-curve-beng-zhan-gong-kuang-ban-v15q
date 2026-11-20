from decimal import Decimal
import pytest
from app.errors import DataError
from app.settings import KEY, UNIT
from app.modules.reconcile.ledger import ledger
from app.modules.reconcile.tolerance import delta_band, verdict
from app.modules.reconcile.service import compare

ROUNDED_HEADER = f'{KEY},{f"外部记录值({UNIT})"},{f"舍入步长({UNIT})"},{f"允差({UNIT})"}'


def rounded_book(lines):
    return (ROUNDED_HEADER + '\n' + '\n'.join(lines) + '\n').encode()


def accepted(key, amount):
    return [{'key': key, 'line': 2, 'amount': str(amount)}]


def test_band_symmetric_around_point_delta():
    lower, upper = delta_band(Decimal('100'), Decimal('100'), Decimal('1'))
    assert (lower, upper) == (Decimal('-0.5'), Decimal('0.5'))
    lower, upper = delta_band(Decimal('120'), Decimal('121'), Decimal('1'))
    assert (lower, upper) == (Decimal('-1.5'), Decimal('-0.5'))


def test_verdict_inside_hold_over():
    # 差值区间整体在允差内
    assert verdict(Decimal('100'), Decimal('100'), Decimal('1'), Decimal('2')) == 'TOL_OK'
    # 区间跨过允差线：一端在内、一端在外
    assert verdict(Decimal('120'), Decimal('121'), Decimal('1'), Decimal('1')) == 'TOL_HOLD'
    # 区间整体超出允差
    assert verdict(Decimal('100'), Decimal('97'), Decimal('1'), Decimal('2')) == 'TOL_OVER'


def test_boundary_touching_tolerance_is_signable():
    # 区间端点恰好落在允差线上，按闭区间允许签认
    assert verdict(Decimal('100'), Decimal('100'), Decimal('2'), Decimal('1')) == 'TOL_OK'


def test_compare_marks_three_rounded_verdicts():
    book = rounded_book(['00101,100,1,2', '00102,121,1,1', '00104,97,1,2'])
    rows = compare([
        {'key': '00101', 'line': 2, 'amount': '100.000'},
        {'key': '00102', 'line': 3, 'amount': '120.000'},
        {'key': '00104', 'line': 4, 'amount': '100.000'},
    ], book)
    by_key = {row['key']: row for row in rows['rows']}
    assert by_key['00101']['code'] == 'TOL_OK' and by_key['00101']['kind'] == '舍入'
    assert by_key['00102']['code'] == 'TOL_HOLD'
    assert (by_key['00102']['delta_min'], by_key['00102']['delta_max']) == ('-1.500', '-0.500')
    assert by_key['00104']['code'] == 'TOL_OVER'
    assert rows['rounding'] == {'enabled': True, 'ok': 1, 'hold': 1, 'over': 1, 'signable': False}
    assert rows['matched'] == 1 and rows['mismatched'] == 2


def test_exact_book_keeps_original_rules(source, book):
    # 同一份精确外账仍按原办法逐笔核对
    from app.pipeline import execute
    result = execute(source, book)['book']
    assert result['rounding'] == {'enabled': False, 'ok': 0, 'hold': 0, 'over': 0, 'signable': True}
    assert all(row['kind'] == '精确' for row in result['rows'])
    assert result['matched'] == 24 and result['mismatched'] == 3


def test_rounded_book_header_requires_step_and_tolerance():
    with pytest.raises(DataError) as error:
        ledger(f'{KEY},外部记录值({UNIT}),舍入步长({UNIT})\n00101,100,1\n'.encode())
    assert error.value.code == 'HEADER'


@pytest.mark.parametrize('step,tolerance', [('0', '2'), ('1', '-1')])
def test_invalid_step_and_tolerance_rejected(step, tolerance):
    with pytest.raises(DataError) as error:
        ledger(rounded_book([f'00101,100,{step},{tolerance}']))
    assert error.value.code == 'TOL_FORMAT'


def test_rounded_book_still_rejects_duplicate_keys():
    with pytest.raises(DataError) as error:
        ledger(rounded_book(['00101,100,1,2', '00101,101,1,2']))
    assert error.value.code == 'BOOK_CONFLICT'


def test_missing_side_rows_keep_codes_under_rounded_book():
    book = rounded_book(['09999,7,1,2'])
    rows = compare([{'key': '00101', 'line': 2, 'amount': '100'}], book)['rows']
    by_key = {row['key']: row for row in rows}
    assert by_key['00101']['code'] == 'MISSING_BOOK'
    assert by_key['09999']['code'] == 'MISSING_RESULT'
