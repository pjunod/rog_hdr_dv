# Frozen sqrt-sum powered PQ-Y/post-SOP hybrid

Algorithm `us961-sqrtsum-pq-y-post-v1`, harness variant `y-pq-post-sqrtsum`,
additive enum `PL_DOVI_DM_OPEN_Y_PQ_POST_SQRTSUM`, private ABI368. This is a
source-grounded open hybrid, NOT identified official CM2.9 or the complete
US9613407B2 implementation. XML detail -0.75 remains unresolved/unapplied.
Old ABI367 outputs and the corrected comparison-only history remain evidence
for their actual executing sources, not new-source outputs.

## Original fields and complete chain

The original declared source mastering minimum/maximum and selected target
minimum/maximum are converted to absolute PQ. Original L1 Crush/Mid/Clip
remain untouched; unordered, collapsed, nonfinite and unsupported physical
anchors reject. US9613407B2 paragraphs0048-0062/Table2 supply:

    ratio = min(1, sqrt((Tmax+Tmin)/(Smax+Smin)))
    ScreenRatio = 1; Rolloff = 1/3; Slope = sqrt(1/ratio)
    Key = 2*(Mid-Crush)/(Clip-Crush)
    Shift = Mid*(1-ratio)*Key; n = Slope/Rolloff
    targets = (max(Crush-Shift,Tmin), Mid-Shift, min(Clip-Shift,Tmax))

Interpolate `(a+b*q^n)/(1+c*q^n) = target^(1/Rolloff)` at those anchors.
The explicit NONLITERAL engineering extension is constant targetMin for
q<=Crush and targetMax for q>=Clip. This is neither fitted extrapolation nor
proof of differentiability/global zero-Y continuity.

Original linear BT2020 RGB -> unchanged (.2627,.6780,.0593) CIE Y -> absolute
PQ -> automatic curve -> actual original W scalar absolute-PQ SOP
(max0 affine, postpower floor1e-5) -> EOTF -> restore ORIGINAL RGB*Yout/Y ->
actual existing PQ CW/SG expression after ratio -> ONE final physical-target
RGB clip -> output encoding. No pre-SOP, dropped SG, stock compensation,
epsilon ratio or second IPT/gamut mapper. Exact Y==0 bypasses to black.
Invalid restored/color channels and fractional bases reject, not silently cap.

## Stable representation and precision

The double oracle `tools/dolby_harness/sqrtsum.py` accepts general original
metadata and has no task-local analysis imports. In z=(q/Clip)^n set

    t=(z-z0)/(1-z0); tm=(zm-z0)/(1-z0)
    wi=target_i^(1/Rolloff)
    k=(wm-w0)*(1-tm)/((w2-wm)*tm)
    v=(w0*(1-t)+k*w2*t)/((1-t)+k*t); output=v^Rolloff

Positive k, ordered anchors and t in[0,1] imply nonnegative convex base,
positive denominator and monotonicity. This is algebraically the SAME powered
rational, avoiding cancellation at Crush without a base clamp or epsilon.
Direct binary64 coefficient closure is retained in algorithm JSON. Finite
rounding is not bitwise identity: Astra's metadata-only derivation found
714 near-Crush differences around1e-10PQ between rounded representations.
C prepares from native float metadata, stores float fields, and re-closes
z0/zm/powered target anchors using the actual stored power before solving k.
The GPU evaluates native FP32. Agreement is measured separately from official
accuracy; no universal sub-.003 deltaEITP bound is claimed.

## Protocol, invalid detection and source closure

Old variants retain DVH3 unchanged. New DVH4 ordered fields:
magic, width, height, primaries-code1, ORIGINAL target-description-ID,
source(min_nits,max_nits,RGBW8), target(min_nits,max_nits,RGBW8),
L1(min,avg,max), variant-index7, S,O,P,CW,SG. Native carries that explicit ID
into its immutable target snapshot. The original-target frontend extension
accepts canonical numeric IDs1..65535 with the actual bound original P3D65,
full-PQ declaration and its selected Trim. It rejects absent/conflicting trims,
ambiguous IDs, changed volume and unsupported gamut; no borrowing target27
or interpolation. Only this DVH4 variant is extended: all DVH3 variants retain
exact target27/0black/600nit/P3 scope. The numerical oracle/library are unchanged.

Reference v2 retains its explicit original global-frame binding and schema
meaning. Selected target ID/volume must agree across the unchanged original
XML, reversible declaration repair, receipt, exact vendor argv, actual unique
normal target-info field and actual unique render Target Display field. Echoed
argv alone is insufficient. v1 remains implicit frame0/target27. Parser version2
and export schema4 semantics are unchanged; the whole-parser source SHA changes,
so new-head consumers need additive newly parsed exports/manifests, NEVER
rewritten historical executions. Old result validation uses its frozen frontend.

The independently reserved case is original global1200/source283, shot3
Record[917,1484), original target48: black0/1000nit/P3D65/full, verified from
original XML SHA a18f5960f61f868932416000c35f08bb39d9966b1dc35a8b6778e9718bb16c0f.
The complete frontend, provenance, test definitions and unchanged mathematical
source/build identities must be committed and frozen BEFORE acquiring or
inspecting those pixels. Then one ordinary reference, one ABI368 candidate,
one full unchanged BT.2124 comparison; mean<=1 AND nearest-rank p95<=3.
No baseline/variant/tuning, scalar diagnosis or repeated development metric.
Independent result is pending at this source freeze, not implied by design.

GPU invalid-only safe operands avoid undefined pow/EOTF but a sticky validity
bit marks alpha0 AFTER mapping; valid alpha is preserved. No MB PQ1 cap is
reused. The new consumer initializes alpha1 and preserves independent RGBA4,
background SKIP/transparency1, border SKIP, no blend/tiles/hooks/LUT/distortion
or overlays. It counts EVERY downloaded alpha before opening the RGB output,
rejecting anything not exactly1. This prevents background composition hiding
invalid pixels. RGB finite/physical validation remains independent. JSON-native
configuration/domain receipts are checked on render and historical verification;
source/headers/compiler/runtime/library/control/stdout/stderr hashes bind them.
TRACE native logs retain generated shader source/config for static inspection.
Cache identity includes original source min AND max plus actual CW/SG, algorithm,
frame/source identity and full target generation/description/volume.

## Actual status and remaining acceptance

Done: additive scalar/header/GPU/native transport and source/cache identity;
full/noDV and matched consumer -Werror compilation (native8bdda603,
library f3b1d3f/treefb4c3879). First build failed only deprecated test background
flags, corrected to current API and retained. New C/domain/cache/invalid-alpha
and Python metadata/protocol regressions are authored/compiled or syntax-checked,
NOT executed. No unit batch has run for this candidate.

Completed development qualification: ONE actual GPU output and ONE unchanged
full BT.2124 comparison for each exact original frame, 8,847,360 pixels each:

| Frame/target | Mean | p95 | Max | Full GPU valid/invalid |
|---|---:|---:|---:|---:|
| 256/27 | 0.5542771866 | 1.1767793301 | 6.3258488471 | 8847360 / 0 |
| 714/27 | 0.7337404231 | 2.0160825394 | 16.0386581163 | 8847360 / 0 |

BOTH pass unchanged aggregate mean<=1 AND p95<=3. Native requests ea052e03
(renders),98ba18bc/ba44904a(comparisons). This is exact-source development
evidence, NOT independent final acceptance or full Dolby identity. Original
PQ/cache and original-derived BT2020/cache maximum differences are zero for
both34560 lattices. NEW production-double vs RETAINED frozen outputs has maximum
deltaEITP2.40e-11/5.50e-11; old candidates/official metrics were not rerun.
Native C vs retained-double means.000527303/.001304986; GPU vs retained-double
means.001493629/.002943773, p95.003744749/.006502622, maxima.008261643/.027977601.
The714 referenceY[100,600) earlier sampled p953.40413 residual remains explicit.
Full GPU domain validity is measured, but full-raster tail/zero-Y branch counts
are not claimed. Deferred negative-domain/endpoint/cache regressions remain
required. Native C's existing rescaler defines PQ0 as0 versus binary64
PQ0=7.309559e-7; exact float preparation fields are retained, not silently repaired.

[Sanitized development evidence](../evidence/sqrtsum-development373.json)
binds source/reference/candidate and comparison hashes. Private complete
archive SHA256 bed09cfc7e18206f90f8f5a6dce5df42d8e85d09ccc2dedf4c4a08c9513cdf0e
retains74 files, including actual generated shaders/receipts/samples; all artifact
hashes verified. Static shader inspection confirms sticky alpha/no background
repair/no generic IPT/no old MB cap; invalid-regression execution remains deferred.

Remaining: coordinator-owned independent evidence and acceptance, not a repeat
of these successful renders/comparisons. Return to coordinator for
frozen independent evidence, genuinely independent final adversarial review,
fixes, ONE whole-candidate affected unit batch/repository gate, substantial
PR/merge and versioned Ubuntu source/binary installation/rollback. No such
final acceptance, publication or deployment is claimed here. PR16 stays held;
no Apple TV or physical display action.
