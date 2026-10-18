"""US10540920B2 Table2 metadata-only powered-curve preflight.

Distinct from US9961237's display-midpoint construction. Fixed disclosed
Rolloff=1/3; no fitted parameters, reference pixels or population comparison.
Source display .005/4000 nits is the retained original mastering contract.
Neutral absolute-PQ post-SOP is an explicitly hypothetical composition, not
proof of the official runtime's trim placement or complete color/detail path.
Usage: python3 astra356_powered.py EVIDENCE_DIR PATENT_TEXT OUTPUT.json
"""
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f


def preflight(meta):
    source = tuple(f.pq_inverse(v) for v in (.005, 4000.))
    target = tuple(f.pq_inverse(v) for v in (0., meta['peak']))
    crush, mid, clip = meta['l1']
    ratio = min(1., (target[1] - target[0]) / (source[1] - source[0]))
    slope, rolloff = 1. / ratio, 1. / 3.
    key = (mid - crush) / (clip - crush)
    shift = mid * (1. - ratio) * 2. * key
    xs = (crush, mid, clip)
    ys = (max(crush - shift, target[0]), mid - shift,
          min(clip - shift, target[1]))
    if not 0 <= xs[0] < xs[1] < xs[2] <= 1 or not 0 <= ys[0] < ys[1] < ys[2] <= 1:
        raise ValueError('Invalid source/target anchors')
    n = slope / rolloff
    xx, yy = tuple(x ** n for x in xs), tuple(y ** (1. / rolloff) for y in ys)
    co = f.pm.solve3([(1., x, -x * y) for x, y in zip(xx, yy)], yy)
    a, b, c = co
    if not all(math.isfinite(v) for v in co) or b - a * c <= 0 or min(1., 1. + c) <= 0:
        raise ValueError('Nonmonotonic/pole over entire physical PQ input interval')

    def evaluate(q):
        v = f.pm.rational_eval(co, q ** n)
        if v < 0 or not math.isfinite(v):
            raise ValueError('Invalid powered rational base')
        return v ** rolloff

    residual = [evaluate(x) - y for x, y in zip(xs, ys)]
    if max(abs(v) for v in residual) > 1e-10:
        raise ValueError('Anchor equation inconsistency')
    selected = f.grid_curve(meta['l1'], meta['peak'], 'mast', 'mob')[1]
    rows = []
    for y in (0., .005, .01, .1, 1., 1.476, 3., 10., 30., 100., 300., 600., 1000.):
        q = f.pq_inverse(y)
        try:
            mapped = evaluate(q)
        except ValueError as error:
            # Report the literal source formula's invalid extrapolation. Do
            # not invent a clamp or silently exclude this point from a metric.
            rows.append({'source_nits': y, 'valid': False, 'error': str(error)})
            continue
        trimmed = f.sop_pq(mapped, meta['sop'])
        z = f.pq_eotf(f.sop_pq(q, meta['sop']))
        baseline = max(0., f.pm.rational_eval(selected['coefficients'], z)) if y else 0.
        rows.append({'source_nits': y, 'automatic_nits': f.pq_eotf(mapped),
                     'absolute_post_sop_nits': f.pq_eotf(trimmed),
                     'selected_pre_nits': baseline,
                     'post_minus_selected_720PQ': 720. * (trimmed - f.pq_inverse(baseline))})
    return {'source_display_pq': source, 'target_display_pq': target,
            'ratio': ratio, 'slope': slope, 'rolloff': rolloff, 'n': n,
            'key': key, 'shift': shift, 'source_anchors': xs, 'mapped_anchors': ys,
            'coefficients': co, 'anchor_residual': residual,
            'nonnegative_base_entire_physical_domain': min(a, a + b) >= 0,
            'points': rows}


def main():
    evidence, patent, output = map(Path, sys.argv[1:])
    report = {'schema': 'hdr.astra356.powered-preflight.v1',
              'status': 'metadata-only neutral transfer, not deltaEITP or full chain',
              'source': 'https://patents.google.com/patent/US10540920B2/en',
              'patent_text_sha256': hashlib.sha256(patent.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'shots': {}}
    for shot in ('256', '714'):
        raw = (evidence / ('fable_eval_' + shot + '_driver.json')).read_bytes()
        result = preflight(json.loads(raw)['meta'])
        report['shots'][shot] = {'input_receipt_sha256': hashlib.sha256(raw).hexdigest(), **result}
        print(shot, json.dumps(result), flush=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
