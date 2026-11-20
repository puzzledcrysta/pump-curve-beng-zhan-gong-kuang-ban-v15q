from app.errors import DataError
from app.settings import KEY, UNIT
from app.modules.domain.values import number
from app.modules.intake.reader import decode, records

VALUE_HEADER = f'外部记录值({UNIT})'
STEP_HEADER = f'舍入步长({UNIT})'
TOLERANCE_HEADER = f'允差({UNIT})'
EXACT_HEADER = [KEY, VALUE_HEADER]
ROUNDED_HEADER = [KEY, VALUE_HEADER, STEP_HEADER, TOLERANCE_HEADER]


def ledger(payload):
    text, _ = decode(payload)
    rows = iter(records(text))
    _, header = next(rows, (0, []))
    if header == EXACT_HEADER:
        rounded = False
    elif header == ROUNDED_HEADER:
        rounded = True
    else:
        raise DataError('HEADER', '外部账表头或计量单位不符；舍入账须同时给出舍入步长与允差两列')
    by_key = {}
    for line, row in rows:
        if not row or not any(value.strip() for value in row):
            continue
        if len(row) != len(header) or not row[0].strip():
            raise DataError('WIDTH', f'外部账第 {line} 行缺少业务键或计量')
        key = row[0].strip()
        if key in by_key:
            raise DataError('BOOK_CONFLICT', f'外部账第 {line} 行重复业务键 {key}')
        entry = {'value': number(row[1]), 'line': line}
        if rounded:
            step = number(row[2])
            tolerance = number(row[3])
            if step <= 0:
                raise DataError('TOL_FORMAT', f'外部账第 {line} 行的舍入步长必须为正数')
            if tolerance < 0:
                raise DataError('TOL_FORMAT', f'外部账第 {line} 行的允差不能为负数')
            entry['step'] = step
            entry['tolerance'] = tolerance
        by_key[key] = entry
    return {'rounded': rounded, 'entries': by_key}
