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

The original mean<=1 and p95<=3 limits remain unchanged. Prior stock and
Hermite/absolute-PQ failures remain failures and were not rerun. Residuals are
stratified on the same cached samples by reference luminance, relative RGB
spread and physical P3 volume. Dark positive and brighter negative intensity
residuals persist. A cached black/neutral audit shows reference-black samples
cluster near the source display's declared black; this is evidence for further
stage analysis, not permission to relabel scene L1 or fit an anchor.

## Actual implementation and finite boundaries

Private ABI365 adds `PL_DOVI_DM_OPEN_RGB_PQ_PRE`, scalar preparation/evaluation,
actual GPU RGB SOP/color and rational-Y mapping, frame-owned color factors and
CW/SG cache identity. Existing no-DM and older diagnostic operators are preserved.
The RGB path replaces stock I mapping, compensation and post-I SOP; the existing
physical-gamut stage executes once afterward. It does not append two mappers.
The standalone scalar-I generator rejects the RGB operation rather than silently
substituting a scalar LUT.

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
all older series/pins remain historical and unchanged. The new source pin is
`wip/libplacebo-dm/public-rgb/SOURCE.json`.

## Done, current and remaining

Done: exact retained input/reference/compiler preparation; distinct public
contract table; continuous XML bridge and source provenance; two-chain cached
analysis; one basis question resolved negatively; actual scalar/GPU operator and
native compilation; one authentic GPU development render.

Current: source-stage/black/neutral residual reasoning with the independent
thinker; supported correction work continues rather than waiting for Dolby.

Remaining: passing exact full-raster official output and independent retained
frames/targets, genuine completed-batch adversarial review/fixes, one affected
unit batch and repository gate, merge-ready substantial PR, versioned Ubuntu
source/binary packages and isolated install/rollback evidence. Raw L2/L8,
chroma/detail, profile/CM coverage, temporal/seek and same-panel/OEM/optical
acceptance remain distinct. No physical display deployment or Apple TV activity.
