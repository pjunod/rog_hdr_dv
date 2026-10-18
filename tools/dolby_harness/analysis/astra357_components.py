"""One frozen per-component MB rational/PQ-trim development diagnostic.

ST2094-10 Annex B.3 supplies componentwise mapping, not this complete hybrid.
The existing MB preparation and absolute-PQ trim are unchanged. No fitting,
new reference, GPU invocation, unit suite or held-out access. Reuses the retained
Fable lattice adapter; 256 reconstructed-source qualification is preserved.
Usage: python3 astra357_components.py OUTPUT.json
"""
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f

NAME = 'mb-component-pqpre-colorpost'


def chain(rgb, meta, prepared, counters):
    """Per channel PQ SOP -> linear MB rational; actual PQ color -> final P3."""
    curve = prepared['g_mast_mob'][1]
    s, o, p = meta['sop']
    mapped = []
    for value in rgb:
        if not math.isfinite(value) or not 0 <= value <= 10000:
            raise ValueError('input RGB outside PQ domain')
        affine = s * f.pq_inverse(value) + o
        if affine > 1:
            raise ValueError('component SOP above PQ1')
        counters['negative_affine_channels'] += affine < 0
        q = max(1e-5, max(0., affine) ** p)
        if not math.isfinite(q) or q > 1:
            raise ValueError('trimmed component outside PQ domain')
        raw = f.pm.rational_eval(curve['coefficients'], f.pq_eotf(q))
        counters['rational_negative_channels'] += raw < 0
        mapped.append(max(0., raw))
    if any(v > 10000 for v in mapped):
        raise ValueError('mapped component exceeds PQ domain')
    return f._colour_only(tuple(mapped), meta)


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise FileExistsError('Immutable receipt already exists')
    f.CHAINS[NAME] = chain
    report = {'schema': 'hdr.astra357.component-diagnostic.v1',
              'variant': NAME, 'status': 'development diagnostic; not acceptance',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'adapter_sha256': hashlib.sha256(Path(f.__file__).read_bytes()).hexdigest(),
              'frontend_sha256': hashlib.sha256(Path(f.pm.__file__).read_bytes()).hexdigest(),
              'tests': 0, 'renders': 0, 'native_requests': 0,
              'holdout_access': False, 'shots': {}}
    for shot in ('256', '714'):
        _, sha, rows, meta = f.load(shot)
        result = f.evaluate(rows, meta, NAME)
        result['primary_all_sample'] = (result['final_clip_all_sample']
                                       if result['valid'] == result['population'] else None)
        result['raw_primary_all_sample'] = (result['raw_all_sample']
            if result['valid'] == result['population']
            and not result['counters'].get('raw_outside_PQ_domain_pixels') else None)
        result['prepared'] = result['prepared']['g_mast_mob']
        report['shots'][shot] = {'input_sha256': sha, 'metadata': meta, 'result': result}
        print(shot, json.dumps({k: result[k] for k in
              ('primary_all_sample', 'invalid', 'counters')}), flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
