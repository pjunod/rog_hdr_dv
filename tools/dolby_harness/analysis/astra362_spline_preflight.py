"""Metadata-only mastering-black/default spline transfer preflight.

A new declared hybrid, not a native library or official Dolby pipeline. Keeps
actual L1 avg/max, mastering black .005 nit and all documented spline defaults.
No population inputs, fitting, native work, renderer changes or holdout access.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f


def prepare(meta):
    l1 = meta['l1']
    # Source min for this hypothesis is mastering black, not altered metadata.
    return f.spline_prepare((f.pq_inverse(.005), l1[1], l1[2]), meta['peak'])


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise FileExistsError('retained receipt exists')
    root = Path(__file__).resolve().parents[4]
    report = {
        'schema': 'hdr.astra362.mastering-spline-preflight.v1',
        'status': 'synthetic neutral transfer only, not image accuracy',
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'adapter_sha256': hashlib.sha256(Path(f.__file__).read_bytes()).hexdigest(),
        'source_contract': 'libplacebo tone_mapping.c spline/st2094_pick_knee defaults; explicit mastering-black hybrid',
        'constants': f.SPLINE_CONST, 'mastering_black_nits': .005,
        'native_requests': 0, 'renders': 0, 'tests': 0, 'holdout_access': False,
        'shots': {},
    }
    for shot in ('256', '714'):
        raw = (root / ('fable_eval_' + shot + '_driver.json')).read_bytes()
        meta = json.loads(raw)['meta']
        curve = prepare(meta)
        old = f.grid_curve(meta['l1'], meta['peak'], 'mast', 'mob')[1]
        probes = []
        for nits in (0., .005, .01, .1, 1., 1.476, 3., 10., 30., 100., 300., 600., 1700.):
            q = f.sop_pq(f.pq_inverse(nits), meta['sop'])
            new_nits = f.pq_eotf(f.spline_eval(curve, q))
            old_nits = max(0., f.pm.rational_eval(old['coefficients'], f.pq_eotf(q)))
            # Actual CW/SG on a neutral after ratio restoration. This is not
            # an assumption that CW/SG can be omitted from chromatic pixels.
            new_rgb = f._colour_only((new_nits,) * 3, meta)
            old_rgb = f._colour_only((old_nits,) * 3, meta)
            probes.append({'source_nits': nits, 'spline_neutral_nits': new_rgb,
                           'selected_neutral_nits': old_rgb,
                           'delta720PQ': [720 * (f.pq_inverse(a) - f.pq_inverse(b))
                                          for a, b in zip(new_rgb, old_rgb)]})
        report['shots'][shot] = {
            'metadata_receipt_sha256': hashlib.sha256(raw).hexdigest(),
            'metadata': meta, 'curve': curve, 'probes': probes,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    for shot, data in report['shots'].items():
        print(shot, json.dumps(data['probes']))


if __name__ == '__main__':
    main()
