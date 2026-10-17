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
| Scalar PQ-Y pre-SOP domain only | 1.4240802336088687 | 2.9756704295090786 | FAIL mean; removes much of per-channel chromaticity error, not yet GPU-integrated |
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

## Done, current and remaining

Done: exact retained input/reference/compiler preparation; distinct public
contract table; continuous XML bridge and source provenance; two-chain cached
analysis; one basis question resolved negatively; actual scalar/GPU operator and
native compilation; one authentic GPU development render.

Current: source-stage/black/neutral and coupled intensity/chroma reasoning with
the independent thinker; supported correction work continues rather than waiting
for Dolby. Independent-shot preparation identified genuine shot-level L1/trims
without frame nodes in later original shots. The strict current adapter admits
only explicit frame-local L1; a truthful shot-inheritance extension is required
before those held-out frames can be consumed. That extension is now written
with export schema4, parser version2 and translation
`dolby-xml205-l1-shot-inheritance-v2`: unique enclosing shot, actual shot L1/trims,
`selection_kind=shot-inherited`, JSON-null frame_id and computed edit offset.
Explicit-frame selection retains its original UUID and conflict rejection.
No Frame node/UUID or metadata record is fabricated. Source/target/rate/range
proof remains mandatory; missing/gapped/ambiguous selections reject. Historical
schema3 exports/old parser receipts stay immutable, not relabelled as current
execution. New boundary/gap/missing-L1/target/null-discriminant regressions are
written and syntax-checked, not executed. No new independent image/reference
was acquired by this preparation.

Remaining: passing exact full-raster official output and independent retained
frames/targets, genuine completed-batch adversarial review/fixes, one affected
unit batch and repository gate, merge-ready substantial PR, versioned Ubuntu
source/binary packages and isolated install/rollback evidence. Raw L2/L8,
chroma/detail, profile/CM coverage, temporal/seek and same-panel/OEM/optical
acceptance remain distinct. No physical display deployment or Apple TV activity.
