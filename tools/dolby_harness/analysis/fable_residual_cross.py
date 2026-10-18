"""Fable349: cross-strata residual of ONE chain (default g_mast_mob_ycol) on a shot: (ref-neutral vs chroma) x (refY bin),
signed 720*ITP, plus highlight saturation diagnostic: for reference Y >= 100 nit, median ratio of reference chroma radius
(hypot(T,P) in metric ITP) to candidate chroma radius, and median ratio of reference/candidate chroma radius in linear
BT2020 (max/min channel spread).  Diagnostic only; nothing fitted.  Run: python3 -I fable_residual_cross.py <256|714> [chain]
"""
import sys, os, json, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fable_eval as fe
from tools.dolby_harness.metric import pq_eotf, pq_inverse, rgb_to_itp, delta_itp
shot = sys.argv[1]; chain = sys.argv[2] if len(sys.argv) > 2 else 'g_mast_mob_ycol'
path, sha, rows, meta = fe.load(shot); P = fe.prep(meta); fn = fe.CHAINS[chain]; counters = collections.Counter()
cells = collections.defaultdict(list); sat = collections.defaultdict(list)
for xy, src, ref in rows:
    itp = rgb_to_itp(ref); rl = tuple(pq_eotf(v) for v in ref); ry = fe.lum(rl)
    try: mapped = fn(src, meta, P, counters)
    except Exception: continue
    clipped, _ = fe.final_clip(mapped, meta['peak']); q = tuple(pq_inverse(v) for v in clipped); a = rgb_to_itp(q)
    e = delta_itp(a, itp); s = tuple(720 * (p - r) for p, r in zip(a, itp))
    spread = (max(rl) - min(rl)) / max(rl) if max(rl) else 0
    g = 'neutral' if spread <= .01 else 'chroma'
    lb = next((str(v) for v in (.01, .1, 1, 10, 100, 300, 600) if ry < v), '>=600')
    cells[(g, lb)].append((e, s))
    if ry >= 30:
        cr = math.hypot(itp[1], itp[2]); cc = math.hypot(a[1], a[2])
        src_lin = tuple(pq_eotf(v) for v in q); sy = fe.lum(src_lin)
        sat[lb].append((cr / cc if cc > 1e-9 else None, (max(rl) / min(rl) if min(rl) > 0 else None), (max(src_lin) / min(src_lin) if min(src_lin) > 0 else None), e))
def med(v): v = sorted(v); return v[len(v) // 2] if v else None
print('shot', shot, 'chain', chain, fn.__doc__)
print('%-8s %-6s %6s %8s %8s %8s %8s %8s' % ('group', 'refY<', 'n', 'mean', 'p95', 'I', 'T', 'P'))
for (g, lb) in sorted(cells, key=lambda k: (k[0], float(k[1].strip('>=')) if k[1] != '>=600' else 1e9)):
    v = cells[(g, lb)]; es = sorted(x[0] for x in v)
    print('%-8s %-6s %6d %8.4f %8.4f %+8.4f %+8.4f %+8.4f' % (g, lb, len(v), sum(es) / len(es), es[math.ceil(.95 * len(es)) - 1], *[sum(x[1][i] for x in v) / len(v) for i in range(3)]))
print('highlight saturation (refY>=30): refY bin, n, median ref/cand ITP chroma radius ratio, median ref max/min channel ratio, median cand max/min, median dE')
for lb in sorted(sat, key=lambda k: float(k.strip('>=')) if k != '>=600' else 1e9):
    v = sat[lb]
    print('  %-6s %6d  itp_chroma_ratio %s  ref_spread %s  cand_spread %s  dE %.3f' % (lb, len(v), round(med([x[0] for x in v if x[0]]), 4), round(med([x[1] for x in v if x[1]]), 4), round(med([x[2] for x in v if x[2]]), 4), med([x[3] for x in v])))
