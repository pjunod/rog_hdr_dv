"""Fable349: SOP domain probe for the MB candidate guard decision.  For each shot: retained W SOP (S,O,P), S+O,
max PQ(Y) and PQ(maxRGB) over the lattice, the resulting q' = (S*q+O)^P, the count of pixels whose affine base S*q+O
exceeds 1 (would need a per-pixel guard), and the count whose post-SOP q' > 1.  Read-only; nothing fitted.
Run: python3 -I fable_sop_domain_probe.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fable_eval as fe
from tools.dolby_harness.metric import pq_inverse
for shot in ('714', '256'):
    path, sha, rows, meta = fe.load(shot); S, O, P = meta['sop']
    qy = [pq_inverse(fe.lum(src)) for xy, src, ref in rows]; qc = [pq_inverse(max(src)) for xy, src, ref in rows]
    over_y = sum(1 for q in qy if S * q + O > 1); over_c = sum(1 for q in qc if S * q + O > 1)
    print(shot, 'sop', meta['sop'], 'S+O=%.9f' % (S + O), 'S*1+O>1:', S + O > 1)
    print('   maxPQ(Y)=%.6f -> q\'=%.6f ; maxPQ(maxRGB)=%.6f -> q\'=%.6f' % (max(qy), (S * max(qy) + O) ** P, max(qc), (S * max(qc) + O) ** P))
    print('   pixels with S*PQ(Y)+O>1: %d ; with S*PQ(maxRGB)+O>1: %d ; lattice n=%d' % (over_y, over_c, len(rows)))
    print('   PQ(Y) at which S*q+O=1: %.6f (= %.1f nit); L1max PQ %.6f' % ((1 - O) / S, fe.pq_eotf((1 - O) / S), meta['l1'][2]))
