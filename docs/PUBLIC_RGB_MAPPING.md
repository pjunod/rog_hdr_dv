# Source-grounded public RGB mapping

Status: active engineering; official-output agreement still FAILS. Do not merge
or package this mapper as accepted. Source review and affected units are deferred
until the completed candidate passes full-raster and independent reference checks.
The earlier ABI364 affected software qualification is retained separately; it
never established image agreement. No support email is needed or authorized.

## Independent contracts, not a candidate lottery

The fixed public sources are DoViBaker `ffba39830b694ddca0bf5f73dcf1b462713bb7f4`
and MPC Video Renderer `6bb2f3d702993f04e888bf5abd0944a83333b3c5`. Both
implementations are GPL. Only their mathematical descriptions inform the
independently written LGPL library and repository analysis code; no implementation
code was transplanted. Public source identity is not vendor runtime identity,
certification, or patent clearance.

Two complete contracts were evaluated once on an immutable, fixed 16-pixel
lattice of a retained authentic original frame/reference pair:

- DoViBaker: rational linear-nits mapping independently per RGB channel, with
  geometric midpoint and the source's explicit computational target-black floor
  of 0.00001 nit; target-peak-normalized linear RGB SOP; inside-exponent color
  expression. Declared physical target black remains zero, not the floor.
- MPC selection6 continuous-XML adaptation: absolute-PQ BT.2020 RGB SOP/color
  BEFORE a rational linear-luminance curve with the published PQ-adapted knee.
  Scene L1 minimum supplies the shader's misleadingly named mastering-minimum
  variable. This implementation preserves continuous XML/L1 precision rather
  than the application's raw12 and UINT-nits transport losses.

Source HALF storage expands exactly to f32, without exposure/transfer conversion.
The source encoding is full RGB P3D65/PQ; the official output is full RGB
BT.2020/PQ, with a separate physical P3D65/zero-black/600-nit target. The basis
matrix is applied in linear light, never directly to PQ values. Reference
conversion and all source/frame/target metadata identities remain private and
source-bound. No reference was regenerated or modified for these comparisons.

The XML bridge composes the pinned dovi_tool serializer's PRE-ROUND algebra
with the public coefficient decode. It preserves original decimals, with no
fabricated raw12 roundtrip. Raw12 neutral2048 means SOP(1,0,1), color(0,0).
The XML color factors are chroma/2 and saturation/2. Zero saturation makes the
published inside-exponent color expression an exact bypass even when chroma
is present and nonzero; this does not qualify general chroma support. The
ST2094-10 outside-exponent chroma factor is a different equation, not silently
substituted here. Signed raw ms_weight=-1 is a local-override sentinel, not a
numeric scale or the authored XML detail value. Detail remains unapplied.

## Actual development observations

All populations below contain the same 34,560 deterministic samples. These
are diagnostics, NOT full-raster acceptance or a threshold change.

| Contract | Mean deltaEITP | p95 deltaEITP | Disposition |
|---|---:|---:|---|
| DoViBaker linear-post | 71.12397578884 | 151.4452742871567 | FAIL; all affine channel bases clamp black on this dark frame |
| MPC RGB-PQ-pre | 1.7284671178784912 | 3.8932169228680786 | FAIL; scalar/domain mismatch remains |
| One source-justified target-native P3-basis correction | 1.7247103852018388 | 3.8852842669051495 | FAIL; negligible basis benefit, not selected by fitting |
| Actual ABI365 GPU M implementation plus existing gamut once | 1.7278739741440665 | 3.894005612470684 | FAIL; correspondence localizes discrepancy before final gamut/compiler |
| Disclosed curve-before-SOP order only | 1.7557783422296565 | 3.7266675986867153 | FAIL; black improves, nonblack neutral worsens; not adopted |
| Scalar PQ-Y pre-SOP domain only | 1.4240802336088687 | 2.9756704295090786 | FAIL mean; frozen cached scalar diagnostic, not acceptance |
| Actual ABI366 SG0 scalar-Y GPU development render | 1.4233977137640779 | 2.9758393807633636 | FAIL mean; scalar/GPU mean difference.001175 deltaEITP, not acceptance |
| Disclosed target-PQ-normalized scalar post-curve composition | 1.9822876353154848 | 4.507778761496315 | FAIL; adverse black/midtone predictions confirmed, not adopted |
| Coupled HPE/IPT scalar pre-SOP with disclosed automatic chroma factor | unavailable | unavailable | FAIL; one final output-domain-invalid pixel prevents an all-sample primary metric; partial diagnostics also fail |
| Predeclared direct-LGG XML units on unchanged scalar-Y pre-SOP chain | 5.535727406752872 | 9.050526281113827 | FAIL; black improves but midtones worsen as predicted; wire baseline retained, not rerun |

The original mean<=1 and p95<=3 limits remain unchanged. Prior stock and
Hermite/absolute-PQ failures remain failures and were not rerun. Residuals are
stratified on the same cached samples by reference luminance, relative RGB
spread and physical P3 volume. Dark positive and brighter negative intensity
residuals persist. A cached black/neutral audit shows reference-black samples
cluster near the source display's declared black; this is evidence for further
stage analysis, not permission to relabel scene L1 or fit an anchor.

The normalized scalar composition uses US12573352B2 Eq6/5/7 around the same
rational-Y curve. It changes both order and normalization relative to pre-Y;
it is not a one-variable or complete-patent reproduction. No source-black
subtraction, post-SOP PQ floor or internal target clamp was inserted. All
34,560 samples were valid, with zero negative affine bases and zero normalized
inputs outside the target span. Reference-black mean2.07936 and nonblack-neutral
mean1.22107 confirm the predeclared adverse predictions. No part of that failed
chain was spliced into another candidate.

A separate exact-input audit found 89 repeated source-color groups containing
nonblack references (208 samples); 28 have differing reference codes, with
observed diameter p95.06332 and maximum.11737 deltaEITP. The 96 repeated
all-black groups (7,037 samples) have zero reference dispersion. These limited
repeats do not support spatial detail as the main order-one residual, and do
not exclude detail globally or identify a filter.

The XML factors remain a hypothesis for direct authoring semantics: their
algebra is exactly the pinned serializer-to-public-raw-decoder composition,
not a primary-source proof of the official XML renderer's control scaling.
No free scale factor was tuned against this frame.

A later finite encoding-convention discriminator keeps the exact pre-Y chain
and changes only the complete authoring-unit interpretation. W is the retained
serializer/public-decoder composition with physical LGG `(L/2,1+G/2,1+H/2)`;
A is the explicitly unproven direct-unit hypothesis `(L,1+G,1+H)`. Both derive
the complete operative SOP via the published Eq1 and preserve CW/SG status.
No continuous scale parameter or intermediate factor is available. A's exact
SOP `(1.028,-.028,1000/1001)` fails all-sample mean5.53573/p959.05053, with
11,422 negative affine bases and11,423 PQ-floor activations. Reference-black
mean.00581 improves while nonblack-neutral mean8.36993 and chromatic mean7.36413
worsen. Reject A for this declared chain; do not splice its black behavior or
change order to rescue it. W remains a failed, provisional best diagnostic,
not proof of direct XML pixel semantics. All original metadata bytes are unchanged.

The coupled discriminator embeds the same M neutral scalar transfer in the
LMS/PQ/IPT path with the US9961237B2 Eq8/9 automatic chroma multiplier
`1 + mapped_I - original_I`, not libplacebo's hull-ratio compensation. Exact
current library forward matrices (HPE plus4% crosstalk) are frozen; this is a
renderer-specific matrix adaptation, not a claimed patent-matrix identity.
Consistent double inverses have maximum identity residual2.22e-16. Its output
policy is one fixed physical P3 clip[0,600], then BT2020/PQ encoding, unlike
earlier raw Y diagnostics. One final encoding-domain-invalid pixel means the
all34,560 primary metric is unavailable. The partial34,559 diagnostic mean1.93870/
p954.47002 is NOT an acceptance statistic. Raw BT2020 negatives793 and P3
excursions1217 are retained; the raw metric is also unavailable rather than
omitting those samples. Nonblack-neutral transfer remains approximately.92348/
1.19216, while chromatic error worsens. This chain is not GPU-promoted.

## Actual implementation and finite boundaries

Private ABI365 adds `PL_DOVI_DM_OPEN_RGB_PQ_PRE`, scalar preparation/evaluation,
actual GPU RGB SOP/color and rational-Y mapping, frame-owned color factors and
CW/SG cache identity. Existing no-DM and older diagnostic operators are preserved.
The RGB path replaces stock I mapping, compensation and post-I SOP; the existing
physical-gamut stage executes once afterward. It does not append two mappers.
The standalone scalar-I generator rejects the RGB operation rather than silently
substituting a scalar LUT. Prepared PQ parameters also have a non-null scalar
marker callback: generic scalar generation/sampling returns NaNs, not an
accidental scalar substitute or null-callback dereference.

Target black must be zero for this named hypothesis; unsupported flat/singular
L1 intervals reject. Rational preparation checks denominator/derivative over the
physical input interval. Negative SOP bases clamp before noninteger powers;
the published post-SOP 1e-5 PQ floor is retained. The actual pipeline additionally
caps post-color PQ at1 as an explicit finite physical-domain extension, not a
fitted coefficient; scalar and shader share that policy. It did not explain or
remove the retained development failure. Source-to-working negative components
are projected to the nonnegative input domain before PQ encoding.

Full and no-DV native x86_64 warnings-as-errors compilation and the matched
ABI365 consumer/header/compiler-dependency/runtime closure passed. Native
scalar/GPU/cache regressions are written and compiled, not yet executed. Source
export and SHA256SUMS were generated deliberately for the new appended patch;
all older series/pins remain historical and unchanged. The scalar-marker safety
correction was incrementally compiled in both full and no-DV configurations
with warnings as errors; its new regressions remain unexecuted. Exercised
earlier library/consumer artifacts were preserved before warm compilation.
The new source pin is
`wip/libplacebo-dm/public-rgb/SOURCE.json`.

## ABI366 continuation and fixed cached family audit

Private ABI366 adds the distinct `PL_DOVI_DM_OPEN_Y_PQ_PRE` evaluator and GPU
path, with `y-pq-pre-rational` frontend selection. It applies absolute-PQ SOP to
linear BT.2020 Y, rational mapping once, restores original linear RGB ratios,
then uses the existing physical gamut stage once. Exact SG0 only is supported;
nonzero SG rejects rather than falling back to RGB. The full-domain SOP must
remain inside PQ1; zero Y maps to black. This is an explicit scalar extension,
not a complete official mapper. Native full/noDV and matched consumer compilation
passed for library5a7500f/tree77878b06 (request11df1b13). Older exercised c21
artifacts were preserved before warm rebuilding. No unit execution occurred.
The ONE frame256 development render94c753eb tracks the frozen scalar diagnostic:
scalar/GPU deltaEITP mean.0011750457/p95.0029119424/max.0071413286; maximum absolute
PQ difference9.40758e-6. Its all-sample diagnostic still fails mean1.

Both thinkers reconciled one audit v2, executed once on the original cache SHA256
`ab04648968e03a8c97a831095f8ea39e0391333aa7e072138b3e465176fc2fb8`.
Reference intervals span adjacent representable HALF PQ codes (subnormals
included); original input source is exact, with no invented quantization tolerance.
Monotone EOTF endpoints and interval arithmetic use outward binary64 expansion;
libm transcendental evaluation is disclosed, not a formally certified interval
implementation. Per-channel scale intervals must overlap, and the hypothetical
source ray at observed Yref must remain inside physical P3[0,600]. Flags overlap:
8527 reference-floor samples, zero SOP-clamp/floor samples,22387 scale-overlap
failures,3 active/undefined P3 rays;3646 samples are eligible for this diagnostic.
The original8439 black/155 nearblack-neutral/33 nonblack-neutral/25933 chromatic
groups are unchanged. Eligibility is NOT an acceptance population.

Descriptive1/8-decade x bins retain paired y/x intervals and actual lower-median
by-x representatives, ties by coordinate order, each with its OWN reference
interval. Empty bins are retained. Nineteen occupied bins give the predeclared
indices0,6,12,18: CRx1.0045260613 versus conservative CRy[.9922560170,1.0079000635],
with absolute log-difference bounds[0,.0122899729]. Thus this test does not refute
the fractional-linear family; it does not establish that family either. Exact
rational W sanity preserves CR, with actual binary64 discrepancy2.22e-16.
No replacement quadruple, fitted Möbius, renderer coefficient or threshold change.
Non-overlap can localize violated colour/scalar assumptions, not automatically
prove mean1/p953 impossibility. Frozen all-sample WpreY remains
1.4240802336/2.9756704295 FAIL. Private full audit JSON SHA256 is
`1c6d367357570073e6c48586ede545f9ff94bb6d66f95ff1bb60cffba53e8e3d`;
the initial export-cap failure occurred AFTER the analysis and did not rerun it.

Historical run343 frame714/target27 preparation binds actual shot-inherited parser2
selection with null frame UUID and proves source-frame0+(714-512)=202. A schema4
draft keeps missing original-acquisition/normalization/reference-receipt bindings
explicitly null; it is NOT an executable validated export. No vendor call or
reference/candidate render on714 occurred in that preparation. Run346 below
supersedes the draft as current acquisition evidence without modifying its history.

## Genuine second-shot development evidence (run346)

The preselected producer global frame714 maps through original XML Record512,
duration405, sourceIn0 to shot source202. The exact producer global EXR sequence
key00714 was acquired, not an unrelated source-number202 frame. The producer's
published original EXR sequence and paired Dolby metadata supply this association;
EXR rate60000/1001 and raw timeCode are retained, not promoted into embedded
asset-UUID authentication or IMF/EXR pixel equality. One ordinary target27 render
uses the unchanged source-associated declaration repair, full P3D65/PQ input and
full BT2020/PQ output. Exact HALF-to-f32 normalization has transforms=[] on both
sides. Existing successful normal validation/target-info evidence is retained
against rehashed unchanged tools/XML/runtime, not executed again.

Actual strict parser2/schema4 export binds the real acquired frame, null frame_id,
shot-inherited L1(.0196536,.272,.853468) and target27 trim
`0,0,0,-0.004,0.006,0.007,-0.021,-0.004,-0.75`. The original W bridge supplies
S1.005006/O-.002006/P2000/2007, CW-.0105/SG-.002; the rational preparation uses
this shot's actual anchors. Rounded brief P=.996512207274539 failed a script
assertion before any cache existed; the assertion was corrected to the existing
exact2000/2007, with no coefficient change. That failure remains in the ledger.

Only the existing COMPLETE W MpreRGB scalar chain was evaluated, including its
actual nonzero-SG inside-exponent color expression. SG0-only Y preparation
explicitly rejects the metadata; no Y render/substitution, SG removal, alternate
order/domain, coefficient fitting or extra vendor variant occurred. As with the
earlier scalar M diagnostic, metrics are raw before final GPU physical-volume
enforcement; excursions are counted rather than clipped into agreement.

On the single4096x2160/16x16 top-left lattice (34560 samples):

- All-sample deltaEITP mean6.015329278630697, p9511.063448559052905,
  max16.229605381653798: FAIL unchanged1/3 bar; invalid0.
- Mean signed720ITP(-5.622285931186368,.09912824114385256,.041147748877907155).
  Full signed-axis and black/neutral/chroma/reference-Y strata remain in the
  private diagnostic receipt, not just a favorable subset.
- Affine-negative/above1, power-PQ-floor, post-color-PQ-above1 and negative
  rational-Y clamp counts are all0. Raw candidate414 physical-P3 excursions
  comprise409 negative and5 above600nit; reference excursions0.
- Reference black0, nearblack-neutral4, nonblack-neutral251, chroma34305.
  SourceY ranges .022108716426156236..1749.4373850948507nit; no sampled Y lies
  below L1min.008377000623053363/mastering.005 or above L1max2540.9552848421195/
  mastering4000. Shot L1 is not relabelled as per-frame observed extrema.
- v2 numerical interval accounting: floor0, subnormal0, zero-source0,
  scale-overlap-fail29881, active/undefined hypothetical P3 rays34, eligible4679.
  Floor threshold is a disclosed diagnostic convention, not an observed714
  black plateau. Eligible samples never replace the primary population.

The audit preserves exactly the seven v2 per-sample columns and flag order,
plus a separately named exact-input table (sourceP3PQ, computed linearBT2020/Y,
referenceBT2020PQ/Y). Its new SOP/curve/cache identities are explicit. Old local
thinker scripts with hardcoded frame256 driver constants must not mislabel those
constants as714; structural columns remain compatible. No CR quadruple or bin
selection was requested. The20893190-byte JSON was retrieved hash-exact through
87 owned <=64KiB XZ export pieces; the22-file receipt archive uses one additional
bounded piece. No cache/analysis/render repetition or other worker's staging
cleanup was used. Private JSON SHA256:
`8b2c7a7cae4db0d5d8c2b19f30a39231d75659cb2252c32937fa15603df54170`.

Shot 714/target27 becomes DEVELOPMENT evidence as soon as the thinkers inspect its results; it is no longer an untouched final holdout. A distinct, untouched genuine shot/target must be reserved and recorded (by the thinkers, not here) for FINAL independent acceptance BEFORE any mapper change is accepted. Frame256 status remains WpreY 1.4240802336/2.9756704295 FAIL; nothing on this card is accuracy acceptance, review, merge or package progress.

Both thinkers reserved frame1200/source283/target48 as untouched final evidence
before the714 results. This task did not acquire, render, cache or inspect it.
Sanitized receipt: [second-shot evidence](../evidence/public-mapping-shot714-development.json).

## Done, current and remaining

### ABI367 mastering-black continuation (measured, accuracy FAIL)

The additive `y-pq-pre-mastblack` / `open-y-pq-pre-mastblack-v1` operator uses
the zero-PQ-low MPC knee, declared source mastering black as the rational nits
anchor, scalar PQ(Y) SOP, original linear RGB ratio restoration, then the actual
inside-exponent PQ color expression (including nonzero SG). The existing physical
P3 gamut stage follows once. Earlier variants and their receipts remain distinct.
The zero-low knee is grounded in pinned MPC DX11VideoProcessor.cpp2369–2371
UINT-nits minimum truncation; the mastering-black anchor follows the shader's
named semantics. These remain disclosed applicability hypotheses, not an official
CM identity or fitted correction. Missing/nonfinite mastering black rejects.
Fable's recorded reconciliation changes ONLY MB: preparation rejects
S*L1max_pq+O>1; scalar evaluation fails closed if actual S*PQ(Y)+O>1, before
power/EOTF. The GPU explicitly caps SOP PQ at1 as a finite extension. Post-ratio
color PQ>1 still rejects. Existing SG0-only Y keeps its full-domain S+O<=1 guard.

Native full/noDV and matched ABI367 consumer compilation passed with -Werror
for library62e3651/tree26e1d848 (requestcf927164). ABI366 source, generated
headers, libraries, test binaries and consumer were preserved before the warm
rebuild. New regressions are written and compiled, not executed.

| Development lattice | Mean deltaEITP | p95 deltaEITP | Maximum | State |
|---|---:|---:|---:|---|
| Frame256 fixed double chain | 1.123974038284229 | 2.7196443032245785 | 7.345997615839801 | FAIL mean; 34560 exact-cache samples, raw before final gamut |
| Frame256 native C scalar | 1.12386483513616 | 2.7193929454778396 | 7.345997615839801 | FAIL mean; same cache and actual ABI367 evaluator |
| Frame714 fixed double chain | 2.418842198716092 | 5.553420219156015 | 16.700345289860316 | FAIL; missing lattice executed once after guard reconciliation |
| Frame714 native C scalar | 2.418863181354413 | 5.553267576315724 | 16.699943126161788 | FAIL; same exact cache, actual nonzero SG |
| Frame256 full-raster GPU | 1.1182596907971711 | 2.7077148379316305 | 9.635916901592578 | FAIL mean; 8,847,360 pixels |
| Frame714 full-raster GPU | 2.4148650268866025 | 5.54951429234905 | 51.900494117471645 | FAIL mean and p95; 8,847,360 pixels |

Frame256 mean signed720ITP is(-.9221676116914387,-.05867643838091357,
.20148548404367084). C-versus-double deltaEITP mean.0005339534/p95.0014968954/
max.0042305511. All34560 samples are valid; affine-negative/PQ-floor0,
rational-negative clamps11677, raw physical-P3-negative34, above600nit0.
Strata and all counters are retained privately. This successful256 lattice was
not rerun.714 signed720ITP is(-.8195592407901202,.0016045517376339232,
.125236812480125); invalid/affine>PQ1/post-color>PQ1 counters are0 on its34560
samples, physicalP3-negative0/above600nit10. No source coefficients were tuned.

The guard-only correction compiles at cd4600f, and explicit shader finite cap at
77894e1/treec595a7b4 (nativeffa70dbd full/noDV/consumer -Werror). Only genuinely
invalidated compile closures reran; prior ABI366 and initial ABI367 artifacts
were preserved. No units executed. One GPU development render per shot gives
sampled2561.1229053006/2.7193929455 and7142.4176843018/5.5502987854.
GPU-versus-retained-double deltaEITP mean/p95/max is256
.0016219377/.0039502363/.0128638421,714.0029444085/.0065655785/.0272562940.
Native-C/GPU means are.0015947494/.0032052254; not every statistic is <=.003.
Cap-unexercised evidence is limited to the evaluated lattice, not all raster pixels.

The first reference manifest rebind failed on missing relocated historical logs;
hash-verified copies repaired that storage prerequisite without changing receipts
or repeating normalization/reference rendering. Old open_dm.compare then rejected
algorithm metadata BEFORE the metric: Python tuples in prepared_curve become
JSON arrays/lists, and strict_equal correctly rejects differing types.
Astra356 authorized a separately source-hashed comparison-only driver:
`tools/dolby_harness/analysis/recorded_open_compare.py`, SHA256
`823bc794c7a6056cf8e25e107940b68bf7ba8bbed296c2526940d2a7ebd2cb7d`.
It checks the complete archived FRONTEND_INPUTS and COMPILE_INPUTS maps against
recorded execution/compile hashes, runs archived prov.validate_record unchanged,
and reproduces schema/alignment/target/control/log/output/reference checks. ONLY
the expected algorithm is serialized/parsed before strict equality; no numeric
or type relaxation. Unchanged metric.compare_pixels then ran ONCE per full raster.
The table reports this corrected comparison of old immutable execution, NOT old
open_dm.compare success or a new-source render. Future algorithm() returns native
JSON containers; regression definitions preserve exact controls and reject factor/
type tampering. Their units remain deferred to whole-batch review/qualification.

Completed sanitized receipt: [mastering-black evidence](../evidence/public-mapping-mastblack-completed-development.json).
The initial [partial receipt](../evidence/public-mapping-mastblack-development.json)
is retained as history, not current status. Both development shots still FAIL,
although lower than the retained sampled WpreY2561.42408 and complete W MpreRGB714
6.01533 baselines (not new full-raster W comparisons). Reserved1200/48 remains
untouched under coordinator clarification; no holdout consumption/correction.
Review, one affected unit batch, merge and packages remain downstream. Current
source hypotheses are recorded by the [coordinating thinker](MAPPING_HYPOTHESES_ASTRA_20261018.md),
not treated as independent final adversarial review.

Done: exact retained input/reference/compiler preparation; distinct public
contract table; continuous XML bridge and source provenance; two-chain cached
analysis; one basis question resolved negatively; actual scalar/GPU operator and
native compilation; one authentic GPU development render.

Current: source-stage/black/neutral and coupled intensity/chroma reasoning by
both joint thinkers; supported correction work continues rather than waiting
for Dolby. Independent-shot preparation identified genuine shot-level L1/trims
without frame nodes in later original shots. The strict current adapter admits
explicit frame-local L1 and truthful shot inheritance. That extension is written
with export schema4, parser version2 and translation
`dolby-xml205-l1-shot-inheritance-v2`: unique enclosing shot, actual shot L1/trims,
`selection_kind=shot-inherited`, JSON-null frame_id and computed edit offset.
Explicit-frame selection retains its original UUID and conflict rejection.
No Frame node/UUID or metadata record is fabricated. Source/target/rate/range
proof remains mandatory; missing/gapped/ambiguous selections reject. Historical
schema3 exports/old parser receipts stay immutable, not relabelled as current
execution. New boundary/gap/missing-L1/target/null-discriminant regressions are
written and syntax-checked, not executed. The preparation alone acquired no
image/reference; run346 has now acquired714 once as DEVELOPMENT evidence above.

Remaining: passing exact full-raster official output and independent retained
frames/targets, genuine completed-batch adversarial review/fixes, one affected
unit batch and repository gate, merge-ready substantial PR, versioned Ubuntu
source/binary packages and isolated install/rollback evidence. Raw L2/L8,
chroma/detail, profile/CM coverage, temporal/seek and same-panel/OEM/optical
acceptance remain distinct. No physical display deployment or Apple TV activity.
