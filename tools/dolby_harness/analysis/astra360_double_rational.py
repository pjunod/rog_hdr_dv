"""Metadata-only US10580367 double-rational midpoint preflight.

Literal zero target-black is rejected, not silently repaired. Also reports ONE
explicit domain-extension hypothesis: use source's stated maximum-DR endpoint
.0001 nit internally, retaining original declared target0. No pixel comparison,
parameter fitting or claim that this extension is official/specified.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f


def prepare(l1, effective_black):
    if effective_black <= 0:
        raise ValueError('literal y3/y1 undefined at declared target black zero')
    x1 = max(.0001, min(.005, effective_black))
    x3 = min(10000., max(4000., 600.))
    def knee(lo, hi, q):
        vmin = lo * (hi / lo) ** .15
        vmax = lo * (hi / lo) ** .85
        mid = math.sqrt(vmin * vmax)
        co = f.pm.rational_prepare((.0001, mid, 10000.), (vmin, mid, vmax))
        return f.pm.rational_eval(co, q), {'min': vmin, 'mid': mid, 'max': vmax, 'co': co}
    x2, xc = knee(x1, x3, f.pq_eotf(l1[1]))
    y2, yc = knee(effective_black, 600., x2)
    # The prose defines the white endpoint x3->y3. Pseudocode prints x3->x3;
    # this explicit discrepancy is retained, not silently called literal source.
    xs, ys = (x1, x2, x3), (effective_black, y2, 600.)
    co = f.pm.rational_prepare(xs, ys)
    return {'source': xs, 'target': ys, 'co': co, 'xmid': xc, 'ymid': yc,
            'white_endpoint_policy': 'prose x3->y3, not printed pseudocode x3->x3'}


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise FileExistsError('retained receipt exists')
    report = {'schema': 'hdr.astra360.double-rational-preflight.v1',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source': 'US10580367B2 numeric pseudocode and WO2018132329A1 paragraphs50-51',
              'kind': 'metadata-only synthetic transfer; no accuracy or source-identity claim',
              'extension_assumptions': ['internal positive black .0001 from stated maximumDR',
                                       'white endpoint from prose rather than conflicting pseudocode'],
              'native_requests': 0, 'renders': 0, 'tests': 0, 'holdout_access': False, 'shots': {}}
    root = Path(__file__).resolve().parents[4]
    for shot in ('256', '714'):
        raw = (root / ('fable_eval_' + shot + '_driver.json')).read_bytes()
        meta = json.loads(raw)['meta']
        try:
            prepare(meta['l1'], 0.)
            raise AssertionError('literal zero target unexpectedly valid')
        except ValueError as error:
            literal_error = str(error)
        cv = prepare(meta['l1'], .0001)
        base = f.grid_curve(meta['l1'], meta['peak'], 'mast', 'mob')[1]
        rows = []
        for nits in (0., .005, .01, .1, 1., 1.476, 3., 10., 30., 100., 300., 600., 1700.):
            x = f.pq_eotf(f.sop_pq(f.pq_inverse(nits), meta['sop']))
            mapped = max(0., f.pm.rational_eval(cv['co'], x))
            old = max(0., f.pm.rational_eval(base['coefficients'], x))
            rows.append({'source_nits': nits, 'extension_nits': mapped,
                         'selected_nits': old, 'delta720PQ': 720*(f.pq_inverse(mapped)-f.pq_inverse(old))})
        report['shots'][shot] = {'metadata_receipt_sha256': hashlib.sha256(raw).hexdigest(),
                                'metadata': meta, 'literal_error': literal_error,
                                'extension_curve': cv, 'probes': rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
