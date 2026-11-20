from decimal import Decimal
from .ledger import ledger
from .tolerance import delta_band, verdict

BAND_QUANTUM = Decimal('0.001')


def compare(accepted, payload):
    book = ledger(payload)
    expected = book['entries']
    actual = {row['key']: (Decimal(row['amount']), row['line']) for row in accepted}
    rows, matches = [], 0
    rounded_ok = rounded_hold = rounded_over = 0
    for key in sorted(actual.keys() | expected.keys()):
        value, line = actual.get(key, (None, None))
        entry = expected.get(key)
        book_line = entry['line'] if entry else None
        reference = entry['value'] if entry else None
        delta = (value or Decimal(0)) - (reference or Decimal(0))
        if entry is None:
            reason = 'MISSING_BOOK'
        elif value is None:
            reason = 'MISSING_RESULT'
        elif 'step' not in entry:
            reason = 'MATCH' if delta == 0 else 'AMOUNT_DELTA'
        else:
            reason = verdict(value, reference, entry['step'], entry['tolerance'])
            if reason == 'TOL_OK':
                rounded_ok += 1
            elif reason == 'TOL_HOLD':
                rounded_hold += 1
            else:
                rounded_over += 1
        if reason in {'MATCH', 'TOL_OK'}:
            matches += 1
        item = {'key': key, 'amount': str(value) if value is not None else None,
                'reference': str(reference) if reference is not None else None, 'delta': str(delta),
                'line': line, 'book_line': book_line, 'code': reason,
                'kind': '舍入' if entry is not None and 'step' in entry else '精确'}
        if entry is not None and 'step' in entry and value is not None:
            lower, upper = delta_band(value, reference, entry['step'])
            item.update({'step': str(entry['step']), 'tolerance': str(entry['tolerance']),
                         'delta_min': str(lower.quantize(BAND_QUANTUM)),
                         'delta_max': str(upper.quantize(BAND_QUANTUM))})
        rows.append(item)
    actual_total = sum((pair[0] for pair in actual.values()), Decimal(0))
    book_total = sum((entry['value'] for entry in expected.values()), Decimal(0))
    rounding = {'enabled': book['rounded'], 'ok': rounded_ok, 'hold': rounded_hold, 'over': rounded_over,
                'signable': rounded_hold == 0 and rounded_over == 0}
    return {'rows': rows, 'matched': matches, 'mismatched': len(rows) - matches, 'actual': str(actual_total),
            'expected': str(book_total), 'delta': str(actual_total - book_total), 'rounding': rounding}
