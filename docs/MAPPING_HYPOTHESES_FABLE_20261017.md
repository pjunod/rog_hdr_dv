# Public mapping equation — thinker notes (Fable, 2026-10-17/18)

Working notes for the source-grounded Dolby-Vision-like mapping chain evaluated
against the two retained development lattices (frame256/target27 and
frame714/target27, 34560 samples each, BT.2124 delta-EITP, bar mean <= 1 and
p95 <= 3).  Nothing here is fitted to a frame: every candidate is a fully
specified algorithm driven by the shot's own metadata.  The held-out
shot3/frame1200/target48 check is untouched and remains reserved until a frozen
candidate passes the development comparisons.  Sources are public patents and
open implementations only.  Analysis scripts live in
`tools/dolby_harness/analysis/` and import the frontend read-only.

## Frozen baselines (reproduced by `fable_eval.py` before any candidate was trusted)

| shot | chain | mean | p95 | signed 720*I |
| --- | --- | --- | --- | --- |
| 714 | M pre-RGB rational (MpreRGB) | 6.015329 | 11.063449 | -5.622 |
| 256 | MpreRGB | 1.728467 | 3.893217 | |
| 256 | W pre-Y rational (WpreY) | 1.424080 | 2.975670 | |

714 source triples are exact; the 256 source is reconstructed from the retained
matched-endpoint scale intervals (relative error <= 2^-52) and is labelled a
prospect until the exact native cache is re-read.  Sol's native 256 lattice of
the selected candidate (1.1238648 C / 1.1239740 double) agrees with the local
evaluator to 1e-4.

## Closed lanes (with receipts)

1. IPT/hue-ray lane closed.  Exact Ebner Eq1 and HPE+4 percent coordinates both
   show thousands of lattice rays whose hue sign differs from the reference,
   but a bounded same-ray oracle on 12 witnesses gives delta-EITP 0.11-1.36,
   so the hue mismatch cannot carry a 6.0 mean.  Decimal-60 interval receipts
   reproduce the earlier counts (4180/4316 on 256; 2409/2705 on 714) with zero
   ordering defects after the libm endpoint-rounding repair.
2. Rejected complete chains on both shots (mean 714 / 256): US10600166 Table 1
   Hermite + Eq5 SOP 13.4 / 9.5; PQ-domain rational after SOP 8.9 / 2.9;
   PQ-domain rational before Y 8.8 / 3.3; libplacebo single-pivot spline
   4.05 / 2.27; Eq7 Hermite on MPC knee anchors (any disclosed slope exponents)
   2.56 / 2.45; US9961237 Eq2-5 powered rational (display-anchored, Rolloff 1/3)
   55 / 44; frame-local L1 (ST2094-10 6.1 style min/avg/max over the frame)
   3.18 on 714 and identity on 256; any L1min-anchored rational on 714 6.0.

## Findings that moved the error

1. The pinned MPC CPU caller truncates PQ-decoded L1 nits to UINT before the
   ST2094-10 knee rule, so 714's L1min 0.0084 nit becomes 0 (256's is already
   0).  Evaluating the knee rule with source low = 0 alone takes 714 from 6.02
   to 2.52 (Y placement) / 2.56 (RGB placement); 256 is unchanged.
2. Empirical PQ(Y_source) -> PQ(Y_reference) transfer tables have the same
   residual shape on both shots against the low-0 rational: the reference is
   0.002-0.004 PQ darker in the toe (< 0.14 PQ), 0.005-0.006 PQ brighter at
   0.3-0.4 PQ, and on 714 0.007 PQ darker at 0.6-0.76 PQ, reaching target peak
   at source ~0.80 PQ (L1max is 0.853).  The lower segment is nearly linear in
   PQ (slope ~0.93-0.95) with a black intercept of 0.006-0.008 PQ.
3. A pre-declared grid (black anchor {0, L1min, declared mastering black
   0.005 nit} x {nits rational, PQ Eq7 Hermite} x stage order {Y-SOP first,
   RGB trim first, trim after}) has exactly one member that lowers both shots:
   mastering-black anchor -> 0, low-0 knee, nits rational, SOP on PQ(Y) before
   the curve, colour step after the ratio restore.  Lattice: 256 1.124 / 2.720,
   714 2.419 / 5.553.  This is the implemented candidate
   `open-y-pq-pre-mastblack-v1` (see PUBLIC_RGB_MAPPING.md).
4. Driving the same chain by maxRGB instead of Y (ST2094-10 6.1 / libplacebo
   max mode) gives 256 0.969 / 2.53 and 714 2.384 / 4.91, but flips the sign
   of the 714 saturated-highlight error (+4 I -> -4.7 I).  Recorded as a
   follow-up variant, not adopted; the dominant residual is driver-independent.

## Current residual of the candidate

Both shots: mid-tones too dark (714 refY 3-100 nit, 22k samples, signed I
-2.1 to -4.4; 256 1-10 nit -1.2); 714 highlights >= 300 nit too bright
(+4 to +5 I, concentrated on saturated pixels, candidate chroma radius 5-9
percent larger than reference).  Interpretation: the knee sits 0.004-0.007 PQ
too low and the shoulder starts too late; a single-knee rational cannot express
the extra contrast.  This is a curve-shape question, not an anchor question.

## SOP domain guard decision (MB variant only)

714's retained W trim has S+O = 1.003 > 1, but the affine base exceeds PQ 1
only above PQ(Y) 0.997 (9719 nit), far above the declared L1max 0.853 and the
frame's max 0.813; zero lattice pixels exceed.  Rule: reject a frame statically
if S*L1max_pq + O > 1; fail closed per pixel in the scalar evaluator if
S*PQ(Y)+O > 1; the GPU path keeps its documented finite cap, and scalar/GPU
lattice agreement is the evidence that the cap was never exercised.  The
existing Y-PQ-pre (SG0-only) variant is unchanged.

## Next step

Identify a disclosed mechanism that raises contrast around the knee without a
fitted constant (candidates under review: ST2094-10 Annex B mid-tone handling,
US9961237 slope/rolloff terms expressed on the knee anchors, maxRGB/Y driver
blend), evaluate on both lattices, then re-run the development comparisons on a
frozen candidate before touching the held-out frame.
