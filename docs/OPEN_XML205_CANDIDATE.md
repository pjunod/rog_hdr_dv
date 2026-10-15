# OPEN XML205 PQ-Hermite/SOP diagnostic

Status: implementation in progress; native compilation and independent source
review pending. No units, candidate renders or accuracy comparisons have run in
this source phase. This is not full Dolby mapping, consumer-CM identification,
certification, legal clearance, Windows/OEM equality or optical acceptance.

## Frozen public embodiment and limits

`open-xml205-hermite-pq-sop-v1` has exactly three fixed diagnostic variants:
`l1-rational`, `l1-hermite`, `l1-hermite-sop`. Choices/constants predate comparison
results; there is no fitting, sweep, threshold change or hidden feature gate.
The rational variant uses the existing ST2094-10 curve in its real nits units,
not a renamed patent Hermite curve. Baseline source, ELF, protocol and receipts
are unchanged. The strict schema3 original-source verifier is reused unchanged;
no new XML parser, authored metadata, raw-RPU serialization or quantization is
introduced. Only exact original target27/600nit/0black/P3D65 is selected.

The primary curve independently implements US10600166B2 Table1 steps1-3,5-8,
Eq7, replacing step4 with the improved cutoff rule in paragraphs0080-0082
(PDF p13 col10). Public source: <https://patents.google.com/patent/US10600166B2/en>.
For genuine normalized-PQ L1 anchors A<=B<=C and physical target PQ bounds a<b:

    L=B-A; H=C-B; cutoff=a+0.5*(b-a)
    Y=min(cutoff,max(B,a+0.5*L)) if B<=cutoff
      else max(cutoff,min(B,b-0.5*H))
    U=max(Y-L,a); V=min(Y+H,b)
    u=(Y-U)/L; v=(V-Y)/H
    s0=min(3*u,u*u); s2=min(3*v,1,v**4)
    s1=min(3*u,3*v,1-B+Y)

These are normalized PQ coordinates and dy_PQ/dx_PQ slopes, not nits or
source/target-normalized RGB. Disclosed example defaults are frozen at tail/head
preservation0.5, cutoff0.5, contrast1 and powers2/4. Stable equivalent secant
calculation avoids cancellation before float preparation. Physical target bounds
remain separate from U,V: V can exceed C when the interval is translated. No
`min(source_peak,target_peak)` cap is imposed on this embodiment.

Each segment evaluates y0+t*(dx*m0+t*(3*dy-dx*(2*m0+m1)
+t*(-2*dy+dx*(m0+m1)))). Exact source-anchor branches return stored mapped anchors;
linear continuations retain full input-domain tails. The GPU uses these same
prepared float coefficients analytically, not a uniform LUT that omits B.
CPU and GPU use binary32 evaluation, subject to normal arithmetic/SPIR-V
rounding; no exact bitwise CPU/GPU claim is made. Identity curves have an exact
x bypass before the final physical clamp. The optional sampled CPU generate
API has a distinct function identity and is not used by the analytic shader.

For strict anchors the improved rule yields a<Y<b, U<Y<V, secants in(0,1].
All slopes are nonnegative and <=3 times the corresponding secant. The normalized
segment derivative is a convex combination of 6t(1-t),3(1-t)^2,3t^2 and
3(1-2t)^2, so it is nonnegative on[0,1]. Shared s1 and matching linear tails give
C1 joins before physical clipping. The deferred C regression also evaluates the
quadratic derivative minimum at endpoints and its interior stationary point.
This is real-arithmetic analysis, not a test pass or exact floating-point proof.

Explicit engineering policies, not claimed patent/consumer rules:

- Reject unordered/out-of-domain/nonfinite anchors and a>=b before division.
- Flat source maps constant clamp(B,a,b).
- Omit collapsed source segment; its endpoint/shared slope is0, surviving
  segment keeps the appropriate head/tail endpoint rule.
- Rounded-flat target segments have both adjacent slopes0.
- Final clamp[a,b] is a physical-volume policy separate from Eq7 linear tails;
  it changes derivative continuity at physical clipping points.

## Typed SOP and unapplied fields

Original XML controls are retained as exact decimal strings. Indexes3/4/5 are
Lift/Gain/Gamma; indexes0/1/2 remain uninterpreted. Exact rational arithmetic uses:

    Gain=1+XMLgain/2; Lift=XMLlift/2; Gamma=1+clamp(XMLgamma,-1,1)/2
    dS=clamp(Gain*(1-Lift)-1,-0.5,0.5)
    dO=clamp(Gain*Lift,-0.5,0.5)
    dP=clamp(1/Gamma-1,-0.5,0.5)
    S=1+dS; O=dO; P=1+dP

Public US12573352B2 Eq1/5/6/7 normalized-PQ embodiment:
<https://patents.google.com/patent/US12573352B2/en>.
With actual physical a=PQ(black), span=PQ(peak)-a:

    z=(y-a)/span
    output=a+span*pow(clamp(S*z+O,0,1),P)

P is a direct exponent, not its reciprocal. Supported Lift/Gain are[-1,1];
nonfinite/out-of-range values reject. Original gamma and its specified clamp are
recorded. S/P are positive[0.5,1.5]. Exact S=P=1,O=0 bypass preserves L1 bytes.
The clamp is an explicit finite nonnegative target-domain policy, not another
asserted exact Dolby operator. No12-bit/raw-code roundtrip occurs.

XML physical-control interpretation, Eq1 delta-to-factor mapping and applicability
to existing HPE-LMS/PQ/IPT I are explicitly OPEN hypotheses. This is neither raw
Profile5 IPT-PQ-c2 nor metric ICtCp, nor a proven consumer domain. SOP executes
once after L1's existing brightness/chroma compensation and before the existing
final physical-target gamut mapping once. It does not recompute compensation
from SOP output or add a post-render image mapper. SOP remains reachable when
L1 is identity. Genuine target27 derives S=507/500,O=-7/500,P=2000/2001 from the
original decimals, chosen before reference comparison.

Every result retains all source records and names unapplied fields explicitly.
Target27's nonzero chroma(-0.002) and detail(-0.75) remain UNAPPLIED; saturation0
is retained, not claimed as support. L3/L8, midcontrast, temporal/CM selection,
raw-RPU SOP, clipping/vector operations and target interpolation are unsupported.
`selected_cm_name` remains null; AlgorithmVersions0,0 does not select a consumer CM.

## Source, transport and receipts

Private development ABI362 deliberately changes frame-owned metadata layout;
only matching headers/library/consumer are built. No installed package or old
ABI360/361 consumer changes. Metadata version2 owns typed SOP values and version0
resets ordinary behavior. Frame target snapshots are copied by value, not borrowed
feedback pointers. The frame-mixing cache includes explicit L1/SOP/variant,
stream/frame and complete physical-target generation/identity/value state even
with preserve_mixing_cache. Analytic coefficients and SOP values enter shader
uniforms/value signatures, not process-global/pointer-only metadata keys.

`DVH3` tokens, in order (no optional tokens; exact EOF): magic,width,height,
sourcePrimariesCode1, source volume(min,max,8xy), target volume(min,max,8xy),
L1min,L1avg,L1max, variant0/1/2, actual S,O,P. Non-SOP variants require identity
factors in transport but do not claim authored identity. Controls derive only
after unchanged strict schema3 source, target, frame, original storage and metadata
verification. Finite/range/geometry validation precedes Vulkan and any output.

    python3 -m tools.dolby_harness.open_dm_build --library-source OWN_SOURCE \
      --library-build OWN_BUILD --source-manifest SOURCE.json --output NEW_BUILD
    python3 -m tools.dolby_harness.open_dm render INPUT \
      --variant l1-hermite-sop --native ELF --compile-receipt RECEIPT --output NEW_DIR
    python3 -m tools.dolby_harness.open_dm compare CANDIDATE REFERENCE --report NEW_FILE

`hdr.open-dm-result.v1` separates role/source_alignment/encoding/output/algorithm/
provenance from historical baseline schema3. It includes original records,
controls/factors, applied/unapplied stages, hypotheses, actual immutable target,
input/frontend/control/log/ELF/header/committed library source/runtime/CPU-ICD
identities. The compile source set includes the candidate's committed SOURCE.json,
not hardcoded baseline COMPILE_INPUTS. Actual loader selection and clean CPU ICD
environment are checked before and after rendering; actual used source/generated
headers and the full source manifest are rehashed. Old receipts are not relabelled.

Comparison independently revalidates candidate and genuine schema3 reference
against their actual input manifest, then exact same-source/frame/metadata/target/
encoding alignment. It takes one bounded hashed output snapshot per result,
validates normalized finite samples, and calls unchanged metric.compare_pixels.
Full raster/BT.2124/nearest-rank p95/mean<=1/p95<=3 stay unchanged. No vendor rerender,
crop, registration, sampled raster, threshold fitting or held-out reuse is added.

## Review and later validation

Write/compile regressions now, execute only after full source review/fixes.
Recovery owns one affected batch and one fixed comparison per variant against
retained genuine reference. Python positive source/result fixtures require actual
authentic256; C/scalar mathematical fixtures are explicitly synthetic algorithm/
cache regressions, not authored Dolby inputs or reference agreement evidence.
No official tool receives mutated test controls. Missing genuine fixtures fail,
never become skips or fabricated positives. Source approval is bounded partial
source qualification, not full mapper acceptance. Existing whole-mapper review,
Windows/OEM, content/profile/CM coverage and optical gates remain open.
