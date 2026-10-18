"""One predeclared corrected-anchor RGB-pre/IPT-Eq8 development diagnostic.

Uses the retained Fable evidence adapter, never obtains vendor inputs or holdouts.
This is an explicitly hybrid hypothesis, not the full patent or official mapper.
Run from any cwd: python3 astra356_ipt.py OUTPUT.json
FABLE_EVIDENCE_DIR can point to retained evidence343/evidence346 directories.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fable_eval as f

pm = f.pm
# Ebner/Fairchild 1998 Eq1, as printed. No crosstalk or row normalization.
XYZ_TO_LMS = ((.4002, .7075, -.0807), (-.2280, 1.15, .0612), (0., 0., .9184))
LMS_TO_IPT = ((.4, .4, .2), (4.455, -4.851, .396), (.8056, .3572, -1.1628))
XYZ_FROM_BT2020 = pm.rgb_matrix(f.BT)
RGB_TO_LMS = tuple(tuple(sum(XYZ_TO_LMS[i][k] * XYZ_FROM_BT2020[k][j]
                            for k in range(3)) for j in range(3)) for i in range(3))
LMS_TO_RGB = pm.inverse_matrix(RGB_TO_LMS)
IPT_TO_LMS = pm.inverse_matrix(LMS_TO_IPT)
NAME = 'mb-rgb-pre-ipt-eq8'


def chain(rgb, meta, prepared, counters):
    """RGB-PQ SOP/CW/SG -> Eq1/PQ/IPT -> MB rational I + Eq8 -> inverse."""
    trimmed = f._rgb_trim(rgb, meta)
    counters['rgb_pre_affine_negative_channels'] += sum(
        meta['sop'][0] * f.pq_inverse(v) + meta['sop'][1] < 0 for v in rgb)
    lms = pm.apply_matrix(RGB_TO_LMS, trimmed)
    if not all(math.isfinite(v) and 0 <= v <= 10000 for v in lms):
        raise ValueError('forward LMS outside PQ domain')
    ipt = pm.apply_matrix(LMS_TO_IPT, tuple(f.pq_inverse(v) for v in lms))
    intensity = ipt[0]
    if not 0 <= intensity <= 1:
        raise ValueError('forward intensity outside PQ domain')
    curve = prepared['g_mast_mob'][1]
    raw_mapped = pm.rational_eval(curve['coefficients'], f.pq_eotf(intensity))
    counters['rational_below_black_pixels'] += raw_mapped < 0
    mapped = max(0., raw_mapped)
    if not math.isfinite(mapped) or mapped > 10000:
        raise ValueError('mapped intensity outside PQ domain')
    j = f.pq_inverse(mapped)
    k = 1 + j - intensity
    counters['nonpositive_chroma_gain_pixels'] += k <= 0
    output_lmspq = pm.apply_matrix(IPT_TO_LMS, (j, k * ipt[1], k * ipt[2]))
    if not all(math.isfinite(v) and v <= 1 for v in output_lmspq):
        raise ValueError('inverse LMS-PQ exceeds physical domain')
    black = f.pq_inverse(0)
    counters['inverse_LMS_below_black_channels'] += sum(v < black for v in output_lmspq)
    linear_lms = tuple(f.pq_eotf(max(black, v)) for v in output_lmspq)
    result = pm.apply_matrix(LMS_TO_RGB, linear_lms)
    if not all(math.isfinite(v) for v in result):
        raise ValueError('nonfinite inverse RGB')
    counters['raw_BT2020_negative_pixels'] += min(result) < 0
    return result


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise FileExistsError('Refusing to overwrite retained receipt')
    identities = {}
    for name, matrix, inverse in (('RGB_LMS', RGB_TO_LMS, LMS_TO_RGB),
                                  ('LMS_IPT', LMS_TO_IPT, IPT_TO_LMS)):
        identities[name] = max(abs(sum(matrix[i][k] * inverse[k][j] for k in range(3))
                                   - (i == j)) for i in range(3) for j in range(3))
        if identities[name] > 1e-12:
            raise ArithmeticError('inverse identity check failed')
    f.CHAINS[NAME] = chain
    report = {'schema': 'hdr.astra356.corrected-ipt.v1', 'variant': NAME,
              'status': 'development diagnostic only; no acceptance',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'adapter_sha256': hashlib.sha256(Path(f.__file__).read_bytes()).hexdigest(),
              'frontend_sha256': hashlib.sha256(Path(pm.__file__).read_bytes()).hexdigest(),
              'rgb_to_lms': RGB_TO_LMS, 'lms_to_ipt': LMS_TO_IPT,
              'identity_residual': identities,
              'domain_policy': 'reject nonfinite/>PQ1; project inverse LMS below PQ(0); final P3 clip once',
              'tests': 0, 'renders': 0, 'native_requests': 0, 'holdout_access': False,
              'shots': {}}
    for shot in ('256', '714'):
        _, sha, rows, meta = f.load(shot)
        result = f.evaluate(rows, meta, NAME)
        # Never advertise subset/raw-domain partial metrics as the primary result.
        result['primary_all_sample'] = (result['final_clip_all_sample']
                                       if result['valid'] == result['population'] else None)
        result['raw_primary_all_sample'] = (result['raw_all_sample']
            if result['valid'] == result['population']
            and result['counters'].get('raw_outside_PQ_domain_pixels', 0) == 0 else None)
        # Keep only the actual active curve, not the adapter's unused precomputations.
        result['prepared'] = result['prepared']['g_mast_mob']
        report['shots'][shot] = {'input_sha256': sha, 'metadata': meta, 'result': result}
        print(shot, json.dumps({key: result[key] for key in
              ('primary_all_sample', 'invalid', 'counters')}), flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
