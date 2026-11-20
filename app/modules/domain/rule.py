from decimal import Decimal as D
from app.errors import DataError
from .values import number, parts


def points(raw, rising):
    data = {}
    for token in raw.split(','):
        a, delimiter, b = token.partition(':')
        if not delimiter:
            raise DataError('PUMP_FORMAT','曲线点须包含流量与扬程')
        flow, head = number(a,0,10000), number(b,0,1000)
        if flow in data:
            raise DataError('PUMP_POINT','同流量有重复测点')
        data[flow] = head
    curve = sorted(data.items())
    if not 2 <= len(curve) <= 40:
        raise DataError('PUMP_LIMIT','每条曲线需有 2 至 40 个点')
    for (_,a),(_,b) in zip(curve,curve[1:]):
        if (b <= a if rising else b >= a):
            raise DataError('PUMP_MONOTONE','泵曲线须随流量下降，管线曲线须上升')
    return curve


def interpolate(curve, x):
    for (a,p),(b,q) in zip(curve,curve[1:]):
        if a <= x <= b:
            return p + (q-p)*(x-a)/(b-a)
    raise DataError('PUMP_SPAN','曲线外禁止外推')


def evaluate(row):
    pumps = {}
    for item in parts(row['泵组曲线']):
        name, sep, source = item.partition('=')
        if not sep or not name or name in pumps:
            raise DataError('PUMP_DUP','泵编号重复或缺少曲线')
        pumps[name] = [(head,flow) for flow,head in reversed(points(source,False))]
    if not 1 <= len(pumps) <= 12:
        raise DataError('PUMP_LIMIT','泵数须在 1 至 12 台之间')
    pipe = points(row['管线曲线'],True)
    lower = max(curve[0][0] for curve in pumps.values())
    upper = min(curve[-1][0] for curve in pumps.values())
    if lower >= upper:
        raise DataError('PUMP_SPAN','各泵实测数据没有公共扬程区间')
    knots = {head for curve in pumps.values() for head,_ in curve if lower <= head <= upper}
    projected = sorted((sum(interpolate(curve, head) for curve in pumps.values()),head) for head in knots)
    low_q = max(pipe[0][0],projected[0][0])
    high_q = min(pipe[-1][0],projected[-1][0])
    breaks = sorted({low_q,high_q} | {flow for curve in (pipe,projected) for flow,_ in curve if low_q <= flow <= high_q})
    if low_q > high_q:
        raise DataError('PUMP_SPAN','管线与泵组没有公共流量区间')
    q0, q1 = breaks[0], breaks[-1]
    diffs = [interpolate(projected,q)-interpolate(pipe,q) for q in breaks]
    if diffs[0] < 0 or diffs[-1] > 0:
        raise DataError('PUMP_CROSS','实测区间内无工况交点')
    if 0 in diffs:
        flow = breaks[diffs.index(0)]
    else:
        idx = next(i for i,diff in enumerate(diffs) if diff<0)
        q0,q1 = breaks[idx-1],breaks[idx]
        a,b = diffs[idx-1],diffs[idx]
        flow = q0+(q1-q0)*a/(a-b)
    head = interpolate(pipe,flow)
    proof = [('工况扬程',f'{head:.3f}','米'),('交点求解段',f'{q0:.2f}–{q1:.2f}','立方米/时')]
    proof.extend((f'{name} 单泵流量',f'{interpolate(curve,head):.3f}','立方米/时') for name,curve in sorted(pumps.items()))
    return flow.quantize(D('0.001')), proof
