"""Declared display endpoints plus fixed content-knee preflight, no image run.

US8593480 display endpoints and libplacebo documented adaptation .4, without
its extra smoothstep tuning, compose an explicit hybrid, not an official rule.
Uses actual shot avg/max to pick the midpoint; .005/4000 displays only supply
rational endpoints. No free coefficient, grid, fit or holdout access.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f


def prepare(meta):
    l1 = meta['l1']
    knee = f.knee_prepare_const((0., l1[1], l1[2]), meta['peak'], adaptation=.4)
    xs = (.005, knee['source_anchors'][1], 4000.)
    ys = (0., knee['mapped_anchors'][1], meta['peak'])
    return {'source_anchors': xs, 'mapped_anchors': ys,
            'coefficients': f.pm.rational_prepare(xs, ys),
            'knee_preparation': knee}


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise FileExistsError('retained receipt exists')
    root = Path(__file__).resolve().parents[4]
    report = {'schema': 'hdr.astra362.display-endpoints-preflight.v1',
              'status': 'metadata-only declared hybrid; not official mapping or acceptance',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'adapter_sha256': hashlib.sha256(Path(f.__file__).read_bytes()).hexdigest(),
              'source_display': {'black': .005, 'white': 4000.},
              'knee_adaptation': .4, 'extra_smoothstep_tuning': False,
              'native_requests': 0, 'renders': 0, 'tests': 0, 'holdout_access': False,
              'shots': {}}
    for shot in ('256', '714'):
        raw = (root / ('fable_eval_' + shot + '_driver.json')).read_bytes()
        meta = json.loads(raw)['meta']
        cv = prepare(meta)
        prior = f.grid_curve(meta['l1'], meta['peak'], 'mast', 'mob')[1]
        probes = []
        for nits in (0., .005, .01, .1, 1., 1.476, 3., 10., 30., 100., 300., 600., 1700.):
            x = f.pq_eotf(f.sop_pq(f.pq_inverse(nits), meta['sop']))
            new = max(0., f.pm.rational_eval(cv['coefficients'], x))
            old = max(0., f.pm.rational_eval(prior['coefficients'], x))
            new = f._colour_only((new,) * 3, meta)[0]
            old = f._colour_only((old,) * 3, meta)[0]
            probes.append({'source_nits': nits, 'new_nits': new, 'selected_nits': old,
                           'delta720PQ': 720*(f.pq_inverse(new)-f.pq_inverse(old))})
        report['shots'][shot] = {'metadata': meta,
            'metadata_receipt_sha256': hashlib.sha256(raw).hexdigest(),
            'curve': cv, 'probes': probes}
        print(shot, json.dumps(probes))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
