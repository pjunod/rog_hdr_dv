"""Metadata-only forward/inverse HK coordinate preflight, not a pixel comparison.

US10540920B2 Eq1,15-17 define K=I+.202*hypot(P,T) and chroma
normalisation (1/K+.5). Its algebraic inverse removes HK AFTER undoing
normalisation. This is a declared hybrid with the existing MB intensity curve,
not identification of Dolby's official chain. No parameters fit reference data.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astra356_ipt as ip

f, pm = ip.f, ip.pm
ALPHA = .202


def forward(i, p, t):
    k = i + ALPHA * math.hypot(p, t)
    if not 0 < k <= 1:
        raise ValueError('HK coordinate outside positive unit domain')
    scale = 1 / k + .5
    return k, p * scale, t * scale


def inverse(j, p, t):
    if not 0 < j <= 1:
        raise ValueError('mapped HK coordinate outside positive unit domain')
    scale = 1 / j + .5
    p, t = p / scale, t / scale
    return j - ALPHA * math.hypot(p, t), p, t


def main():
    out = Path(sys.argv[1])
    if out.exists():
        raise FileExistsError('Retained receipt exists')
    # Metadata only; do not load development pixels or inspect any holdout.
    metas = {
        '256': {'l1': (0., .290273, .879591), 'peak': 600.},
        '714': {'l1': (.0196536, .272, .853468), 'peak': 600.},
    }
    report = {'schema': 'hdr.astra360.hk-preflight.v1',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'alpha': ALPHA, 'basis': 'analytic synthetic coordinate probes, not measured accuracy',
              'definition': 'F(I,P,T)=(K,P*(1/K+.5),T*(1/K+.5)); K=I+.202*hypot(P,T); inverse exact',
              'tests': 0, 'native_requests': 0, 'renders': 0, 'holdout_access': False,
              'roundtrip_max_abs': 0., 'shots': {}}
    for shot, meta in metas.items():
        cv = f.grid_curve(meta['l1'], meta['peak'], 'mast', 'mob')[1]
        def mapping(q):
            v = max(0., pm.rational_eval(cv['coefficients'], f.pq_eotf(q)))
            if not 0 <= v <= 10000:
                raise ValueError('mapped intensity outside PQ domain')
            return f.pq_inverse(v)
        rows = []
        # Fixed synthetic colours probe the coordinate direction, not curve coefficients.
        for nits in (.01, .1, 1., 3., 10., 30., 100., 300., 600., 1700.):
            i = f.pq_inverse(nits)
            for relative_chroma in (0., .1, .3):
                p, t = relative_chroma * i, 0.
                k, pn, tn = forward(i, p, t)
                back = inverse(k, pn, tn)
                err = max(abs(a-b) for a,b in zip((i,p,t), back))
                report['roundtrip_max_abs'] = max(report['roundtrip_max_abs'], err)
                j = mapping(k)
                mapped = inverse(j, pn, tn)
                plain_j = mapping(i)
                rows.append({'synthetic_intensity_nits': nits,
                             'synthetic_chroma_over_I': relative_chroma,
                             'input_HK': k, 'mapped_HK': j,
                             'inverse_I': mapped[0],
                             'delta720_IPT_I_vs_noHK': 720*(mapped[0]-plain_j),
                             'forward_only_delta720_IPT_I': 720*(j-plain_j),
                             'gain': (1/k+.5)/(1/j+.5),
                             'inverse_I_valid': 0 <= mapped[0] <= 1})
        report['shots'][shot] = {'metadata': meta, 'curve': cv, 'probes': rows}
    if report['roundtrip_max_abs'] > 1e-14:
        raise ArithmeticError('coordinate roundtrip failed')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
