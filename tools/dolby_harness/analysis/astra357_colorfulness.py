"""Single US10540920 Eq11-13 colorfulness discriminator on corrected MB/IPT.

Same complete hybrid as astra356_ipt, except the explicitly disclosed saturation
factor J*(.5*I+1)/(I*(.5*J+1)) replaces US9961237 Eq8. No fitted constants.
Usage: python3 astra357_colorfulness.py OUTPUT.json
"""
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astra356_ipt as ip

f, pm = ip.f, ip.pm
NAME = 'mb-rgb-pre-ipt-colorfulness-eq12'


def chain(rgb, meta, prepared, counters):
    """Full RGB-PQ trim/color, Eq1/IPT MB intensity, Eq12 chroma, inverse/P3."""
    trimmed = f._rgb_trim(rgb, meta)
    counters['rgb_pre_affine_negative_channels'] += sum(
        meta['sop'][0] * f.pq_inverse(v) + meta['sop'][1] < 0 for v in rgb)
    lms = pm.apply_matrix(ip.RGB_TO_LMS, trimmed)
    if not all(math.isfinite(v) and 0 <= v <= 10000 for v in lms):
        raise ValueError('forward LMS outside PQ domain')
    signal = pm.apply_matrix(ip.LMS_TO_IPT, tuple(f.pq_inverse(v) for v in lms))
    intensity = signal[0]
    if not 0 < intensity <= 1:
        raise ValueError('forward intensity outside positive PQ domain')
    curve = prepared['g_mast_mob'][1]
    raw = pm.rational_eval(curve['coefficients'], f.pq_eotf(intensity))
    counters['rational_below_black_pixels'] += raw < 0
    mapped = max(0., raw)
    if not math.isfinite(mapped) or mapped > 10000:
        raise ValueError('mapped intensity outside PQ domain')
    j = f.pq_inverse(mapped)
    # US10540920B2 paragraphs0079-0082 Eq11-13; K1=.5 and K2=1 example.
    gain = j * (.5 * intensity + 1) / (intensity * (.5 * j + 1))
    counters['nonpositive_chroma_gain_pixels'] += gain <= 0
    output = pm.apply_matrix(ip.IPT_TO_LMS, (j, gain * signal[1], gain * signal[2]))
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
    coordinate_path = ip.__file__
    if coordinate_path is None:
        raise ValueError('Coordinate source file unavailable')
    f.CHAINS[NAME] = chain
    report = {'schema': 'hdr.astra357.colorfulness-eq12.v1', 'variant': NAME,
              'status': 'development complete hybrid, not official algorithm or acceptance',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'coordinate_script_sha256': hashlib.sha256(Path(coordinate_path).read_bytes()).hexdigest(),
              'adapter_sha256': hashlib.sha256(Path(f.__file__).read_bytes()).hexdigest(),
              'frontend_sha256': hashlib.sha256(Path(pm.__file__).read_bytes()).hexdigest(),
              'source_constants': {'k1': .5, 'k2': 1.},
              'domain_policy': 'reject nonfinite/>PQ1; inverse LMS projected belowPQ0; finalP3once',
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
