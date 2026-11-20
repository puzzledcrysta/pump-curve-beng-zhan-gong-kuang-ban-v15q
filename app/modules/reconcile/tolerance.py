from decimal import Decimal as D

# 外部账只给四舍五入后的显示值：真实值 x 满足 |x - 显示值| <= 步长/2。
# 复算流量视为精确值，按 复算 - 外部 计算差值，差值区间随外部区间对称展开。
HALF = D('0.5')


def step_width(step):
    """舍入步长的半宽，即外部真实值相对显示值的最大偏移。"""
    if step <= 0:
        raise ValueError('舍入步长必须为正数')
    return step * HALF


def delta_band(amount, reference, step):
    """返回复算与外部真实值之间差值的闭区间 [下限, 上限]。"""
    half = step_width(step)
    point = amount - reference
    return point - half, point + half


def verdict(amount, reference, step, tolerance):
    """按差值区间与允差线的位置给出签认判定。

    TOL_OK   区间整体落在允差内，可按显示值签认；
    TOL_HOLD 区间跨过允差线，无法判定是否超差，等精测后再签；
    TOL_OVER 区间整体超出允差，确定超差，不得签认。
    """
    lower, upper = delta_band(amount, reference, step)
    if abs(upper) <= tolerance and abs(lower) <= tolerance:
        return 'TOL_OK'
    if abs(lower) > tolerance and abs(upper) > tolerance:
        return 'TOL_OVER'
    return 'TOL_HOLD'
