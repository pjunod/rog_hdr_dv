"""US9613407B2 0048-0062/Table2 automatic curve in a named open hybrid.

Not identified Dolby CM. Constant endpoint extension, scalar PQ-Y placement,
W post-SOP and post-ratio CW/SG are explicit composition decisions. No fitting.
Linear BT2020 RGB in nits; the caller owns ONE final physical gamut clip.
"""
import math

from tools.dolby_harness.metric import pq_inverse, pq_eotf
from tools.dolby_harness.public_mapping import BT2020_WEIGHTS, color_transform, solve3

ALGORITHM = 'us961-sqrtsum-pq-y-post-v1'
REPRESENTATION = 'positive-weight-powered-anchor-v1'


def prepare(l1, source_min, source_max, target_min, target_max):
    """Original declared mastering/display bounds, not reconstructed pixels."""
    values = (*l1, source_min, source_max, target_min, target_max)
    if (len(l1) != 3 or not all(math.isfinite(v) for v in values) or
            not 0 <= l1[0] < l1[1] < l1[2] <= 1 or
            not 0 <= source_min < source_max <= 10000 or
            not 0 <= target_min < target_max <= 10000):
        raise ValueError('strict ordered physical L1/display declarations required')
    smin, smax = map(pq_inverse, (source_min, source_max))
    tmin, tmax = map(pq_inverse, (target_min, target_max))
    ratio = min(1., math.sqrt((tmax + tmin) / (smax + smin)))
    rolloff, screen_ratio = 1. / 3., 1.
    slope = math.sqrt(1. / ratio)
    crush, mid, clip = l1
    key = 2 * (mid - crush) / (clip - crush)
    shift = mid * (1 - ratio) * key
    ys = (max(crush - shift, tmin), mid - shift, min(clip - shift, tmax))
    if not 0 <= ys[0] < ys[1] < ys[2] <= 1:
        raise ValueError('unsupported automatic target anchors')
    n = slope / rolloff
    z = tuple((x / clip) ** n for x in l1)
    w = tuple(y ** (1 / rolloff) for y in ys)
    if not 0 <= z[0] < z[1] < z[2] or not 0 <= w[0] < w[1] < w[2]:
        raise ValueError('powered anchors collapse at binary64 precision')
    tm = (z[1] - z[0]) / (z[2] - z[0])
    k = (w[1] - w[0]) * (1 - tm) / ((w[2] - w[1]) * tm)
    if not math.isfinite(k) or k <= 0:
        raise ValueError('nonpositive/nonfinite rational anchor weight')
    # Direct coefficient closure is evidence only; evaluation uses positive
    # anchor weights to avoid cancellation near a zero powered output anchor.
    xx = [x ** n for x in l1]
    coefficients = solve3([(1., x, -x*y) for x, y in zip(xx, w)], w)
    return dict(algorithm=ALGORITHM, representation=REPRESENTATION,
                ratio=ratio, slope=slope, screen_ratio=screen_ratio, key=key,
                shift=shift, rolloff=rolloff, n=n, source_anchors=list(l1),
                target_anchors=list(ys), coefficients=list(coefficients),
                normalized_powered_source=list(z), powered_target=list(w), weight=k,
                source_display_nits=[source_min, source_max],
                target_display_nits=[target_min, target_max],
                source_display_PQ=[smin, smax], target_display_PQ=[tmin, tmax],
                endpoint_extension='NONLITERAL q<=Crush:targetMin; q>=Clip:targetMax',
                proof='positive k; ordered powered anchors; convex nonnegative numerator; positive denominator; positive derivative')


def curve_eval(q, curve, counters=None):
    if not math.isfinite(q) or not 0 <= q <= 1:
        raise ValueError('automatic input outside physical PQ domain')
    def count(name):
        if counters is not None:
            counters[name] = counters.get(name, 0) + 1
    lo, _, hi = curve['source_anchors']
    if q <= lo:
        count('lower_endpoint')
        return curve['target_anchors'][0]
    if q >= hi:
        count('upper_endpoint')
        return curve['target_anchors'][2]
    count('interior')
    z0, _, z2 = curve['normalized_powered_source']
    t = ((q / hi) ** curve['n'] - z0) / (z2 - z0)
    if not math.isfinite(t) or not 0 <= t <= 1:
        raise ValueError('powered coordinate outside anchor interval')
    w0, _, w2 = curve['powered_target']
    k = curve['weight']
    den = (1 - t) + k*t
    base = (w0*(1 - t) + k*w2*t) / den
    if not math.isfinite(base) or base < 0 or den <= 0:
        raise ValueError('negative/nonfinite fractional-power base or pole')
    mapped = base ** curve['rolloff']
    if not math.isfinite(mapped) or not 0 <= mapped <= 1:
        raise ValueError('automatic output outside physical PQ domain')
    return mapped


def evaluate(rgb, curve, sop, color, counters=None):
    if (len(rgb) != 3 or not all(math.isfinite(v) and 0 <= v <= 10000 for v in rgb) or
            len(sop) != 3 or not all(math.isfinite(v) for v in sop) or
            not .5 <= sop[0] <= 1.5 or not -.5 <= sop[1] <= .5 or not .5 <= sop[2] <= 1.5 or
            len(color) != 2 or not all(math.isfinite(v) and -.5 <= v <= .5 for v in color)):
        raise ValueError('unsupported source RGB/SOP/color')
    y = sum(w * v for w, v in zip(BT2020_WEIGHTS, rgb))
    if y == 0:
        if counters is not None:
            counters['zero_Y'] = counters.get('zero_Y', 0) + 1
        return (0., 0., 0.)
    q = curve_eval(pq_inverse(y), curve, counters)
    s, o, p = sop
    affine = s*q + o
    power = max(0., affine) ** p
    qt = max(1e-5, power)
    if not math.isfinite(qt) or not 0 <= qt <= 1:
        raise ValueError('scalar SOP outside physical PQ domain')
    if counters is not None:
        for name, active in (('affine_negative', affine < 0), ('power_floor', power < 1e-5)):
            counters[name] = counters.get(name, 0) + int(active)
    mapped_y = pq_eotf(qt)
    restored = tuple(v * mapped_y / y for v in rgb)
    if not all(math.isfinite(v) and 0 <= v <= 10000 for v in restored):
        raise ValueError('restored RGB outside physical PQ domain')
    qrgb = color_transform(tuple(pq_inverse(v) for v in restored), BT2020_WEIGHTS, *color)
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in qrgb):
        raise ValueError('post-color RGB outside physical PQ domain')
    return tuple(pq_eotf(v) for v in qrgb)
