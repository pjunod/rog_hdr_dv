"""Fable349: LOCAL all-sample BT.2124 evaluator for complete mapping chains on the two retained development
lattices (34560 samples each).  Imports the owned frontend read-only (tools.dolby_harness.public_mapping, metric).
Inputs
  714: evidence346/joint-audit714-346.json exact_inputs (exact source linear BT2020 nits + exact reference PQ).
  256: evidence343/joint-audit343.json per_sample (exact reference HALF codes; source RECONSTRUCTED from the stored
       matched-endpoint scale intervals C = U/su, relative error <= 2^-52) -> labelled 'reconstructed prospect'.
Validation: the existing baselines must reproduce (714 MpreRGB 6.015329278630697 / signed I -5.622285931186368;
256 MpreRGB 1.7284671178784912, WpreY 1.4240802336088687).  Metrics are reported RAW (pre final clip, as the
retained diagnostics did; excursions counted) and after ONE final physical P3 clip [0,peak] (as the GPU does).
No fitting: every chain is a fixed, fully specified algorithm using the shot's own metadata.  Nothing enters the
renderer from here; 1200/48 untouched.
Run: python3 -I fable_eval.py <256|714> <chain,chain,...|all>   (writes fable_eval_<shot>.json)
"""
import sys, json, math, struct, hashlib, collections, os
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))          # tools/dolby_harness/analysis -> repository root
sys.path.insert(0, REPO)
# Retained development lattices are private evidence (not in version control); point at their directory.
EVIDENCE = os.environ.get('FABLE_EVIDENCE_DIR', os.path.abspath(os.path.join(REPO, '..')))
from tools.dolby_harness import public_mapping as pm
from tools.dolby_harness.metric import pq_eotf, pq_inverse, rgb_to_itp, delta_itp, summarize
P3 = ((.68, .32), (.265, .69), (.15, .06), (.3127, .329)); BT = ((.708, .292), (.17, .797), (.131, .046), (.3127, .329))
P3_TO_BT = pm.convert_matrix(P3, BT); TO_P3 = pm.convert_matrix(BT, P3); W = pm.BT2020_WEIGHTS
def half_to_pq(bits): return struct.unpack('<e', struct.pack('<H', bits))[0]
def lum(rgb): return sum(w * v for w, v in zip(W, rgb))

def load(shot):
    if shot == '714':
        path = os.path.join(EVIDENCE, 'evidence346', 'joint-audit714-346.json'); raw = open(path, 'rb').read(); doc = json.loads(raw)
        rows = [(tuple(xy), tuple(sl), tuple(rpq)) for xy, sp3, sl, sy, rpq, ry in doc['exact_inputs']]
        meta = {'l1': tuple(doc['l1']), 'sop': tuple(doc['SOP']), 'color': tuple(doc['CW_SG']), 'peak': 600.0,
                'source': 'EXACT stored linear BT2020 triples', 'trim_note': '714 target27 shot-inherited'}
    else:
        path = os.path.join(EVIDENCE, 'evidence343', 'joint-audit343.json'); raw = open(path, 'rb').read(); doc = json.loads(raw)
        rows = []; maxrel = 0.0
        for xy, hb, ivs, scales, common, ray, mask in doc['per_sample']:
            ref = tuple(half_to_pq(b) for b in hb); src = []
            for iv, sc in zip(ivs, scales):
                if sc is None: src.append(0.0); continue
                c_hi = iv[1] / sc[1]
                if sc[0] > 0 and iv[0] > 0: maxrel = max(maxrel, abs(iv[0] / sc[0] - c_hi) / c_hi)
                src.append(c_hi)
            rows.append((tuple(xy), tuple(src), ref))
        meta = {'l1': (0.0, 0.290273, 0.879591), 'sop': (507 / 500, -7 / 500, 2000 / 2001), 'color': (-0.001, 0.0), 'peak': 600.0,
                'source': 'RECONSTRUCTED from matched-endpoint scale intervals (C=U/su); max endpoint disagreement %.3e; labelled prospect, not exact acceptance' % maxrel,
                'trim_note': '0,0,0,-0.028,0,0.001,-0.002,0,-0.75 (sample_native.py assertion)'}
    mode = os.environ.get('FABLE_L1', '')
    if mode in ('frame_maxrgb', 'frame_y'):
        # frame-local L1 HYPOTHESIS (diagnostic): min/avg/max over the lattice of PQ(maxRGB) (ST2094-10 6.1 style) or PQ(Y)
        vals = []
        for xy, src, ref in rows:
            v = max(src) if mode == 'frame_maxrgb' else lum(src)
            vals.append(pq_inverse(max(0.0, min(10000.0, v))))
        meta['l1_xml'] = meta['l1']; meta['l1'] = (min(vals), sum(vals) / len(vals), max(vals)); meta['l1_mode'] = mode
    return path, hashlib.sha256(raw).hexdigest(), rows, meta

# ---------------------------------------------------------------- curves -------------------------------------------
def hermite_prepare(l1, peak, cutoff_frac=0.5, pres=0.5, contrast=1.0, tpow=2, hpow=4):
    """US10600166B2 Table1 steps1-3,5-8 + Eq7 with improved cutoff rule (0080-0082), normalized PQ (OPEN_XML205 doc)."""
    a, b = pq_inverse(0), pq_inverse(peak); A, B, C = l1; L, H = B - A, C - B
    cutoff = a + cutoff_frac * (b - a)
    Y = min(cutoff, max(B, a + pres * L)) if B <= cutoff else max(cutoff, min(B, b - pres * H))
    U, V = max(Y - L, a), min(Y + H, b)
    u, v = (Y - U) / L if L > 0 else 0.0, (V - Y) / H if H > 0 else 0.0
    s0 = min(3 * u, u ** tpow); s2 = min(3 * v, 1.0, v ** hpow); s1 = min(3 * u, 3 * v, contrast * (1 - B + Y))
    return {'A': A, 'B': B, 'C': C, 'U': U, 'Y': Y, 'V': V, 's0': s0, 's1': s1, 's2': s2, 'a': a, 'b': b}
def hermite_eval(h, x):
    def seg(x0, y0, m0, x1, y1, m1):
        dx, dy = x1 - x0, y1 - y0; t = (x - x0) / dx
        return y0 + t * (dx * m0 + t * (3 * dy - dx * (2 * m0 + m1) + t * (-2 * dy + dx * (m0 + m1))))
    if x < h['A']: y = h['U'] + (x - h['A']) * h['s0']
    elif x <= h['B']: y = seg(h['A'], h['U'], h['s0'], h['B'], h['Y'], h['s1'])
    elif x <= h['C']: y = seg(h['B'], h['Y'], h['s1'], h['C'], h['V'], h['s2'])
    else: y = h['V'] + (x - h['C']) * h['s2']
    return min(h['b'], max(h['a'], y))
def pq_rational_prepare(l1, peak):
    """Astra350 PQ_RATIONAL_POST_CONTRACT: MPC knee rule, rational interpolated in PQ through (lo,PQ0),(src,dst),(hi,PQ(peak))."""
    lo, hi = l1[0], l1[2]; dstlo, dsthi = pq_inverse(0), pq_inverse(peak)
    src = min(lo + 0.8 * (hi - lo), max(lo + 0.1 * (hi - lo), l1[1])); t = (src - lo) / (hi - lo)
    adaptation = 0.4 + 0.6 * (1 - pm.smoothstep(0.8, 0.4, t) * pm.smoothstep(0.1, 0.4, t))
    dst = src + adaptation * (dstlo + t * (dsthi - dstlo) - src); dst = min(dstlo + 0.8 * (dsthi - dstlo), max(dstlo + 0.1 * (dsthi - dstlo), dst))
    xs, ys = (lo, src, hi), (dstlo, dst, dsthi)
    a, b, c = pm.solve3([(1, x, -x * y) for x, y in zip(xs, ys)], ys)
    if b - a * c < 0 or 1 + c * 1.0 <= 0: raise ValueError('PQ rational not increasing/pole')
    return {'coefficients': (a, b, c), 'source_anchors': xs, 'mapped_anchors': ys, 'peak': peak}
def pq_rational_eval(co, q):
    a, b, c = co; return (a + b * q) / (1 + c * q)
def sop_pq(q, sop):
    s, o, p = sop; return max(1e-5, max(0.0, s * q + o) ** p)

# ---------------------------------------------------------------- chains -------------------------------------------
def prep(meta):
    l1, peak = meta['l1'], meta['peak']
    return {'mpc': pm.mpc_prepare(l1, peak), 'mpc_lo0': pm.mpc_prepare((0.0, l1[1], l1[2]), peak),
            'hermite': hermite_prepare(l1, peak), 'pqr': pq_rational_prepare(l1, peak)}
def chain_mpre_rgb(rgb, meta, P, counters): return pm.mpc(rgb, P['mpc'], meta['sop'], meta['color'])
def chain_mpost(rgb, meta, P, counters): return pm.mpc_post(rgb, P['mpc'], meta['sop'], meta['color'])
def chain_wpre_y(rgb, meta, P, counters): return pm.mpc_pre_y(rgb, P['mpc'], meta['sop'], meta['color'])
def chain_mpre_rgb_lo0(rgb, meta, P, counters): return pm.mpc(rgb, P['mpc_lo0'], meta['sop'], meta['color'])
def chain_hermite_y_sop(rgb, meta, P, counters):
    """scalar: Y -> PQ -> Hermite(PQ) -> absolute-PQ SOP (Eq5) -> E -> ratio-scale RGB; colour step omitted (Y-only)."""
    y = lum(rgb)
    if y == 0: return (0.0, 0.0, 0.0)
    q = hermite_eval(P['hermite'], pq_inverse(y)); qt = sop_pq(q, meta['sop'])
    if qt > 1: raise ValueError('trimmed PQ exceeds physical domain')
    m = pq_eotf(qt); return tuple(v * m / y for v in rgb)
def chain_pq_rational_post(rgb, meta, P, counters):
    """Astra350 2280: PQ-rational automatic Y (MPC anchors) -> ratio-scale RGB -> mpc_post RGB-PQ SOP + full colour -> EOTF."""
    y = lum(rgb)
    if y > 0:
        hq = pq_rational_eval(P['pqr']['coefficients'], pq_inverse(y))
        if hq < pq_inverse(0): counters['pqr_underblack_clamp'] += 1; hq = pq_inverse(0)
        if not math.isfinite(hq) or hq > 1: raise ValueError('PQ rational outside physical domain')
        m = pq_eotf(hq); rgb = tuple(v * m / y for v in rgb)
    s, o, p = meta['sop']
    q = tuple(max(1e-5, max(0.0, s * pq_inverse(v) + o) ** p) for v in rgb)
    counters['affine_negative_channels'] += sum(s * pq_inverse(v) + o < 0 for v in rgb)
    q = pm.color_transform(q, W, *meta['color'])
    if any(v > 1 for v in q): raise ValueError('trimmed PQ exceeds physical domain')
    return tuple(pq_eotf(v) for v in q)
def chain_pq_rational_pre_y(rgb, meta, P, counters):
    """scalar: Y -> PQ -> SOP -> PQ-rational(MPC anchors in PQ) -> E -> ratio-scale RGB (W placement, PQ coordinate)."""
    y = lum(rgb)
    if y == 0: return (0.0, 0.0, 0.0)
    qt = sop_pq(pq_inverse(y), meta['sop']); hq = pq_rational_eval(P['pqr']['coefficients'], qt)
    if hq < pq_inverse(0): counters['pqr_underblack_clamp'] += 1; hq = pq_inverse(0)
    if hq > 1: raise ValueError('PQ rational outside physical domain')
    m = pq_eotf(hq); return tuple(v * m / y for v in rgb)
# ---- pinned MPC caller: PQ-decoded L1 nits truncated to UINT, SetHDR10ShaderParams guards, shader knee rule ----
def mpc_prepare_uint(l1, peak):
    """Pinned DX11VideoProcessor.cpp:2369-2371 (UINT truncation of L1 nits) + SetHDR10ShaderParams guards + ps_hdr10_tonemap ST2094-10 knee rule."""
    mn, av, mx = (float(int(pq_eotf(v))) for v in l1)
    if mn <= 0: mn = 0.0
    maxcll = mx if mx > 10 else mx; maxfall = av if av > 1 else maxcll
    if peak >= maxcll: return {'identity': True, 'peak': peak}
    smin, smax, savg = pq_inverse(mn), pq_inverse(maxcll), pq_inverse(maxfall)
    dmin, dmax = pq_inverse(0), pq_inverse(peak)
    src = savg if maxfall > 0 else smin + 0.4 * (smax - smin); src = min(smin + 0.8 * (smax - smin), max(smin + 0.1 * (smax - smin), src))
    t = (src - smin) / (smax - smin); adaptation = 0.4 + 0.6 * (1 - pm.smoothstep(0.8, 0.4, t) * pm.smoothstep(0.1, 0.4, t))
    dst = src + adaptation * (dmin + t * (dmax - dmin) - src); dst = min(dmin + 0.8 * (dmax - dmin), max(dmin + 0.1 * (dmax - dmin), dst))
    xs, ys = (mn, pq_eotf(src), maxcll), (0.0, pq_eotf(dst), peak)
    return {'identity': False, 'coefficients': pm.rational_prepare(xs, ys), 'source_anchors': xs, 'mapped_anchors': ys, 'peak': peak, 'uint_l1_nits': (mn, av, mx)}
def hermite_from_anchors(SMin, TMin, SMid, TMid, SMax, TMax, contrast=1.0, tpow=2, hpow=4, a=None, b=None):
    """US10600166B2 Table1 steps7-8 slopes + Eq7 segments for GIVEN PQ anchors (knee supplied by the MPC rule, not Table1 step4)."""
    L, H = SMid - SMin, SMax - SMid; u, v = (TMid - TMin) / L, (TMax - TMid) / H
    s0 = min(3 * u, u ** tpow); s2 = min(3 * v, 1.0, v ** hpow); s1 = min(3 * u, 3 * v, contrast * (1 - SMid + TMid))
    return {'A': SMin, 'B': SMid, 'C': SMax, 'U': TMin, 'Y': TMid, 'V': TMax, 's0': s0, 's1': s1, 's2': s2, 'a': a if a is not None else TMin, 'b': b if b is not None else TMax}
def hermite_mpc(curve, peak):
    xs, ys = curve['source_anchors'], curve['mapped_anchors']
    return hermite_from_anchors(pq_inverse(xs[0]), pq_inverse(ys[0]), pq_inverse(xs[1]), pq_inverse(ys[1]), pq_inverse(xs[2]), pq_inverse(ys[2]), a=pq_inverse(0), b=pq_inverse(peak))
def hermite_variant(l1, peak, smin_mode, tpow, hpow):
    """Eq7 Hermite: knee (SMid->TMid) from the MPC/libplacebo rule with lo=0; tail anchor SMin=0 ('0') or L1min ('l1')
    mapped to TMin=PQ(0); slopes Table1 step 8 with disclosed exponents t,h in {1,2,4} (US10600166 0071)."""
    cv = pm.mpc_prepare((0.0, l1[1], l1[2]), peak)
    if cv['identity']: raise ValueError('identity')
    xs, ys = cv['source_anchors'], cv['mapped_anchors']
    smin = pq_inverse(0) if smin_mode == '0' else l1[0]
    return hermite_from_anchors(smin, pq_inverse(0), pq_inverse(xs[1]), pq_inverse(ys[1]), pq_inverse(xs[2]), pq_inverse(ys[2]), tpow=tpow, hpow=hpow, a=pq_inverse(0), b=pq_inverse(peak))
HV = [(s, t, h) for s in ('0', 'l1') for t, h in ((2, 4), (2, 2), (1, 1), (1, 2), (4, 4))]
SPLINE_CONST = {'slope_tuning': 1.5, 'slope_offset': 0.2, 'spline_contrast': 0.5}   # libplacebo defaults (verified against tone_mapping.h)
def spline_prepare(l1, peak, lo_mode='l1', const=SPLINE_CONST):
    """library pl_tone_map_spline (single-pivot polynomial spline, PQ scaling) on the same st2094 knee rule
    (knee_adaptation .4, min .1, max .8, default .4); input_min = L1min ('l1') or 0 ('0'); output [PQ(0),PQ(peak)]."""
    smin = l1[0] if lo_mode == 'l1' else 0.0; smid, smax = l1[1], l1[2]
    dmin, dmax = pq_inverse(0), pq_inverse(peak)
    if dmax >= smax: raise ValueError('identity')
    src = min(smin + 0.8 * (smax - smin), max(smin + 0.1 * (smax - smin), smid)); t = (src - smin) / (smax - smin)
    adaptation = 0.4 + 0.6 * (1 - pm.smoothstep(0.8, 0.4, t) * pm.smoothstep(0.1, 0.4, t))
    dst = src + adaptation * (dmin + t * (dmax - dmin) - src); dst = min(dmin + 0.8 * (dmax - dmin), max(dmin + 0.1 * (dmax - dmin), dst))
    slope = (dst - dmin) / (src - smin)
    ratio = smax / dmax - 1.0; ratio = min(1.0 + const['slope_offset'], max(const['slope_offset'], const['slope_tuning'] * ratio))
    slope = slope ** ((1.0 - const['spline_contrast']) * ratio)
    in_min, in_max, out_min, out_max = smin - src, smax - src, dmin - dst, dmax - dst
    Pa = (out_min - slope * in_min) / (in_min * in_min); Pb = slope
    tt = 2 * in_max * in_max; Qa = (slope * in_max - out_max) / (in_max * tt); Qb = -3 * (slope * in_max - out_max) / tt; Qc = slope
    return {'src_pivot': src, 'dst_pivot': dst, 'slope': slope, 'Pa': Pa, 'Pb': Pb, 'Qa': Qa, 'Qb': Qb, 'Qc': Qc, 'a': dmin, 'b': dmax, 'ratio': ratio}
def spline_eval(s, q):
    x = q - s['src_pivot']
    y = ((s['Qa'] * x + s['Qb']) * x + s['Qc']) * x if x > 0 else (s['Pa'] * x + s['Pb']) * x
    return min(s['b'], max(s['a'], y + s['dst_pivot']))
_old_prep = prep
def prep(meta):
    P = _old_prep(meta); l1, peak = meta['l1'], meta['peak']
    P['mpc_uint'] = mpc_prepare_uint(l1, peak)
    P['herm_mpc'] = hermite_mpc(P['mpc'], peak); P['herm_mpc_lo0'] = hermite_mpc(P['mpc_lo0'], peak); P['herm_mpc_uint'] = hermite_mpc(P['mpc_uint'], peak)
    for s, t, h in HV:
        try: P['hv_%s_t%d_h%d' % (s, t, h)] = hermite_variant(l1, peak, s, t, h)
        except ValueError: pass
    for lo in ('l1', '0'):
        try: P['spline_' + lo] = spline_prepare(l1, peak, lo)
        except ValueError: pass
    return P
def _spline_chain(key, order):
    def f(rgb, meta, P, c):
        s = P[key]
        if order == 'pre':   # MPC order: RGB SOP+colour first, then spline on PQ(Y)
            rgb2 = _rgb_trim(rgb, meta); return _scale_y(rgb2, lambda y: pq_eotf(spline_eval(s, pq_inverse(y))))
        if order == 'y':     # W placement: SOP on PQ(Y), then spline (colour ignored, labelled)
            return _scale_y(rgb, lambda y: pq_eotf(spline_eval(s, sop_pq(pq_inverse(y), meta['sop']))))
        if order == 'post':  # spline on PQ(Y) then RGB SOP+colour
            rgb2 = _scale_y(rgb, lambda y: pq_eotf(spline_eval(s, pq_inverse(y)))); return _rgb_trim(rgb2, meta)
        return _scale_y(rgb, lambda y: pq_eotf(spline_eval(s, pq_inverse(y))))   # plain
    f.__doc__ = 'library single-pivot spline (%s) order=%s' % (key, order)
    return f
def _y_only_force(fn_curve_key, kind):
    """Y placement ignoring the colour step (labelled: 714 CW/SG effect <0.2%); kind 'herm' or 'mob'."""
    def f(rgb, meta, P, c):
        if kind == 'herm': h = P[fn_curve_key]; return _scale_y(rgb, lambda y: pq_eotf(hermite_eval(h, sop_pq(pq_inverse(y), meta['sop']))))
        cv = P[fn_curve_key]; return _scale_y(rgb, lambda y: max(0.0, pm.rational_eval(cv['coefficients'], pq_eotf(sop_pq(pq_inverse(y), meta['sop'])))))
    f.__doc__ = 'Y-only W placement (SOP on PQ(Y) then curve), colour step IGNORED (labelled), curve ' + fn_curve_key
    return f
def _scale_y(rgb, fn):
    y = lum(rgb)
    if y == 0: return (0.0, 0.0, 0.0)
    m = fn(y); return tuple(v * m / y for v in rgb)
def _rgb_trim(rgb, meta):
    s, o, p = meta['sop']; q = tuple(max(1e-5, max(0.0, s * pq_inverse(v) + o) ** p) for v in rgb)
    q = pm.color_transform(q, W, *meta['color'])
    if any(v > 1 for v in q): raise ValueError('trimmed PQ exceeds physical domain')
    return tuple(pq_eotf(v) for v in q)
def chain_mpre_rgb_uint(rgb, meta, P, c): return pm.mpc(rgb, P['mpc_uint'], meta['sop'], meta['color'])
def _herm_pre(key):
    def f(rgb, meta, P, c):
        """MPC order: RGB absolute-PQ SOP + colour FIRST, then Y -> PQ -> Eq7 Hermite (MPC-rule knee, Table1 slopes) -> E -> ratio."""
        h = P[key]; rgb2 = _rgb_trim(rgb, meta); return _scale_y(rgb2, lambda y: pq_eotf(hermite_eval(h, pq_inverse(y))))
    return f
def _herm_post(key):
    def f(rgb, meta, P, c):
        """post order: Y -> PQ -> Eq7 Hermite (MPC-rule knee) -> E -> ratio, THEN RGB absolute-PQ SOP + colour."""
        h = P[key]; rgb2 = _scale_y(rgb, lambda y: pq_eotf(hermite_eval(h, pq_inverse(y)))); return _rgb_trim(rgb2, meta)
    return f
def _herm_y(key):
    def f(rgb, meta, P, c):
        """W placement (SG must be 0): Y -> PQ -> SOP -> Eq7 Hermite (MPC-rule knee) -> E -> ratio."""
        if meta['color'][1] != 0: raise ValueError('Y-only discrimination requires neutral saturation')
        h = P[key]; return _scale_y(rgb, lambda y: pq_eotf(hermite_eval(h, sop_pq(pq_inverse(y), meta['sop']))))
    return f
def _herm_plain(key):
    def f(rgb, meta, P, c):
        """Hermite only (no SOP/colour), diagnostic for the curve shape alone."""
        h = P[key]; return _scale_y(rgb, lambda y: pq_eotf(hermite_eval(h, pq_inverse(y))))
    return f
def _mob_plain(key):
    def f(rgb, meta, P, c):
        """nits rational only (no SOP/colour), diagnostic for the curve shape alone."""
        cv = P[key]; return _scale_y(rgb, lambda y: max(0.0, pm.rational_eval(cv['coefficients'], y)))
    return f
def knee_prepare_const(l1, peak, adaptation=0.4):
    """Knee rule WITHOUT libplacebo's smoothstep 'tuning' ramp: dst = src + knee_adaptation*(linear_rescale - src), knee_adaptation=0.4
    (the documented default constant); clamps 10%-80% unchanged; anchors (lo->0, knee, L1max->peak) in nits."""
    lo, hi = l1[0], l1[2]; dstlo, dsthi = pq_inverse(0), pq_inverse(peak)
    if peak >= pq_eotf(hi): return {'identity': True, 'peak': peak}
    src = min(lo + 0.8 * (hi - lo), max(lo + 0.1 * (hi - lo), l1[1])); t = (src - lo) / (hi - lo)
    dst = src + adaptation * (dstlo + t * (dsthi - dstlo) - src); dst = min(dstlo + 0.8 * (dsthi - dstlo), max(dstlo + 0.1 * (dsthi - dstlo), dst))
    xs, ys = (pq_eotf(lo), pq_eotf(src), pq_eotf(hi)), (0.0, pq_eotf(dst), peak)
    return {'identity': False, 'coefficients': pm.rational_prepare(xs, ys), 'source_anchors': xs, 'mapped_anchors': ys, 'peak': peak, 'knee_pq': (src, dst)}
# ---- US9961237B2 Eq2-5 powered rational in PQ:  y = ((C1 + C2*x^Slope)/(1 + C3*x^Slope))^Rolloff -------------------
def powered_prepare(xs, ys, slope, rolloff):
    """Solve C1..C3 from three PQ anchors (x_i, y_i): with z=x^Slope, w=y^(1/Rolloff):  C1 + C2*z - C3*z*w = w (linear)."""
    zs = [x ** slope for x in xs]; ws = [y ** (1.0 / rolloff) for y in ys]
    c1, c2, c3 = pm.solve3([(1.0, z, -z * w) for z, w in zip(zs, ws)], ws)
    for z in zs:
        if 1 + c3 * z <= 0: raise ValueError('powered rational pole')
    return {'C': (c1, c2, c3), 'slope': slope, 'rolloff': rolloff, 'x': xs, 'y': ys}
def powered_eval(p, q):
    c1, c2, c3 = p['C']; z = q ** p['slope']; w = (c1 + c2 * z) / (1 + c3 * z)
    if w < 0: return 0.0
    return min(1.0, w ** p['rolloff'])
def powered_variants(l1, peak):
    """Pre-declared anchor sets (all PQ): 'disp' = patent 0045-0051 (source display .005/4000 nit, target 0/peak, Shift=S2T/2,
    Slope=S2T+1, Rolloff 1/3); 'knee' = (black .005->0, MPC lo0 knee, L1max->peak) with Rolloff 1/3 and Slope 1 or S2T+1 from
    those anchors ('kneeS'); 'knee0' = same with black 0."""
    out = {}
    tmin, tmax = pq_inverse(0), pq_inverse(peak)
    smin, smax = pq_inverse(0.005), pq_inverse(4000.0)
    s2t = (smin + smax) / 2 - (tmin + tmax) / 2; shift, slope = s2t / 2, s2t + 1
    smid = (smin + smax) / 2
    try: out['pw_disp'] = powered_prepare((smin, smid, smax), (max(smin - shift, tmin), smid - shift, min(smax - shift, tmax)), slope, 1 / 3)
    except ValueError: pass
    cv = pm.mpc_prepare((0.0, l1[1], l1[2]), peak)
    if not cv['identity']:
        xs, ys = cv['source_anchors'], cv['mapped_anchors']
        for name, xb in (('knee', 0.005), ('knee0', 0.0)):
            X = (pq_inverse(xb), pq_inverse(xs[1]), pq_inverse(xs[2])); Y = (tmin, pq_inverse(ys[1]), tmax)
            s2t_l1 = (X[0] + X[2]) / 2 - (Y[0] + Y[2]) / 2
            for tag, sl in (('', 1.0), ('S', s2t_l1 + 1)):
                for rtag, ro in (('', 1 / 3), ('R1', 1.0)):
                    try: out['pw_%s%s%s' % (name, tag, rtag)] = powered_prepare(X, Y, sl, ro)
                    except ValueError: pass
    return out
def _pw_chain(key, order):
    def f(rgb, meta, P, c):
        p = P[key]
        if order == 'y':   return _scale_y(rgb, lambda y: pq_eotf(powered_eval(p, sop_pq(pq_inverse(y), meta['sop']))))
        if order == 'pre': return _scale_y(_rgb_trim(rgb, meta), lambda y: pq_eotf(powered_eval(p, pq_inverse(y))))
        return _scale_y(rgb, lambda y: pq_eotf(powered_eval(p, pq_inverse(y))))   # plain
    f.__doc__ = 'US9961237 Eq2 powered rational %s order=%s' % (key, order)
    return f
PW_KEYS = ['pw_disp', 'pw_knee', 'pw_kneeS', 'pw_kneeR1', 'pw_kneeSR1', 'pw_knee0', 'pw_knee0S']
# ---- compact pre-declared grid: black anchor x documented curve kind x stage order (knee rule fixed = MPC/libplacebo lo=0) ----
def grid_curve(l1, peak, black, kind):
    """black: '0' (pinned caller UINT truncation), 'l1' (L1min), 'mast' (declared mastering black .005 nit);
    kind: 'mob' nits rational through (xb,0),(knee),(L1max,peak) ; 'herm' PQ Eq7 Hermite (Table1 slopes t=2,h=4) on the same anchors."""
    knee_lo = {'0': 0.0, 'l1': 0.0, 'mast': 0.0, 'mastfull': pq_inverse(0.005), 'l1full': l1[0], 'mastK4': 0.0, '0K4': 0.0}[black]
    cv = knee_prepare_const((knee_lo, l1[1], l1[2]), peak) if black.endswith('K4') else pm.mpc_prepare((knee_lo, l1[1], l1[2]), peak)
    if cv['identity']: raise ValueError('identity')
    xs, ys = cv['source_anchors'], cv['mapped_anchors']
    xb = {'0': 0.0, 'l1': pq_eotf(l1[0]), 'mast': 0.005, 'mastfull': 0.005, 'l1full': pq_eotf(l1[0]), 'mastK4': 0.005, '0K4': 0.0}[black]
    if xb >= xs[1]: raise ValueError('black above knee')
    if kind == 'mob':
        return ('mob', {'coefficients': pm.rational_prepare((xb, xs[1], xs[2]), (0.0, ys[1], ys[2])), 'source_anchors': (xb, xs[1], xs[2]), 'mapped_anchors': (0.0, ys[1], ys[2]), 'peak': peak})
    return ('herm', hermite_from_anchors(pq_inverse(xb), pq_inverse(0), pq_inverse(xs[1]), pq_inverse(ys[1]), pq_inverse(xs[2]), pq_inverse(ys[2]), a=pq_inverse(0), b=pq_inverse(peak)))
GRID = [(b, k, o) for b in ('0', 'l1', 'mast', 'mastfull', 'l1full', 'mastK4', '0K4') for k in ('mob', 'herm') for o in ('y', 'pre', 'post', 'ycol')]
def _colour_only(rgb, meta):
    """CW/SG inside-exponent colour expression on PQ RGB (no SOP); exact identity when SG=0."""
    q = pm.color_transform(tuple(pq_inverse(v) for v in rgb), W, *meta['color'])
    if any(v > 1 for v in q): raise ValueError('colour PQ exceeds physical domain')
    return tuple(pq_eotf(v) for v in q)
_prep2 = prep
def prep(meta):
    P = _prep2(meta)
    for b, k, _ in GRID:
        key = 'g_%s_%s' % (b, k)
        if key in P: continue
        try: P[key] = grid_curve(meta['l1'], meta['peak'], b, k)
        except ValueError: pass
    P.update(powered_variants(meta['l1'], meta['peak']))
    return P
def _grid_chain(b, k, o):
    def f(rgb, meta, P, c):
        kind, cv = P['g_%s_%s' % (b, k)]
        if kind == 'mob': curve_y = lambda y: max(0.0, pm.rational_eval(cv['coefficients'], y))
        else: curve_y = lambda y: pq_eotf(hermite_eval(cv, pq_inverse(y)))
        if o == 'y':   return _scale_y(rgb, lambda y: curve_y(pq_eotf(sop_pq(pq_inverse(y), meta['sop']))))   # W placement (colour ignored, labelled)
        if o == 'ycol': return _colour_only(_scale_y(rgb, lambda y: curve_y(pq_eotf(sop_pq(pq_inverse(y), meta['sop'])))), meta)  # W placement + CW/SG honoured after
        if o == 'pre': return _scale_y(_rgb_trim(rgb, meta), curve_y)                                           # MPC order
        return _rgb_trim(_scale_y(rgb, curve_y), meta)                                                           # post order
    f.__doc__ = 'grid: black=%s curve=%s order=%s (knee rule MPC lo=0 fixed; nothing fitted)' % (b, k, o)
    return f
def _driver_chain(b, driver):
    """Leader chain (black=b, lo0 knee, nits rational, PQ SOP before curve, colour after) but the scalar is DRIVEN by
    maxRGB ('max') or by the per-pixel maximum of Y and the knee-weighted blend ('mix' = max(Y, .5*(Y+maxRGB)))
    instead of CIE Y; all channels scaled by f(x)/x (hue-preserving).  ST2094-10 §6.1 defines L1 on maxRGB."""
    def f(rgb, meta, P, c):
        kind, cv = P['g_%s_mob' % b]
        x = max(rgb) if driver == 'max' else max(lum(rgb), 0.5 * (lum(rgb) + max(rgb)))
        if x <= 0: return (0.0, 0.0, 0.0)
        y2 = pq_eotf(sop_pq(pq_inverse(x), meta['sop'])); m = max(0.0, pm.rational_eval(cv['coefficients'], y2))
        return _colour_only(tuple(v * m / x for v in rgb), meta)
    f.__doc__ = 'leader (black=%s) driven by %s instead of Y' % (b, driver)
    return f
CHAINS = {**{'g_%s_%s_%s' % (b, k, o): _grid_chain(b, k, o) for b, k, o in GRID},
          'drv_mast_max': _driver_chain('mast', 'max'), 'drv_mast_mix': _driver_chain('mast', 'mix'),
          'drv_0_max': _driver_chain('0', 'max'),
          **{'%s_%s' % (k, o): _pw_chain(k, o) for k in PW_KEYS for o in ('y', 'pre', 'plain')},
          'mpre_rgb_uint': chain_mpre_rgb_uint, 'mob_lo0_yforce': _y_only_force('mpc_lo0', 'mob'),
          **{'spline_%s_%s' % (lo, o): _spline_chain('spline_' + lo, o) for lo in ('l1', '0') for o in ('pre', 'y', 'post', 'plain')},
          **{'hv_%s_t%d_h%d_pre' % (s, t, h): _herm_pre('hv_%s_t%d_h%d' % (s, t, h)) for s, t, h in HV},
          **{'hv_%s_t%d_h%d_yforce' % (s, t, h): _y_only_force('hv_%s_t%d_h%d' % (s, t, h), 'herm') for s, t, h in HV},
          'herm_mpc_pre': _herm_pre('herm_mpc'), 'herm_mpc_lo0_pre': _herm_pre('herm_mpc_lo0'), 'herm_mpc_uint_pre': _herm_pre('herm_mpc_uint'),
          'herm_mpc_lo0_post': _herm_post('herm_mpc_lo0'), 'herm_mpc_lo0_y': _herm_y('herm_mpc_lo0'), 'herm_mpc_uint_y': _herm_y('herm_mpc_uint'),
          'herm_mpc_lo0_plain': _herm_plain('herm_mpc_lo0'), 'mob_lo0_plain': _mob_plain('mpc_lo0'),
          'mpre_rgb': chain_mpre_rgb, 'mpost': chain_mpost, 'wpre_y': chain_wpre_y, 'mpre_rgb_lo0': chain_mpre_rgb_lo0,
          'hermite_y_sop': chain_hermite_y_sop, 'pq_rational_post': chain_pq_rational_post, 'pq_rational_pre_y': chain_pq_rational_pre_y}

# ---------------------------------------------------------------- evaluation ---------------------------------------
def final_clip(rgb, peak):
    nat = pm.apply_matrix(TO_P3, rgb); clipped = tuple(min(peak, max(0.0, v)) for v in nat)
    excur = any(v < 0 or v > peak for v in nat)
    return tuple(max(0.0, v) for v in pm.apply_matrix(P3_TO_BT, clipped)), excur
def strata_key(ref_lin, ry):
    spread = (max(ref_lin) - min(ref_lin)) / max(ref_lin) if max(ref_lin) else None
    g = 'black' if spread is None else 'neutral' if spread <= .01 else 'chroma'
    lb = next((str(v) for v in (.01, .1, 1, 10, 100, 600) if ry < v), 'above600')
    return g, 'refY<' + lb
def evaluate(rows, meta, chain):
    P = prep(meta); fn = CHAINS[chain]; counters = collections.Counter(); invalid = collections.Counter()
    raw_e, raw_s, clip_e, clip_s = [], [], [], []; bins_raw = collections.defaultdict(list); bins_clip = collections.defaultdict(list); srcbins = collections.defaultdict(list)
    for xy, src, ref in rows:
        itp = rgb_to_itp(ref); ref_lin = tuple(pq_eotf(v) for v in ref); ry = lum(ref_lin); keys = strata_key(ref_lin, ry)
        try: mapped = fn(src, meta, P, counters)
        except (ValueError, ZeroDivisionError, OverflowError) as exc: invalid[str(exc)] += 1; continue
        clipped, exc = final_clip(mapped, meta['peak']); counters['final_P3_excursion_pixels'] += exc
        qc = tuple(pq_inverse(v) for v in clipped); ac = rgb_to_itp(qc); ec = delta_itp(ac, itp); sc = tuple(720 * (p - q) for p, q in zip(ac, itp))
        clip_e.append(ec); clip_s.append(sc)
        for k in keys: bins_clip[k].append((ec, sc))
        sy = lum(src); kb = math.floor(2 * math.log10(sy)) if sy > 0 else -99; srcbins[kb].append((ec, sc))
        if all(0 <= v <= 10000 for v in mapped):
            q = tuple(pq_inverse(v) for v in mapped); a = rgb_to_itp(q); e = delta_itp(a, itp); s = tuple(720 * (p - r) for p, r in zip(a, itp))
            raw_e.append(e); raw_s.append(s)
            for k in keys: bins_raw[k].append((e, s))
        else: counters['raw_outside_PQ_domain_pixels'] += 1
    def summ(es, ss): return {**summarize(es), 'mean_signed720ITP': [math.fsum(s[i] for s in ss) / len(ss) for i in range(3)]} if es else None
    def binsum(b): return {k: summ([v[0] for v in vals], [v[1] for v in vals]) for k, vals in sorted(b.items())}
    return {'chain': chain, 'doc': fn.__doc__, 'prepared': {k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items()}) for k, v in P.items()},
            'population': len(rows), 'valid': len(clip_e), 'invalid': dict(invalid), 'counters': dict(counters),
            'raw_all_sample': summ(raw_e, raw_s), 'final_clip_all_sample': summ(clip_e, clip_s),
            'raw_strata': binsum(bins_raw), 'final_clip_strata': binsum(bins_clip),
            'final_clip_by_source_Y_halfdecade': {('%g' % 10 ** (k / 2)) if k != -99 else 'zero': summ([v[0] for v in vals], [v[1] for v in vals]) for k, vals in sorted(srcbins.items())}}
if __name__ == '__main__':
    shot = sys.argv[1]; chains = list(CHAINS) if sys.argv[2] == 'all' else sys.argv[2].split(',')
    path, sha, rows, meta = load(shot)
    out = {'shot': shot, 'input_path': path, 'input_sha256': sha, 'meta': meta, 'frontend': 'repo/ (read-only import of tools.dolby_harness)', 'results': {}}
    for c in chains:
        try: out['results'][c] = evaluate(rows, meta, c)
        except Exception as exc: out['results'][c] = {'chain': c, 'error': str(exc)}
        r = out['results'][c]; fc = r.get('final_clip_all_sample'); rw = r.get('raw_all_sample')
        print('%s %-20s raw %s | clip %s | invalid %s' % (shot, c, ('%.6f/%.6f I%+.4f' % (rw['mean'], rw['p95'], rw['mean_signed720ITP'][0])) if rw else None,
              ('%.6f/%.6f I%+.4f' % (fc['mean'], fc['p95'], fc['mean_signed720ITP'][0])) if fc else r.get('error'), sum(r.get('invalid', {}).values()) if 'invalid' in r else '-'), file=sys.stderr)
    name = 'fable_eval_%s.json' % shot
    json.dump(out, open(name, 'w'), indent=1); print('wrote', name, file=sys.stderr)
