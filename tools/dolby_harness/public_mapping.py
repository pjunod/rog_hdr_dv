"""Independently expressed public RGB mapping hypotheses (not Dolby CM identity).

Only mathematical descriptions inform this utility; GPL implementation source is
not imported. Whole stage contracts are kept separate, with explicit finite
extensions and target-black policy. All RGB here is linear BT.2020 in nits.
"""
import math
from fractions import Fraction

from tools.dolby_harness.metric import pq_eotf, pq_inverse

BAKER_WEIGHTS = (0.22897, 0.69174, 0.07929)
BT2020_WEIGHTS = (0.2627, 0.6780, 0.0593)


def xml_lgg_coefficients(controls, convention):
    """Finite declared XML convention hypotheses, never a fitted scale.

    Wire-continuous composes the pinned serializer/public decoder algebra.
    Direct LGG is a neutral-preserving authoring-unit hypothesis only, not
    established official XML pixel semantics. Input order is L/G/H/C/Q.
    """
    if convention not in ('xml-wire-continuous-v1', 'xml-direct-lgg-hypothesis-v1'):
        raise ValueError('unknown declared XML convention')
    if len(controls) != 5:
        raise ValueError('five original XML controls required')
    values = tuple(Fraction(str(v)) for v in controls)
    if not all(-1 <= v <= 1 for v in values):
        raise ValueError('XML controls outside supported domain')
    unit = Fraction(1, 2) if convention == 'xml-wire-continuous-v1' else Fraction(1)
    lift, gain, gamma = unit * values[0], 1 + unit * values[1], 1 + unit * values[2]
    if gamma <= 0:
        raise ValueError('positive authoring gamma required')
    def clip(v):
        return min(Fraction(1, 2), max(Fraction(-1, 2), v))
    sop = (1 + clip(gain * (1 - lift) - 1), clip(gain * lift), 1 + clip(1 / gamma - 1))
    return {'convention': convention, 'sop': tuple(float(v) for v in sop),
            'color': (float(unit * values[3]), float(unit * values[4])),
            'physical_lgg': tuple(float(v) for v in (lift, gain, gamma)),
            'direct_XML_pixel_semantics_proven': False}


def solve3(rows, rhs):
    """Pivoted three-equation solve; reject singular anchors, never invent them."""
    a = [list(map(float, r)) + [float(y)] for r, y in zip(rows, rhs)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda i: abs(a[i][col]))
        a[col], a[pivot] = a[pivot], a[col]
        if not math.isfinite(a[col][col]) or abs(a[col][col]) < 1e-15:
            raise ValueError('singular rational anchors')
        scale = a[col][col]
        a[col] = [v / scale for v in a[col]]
        for i in range(3):
            if i != col:
                scale = a[i][col]
                a[i] = [u - scale * v for u, v in zip(a[i], a[col])]
    return tuple(a[i][3] for i in range(3))


def rational_prepare(xs, ys):
    if not all(math.isfinite(v) and v >= 0 for v in (*xs, *ys)):
        raise ValueError('nonnegative finite anchors required')
    if not xs[0] < xs[1] < xs[2] or not ys[0] <= ys[1] <= ys[2]:
        raise ValueError('nondegenerate ordered anchors required')
    # a+b*x-c*x*y=y. Scale x to bound conditioning without changing the curve.
    scale = xs[2]
    rows = [(1, x / scale, -x * y / scale) for x, y in zip(xs, ys)]
    a, b, c = solve3(rows, ys)
    b, c = b / scale, c / scale
    if not all(math.isfinite(v) for v in (a, b, c)) or b - a * c < 0:
        raise ValueError('nonfinite or descending rational curve')
    if min(1, 1 + c * xs[2]) <= 0:
        raise ValueError('rational pole in source anchor interval')
    return a, b, c


def rational_eval(coeffs, x):
    a, b, c = coeffs
    if not math.isfinite(x) or not 0 <= x <= 10000:
        raise ValueError('RGB nits outside physical input domain')
    if 1 + c * x <= 0:
        raise ValueError('rational pole reached outside anchor interval')
    y = (a + b * x) / (1 + c * x)
    if not math.isfinite(y):
        raise ValueError('nonfinite rational result')
    return y


def color_transform(rgb, weights, chroma_weight, saturation_gain):
    """Continuous zero-channel limit when exponent 1+gain is positive."""
    if not -0.5 <= chroma_weight <= 0.5 or not -0.5 <= saturation_gain <= 0.5:
        raise ValueError('unsupported color coefficient')
    if not all(math.isfinite(v) and v >= 0 for v in rgb):
        raise ValueError('nonnegative finite RGB required')
    if saturation_gain == 0:
        return tuple(rgb)
    y = sum(w * v for w, v in zip(weights, rgb))
    if y == 0:
        return (0.0, 0.0, 0.0)
    return tuple(0.0 if v == 0 else v * ((1 + chroma_weight) * v / y) ** saturation_gain
                 for v in rgb)


def baker_prepare(l1, target_black, target_peak):
    # Source's floor is part of this hypothesis, not an altered target declaration.
    black = min(5.0, max(0.00001, target_black))
    peak = min(10000.0, max(5.0, target_peak))
    xs = tuple(pq_eotf(v) for v in l1)
    ys = (black, math.sqrt(xs[1] * math.sqrt(black * peak)), peak)
    return {'coefficients': rational_prepare(xs, ys), 'source_anchors': xs,
            'mapped_anchors': ys, 'declared_black': target_black,
            'effective_black': black, 'peak': peak}


def baker(rgb, curve, sop, color):
    s, o, p = sop
    peak = curve['peak']
    base = tuple(rational_eval(curve['coefficients'], v) for v in rgb)
    mapped = tuple(peak * min(1.0, max(0.0, s * v / peak + o)) ** p for v in base)
    return color_transform(mapped, BAKER_WEIGHTS, *color)


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def mpc_prepare(l1, target_peak):
    peak = pq_eotf(l1[2])
    if target_peak >= peak:
        return {'identity': True, 'peak': target_peak}
    # CPU call site supplies scene minimum to the shader's misleadingly named
    # MasteringMinLuminanceNits. Our adaptation keeps continuous L1, not UINT nits.
    black = pq_eotf(l1[0])
    lo, hi = l1[0], l1[2]
    dstlo, dsthi = pq_inverse(0), pq_inverse(target_peak)
    if lo >= hi:
        raise ValueError('scene minimum exceeds scene maximum')
    src = min(lo + 0.8 * (hi - lo), max(lo + 0.1 * (hi - lo), l1[1]))
    t = (src - lo) / (hi - lo)
    adaptation = 0.4 + 0.6 * (1 - smoothstep(0.8, 0.4, t) * smoothstep(0.1, 0.4, t))
    dst = src + adaptation * (dstlo + t * (dsthi - dstlo) - src)
    dst = min(dstlo + 0.8 * (dsthi - dstlo), max(dstlo + 0.1 * (dsthi - dstlo), dst))
    xs = (black, pq_eotf(src), peak)
    ys = (0.0, pq_eotf(dst), target_peak)
    return {'identity': False, 'coefficients': rational_prepare(xs, ys),
            'source_anchors': xs, 'mapped_anchors': ys, 'peak': target_peak}


def mpc(rgb, curve, sop, color, weights=BT2020_WEIGHTS):
    s, o, p = sop
    # Explicit finite extension: negative affine bases clamp BEFORE noninteger pow.
    q = tuple(max(0.00001, max(0.0, s * pq_inverse(v) + o) ** p) for v in rgb)
    q = color_transform(q, weights, *color)
    if any(v > 1 for v in q):
        raise ValueError('trimmed PQ exceeds physical domain')
    rgb = tuple(pq_eotf(v) for v in q)
    if curve['identity']:
        return rgb
    y = sum(w * v for w, v in zip(weights, rgb))
    if y == 0:
        return (0.0, 0.0, 0.0)
    mapped = max(0.0, rational_eval(curve['coefficients'], y))
    return tuple(v * mapped / y for v in rgb)


def rgb_matrix(primaries):
    xyz = tuple((x / y, 1.0, (1 - x - y) / y) for x, y in primaries[:3])
    wx, wy = primaries[3]
    rows = tuple(zip(*xyz))
    scales = solve3(rows, (wx / wy, 1, (1 - wx - wy) / wy))
    return tuple(tuple(v * s for v, s in zip(row, scales)) for row in rows)


def mpc_post(rgb, curve, sop, color):
    """Disclosed curve->SOP order adaptation; not MPC application reproduction."""
    y = sum(w * v for w, v in zip(BT2020_WEIGHTS, rgb))
    if not curve['identity'] and y > 0:
        scale = max(0.0, rational_eval(curve['coefficients'], y)) / y
        rgb = tuple(v * scale for v in rgb)
    s, o, p = sop
    q = tuple(max(0.00001, max(0.0, s * pq_inverse(v) + o) ** p) for v in rgb)
    q = color_transform(q, BT2020_WEIGHTS, *color)
    return tuple(pq_eotf(v) for v in q)


def mpc_pre_y(rgb, curve, sop, color):
    """Scalar PQ-Y trim adaptation; retains M's exact neutral transfer."""
    if color[1] != 0:
        raise ValueError('Y-only discrimination requires neutral saturation')
    y = sum(w * v for w, v in zip(BT2020_WEIGHTS, rgb))
    if y == 0:
        return (0.0, 0.0, 0.0)
    s, o, p = sop
    qt = max(0.00001, max(0.0, s * pq_inverse(y) + o) ** p)
    yt = pq_eotf(qt)
    mapped = yt if curve['identity'] else max(0.0, rational_eval(curve['coefficients'], yt))
    return tuple(v * mapped / y for v in rgb)


def mpc_mastblack_prepare(l1, target_peak, mastering_black):
    """Frozen zero-low knee and declared mastering-black nits anchor."""
    if (not all(math.isfinite(v) and 0 <= v <= 1 for v in l1) or
            not l1[0] <= l1[1] <= l1[2] or l1[0] >= l1[2]):
        raise ValueError('ordered nondegenerate L1 required')
    if (not math.isfinite(mastering_black) or not 0 <= mastering_black <= 10000 or
            not math.isfinite(target_peak) or not 0 < target_peak <= 10000):
        raise ValueError('explicit finite mastering black and target peak required')
    curve = mpc_prepare((0.0, l1[1], l1[2]), target_peak)
    if curve['identity']:
        return curve
    xs = (mastering_black, *curve['source_anchors'][1:])
    curve.update(source_anchors=xs,
                 coefficients=rational_prepare(xs, curve['mapped_anchors']))
    a, b, c = curve['coefficients']
    if min(1, 1 + c * 10000) <= 0 or b - a * c < 0:
        raise ValueError('invalid physical-domain mastering-black rational')
    return curve


def mpc_pre_y_mastblack(rgb, curve, sop, color, counters=None):
    """PQ(Y) SOP/rational -> restore RGB ratios -> actual PQ color.

    Raw BT2020 nits output; the existing single physical gamut stage follows.
    """
    if not all(math.isfinite(v) and 0 <= v <= 10000 for v in rgb):
        raise ValueError('nonnegative finite RGB nits required')
    s, o, p = sop
    if not all(math.isfinite(v) for v in sop) or p <= 0 or s + o > 1:
        raise ValueError('scalar SOP outside physical PQ domain')
    y = sum(w * v for w, v in zip(BT2020_WEIGHTS, rgb))
    if y > 0:
        affine = s * pq_inverse(y) + o
        power = max(0.0, affine) ** p
        q = max(1e-5, power)
        if not math.isfinite(q) or q > 1:
            raise ValueError('trimmed scalar PQ exceeds physical domain')
        yt = pq_eotf(q)
        raw = yt if curve['identity'] else rational_eval(curve['coefficients'], yt)
        mapped = max(0.0, raw)
        rgb = tuple(v * mapped / y for v in rgb)
        if counters is not None:
            for key, active in (('affine_negative', affine < 0),
                                ('pq_floor', power < 1e-5),
                                ('rational_negative', raw < 0)):
                counters[key] = counters.get(key, 0) + int(active)
    else:
        rgb = (0.0, 0.0, 0.0)
    if any(v > 10000 for v in rgb):
        raise ValueError('restored RGB exceeds physical PQ domain')
    q = color_transform(tuple(pq_inverse(v) for v in rgb), BT2020_WEIGHTS, *color)
    if any(not math.isfinite(v) or v > 1 for v in q):
        raise ValueError('post-ratio color PQ exceeds physical domain')
    return tuple(pq_eotf(v) for v in q)


def mpc_post_normalized_y(rgb, curve, sop, color, counters=None):
    """Eq6/5/7 scalar post-curve adaptation, not the complete patent model.

    No MPC PQ floor, source-black subtraction, or internal target clipping.
    The caller owns the existing final physical-volume policy.
    """
    if color[1] != 0:
        raise ValueError('normalized Y discrimination requires neutral saturation')
    if not all(math.isfinite(v) and 0 <= v <= 10000 for v in rgb):
        raise ValueError('nonnegative finite RGB nits required')
    s, o, p = sop
    if not all(math.isfinite(v) for v in sop) or p <= 0:
        raise ValueError('finite SOP and positive power required')
    peak = curve['peak']
    if not math.isfinite(peak) or not 0 < peak <= 10000:
        raise ValueError('physical positive target peak required')
    y = sum(w * v for w, v in zip(BT2020_WEIGHTS, rgb))
    if y == 0:
        return (0.0, 0.0, 0.0)
    base = y if curve['identity'] else rational_eval(curve['coefficients'], y)
    if not 0 <= base <= 10000:
        raise ValueError('mapped Y outside physical PQ input domain')
    lo, hi = pq_inverse(0), pq_inverse(peak)
    u = (pq_inverse(base) - lo) / (hi - lo)
    affine = s * u + o
    if counters is not None:
        for name, active in (('affine_negative', affine < 0),
                             ('normalized_u_outside_target', not 0 <= u <= 1)):
            counters[name] = counters.get(name, 0) + int(active)
    q = lo + (hi - lo) * max(0.0, affine) ** p
    if not math.isfinite(q) or not 0 <= q <= 1:
        raise ValueError('trimmed PQ outside physical domain')
    mapped = pq_eotf(q)
    result = tuple(v * mapped / y for v in rgb)
    if not all(math.isfinite(v) and v >= 0 for v in result):
        raise ValueError('nonfinite normalized Y result')
    return result


def inverse_matrix(matrix):
    columns = [solve3(matrix, tuple(float(i == j) for i in range(3))) for j in range(3)]
    return tuple(zip(*columns))


def mpc_pre_ipt(rgb, curve, sop, color, matrices, counters=None):
    """M neutral scalar transfer in the disclosed IPT/Eq8 chroma composition.

    Renderer-specific frozen forward matrices, not a patent-matrix identity.
    Returns raw RGB; a single declared physical-target policy must follow.
    """
    if color[1] != 0:
        raise ValueError('IPT discrimination requires neutral saturation')
    if not all(math.isfinite(v) and 0 <= v <= 10000 for v in rgb):
        raise ValueError('nonnegative finite RGB nits required')
    lms = apply_matrix(matrices['rgb2lms'], rgb)
    ipt = apply_matrix(matrices['lms2ipt'], tuple(pq_inverse(v) for v in lms))
    intensity = ipt[0]
    s, o, p = sop
    if not all(math.isfinite(v) for v in sop) or p <= 0:
        raise ValueError('finite SOP and positive power required')
    affine = s * intensity + o
    z = max(1e-5, max(affine, 0.0) ** p)
    value = pq_eotf(z)
    mapped = value if curve['identity'] else max(0.0, rational_eval(curve['coefficients'], value))
    j = pq_inverse(mapped)
    k = 1 + j - intensity
    lmspq = apply_matrix(matrices['ipt2lms'], (j, k * ipt[1], k * ipt[2]))
    if not all(math.isfinite(v) and v <= 1 for v in lmspq):
        raise ValueError('inverse LMS-PQ exceeds physical domain')
    if counters is not None:
        counters['affine_negative'] = counters.get('affine_negative', 0) + int(affine < 0)
        counters['pq_floor'] = counters.get('pq_floor', 0) + int(z == 1e-5)
        counters['negative_inverse_lms_pq'] = counters.get('negative_inverse_lms_pq', 0) + sum(v < 0 for v in lmspq)
        counters['inverse_lms_pq_below_black'] = counters.get('inverse_lms_pq_below_black', 0) + sum(v < pq_inverse(0) for v in lmspq)
        counters['k_min'] = min(counters.get('k_min', k), k)
        counters['k_max'] = max(counters.get('k_max', k), k)
    linear_lms = tuple(pq_eotf(max(v, pq_inverse(0))) for v in lmspq)
    result = apply_matrix(matrices['lms2rgb'], linear_lms)
    if not all(math.isfinite(v) for v in result):
        raise ValueError('nonfinite inverse RGB')
    return result


def convert_matrix(source, target):
    a, b = rgb_matrix(source), rgb_matrix(target)
    columns = [solve3(b, col) for col in zip(*a)]
    return tuple(zip(*columns))


def apply_matrix(matrix, rgb):
    return tuple(sum(x * y for x, y in zip(row, rgb)) for row in matrix)
