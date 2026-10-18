"""One metadata-only BT2390 standard-offset/mastering-black preflight.

Independent formula expression with standard knee_offset=.5, not libplacebo's
modified default1. No parameter grid, population comparison or official claim.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f


def prepare(meta):
    lo, hi = f.pq_inverse(.005), meta['l1'][2]
    outlo, outhi = f.pq_inverse(0), f.pq_inverse(meta['peak'])
    a, b = (outlo-lo)/(hi-lo), (outhi-lo)/(hi-lo)
    return {'lo': lo, 'hi': hi, 'a': a, 'b': b, 'knee': 1.5*b-.5,
            'gain': 1/(1+a/b*(1-b)**4) if b < 1 else 1,
            'outlo': outlo, 'outhi': outhi}


def transfer(curve, q):
    x = (q-curve['lo'])/(curve['hi']-curve['lo'])
    x = min(1., max(0., x))
    k = curve['knee']
    if x >= k and k < 1:
        t = (x-k)/(1-k)
        x = (2*t**3-3*t*t+1)*k + (t**3-2*t*t+t)*(1-k) + (-2*t**3+3*t*t)*curve['b']
    if x < 1:
        x += curve['a']*(1-x)**4
        x = curve['gain']*(x-curve['a'])+curve['a']
    q = curve['lo'] + (curve['hi']-curve['lo'])*x
    if not math.isfinite(q):
        raise ValueError('nonfinite EETF')
    return min(curve['outhi'], max(curve['outlo'], q))


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise FileExistsError('retained receipt exists')
    root = Path(__file__).resolve().parents[4]
    report = {'schema': 'hdr.astra362.bt2390-preflight.v1',
              'status': 'synthetic neutral transfer only; no official or accuracy claim',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'adapter_sha256': hashlib.sha256(Path(f.__file__).read_bytes()).hexdigest(),
              'constants': {'knee_offset': .5, 'black_power': 4},
              'extension': 'actual scalar PQ pre-SOP, declared mastering black, L1max inputpeak; output interval clamp',
              'native_requests': 0, 'renders': 0, 'tests': 0, 'holdout_access': False, 'shots': {}}
    for shot in ('256', '714'):
        raw = (root / ('fable_eval_' + shot + '_driver.json')).read_bytes()
        meta = json.loads(raw)['meta']
        cv = prepare(meta)
        old = f.grid_curve(meta['l1'], meta['peak'], 'mast', 'mob')[1]
        probes = []
        for nits in (0., .005, .01, .1, 1., 1.476, 3., 10., 30., 100., 300., 600., 1700.):
            q = f.sop_pq(f.pq_inverse(nits), meta['sop'])
            new = f.pq_eotf(transfer(cv, q))
            prior = max(0., f.pm.rational_eval(old['coefficients'], f.pq_eotf(q)))
            new = f._colour_only((new,) * 3, meta)[0]
            prior = f._colour_only((prior,) * 3, meta)[0]
            probes.append({'source_nits': nits, 'bt2390_nits': new,
                           'selected_nits': prior,
                           'delta720PQ': 720*(f.pq_inverse(new)-f.pq_inverse(prior))})
        report['shots'][shot] = {'metadata': meta,
            'metadata_receipt_sha256': hashlib.sha256(raw).hexdigest(),
            'prepared': cv, 'probes': probes}
        print(shot, json.dumps(probes))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
