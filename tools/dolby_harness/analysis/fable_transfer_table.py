"""Fable349: empirical PQ(Y_src) -> PQ(Y_ref) transfer table per shot, beside candidate curve values.
Diagnostic only (no fitting): bins by source-Y PQ (width 0.02), reports n, median PQ_src, median PQ_ref (all samples;
and the <=2%-spread near-neutral subset), and for the same median PQ_src the PQ output of each prepared curve:
  W placement  : SOP(PQ) -> curve                       (Y-only; 714 colour step is ~identity on neutrals, A=1.000021)
  curves       : mpc (file L1min), mpc_lo0, mpc_uint (nits rationals), herm_mpc_lo0 (Eq7 on MPC-rule anchors), hermite_table1
Reads the same inputs as fable_eval.py.  Run: python3 -I fable_transfer_table.py <256|714>
"""
import sys, json, math, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fable_eval as fe
from tools.dolby_harness.metric import pq_eotf, pq_inverse
shot = sys.argv[1]; path, sha, rows, meta = fe.load(shot); P = fe.prep(meta)
def sop(q): return fe.sop_pq(q, meta['sop'])
curves = {
    'mpc': lambda q: pq_inverse(max(0.0, fe.pm.rational_eval(P['mpc']['coefficients'], pq_eotf(sop(q))))),
    'mpc_lo0': lambda q: pq_inverse(max(0.0, fe.pm.rational_eval(P['mpc_lo0']['coefficients'], pq_eotf(sop(q))))),
    'mpc_uint': lambda q: pq_inverse(max(0.0, fe.pm.rational_eval(P['mpc_uint']['coefficients'], pq_eotf(sop(q))))) if not P['mpc_uint']['identity'] else sop(q),
    'herm_lo0': lambda q: fe.hermite_eval(P['herm_mpc_lo0'], sop(q)),
    'herm_t1': lambda q: sop(fe.hermite_eval(P['hermite'], q)),
}
bins = collections.defaultdict(list); nbins = collections.defaultdict(list)
for xy, src, ref in rows:
    ys = fe.lum(src); rl = tuple(pq_eotf(v) for v in ref); yr = fe.lum(rl)
    if ys <= 0 or yr <= 0: continue
    qs, qr = pq_inverse(ys), pq_inverse(yr); k = int(qs / 0.02)
    bins[k].append((qs, qr))
    if min(src) > 0 and max(src) / min(src) - 1 <= 0.02: nbins[k].append((qs, qr))
def med(v): v = sorted(v); return v[len(v) // 2]
print('shot', shot, 'anchors mpc', P['mpc']['source_anchors'], P['mpc']['mapped_anchors'], '| lo0', P['mpc_lo0']['mapped_anchors'], '| uint', P['mpc_uint'].get('mapped_anchors'))
print('%-6s %6s %8s %8s %6s %8s | %8s %8s %8s %8s %8s | %s' % ('binPQ', 'n', 'medSrc', 'medRef', 'nNeu', 'neuRef', 'mpc', 'lo0', 'uint', 'hermlo0', 'hermT1', 'ref-lo0 (PQ)'))
for k in sorted(bins):
    v = bins[k]; qs = med([a for a, b in v]); qr = med([b for a, b in v]); nn = nbins.get(k, [])
    nq = med([b for a, b in nn]) if nn else float('nan')
    cv = {n: f(qs) for n, f in curves.items()}
    print('%-6.2f %6d %8.4f %8.4f %6d %8.4f | %8.4f %8.4f %8.4f %8.4f %8.4f | %+.4f' % (k * 0.02, len(v), qs, qr, len(nn), nq, cv['mpc'], cv['mpc_lo0'], cv['mpc_uint'], cv['herm_lo0'], cv['herm_t1'], qr - cv['mpc_lo0']))
