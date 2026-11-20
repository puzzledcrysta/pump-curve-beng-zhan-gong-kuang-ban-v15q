from decimal import Decimal
import pytest
from app.errors import DataError
from app.modules.domain.rule import evaluate


def test_twin_same(cases):
    actual, proof = evaluate(cases['twin_same'])
    assert actual == Decimal('100.000')
    assert Decimal(str(dict((label, value) for label, value, _ in proof)['工况扬程'])) == Decimal('50.000')


def test_asymmetric(cases):
    # TRAP-112
    actual, proof = evaluate(cases['asymmetric'])
    assert actual == Decimal('120.000')
    assert Decimal(str(dict((label, value) for label, value, _ in proof)['乙 单泵流量'])) == Decimal('80.000')


def test_piecewise_knot(cases):
    actual, proof = evaluate(cases['piecewise_knot'])
    assert actual == Decimal('60.000')
    assert proof


def test_endpoint(cases):
    actual, proof = evaluate(cases['endpoint'])
    assert actual == Decimal('100.000')
    assert proof


def test_exact_midpoint(cases):
    actual, proof = evaluate(cases['exact_midpoint'])
    assert actual == Decimal('50.000')
    assert Decimal(str(dict((label, value) for label, value, _ in proof)['工况扬程'])) == Decimal('50.000')


def test_calibrated_nonzero(cases):
    actual, proof = evaluate(cases['calibrated_nonzero'])
    assert actual == Decimal('60.000')
    assert proof


def test_no_cross(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['no_cross'])
    assert error.value.code == 'PUMP_CROSS'


def test_non_monotone(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['non_monotone'])
    assert error.value.code == 'PUMP_MONOTONE'


def test_no_common_head(cases):
    # TRAP-113
    with pytest.raises(DataError) as error:
        evaluate(cases['no_common_head'])
    assert error.value.code == 'PUMP_SPAN'
