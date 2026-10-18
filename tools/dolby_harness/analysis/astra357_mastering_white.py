"""Metadata-only source-display-white versus scene-L1-white preparation check.

US8593480B1 describes source display black/white anchors. This keeps the selected
MB knee/trim hypothesis but uses declared mastering4000nit as the white bound.
It is not an official mapper or a claim of reproducing the complete patent.
No images, fitted parameters, tests, native requests or holdouts.
Usage: python3 astra357_mastering_white.py EVIDENCE_DIR OUTPUT.json
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f


def transfer(curve, sop, y):
    if y == 0:
        return 0.
    trimmed = f.pq_eotf(f.sop_pq(f.pq_inverse(y), sop))
    return max(0., f.pm.rational_eval(curve['coefficients'], trimmed))


def main():
    evidence, output = map(Path, sys.argv[1:])
    report = {'schema': 'hdr.astra357.mastering-white-preflight.v1',
              'status': 'metadata-only neutral transfer, not measured deltaEITP',
              'declared_mastering_black_nits': .005,
              'declared_mastering_white_nits': 4000.,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'frontend_sha256': hashlib.sha256(Path(f.pm.__file__).read_bytes()).hexdigest(),
              'shots': {}}
    for shot in ('256', '714'):
        raw = (evidence / ('fable_eval_' + shot + '_driver.json')).read_bytes()
        meta = json.loads(raw)['meta']
        source_l1 = tuple(meta['l1'])
        hypothetical_driver = (*source_l1[:2], f.pq_inverse(4000.))
        base = f.pm.mpc_mastblack_prepare(source_l1, meta['peak'], .005)
        candidate = f.pm.mpc_mastblack_prepare(hypothetical_driver, meta['peak'], .005)
        rows = []
        for y in (0., .005, .01, .1, 1., 3., 10., 30., 100., 300., 600., 1000., 1700., 2500., 4000.):
            a, b = transfer(base, meta['sop'], y), transfer(candidate, meta['sop'], y)
            rows.append({'source_nits': y, 'selected_nits': a, 'mastering_white_nits': b,
                         'difference_720PQ': 720 * (f.pq_inverse(b) - f.pq_inverse(a))})
        report['shots'][shot] = {'input_receipt_sha256': hashlib.sha256(raw).hexdigest(),
                                'original_metadata_unchanged': meta,
                                'hypothetical_preparation_driver': hypothetical_driver,
                                'selected_curve': base, 'mastering_white_curve': candidate,
                                'neutral_transfer_points': rows}
        print(shot, json.dumps(rows), flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
