"""Metadata-only transfer preflight for MB rational + normalized target-PQ post SOP.

No reference pixels, fitting, native request or image comparison. Metadata is
loaded from existing diagnostic receipts; the candidate remains unpromoted.
Usage: python3 astra356_normalization.py EVIDENCE_DIR OUTPUT.json
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f


def preflight(meta):
    curve = f.grid_curve(meta['l1'], meta['peak'], 'mast', 'mob')[1]
    s, o, p = meta['sop']
    a, b = f.pq_inverse(0), f.pq_inverse(meta['peak'])
    span = b - a
    rows = []
    for y in (0., .005, .01, .1, 1., 3., 10., 30., 100., 300., 600., 1000.):
        # Current selected scalar transfer, without color (neutral-axis check).
        z = f.pq_eotf(f.sop_pq(f.pq_inverse(y), meta['sop']))
        pre = max(0., f.pm.rational_eval(curve['coefficients'], z)) if y else 0.
        base = max(0., f.pm.rational_eval(curve['coefficients'], y))
        q = f.pq_inverse(base)
        un = (q - a) / span
        normalized = a + span * max(0., s * un + o) ** p
        absolute = max(0., s * q + o) ** p
        rows.append({'source_nits': y, 'selected_pre_nits': pre,
                     'normalized_post_nits': f.pq_eotf(normalized),
                     'absolute_post_nits': f.pq_eotf(absolute),
                     'normalized_minus_selected_720PQ': 720 * (normalized - f.pq_inverse(pre)),
                     'absolute_minus_selected_720PQ': 720 * (absolute - f.pq_inverse(pre))})
    return {'curve': curve, 'sop': meta['sop'], 'target_pq_span': span, 'points': rows}


def main():
    evidence, output = Path(sys.argv[1]), Path(sys.argv[2])
    report = {'schema': 'hdr.astra356.normalization-preflight.v1',
              'status': 'metadata-only neutral transfer; not measured deltaEITP',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'shots': {}}
    for shot in ('256', '714'):
        raw = (evidence / ('fable_eval_' + shot + '_driver.json')).read_bytes()
        meta = json.loads(raw)['meta']
        report['shots'][shot] = {'input_receipt_sha256': hashlib.sha256(raw).hexdigest(),
                                 **preflight(meta)}
        print(shot, json.dumps(report['shots'][shot]['points']), flush=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
