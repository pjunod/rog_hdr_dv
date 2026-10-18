# Mapping equation continuation — Astra, 2026-10-18

Status: ongoing analysis, not accepted mapping. This continues the committed
[Fable checkpoint](MAPPING_HYPOTHESES_FABLE_20261017.md). Sol completed and released
the previous implementation/native lease; the full-raster results still fail.
New bounded work and file/native ownership are recorded on the shared board.
The untouched frame1200/target48 remains reserved for a frozen development-passing
candidate; none of this analysis accesses it.

## Primary-source check: the actual ST 2094-10 Annex B

Retrieved the public SMPTE ST 2094-10:2021 publication from
https://pub.smpte.org/pub/st2094-10/st2094-10-2021.pdf . SHA256:
`289f2230c949bb9490f15d75e793d9042cc1bdd6a75e0d2769a5565f15d19764`.
The publisher's landing page identifies the document and links this PDF. The
2021 foreword identifies changes to minimum-statistic computation and offset
ranges; it does not describe a new Annex B curve.

- Section 6.1.2 computes statistics on 2x2 component averages throughout the
  image essence associated with a metadata interval. Replacing shot metadata
  with the sparse current-frame lattice is not this calculation.
- Annex B.2 Eq2 includes a contrast exponent n but explicitly fixes n=1 for
  Application #1. It is not a free metadata-controlled contrast parameter.
- The Annex B adaptation point is the nested geometric mean
  `sqrt(input_average * sqrt(target_minimum * target_maximum))`, not the cube
  root of the product of three luminances. The actual example
  is 120, 0.5, 100 nits producing approximately 29 nits; it also discusses an
  upper bound such as 80% of target maximum.
- Consequently the modified PQ knee in libplacebo/MPC is not the standard's
  literal adaptation equation. With the current zero target black, the literal
  geometric midpoint degenerates. Choosing another black floor would require
  an explicit, separate source justification, not a value fitted to references.
- Annex B.3 applies its rational curve independently to linear RGB, followed
  by target-peak-normalized linear SOP and color adjustment. The existing failed
  DoViBaker contract already tests a disclosed nonzero-floor extension of that
  architecture. Do not repeat it or treat it as PQ-Y mapping.

Decision: no n sweep, frame-local L1 substitution, or claim that Annex B supplies
an extra contrast knob. These source questions are resolved without new renders.

## Current evidence and ownership

Sol's corrected ABI367 guard compiles full/noDV/consumer with warnings as errors
(library cd4600f). The missing frame714 lattice now reproduces the chosen chain:
mean 2.418842198716092, p95 5.553420219156015 in the double evaluator; native C
mean 2.4188631814, p95 5.5532675763. Invalid and above-PQ1 counters are zero on
that lattice. The successful frame256 lattice was not repeated. Both shots
still fail unchanged accuracy requirements. These are sampled, not full-raster
results. Lattice scalar/GPU agreement cannot establish that a cap was unexercised
on unsampled full-raster pixels.

## Corrected-anchor intensity/chroma diagnostic — rejected

The older failed IPT/Eq8 composition used the old L1-min knee, whereas the new
mastering-black/zero-low-knee correction materially improves scalar-Y mapping.
The chroma-ray interval failures reject exact equality for that embedding, but
the retained bounded witnesses do not establish failure of the mean/p95 metric.
One complete composition was frozen before execution: full RGB-PQ SOP and actual
CW/SG first, then patent-cited Ebner1998 Eq1 XYZ/LMS, absolute PQ and IPT; apply
the selected mastering-black/zero-low-knee rational to EOTF(I), encode J, scale
P/T by `1+J-I` (US9961237 Eq8/9), inverse colorimetry, then one physical P3 clip.
This is an explicitly hybrid hypothesis, not an identified official pipeline.
No alpha/beta values or matrix sweep were introduced. Below-black inverse LMS
components project to PQ(0), counted explicitly; nonfinite/above-PQ1 rejects.

`tools/dolby_harness/analysis/astra356_ipt.py` executed this new chain exactly
once per retained development lattice, with all 34,560 samples valid per shot:

| Shot | Post-P3 mean | p95 | Signed 720 I/T/P |
| --- | ---: | ---: | --- |
| 256 | 1.7248121682 | 4.6293281770 | -0.827812 / -0.253054 / +0.731762 |
| 714 | 2.7798244959 | 4.8369961758 | -0.839430 / -0.434864 / +0.602183 |

Both mean errors worsen against the selected MB-Y candidate, and both fail.
Frame256 has 12,077 raw-negative pixels and 12,174 physical-P3 excursions;
its raw all-population metric is unavailable (partial raw metrics must not be
promoted). Frame714 has 576 P3 excursions. This diagnostic is rejected, not
promoted into the renderer. Exact source/reference input hashes, metadata,
inverse identity checks, strata and counters are retained in its JSON receipt.
Frame256 retains the adapter's reconstructed-source prospect qualification;
frame714 uses exact stored source triples. No native, render, unit, reference
acquisition, or holdout operation was performed by this analysis.

Current: inspect the remaining metadata/normalization and scalar-curve contract
without fitting free coefficients or repeating rejected chains. Sol's existing
frozen candidate and full-raster comparison ownership remain unchanged.

## Normalized scalar post-SOP preflight — no population run

`astra356_normalization.py` checks a disclosed alternative from US12573352
Eq6/7: the selected MB rational first, followed by scalar SOP normalized to the
target PQ interval, then ratio restoration. This differs from the older failed
normalized-post experiment's black/curve anchors and from Fable's absolute-RGB
post-trim grid. Metadata-only neutral transfer predictions were computed before
deciding whether to commission a new comparison.

At source 1/3/10/30/100 nits, the normalized-post minus selected-pre differences
in 720*PQ are respectively:

| Shot | 1 nit | 3 nits | 10 nits | 30 nits | 100 nits |
| --- | ---: | ---: | ---: | ---: | ---: |
| 256 | 2.108227 | 2.204463 | 2.273680 | 2.251991 | 2.036320 |
| 714 | 0.201039 | 0.164012 | 0.107456 | 0.050212 | 0.019871 |

This could materially change 256, but not supply the dominant 714 midtone
correction; it also raises 714 highlights rather than lowering them. No lattice
or full-raster comparison was commissioned. These numbers are analytic neutral
transfer differences, NOT measured deltaEITP or an all-pixel impossibility proof.
Continue automatic-curve/driver investigation, not another small trim-order
permutation. The original cosine Table1 midpoint rule also gives zero offsets
for these below-midrange source averages, just like the previously tested
improved rule; merely reverting that rule offers no distinct candidate here.

## Comparator transport blocker — policy recorded, repair owned by Sol

The first full-raster comparison stopped before its metric: `algorithm()`
returned tuples in `prepared_curve`, JSON encoded these as arrays, and the
validator's deliberately exact-type comparison rejected lists versus tuples.
No rendered pixel was invalidated by this transport mismatch.

Decision: future metadata must be JSON-native; do not weaken strict equality.
For existing immutable renders, a separately hashed comparison-only driver must
validate the exact archived rendering frontend/compile source closure, preserve
every existing schema/alignment/target/control/log/output check, and normalize
only the expected algorithm container representation through JSON. Reference
validation and exact same-input association remain independent. Renderer and
comparator identities must remain distinct, with unchanged candidate manifests
and pixels; no monkeypatch, hash rewrite, skipped closure check, or rerender.
The metric itself is unchanged. This note records a design decision, not an
assertion that Sol's repair or either full-raster comparison has finished.

### Subsequent verified completion of the comparison repair

Sol completed each corrected full-raster comparison exactly once. Local report
hashes were independently checked, without rerendering or recomparing:

| Shot | Pixels | Mean deltaEITP | p95 | Maximum | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| 256 | 8847360 | 1.1182596907971711 | 2.7077148379316305 | 9.635916901592578 | FAIL mean |
| 714 | 8847360 | 2.4148650268866025 | 5.54951429234905 | 51.900494117471645 | FAIL mean/p95 |

Report SHA256 identities:
- 256: `10358cb3d07c9f1b510319b38d02d8a996723838d5e349db59704eea168d6efc`
- 714: `eb6a86f7e151767a47c8eae24cad216dec34b34b33da8587c2f92e475a4a1f20`
- Comparator: `823bc794c7a6056cf8e25e107940b68bf7ba8bbed296c2526940d2a7ebd2cb7d`

The old `open_dm.compare` attempt did NOT succeed. These receipts identify the
new comparison-only driver and the archived original renderer independently.
Source/evidence inspection is not final independent adversarial review. Previous
W results are sampled baselines, not new full-raster W measurements. Sol released
the source/native lease at repo `211c119` / library `77894e1`; unit runs remain
zero. Frame1200/target48 is untouched. No acceptance or package claim follows.

## Distinct scene-key powered curve — metadata preflight rejected

US10540920B2 paragraphs0049–0061/Table2 differs materially from the previously
rejected US9961237 display-midpoint construction. It specifies:

    ratio = (Tmax-Tmin)/(Smax-Smin), in PQ
    Slope = 1/ratio
    Key = (Mid-Crush)/(Clip-Crush)
    Shift = Mid*(1-ratio)*2*Key
    Rolloff = 1/3
    n = Slope/Rolloff

Table2 solves a rational through transformed anchors x^n and y^(1/Rolloff).
The metadata-only `astra356_powered.py` uses the declared .005/4000-nit source
display, 0/600-nit target and actual scene L1 statistics, without fitted values.
Automatic mapping followed by absolute-PQ SOP is explicitly a neutral-transfer
hypothesis, not a full official color/detail chain.

The first diagnostic exited1 at shot714's negative below-Crush fractional-power
base. The reporter was then corrected to retain invalid rows explicitly; the
failed metadata diagnostic completed on retry with unchanged equations. No image
metric or render ran. At source1.476nit, shot256 predicts .479482nit after SOP,
versus selected .813089 and the retained near-neutral reference .829980. Shot714
predicts -15.5185 units720PQ relative to selected at1nit but +13.2219 at100nit.
The literal source formula is invalid at0/.005nit on714. This is not a justified
next image hypothesis; neither a clamp nor new coefficient was introduced to
rescue it. A transfer prediction is not an all-pixel impossibility proof.

## Neutral coverage and the remaining implementation decision

`astra356_neutral_coverage.py` reads only retained input/reference rows. It does
not evaluate a candidate or recompute an error metric. It keeps the existing
reference-linear-BT2020 relative-spread <=1% definition:

- 256: 153 near-black samples, 2 at source .0159–.0173nit, and 33 at1.476–2.197nit.
- 714: 233 of255 at source1699.62–1749.44nit; only13 at3.996–99.175nit, with the
  remaining9 below.383nit. Thus its marginal neutral signed-I residual chiefly
  describes highlights, not a broad neutral midtone population.

The current evidence motivates fixing midtone/shoulder behaviour, but does not
justify fitting a free contrast or knee coefficient. Source-grounded modified
IPT composition, normalized post-SOP and the distinct scene-key powered curve
have now been tested or preflighted and rejected as described above. There is no
new promoted candidate. The unresolved decision is a complete source-supported
automatic curve/driver or coupled stage that improves both development shots;
do not substitute more exact-invariant exclusion work for that implementation
goal. Preserve the neutral-coverage limitation when interpreting marginal bins.
Full-raster and independent accuracy, final independent review/fixes, the one
affected unit batch, merge and versioned Ubuntu delivery remain outstanding.

## Per-component mapping embedding — rejected (Astra357)

The primary ST2094-10 Annex B.3 applies its rational independently to RGB
components. A single new complete hybrid checked that embedding using the
unchanged MB anchors and W absolute-PQ trim: each linear BT2020 component gets
its own PQ SOP then the MB nits rational, followed by actual PQ CW/SG and the
single physical P3 clip. This is not the earlier DoViBaker chain, which used a
different knee and linear target-normalized trim, nor an official model claim.

`tools/dolby_harness/analysis/astra357_components.py` ran once per retained
development lattice. Each had 34,560 valid samples and zero invalid samples:

| Shot | Mean deltaEITP | p95 | Maximum | Signed 720 I/T/P |
| --- | ---: | ---: | ---: | --- |
| 256 | 1.4402063301 | 3.8733587698 | 13.0358200967 | -0.870196 / -0.205620 / +0.487878 |
| 714 | 2.7992570343 | 7.9617637696 | 23.6757642022 | -0.887333 / -0.558558 / +0.731863 |

Both worsen against the selected MB-Y chain and fail. The hypothesis is
rejected, not promoted to the renderer. Source reconstruction qualification on
256 is unchanged; 714 uses exact retained source triples. There were no native
requests, new references, GPU renders, unit runs, or holdout accesses. Receipt
SHA256: `c58557b7666a6f759e172abc90685ee4baa76521db38ae6dc769d8859045cb49`.

The public CPU trace was also rechecked: all-three UINT L1 transport and its
guards are already represented in `fable_eval.py:130-142`. It supplies no new
untried caller correction, so no transport comparison was repeated.

## Next bounded decision — a specified spatial operator, not sharpening

US10540920B2 paragraphs0062-0065 Eq5 specifies
`Is = Io - Gaussian(Io - Im)`, with an example separable 11-by-11 Gaussian of
sigma2. It is a concrete untested spatial mechanism rather than an arbitrary
detail enhancement. The source does NOT identify XML detail -0.75 with that
filter, a weight, or a selection mode. The diagnostic is explicitly a hybrid
of that fixed operator on PQ(Y) and the current MB chain, not the complete
patent's IPT model or a discovered official detail contract.

A bounded Sol card owns the native lane for one complete new diagnostic on
256 and 714, using original full-source neighborhoods but the existing fixed
34,560-point metric lattice. Kernel radius5/sigma2, normalized separable weights,
edge replication, below-PQ-black projection and the achromatic zero-Y extension
are frozen before execution. Actual CW/SG and the final physical gamut stage
are retained. No radius/weight/coordinate sweep, reference perturbation, old
comparison rerun, or holdout operation is authorized. Failed or invalid results
stop this hypothesis; passing sampled results alone would not be acceptance.

Separately, Opus has a bounded read-only source/assumption audit, not final
adversarial acceptance review. Neither assignment is a completed exchange or
an accuracy improvement. Current: new spatial diagnostic and fresh source
audit pending; last implemented full-raster candidate remains failing. Final
review and qualification must not be claimed on the strength of these tasks.

Remaining: source-grounded passing complete chain, full-raster development and
independent evidence, genuinely independent adversarial review/fixes, one
whole-candidate affected unit batch and repository gate, substantial PR/merge,
and uniquely versioned Ubuntu source/binary packages with isolated install and
rollback evidence. PR16 stays held; no physical device deployment.
