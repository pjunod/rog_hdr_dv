# Fable341 joint equation analysis — active, not acceptance

Shared card t_bb5b2ce0 (Fable run341 holds the claim); Astra joint context t_6659274d with its
note under workspaces/astra-joint-t_6659274d/. Fable write ownership: this file and
fable_mobius_check.py only. Fable edits no implementation, sends no native request. Sol's
preserved state (verified read-only 19:30 EDT): repo c18b9d2 + 13 uncommitted files, library
committed 5a7500f (clean, NOT yet natively compiled), ABI366 upload chunks 0..27 of
stage_build_y366_338.py landed natively (last 06b3a2e7), chunk 28+ pending, mailbox empty.

## Done, current, remaining

Done: read HANDOFF/brief/CONTINUE336/CHECKPOINT338, all run336–340 receipts and decisions;
verified native/upload state; local analytic Moebius/cross-ratio check on retained neutral
points (fable_mobius_check.py; arithmetic only). Current: reconciling with Astra one cached
audit for a Sol continuation card. Remaining: everything in the brief — full-raster and
independent-content agreement mean<=1/p95<=3, implementation, independent adversarial
review/fixes, one affected unit batch/gate, merge, versioned Ubuntu delivery. Best retained
WpreY 1.4240802336/2.9756704295 still FAILS mean. Nothing here changes that.

## Inputs (immutable, from retained receipt 4dc56b51 and run336 constants)

Reference-black stratum: 8439 samples, source Y .0049995–.0077208 nit, reference code floor
(PQ 7.15e-7/1.13e-6; linear Y ~1.7e-14 nit — PQ and nits kept distinct per Astra 2096).
Low neutral xy3728,1536: source Y .01588074573021141, reference .0013544853 nit.
Bright neutral xy4080,672: source Y 1.4757298254554523 (script uses 1.476; effect <0.1%),
reference .8299804 nit.
CORRECTION (Astra 2108, accepted): .0077208 is the MAX source Y of the ALL-COLOUR
reference-black stratum, not a third neutral observation. Result 1 therefore shows that
a Moebius through low+bright cannot also pass through the plateau's upper edge; it is not
a three-neutral-point proof and says nothing about whether every near-black sample is on
or off a unique law. Result 3's quadruple conditioning numbers are SIMULATED/analytic,
not cached measurements. Result 2's negative-intercept curve is diagnostic only: it is
NOT an allowed source anchor, pedestal or renderer coefficient.
Audit spec v2 (reconciled, supersedes draft v1 below) is recorded on t_b69e54cd.
W chain: x = E(max(1e-5, max(1.014*PQ(Y)-.014, 0)^(2000/2001))), f_W(x)=.6831692335*x/(1+.00082932020*x).

## Result 1 — the black plateau cannot lie on the scalar law

Forcing f=(a+bx)/(1+cx) through (x(.0077208),0), (x(.0158807),.0013545), (x(1.476),.82998)
gives c=-0.3387 (pole at x=2.95 nit) and negative output above 2 nit. Chord slopes
black→low 0.414 versus low→bright 0.695 are concave-up, impossible for a monotone Moebius
with c>0. Therefore the reference black plateau is a floor/clamp outside the family (or the
placement is wrong), and floor-code references are ineligible for any cross-ratio quadruple.
A CR audit admitting them fails trivially and proves nothing.

## Result 2 — eligible neutrals are consistent with the rational family, not with W's anchors

Through low, bright and the DECLARED peak (L1max 3233.157→600, an assumption, reference peak
unmeasured): a=-0.0014075 nit, b=0.696032, c=0.00084607, b-ac>0, no pole. It reproduces the
plateau by negative intercept + zero clamp (.0077→-0.00092→0) and tracks W within 2% above
10 nit (10→6.107 vs 5.996; 30→18.61 vs 18.27; 100→60.32 vs 59.29). Versus W: b ratio 1.0188,
intercept -0.0014 nit, crossover ≈0.1 nit post-SOP. Reading: a +1.9% gain and a negative
black intercept — a contrast/pivot error, not a black-offset error. Robustness: HALF
reference interval ±0.13% (bright) / ±0.05% (low); the low point violates exact pure-Y
collinearity by ~0.5% per channel (Astra retained_ray_interval), so its Y carries ~0.3%
model ambiguity. The gain and the intercept SIGN survive; the intercept magnitude does not.
The implied zero crossing (~0.002 nit post-SOP, ~0.011 nit source) equals neither mastering
.005 nor L1min 0; Astra's mastering-intersection lowers b to 0.631 (wrong direction). Cause
left explicitly unexplained; no candidate anchor is proposed for rendering.

## Result 3 — cross-ratio conditioning

With HALF-neighbor reference intervals propagated to Y: wide quadruples (0.016/0.3/1.5/8 nit)
|Δln CR| p95 ≈7e-4 (well conditioned); quadruples from only the 33-sample .15–.2 PQ cluster
p95 ≈7e-3 (marginal) and, being gain-invariant, blind to a 1.9% gain. Hence the audit must
use all-colour samples passing Astra's per-channel scale-interval overlap precheck across
reference-Y bins, with floor-code references excluded and every exclusion counted.

## Proposed single cached audit (joint spec, draft v1 for the Sol card)

On the existing 34560 cache, per sample: (1) reference HALF-neighbor interval per channel →
ref/src scale interval per channel → overlap flag; floor-code references excluded; zero-source
channels handled separately. (2) Eligible: x=E(SOP_W(PQ(Ysrc))), y-interval from Yref interval.
(3) Empirical transfer, not a fit: 1/8-decade log-x bins, count, median and interval of y/x,
W prediction per bin, per-bin gain vs W and sign-flip x. (4) Cross-ratio on predeclared
quadruples of bin medians from every second bin: CR(x) vs CR(y)-interval. (5) Consistency of
one Moebius through three predeclared bin medians (lowest eligible, 1 nit, highest) with all
other bins within interval. No coefficient leaves the JSON into rendering. Discrimination:
CR holds + uniform gain/intercept vs W → anchor/knee inside the family; CR fails on wide
quadruples → different scalar law; many overlap failures → colour stage dominates.

## Fable344 — colour lead (US8593480 Eq26–31) checked against retained points

Status 2026-10-17 run344 (three-worker direction: thinkers keep deriving while Sol343 builds).
Done: Sol343 ABI366 compiled (library 5a7500f/tree 77878b06), GPU dev render 94c753eb
(GPU/ref 1.4233977/2.9758394 FAIL; scalar/GPU agreement mean .00117505 — implementation
closure only), joint audit v2 executed once (eligible 3646, scale-overlap FAIL 22387,
floor 8527, quad 0/6/12/18 CRx 1.00453 inside CRy [.99226,1.00790] — family not refuted).
Current: resaturation analysis below; proposed per-sample exponent discriminator awaiting
Astra confirmation. Remaining: unchanged (full-raster pass, review, batch, merge, Ubuntu).

Script fable_resat_check.py SHA256 1b92419ad3ad535cc72718d79ea424ff98069a8ac8d3fa150e99faf9a3316c2b;
executed output fable_resat_check.json SHA256 c8a40467045d26199d38bd17c39bbe8bcec367104d6bfd4079fdfbac55932612.

Reconciliation with Astra (v2 excludes the low neutral because it fails scale overlap):
under the ratio-operator hypothesis the reference Y of that point is Yout·Σw_i r_i^(1+e);
with e=−0.36 and |ln r_i|≤0.4% that factor differs from 1 by ~e(1+e)/2·Var(ln r)≈1e−6,
far inside the HALF interval, so the point's Y-secant (and the zero-origin refutation that
uses it) survives the colour explanation — it is excluded from the audit by rule, not wrong.

- Eq27 derived independently: n L^n (c2−c1c3)/((c1+c2L^n)(1+c3L^n)); rendered c3 in the
  first factor is a text error (numeric check 2.0224 vs −1.98).
- Low neutral xy3728,1536: the three channel scales fit output_i = Yout·r_i^(1+e) with
  e=−0.361 (R/G interval [−0.53,−0.22]); residuals 3e−4 < HALF half-width 9e−4. The
  reference is DESATURATED relative to pure-Y ⇒ log-log slope c>1 ⇒ c≈1.50 (1.32–1.72)
  through f(c)−c with disclosed k1=1.6774, k2=.9925.
- Base rational alone gives e≈2e−6 (Astra, confirmed). The W composite slope at 0.0159 nit
  is 1.885 (e=−0.67, too much); the reference secant 1.416 (e=−0.29, slightly under). If the
  operator is driven by the composite slope, the true toe has log-log slope ≈1.3–1.7 at
  0.016 nit — a shape constraint, consistent with the secant topology. One point; sign robust.
- Bright neutral: predicted ln-scale spread 7e−4 < HALF 2.5e−3, so a common scale must exist;
  matches Astra's nonempty intersection.
- Negative exponent ⇒ Σw_i r_i^(1+e) ≤ 1 (concave), negligible for neutrals: this operator
  cannot repair the achromatic mean-1 failure; it targets the 65% non-collinear population.
- Proposed discriminator (cached, no render; awaiting Astra): per-sample exponent e_s for
  overlap-failing samples, fraction e_s<0, median per source-Y bin, independence from chroma.
- Predeclared predictions frozen in fable_exponent_predictions.py (SHA256 dd379b86d1a43e35
  613d9895b5017074a36b0fd084342531c8e1d65dafb22e81) / .json (07caee5ce19ecd9a37a4f7cdf8b015
  b8606d3148af3cf890506f7dca5706185b): D_W median e −0.74 @0.0146 nit → −0.046 @1.1 → sign
  change to +0.002 @35 nit → +0.14 @460 nit; D_sec −0.29 in the lowest nonfloor bins.
  HALF-driven estimator noise σ(e_s)≈0.005 at ln-r spread 0.1. Falsification rules (a)–(d)
  recorded in the JSON; the bright-side sign change is a second independent signature.

## CHECKPOINT Fable344 (2026-10-17 ~20:10 EDT) — resume point for a fresh execution

State of the lanes: Sol t_b69e54cd COMPLETE (repo 0a805e02bf05fbc2e8713e9e663bbdd61290d6c2 /
tree f5fb649b, library 5a7500f / tree 77878b06, ABI366 compiled 11df1b13, GPU dev render
94c753eb 1.4233977/2.9758394 FAIL-mean, scalar/GPU agreement .001175; audit v2 executed once,
local evidence343/joint-audit343.json SHA 1c6d3673…; 714 provenance DRAFT only, no vendor
call; no native request in flight; native/source idle awaiting an EXPLICIT builder claim).
Astra t_6659274d run345 live (notes under workspaces/astra-joint-t_6659274d/, incl.
ratio_interval_derivation345.md, ROOT_PATENT_FOLLOWUP.md, retained_exponent345.py).
Fable owns ONLY: this note and fable_*.py/.json here; no implementation edits; no native.

Fable files (all executed, hashes exact):
  fable_mobius_check.py 40c7d5a8… / .json 7bf140f6…   (run341: a=0 refuted, a<0 Möbius diagnostic)
  fable_resat_check.py 1b92419a… / .json c8a40467…   (Eq27 derivation; low neutral e=−0.36 under pure-Y adaptation;
                                                      §4 bright used lower-neighbour codes — see Astra correction, conclusion unchanged)
  fable_exponent_predictions.py dd379b86… / .json 07caee5c…  (frozen D_W/D_sec predictions, before data)
  fable_toe_profiles.py cf622562… / .json 65b8913e…        (frozen T0–T3 slope-vs-Y profiles)
  fable_exponent_feasibility.py 37cb665b… / .json 26647f96… (SUPERSEDED by v2; retained)
  fable_exponent_feasibility_v2.py 9996cfb6… / .json 8560c733… (CURRENT RESULT: source enclosure
        8-corner, per-sample D_W, full-bin H_shared, avg-rank Spearman; counts identical to v1:
        20358 feasible / 5672 infeasible; D_W rejected 11968/20358, 100% above 3 nit)
  fable_dark_infeasible.py c3570af5… / .json 6e40490c…      (RESULT, cause of dark infeasibility)

Mathematical conclusions so far (all diagnostic; nothing enters rendering; WpreY 1.4240802336/
2.9756704295 still FAIL):
  1. Zero-origin rational at the W placement is refuted by the two retained nonblack neutrals +
     declared peak (rise-then-fall secants); general a≠0 Möbius is NOT refuted (v2 CR interval
     contains CR_x) and the a<0 diagnostic curve reproduces the black plateau. Toe/shape/order
     mechanism remains the open scalar question.
  2. Pure-Y ratio-exponent adaptation of US8593480 Eq28–31 is REJECTED as the colour explanation:
     88–97% of samples 0.006–0.05 nit admit NO single ratio exponent (not floor/subnormal
     artefacts); where feasible (≥0.3 nit) every per-sample e-hull excludes 0 and the hull
     MEDIANS plateau near −0.034 above 3 nit, but per-bin shared intersections are EMPTY in
     almost every bin (only 13.3/17.8/31.6 nit, n=11/12/4, share [−.033,−.032]) — no single
     exponent is a population law even where per-sample feasible. Per-sample e_DW(Y) is
     rejected in 11968/20358 (100% above 3 nit, slack .011–.033). Average-rank Spearman
     (e_mid, chroma spread) +0.5…+0.9 in 0.3–4 nit bins. Scope: rejects the pure-source-ratio
     adaptation only, not post-F/SOP consumer chains nor native-P3 per-channel maps.
     (Correction of an earlier overstatement, see card comment after 2150.)
  3. Structural: the linear-RGB consumer colour expression v_i((1+cw)v_i/Y)^sg cannot fit the
     dark references for ANY sg/cw; a pure per-channel map ref_i=F(src_i) is also rejected
     (larger input → smaller output across pixels). The dark colour operator is coupled
     (luminance/neighbour-dependent) and per-channel, in the desaturation direction.
  4. Per Astra: full patent chain is per-channel F then r^(H(c)−c), relative exponent H(c)−1;
     working basis target-native P3. Observed negative relative exponent would imply c<1 there.
  5. v3 OUTER-interval rerun (fable_exponent_feasibility_v3 0844ed5b…/3953ccb4…) reproduces
     v2 counts exactly: 5672 pure-Y-ratio incompatible is a sufficient outer-interval result,
     not a corner artefact. Astra accepted as robust numerical diagnostic.
  6. Four two-parameter per-channel families (lin/PQ × ratio/affine) in BT2020
     (fable_colour_families 3b684bb1…/cfb5d032…) and P3 (fable_p3_families 5a9adf73…/
     c78dc04c…): dark <0.05 nit 87–97% infeasible under ALL of them in both bases; above
     ~1 nit per-channel PQ-affine (d>0, A .86→.92) is feasible for ~100%. Corner-hull
     diagnostics, not proofs.
  7. Native-P3 shared-monotone-F sweep (fable_p3_monotone CURRENT 0fbe5fbd…/284c0857…;
     first run 9bb469ed…/6f5edbac… superseded for per-channel bin denominators only;
     counts identical): pooled 77281/78088 observations
     violate monotonicity (near-total up to 4 nit); per-channel R 51% / G 38% / B 98%;
     within-pixel channel-order reversals 939/26030, concentrated 0.005–0.03 nit → rejects
     positive local gain → shared monotone F for those pixels. Not a ΔE statement.
  8. Reversal pairs (fable_reversal_pairs 031053ee…/05b4500a…): 939 P3 / 934 BT2020 / 568
     both; dominant signature G pushed below channels it exceeded in source (B>G 554,
     R>G 188 in P3), G never raised above brighter R/B; margins p50 2.8%, p95 17%, max 76%.
     Not a basis artefact. Hypothesis handed to Astra's source trace: a coupled stage relative
     to a G-heavy luminance quantity with a negative near-black lobe. No candidate proposed.
  [Items 8–9 interpretation SUPERSEDED by Astra345's algebra: O_i=a(Y)C_i+b(Y) preserves all
   strict pair orders (a>0) or reverses all (a<0); no Y-relative stage can be selectively
   G-specific; raw pair counts need conditioning on ordered-source-pair denominators.
   Replacement accounting: fable_reversal_conditioned.{py,json}, item 10 below.]
  9. Reversal direction (fable_reversal_spread 5d31d713…/e7dce72b…): reversal pixels still
     net-desaturate (794/939 smaller spread, like the dark control 3578/4119), but G swaps
     from source max (473) to reference MIN (462) while R/B identities hold — a G-specific
     hue rotation at 0.005–0.03 nit, not stronger desaturation. Excludes any scalar
     saturation gain about Y for these pixels; consistent with a matrix stage with negative
     G off-diagonals in a non-linear domain near black. Authored SG=0 so not the L2 trim.
  10. Conditioned accounting (fable_reversal_conditioned 0fcd601b…/b1569fd3…): all 939
      reversal pixels have reversed AND preserved strict pairs (939 rev / 1878 pres / 0 und)
      → every common-scale stage O_i=a(Y)C_i+b(Y) excluded for them. Conditioned on ordered
      source pair: B<G 3.8% (20% at 0.006–0.01 nit), R<G 2.1% (7–13%), R<B 1.3%, B<R 0.4%,
      G<B 0/11250, G<R 4/17166. Standing statement: the reference lowers G relative to the
      other channels in a sizeable fraction of dark pixels; G never overtakes a brighter
      channel. Open: Astra's Eq28–31 selective-inversion condition appears to predict the
      channel far from Y (R/B) losing, not G, unless base elasticity is non-monotone near
      black — to be checked by Astra's exact derivation.
  11. Astra root_compensation_order345 (d657e0d7…/67f03731…): toy F(C)=C−1 shows Eq28–31
      compensation CAN selectively invert one pair (existence proof, no HDR parameters);
      finite-pair criterion log(F(Ci)/F(Cj))/log(Ci/Cj) < −q(Y). My 2193 'G nearest Y ⇒
      least likely loser' exclusion WITHDRAWN (secant over the pair, not loser derivative).
      fable_reversal_loser (78fa68b6…/19307bc1…): loser G 742/B 132/R 65; loser rank
      nearest-Y 419 / middle 477 / farthest 43; winner & loser same side of Y 857/939;
      median |Δln| loser–winner ≈ 0.035. Constraint for any base/SOP hypothesis: the pair
      secant must fall below −q(Y) for these close pairs while the 1878 preserved pairs in the
      same pixels must not. Current a=0/n=1 base has q≥0 → cannot. Astra deriving bounds for
      full original-metadata SOP+rational chain (COUPLED_ORDER_TRACE345.md).
  12. Interval-robust side-of-Y (fable_reversal_sideY_robust 445eab6b…/9bfa37f7…): 539
      both-strictly-below-Y (ln(Y_lo/loserHi) p50 0.11), 318 both-strictly-above-Y, 82
      undetermined; both classes in every dark bin. Astra347 lemma: nonincreasing elasticity
      on [C_w,Y] forbids the 539; nondecreasing on [Y,C_l] forbids the 318 → a single
      Eq28–31 compensation on a shared base needs NON-monotone elasticity near black. Astra's
      exact SOP+rational composite (c_F 10.49→1.885→1.062, q −8.98/−0.67/−0.04,
      composite_elasticity347 0a801264…/335e69cc…) — CORRECTION (Astra 2213): ten sampled
      cF values do not prove monotone elasticity over each reversal interval, so the lemma
      route is NOT an independent exclusion; the SOP composite is excluded by the exact
      low-neutral finite-pair q interval alone (item 13), which is sufficient.
  13. Astra347 family-wide: for powered rational F=(a+b·vⁿ)/(1+d·vⁿ), a<0, sign(dc/dt)=
      sign(a−b·d·t²)<0 ⇒ monotone-decreasing elasticity ⇒ lemma excludes the ENTIRE
      negative-intercept powered-rational + same-curve Eq28–31 family for the 539 robust
      below-Y inversions. Exact pair-ratio interval (composite_ratio_bounds347 afb2a5a1…/
      2874bbab…, readback verified): low neutral xy3728,1536 needs q∈[−1.3955,−1.1114], root
      composite q=−0.6738 outside for any K>0 → the sufficient exclusion. Fable check
      offered for Astra verification: a>0 gives non-monotone elasticity but n=1 ⇒ c<1 ⇒ q≥0
      ⇒ no reversal; only n>1 / composed-SOP / nonzero-normalization branches remain open.
  14. fable_posintercept_check (e3cd7c89…/5997768c…): a>0, n=1 ⇒ c<1 ⇒ q≥0 (200k samples,
      0 violations) ⇒ no reversal; n>1 witnesses q<0. Scope (Astra): monotone pole-free
      a,b,d>0, b−ad>0 only; no generalisation to d<0 or arbitrary normalisation. n=1 branch
      closed for both intercept signs within that scope; open: n>1 / nonzero normalization.
  13b. Astra347 anchor extension: declared target black 0 + same D65 ⇒ F(x_black)=0 ⇒ a≤0;
      lemma covers a=0 (d≥0). Whole target-zero-black, d≥0, shared powered-rational +
      same-curve compensation chain excluded for ALL n>0 by the 539 robust below-Y reversals
      (scope: not d<0, composed SOP, nonzero effective black/normalisation, other bases/stages).
  15b. Cross-shot caution (Astra): compare 714 MpreRGB 6.0153/11.0634 with frame256 MpreRGB
      1.72847/3.89322 (same operator), not with the Y-variant 1.42408/2.97567; 714's 34305
      chromatic samples do not isolate scalar vs coupled defect; my 'scalar anchor defect'
      downgraded to 'evidence against a frame256-only dark repair'. Discriminating stratum:
      714's 251 nonblack-neutral samples with exact paired rays. 714 evidence LOCAL:
      evidence346/joint-audit714-346.json 8b2c7a7c… (20,893,190 B), receipts346 227468d8….
  16. IPT chroma-ray invariant audit (fable_ipt_ray_invariant.py, Astra amendments applied:
      full population, flags informational, peak bound per run, outer det interval, dot-product
      antiparallel test, neutral/clip-possible classes, v2 schema guard). FRAME256 RESULT
      (6d29f446…/058f323c…): 34560 rows, 8479 excluded (floor, negative ref low), 26034
      clip-free: det EXCLUDES 0 in 4180 (all below ~0.24 nit; 643/685 at 0.01 nit; zero
      above 1.3 nit), margin p50 0.23/p95 0.76; antiparallel 0; 47 clip-possible all det∋0.
      Reading: in the frozen HPE+4%/Ebner embedding no tone curve/alpha-beta/I-only detail
      stage of the disclosed chain can repair M_pre_IPT_Eq8 for those dark samples — the
      embedding itself is wrong there; det∋0 above 1 nit is necessary-only. Rejects this
      concrete embedding, not every undocumented matrix.
      714 RESULT (fable_ipt_ray_invariant_714 64315ff3…/3a1156a1…; exact source triples,
      xy-joined, LMS≤10000, clip-free-only margin; frame256 script relabelled b3de6a2f…):
      34560 rows, 0 excluded, clip-free 34556: det EXCLUDES 0 in 2409 (dominant 0.04–0.24
      nit, ~5–10% at 0.3–1.3 nit, ≤4/bin above 3 nit, none above 32 nit), margins p50 .035
      /p95 .26/max .86; antiparallel 0. Both genuine shots reject the frozen HPE+4%/Ebner
      embedding on a clip-free dark-to-mid population; rejection luminance tracks each
      shot's content floor → embedding near-black behaviour, not frame content. Scope: this
      embedding only. Exact-neutral MpreRGB chain for scalar work (Astra): A=(1+CW)^SG =
      1.0000211112507182 on 714 multiplies z before the rational; never drop SG / no Y sub.
      714 nonblack-neutral strata (Astra readback): 233 at refY 100–600 signed I +.96; 6 at
      10–100 I −11.03; 7 at 1–10 I −8.84 → mid-tone deficit + slight bright overshoot.
  17. Neutral contract reproduction on 714 (fable_neutral_contract_714 b2196c77…/e2751717…):
      exact chain re-implemented locally, coefficients reproduce bit-for-bit (max |Δ| 0.0),
      A=1.0000211112507182. 308 near-neutral (≤2% spread) samples: dPQ(ref−pred) +0.003 at
      0.022 nit (ratio 1.37), +0.004 at 0.1–0.3, +0.010 at 1–3, +0.012 at 3–10, +0.015 at
      10–30, +0.016 at 30–100, +0.008 at 100, +0.001 at 300, −0.0015 at ≥1000 nit (n=251).
      Hump peaking ≈20% luminance deficit at 10–50 nit, bright stratum slightly too bright.
      Implied-knee shape diagnostic: floor 5.9 / mid 5.0–5.3 / bright 3.97 vs contract 4.37
      → no single mid-anchor/normalisation/SOP-order scalar correction fits all strata; the
      anchor contract (which L1 points map where; zero-black end) differs, not a coefficient.
      Nothing fitted or promoted.
  18. Astra 2230/2231: on 714 metadata the Hermite/original-cosine lower segment is identity
      (TMid = .272 PQ = 6.971 nit; HEAD clamps 0, TAIL amplitude 0) while MPC maps the knee
      to .23838841046057618 PQ = 4.3669 nit (matches my dst_pq to 1e−14). Reference-implied
      knee ≈ 5.0–5.3 nit (PQ ≈ .25) in midtones lies strictly BETWEEN the two frozen scalar
      contracts (MPC ~20% dark, identity ~30% bright); neither single-knee shape fits floor
      (5.9) and bright (3.97) strata. Cosine-vs-cutoff cannot repair 714; no image experiment.
  17b. Narrowings (Astra 2234/2235, accepted): endpoint residuals NOT observed (whole-chain
      SOP/colour moves input before the rational; endpoints unmeasured); implied-knee spread
      excludes only the ONE free-knee rational with fixed pre-SOP x and endpoints; IPT
      failures do not identify the 4% crosstalk as cause; rejection-Y profiles on two shots
      do not prove content-floor scaling; 256 'excluded 8479' combines source+reference bounds.
  19. Interval-robust knee test (fable_knee_interval_714 1eab2252…/27454872…): 308/308
      outer knee intervals; all-sample AND every per-stratum intersection EMPTY (floor 5.85–
      6.06, 1–10 nit 5.01–5.30, 10–100 5.03–5.36, ≥1000 3.79–5.03 vs contract 4.367) →
      frozen one-knee rational (fixed pre-SOP x, fixed endpoints) robustly rejected on 714
      near-neutrals; near-neutral reference not a function of post-SOP Y alone (observation).
      Does not exclude changed SOP order/normalisation; selects nothing.
  20. DECISION (Blocker status comment after 2238): Astra347 primary-source discrepancy —
      Ebner/Fairchild 1998 Eq1 XYZ(D65)→LMS (.4002,.7075,−.0807)/(−.2280,1.1500,.0612)/
      (0,0,.9184) (PDF 6c2f5905…) vs libplacebo HPE variant + 4% crosstalk. Fable AGREES to
      ONE source-faithful Eq1/PQ/Ebner invariant audit on both JSONs, same rules, side by side
      with frozen results, on resume. Preconditions: Astra pins BT2020→XYZ(D65) convention
      and rows as printed (no renormalisation unless sourced); negative LMS counted/excluded;
      absolute PQ replaces .43 per §0037; necessary-condition only; no sweep/fit/render/
      renderer change; not accuracy evidence.
  21. Fable349 (resumed after recovery t_91c655c1) — PRIMARY-SOURCE Eq1 IPT invariant audit
      executed once per shot (fable_ipt_ray_invariant_eq1.py 9d65df94…; self-checks exact-rational
      BT2020→XYZ→Eq1 composition against Astra ebner_coordinate347.json ac13da38… before reading
      samples; absolute 10000-nit PQ per Table 1/§0037; paper LMS'→IPT; no crosstalk/renorm).
      FRAME256 (…_eq1_256.json 7aa4f9ae…): excluded 8479 (same set), clip-free 26034, det∌0 in
      4316 (frozen HPE+4%: 4180), margin p50 .227/p95 .751/max .961; zero rejections >1.33 nit.
      714 (…_eq1_714.json e59b41dd…): clip-free 34556, det∌0 in 2705 (frozen 2409), margin
      .034/.263/.876; same luminance profile. CONCLUSION: the patent-cited Eq1 coordinate is
      rejected by the same necessary condition on both shots, slightly MORE than the renderer
      variant → the LMS-matrix discrepancy is real but is not the cause; the dark P:T ray change
      is robust to the near-HPE coordinate family. Open: a stage that is NOT a common P,T scalar
      (other chroma coordinate, non-I-only local stage, pre-clip black-volume/gamut, non-pointwise).
      Not accuracy evidence; nothing promoted. Proposed next: rejection-set overlap + det sign/
      direction (Fable); named non-common-scalar stage trace (Astra).
  22. SOLO MODE (owner 21:23/21:25 EDT: Fable sole thinker; Astra paused; Sol/GPT workers available for
      builds). IPT lane closed (v2 Decimal receipts, counts unchanged; hue mismatch not the mean deficit).
      Local all-sample evaluator fable_eval.py (read-only import of repo/ tools.dolby_harness; 714 exact
      triples; 256 source reconstructed from scale intervals = labelled prospect) REPRODUCES baselines
      (714 6.015329/−5.6223 I; 256 1.728467 MpreRGB, 1.424080 WpreY). Rejected complete chains (both
      shots): Table1 Hermite+Eq5 (13.4/9.5), PQ-rational post/pre (8.9/2.9, 8.8/3.3), library spline
      (4.05/2.27), Eq7 Hermite on MPC anchors (2.56/2.45), L1min-anchored anything on 714 (6.0).
      KEY FINDINGS: (i) pinned MPC caller truncates L1 nits to UINT → 714 L1min .0084 nit → 0; lo=0 knee
      rule alone takes 714 6.02 → 2.52 (Y) / 2.56 (RGB); 256 unchanged. (ii) transfer tables
      (fable_transfer_table.py): identical residual shape on both shots vs lo0 rational — toe −.004 PQ,
      mids +.005, 714 highlights −.007; lower segment ≈ linear in PQ with intercept ≈.006–.008 PQ.
      (iii) pre-declared grid (black {0,L1min,.005} × {rational,Eq7} × order {Y,pre,post}): only
      black=.005 nit→0 + lo0 knee + nits rational + Y-SOP lowers BOTH: 256 1.124/2.720, 714 2.432/5.569
      (ycol 2.419). Constant knee_adaptation .4 (no ramp): 256 1.298, 714 2.494 (Hermite 1.832 but 256
      1.496). Residual: 714 mids −2.6…−4.1 I, highlights +4…+5.4 I; 256 same signs smaller.
      US9961237 Eq2–5 powered rational REJECTED (fable_eval_*_powered.json): display-anchored (.005/4000,
      Shift=S2T/2, Slope=S2T+1, Rolloff 1/3) 714 55.4 / 256 43.6 (I +42, far too bright — agrees with
      Astra's analytic 1.476→5.11 nit); knee-anchored Rolloff-1/3 variants ≥35 (probably a pole inside
      the anchor range; not investigated further); Rolloff 1 = PQ Möbius 4.05/1.21 (worse than nits).
      CANDIDATE DECISION (Fable349, solo): 'open-y-pq-pre-mastblack' = existing PL_DOVI_DM_OPEN_Y_PQ_PRE
      operator (absolute-PQ SOP on BT2020 Y, nits rational once, restore RGB ratios) with TWO preparation
      changes, both source-grounded, no fitted constant: (a) knee rule evaluated with source lo = 0 (the
      pinned MPC caller's UINT truncation of L1min nits; 256 already 0), (b) rational black anchor
      x1 = declared mastering display minimum luminance (hdr metadata min_luma, .005 nit on both shots)
      → 0, i.e. the shader's named MasteringMinLuminanceNits semantics for x1; CW/SG inside-exponent
      colour step applied to PQ RGB AFTER the ratio restore so nonzero-SG shots (714) are supported.
      Lattice results: 256 1.124/2.720 (I −.92; black 8439 → 0.000, neutral .26, chroma 1.50);
      714 2.432/5.569 (ycol 2.419/5.553; I −.82). Both LOWER than W (1.424/2.976; 6.015/11.063); both
      still FAIL 1/3 (714 mids −2.6…−4.1 I, highlights ≥300 nit +4…+5.4 I = contrast/shape the single-knee
      rational cannot express; 256 same signs smaller). Selection among 3 pre-declared black anchors ×
      fixed knee rules was made on the two development shots → honest test is the untouched 1200/48.
      HANDOFF: Sol card created for scalar+GPU integration (new appended enum, old variants retained),
      native build, exact-cache lattice reproduction (256 exact source replaces my reconstructed
      prospect), full-raster official comparison 256+714, then owner-requested 1200/48 check (consumes
      the holdout; a new untouched reservation will be needed for any later candidate).
      Receipts: fable_eval.py / fable_transfer_table.py / fable_eval_{714,256}_{grid,powered}.json (SHAs in thread).
  RESUME POINT (budget checkpoint ~95/100, 2026-10-18 ~02:15Z; superseded by item 21 for the IPT
  lane, otherwise still valid): all scripts above executed,
  SHAs in thread (2229 latest); lease released, no claim pending; nothing fitted/promoted.
  NEXT (Fable): test Astra's source-traced anchor/black-end contract candidates against the
  714 hump + 256 toe (local, no fit); cross-shot neutral check on 256 with ITS file-bound SOP
  (1.014/−.014/2000/2001) and curve (0, .68316923…, .00082932…) — never 714 constants.
  Astra: anchor-contract source trace; IPT_RAY_CONTRACT347.md / coupled stages.
  15. Sol346 714/target27 complete W MpreRGB: mean 6.0153 / p95 11.0634 / max 16.2296 FAIL,
      signed ITP [−5.622,+.099,+.041] (chain too dark), clamps 0, 414 pre-volume outside P3
      (409 negative), black 0 / nearblack 4 / chroma 34305; overlap-fail 29881, eligible 4679;
      joint JSON 8b2c7a7c… (20,893,190 B) with exact source/reference triples. 714 =
      DEVELOPMENT. Fails differently from 256 (no dark population; mid-tone I deficit) →
      scalar anchor/normalization defect, not a dark colour repair. WARNING: predictions/
      toe_profiles/resat/mobius/dark_infeasible/feasibility v1–v3 carry 256 driver constants;
      only interval-column-only scripts (families, p3_monotone, reversal_*) may run on 714.
  Next ownership (agreed with Astra 2211/…): Astra → IPT full-stage contract + interval/clip/
  neutral edge cases; Fable → (a) IPT chroma-ray invariant audit det=P_src·T_ref−T_src·P_ref
  ∋0 in frozen HPE+4%/PQ/Ebner basis from receipt c362b7b7, clip-active samples separated,
  256 then 714; (b) challenge which original-metadata scalar anchor/normalization contract
  remains source-supported after failed MPC/Baker/post/direct variants.
  Lane 00:45Z: Sol346 acquired 714 EXR once (cd03962d…, official producer sequence, XML edit
  map association); staging next; Astra347 resumed after 30-min wall limit (not a blocker).
  Joint direction (Fable+Astra agreed): no single scalar/rational/ratio/local-only dark
  repair is promotable; investigate SPECIFIED coupled chroma/gamut/black-volume stages;
  obtain second genuine shot.

Build decision executed: Sol continuation 2 t_eb84d7f1 created (714/target27 ScopeA
acquisition per 2079, complete nonzero-SG W MpreRGB chain only, v2 audit columns, 714 →
development evidence; distinct untouched shot/target to be reserved for final acceptance).
Lane state ~01:40Z: Sol346 COMPLETE, t_eb84d7f1 done; source/native/staging lease RELEASED
(no owner; next claim is an explicit joint thinker decision; Sol optional). Clean repo
1a5e76f2 / tree f17a60bd, library 5a7500f / tree 77878b06; CONTINUE346/CHECKPOINT346 hold
all 100 native requests; staging holds OWNERSHIP.json only; 714 evidence immutable (no repeat).
Deferred: check_repository, independent review, affected batch, merge, packages.
Earlier lane state 00:30Z: Sol run346 CLAIMED t_eb84d7f1 (sole source/native/staging owner; enrolled for
automatic continuation); owner clarified Sol is optional capacity — thinkers may build
themselves when faster; no abrupt lane takeover, coordinate a clean checkpoint first.
t_eb84d7f1 has BOTH thinker confirmations (Astra amendment: 714-specific metadata/SOP/curve
binding, exact source/reference triples retained per coordinate, scope wording, 714 =
development on inspection) and is ready for Sol's claim. Scope wording (Astra, adopted):
frame256 results exclude the SPECIFIC tested two-parameter families and simple
shared-monotone/native/local-gain structures, not any abstract pointwise stage nor every
nonlocal mechanism; corner-based probes are numerical diagnostics; no mapper follows from
per-pixel values. Observed channel asymmetry (B non-monotone to ~5 nit, R/G to ~1 nit) is
carried into the coupled-stage source trace.
Pending peer questions: Astra's coupled chroma/gamut/black-volume (WARD/root) source trace
naming a specific stage; Fable's proposed ordering-basis test on the 939 reversal pixels
(hold if Astra prefers a sourced stage first).
FINAL-ACCEPTANCE RESERVATION (frozen by Astra345 + Fable344, metadata-only selection, no
output ever inspected): shot 3 5513873e-6e64-48a2-9b02-0ec5e4e781f6, Record [917,1484),
source parent 23ed4d2b-bb33-480b-9ac0-cedd5118d487 / sourceIn 0, global frame 1200 =
917+floor((567−1)/2), source 283, target 48 (1000 nit P3D65 full), L1 .0193027/.249426/
.909041, trim 0,0,0,−.008,0,.013,−.012,0,−.75, XML a18f5960…. Rules: never rendered/cached/
acquired/inspected on t_eb84d7f1 or any development card; no correction derived from it;
consumed once by the frozen final candidate via the full-raster + independent gate; if found
already touched, record and advance by the same fixed rule before any candidate change.
Does not relieve nonzero-SG/L8/profile/temporal/physical acceptance.
Remaining programme: full-raster + independent pass → independent review/fixes → one
affected unit batch + gate → merge → versioned Ubuntu packages. Human action: None required.

## Coordination

Sol continuation card created by Fable (see card comment) owning repo/, library/, native lane
and staging: resume hash-bound ABI366 upload from chunk 28, compile, one frame256 dev render
for scalar/GPU agreement; then this audit after both thinkers confirm; 714 association prep
only, no vendor call until decided, so holdout status is not consumed silently.
Human action: None required.
