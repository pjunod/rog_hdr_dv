"""BT.2124-0 Annex 1, display-referred PQ BT.2020 RGB only.

No image normalization, gamut clipping, exposure fitting or alignment search.
The supported input domain is [0, 1] PQ; XYZ/negative-light extensions are
intentionally not accepted by this stage-1 image interface.
"""
import math

M1, M2 = 2610 / 16384, 2523 / 32
C1, C2, C3 = 3424 / 4096, 2413 / 128, 2392 / 128


def pq_eotf(code):
    if not math.isfinite(code) or not 0 <= code <= 1:
        raise ValueError('PQ sample outside finite [0,1] domain')
    p = code ** (1 / M2)
    return 10000 * (max(p - C1, 0) / (C2 - C3 * p)) ** (1 / M1)


def pq_inverse(nits):
    if not math.isfinite(nits) or not 0 <= nits <= 10000:
        raise ValueError('luminance outside finite [0,10000] domain')
    p = (nits / 10000) ** M1
    return ((C1 + C2 * p) / (1 + C3 * p)) ** M2


def rgb_to_itp(rgb):
    if len(rgb) != 3:
        raise ValueError('three RGB components required')
    r, g, b = map(pq_eotf, rgb)
    l = pq_inverse((1688 * r + 2146 * g + 262 * b) / 4096)
    m = pq_inverse((683 * r + 2951 * g + 462 * b) / 4096)
    s = pq_inverse((99 * r + 309 * g + 3688 * b) / 4096)
    return ((l + m) / 2,
            (6610 * l - 13613 * m + 7003 * s) / 8192,
            (17933 * l - 17390 * m - 543 * s) / 4096)


def delta_itp(a, b):
    if len(a) != 3 or len(b) != 3 or not all(math.isfinite(x) for x in (*a, *b)):
        raise ValueError('finite ITP triples required')
    return 720 * math.sqrt(math.fsum((x - y) ** 2 for x, y in zip(a, b)))


def summarize(values):
    values = sorted(values)
    if not values or not all(math.isfinite(x) and x >= 0 for x in values):
        raise ValueError('nonempty finite nonnegative differences required')
    # Nearest rank, 1-based; explicitly not interpolated quantiles.
    return {'pixels': len(values), 'mean': math.fsum(values) / len(values),
            'p95': values[math.ceil(0.95 * len(values)) - 1], 'max': values[-1],
            'percentile': 'nearest-rank-ceil(0.95*N)'}


def compare_pixels(a, b):
    if len(a) != len(b) or not a:
        raise ValueError('equal nonempty pixel arrays required')
    return summarize(delta_itp(rgb_to_itp(x), rgb_to_itp(y)) for x, y in zip(a, b))
