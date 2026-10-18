"""One frozen complete MB/HK forward+inverse diagnostic on retained 256/714.

US10540920 Eq1/15-17 coordinates and algebraic inverse around the retained
MB curve. Same RGB-pre actual trim, matrix, domain policy and final P3 stage
as astra357_colorfulness. Hybrid hypothesis, not an official contract.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astra356_ipt as ip
import astra360_hk_preflight as hk

f, pm = ip.f, ip.pm
NAME = 'mb-rgb-pre-hk-normalized-exact-inverse'


def chain(rgb, meta, prepared, counters):
    """Full RGB trim -> Ebner/PQ/IPT -> HK/normalise -> MB(K) -> exact inverse -> P3."""
    trimmed = f._rgb_trim(rgb, meta)
    counters['rgb_pre_affine_negative_channels'] += sum(
        meta['sop'][0]*f.pq_inverse(v)+meta['sop'][1] < 0 for v in rgb)
    lms = pm.apply_matrix(ip.RGB_TO_LMS, trimmed)
    if not all(math.isfinite(v) and 0 <= v <= 10000 for v in lms):
        raise ValueError('forward LMS outside PQ domain')
    signal = pm.apply_matrix(ip.LMS_TO_IPT, tuple(f.pq_inverse(v) for v in lms))
    k, pn, tn = hk.forward(*signal)
    curve = prepared['g_mast_mob'][1]
    raw = pm.rational_eval(curve['coefficients'], f.pq_eotf(k))
    counters['rational_below_black_pixels'] += raw < 0
    mapped = max(0., raw)
    if not math.isfinite(mapped) or mapped > 10000:
        raise ValueError('mapped HK outside PQ domain')
    j = f.pq_inverse(mapped)
    output_signal = hk.inverse(j, pn, tn)
    if not all(math.isfinite(v) for v in output_signal):
        raise ValueError('nonfinite inverse HK')
    if not 0 <= output_signal[0] <= 1:
        raise ValueError('inverse HK intensity outside unit domain')
    output = pm.apply_matrix(ip.IPT_TO_LMS, output_signal)
    if not all(math.isfinite(v) and v <= 1 for v in output):
        raise ValueError('inverse LMS-PQ exceeds physical domain')
    black = f.pq_inverse(0)
    counters['inverse_LMS_below_black_channels'] += sum(v < black for v in output)
    lin = tuple(f.pq_eotf(max(black, v)) for v in output)
    result = pm.apply_matrix(ip.LMS_TO_RGB, lin)
    if not all(math.isfinite(v) for v in result):
        raise ValueError('nonfinite inverse RGB')
    counters['raw_BT2020_negative_pixels'] += min(result) < 0
    return result


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise FileExistsError('Retained receipt already exists')
    identities = {}
    for module in (ip, hk, f, pm):
        if module.__file__ is None:
            raise ValueError('source identity unavailable')
        identities[Path(module.__file__).name] = hashlib.sha256(
            Path(module.__file__).read_bytes()).hexdigest()
    f.CHAINS[NAME] = chain
    report = {'schema': 'hdr.astra360.hk-complete.v1', 'variant': NAME,
              'status': 'new complete development hybrid; not official algorithm or acceptance',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'import_source_sha256': identities,
              'source_constants': {'hk_alpha': hk.ALPHA, 'normalisation_addend': .5},
              'domain_policy': 'reject nonfinite/HK outside0..1/>PQ1; inverse LMS projected belowPQ0; finalP3once',
              'native_requests': 0, 'tests': 0, 'renders': 0, 'holdout_access': False,
              'shots': {}}
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
