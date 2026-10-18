# OPEN absolute-PQ SOP alternative

Status: implementation and native whole-batch compilation delivered. The single
authorized development comparison FAILED unchanged mean/p95 limits. Independent
whole-batch source/evidence review is next; new/invalidated units remain deferred.
This isolated candidate is NOT merged, packaged, qualified, released or installed.
It is excluded from the parallel merged-runtime Ubuntu packaging lane.

## Frozen alternative, not a fit

The new `l1-hermite-sop-absolute-pq` variant uses algorithm
`open-xml205-hermite-absolute-pq-sop-v1`. Public US12573352B2 Eq5 discloses
`(S*y+O)^P`; optional Eq6/7 target normalization is a distinct embodiment.
The source/domain ambiguity was documented before these outputs. Selection of
this embodiment by any consumer CM/profile remains unknown.

The existing public improved Hermite, authentic L1, target, coefficient derivation
and post-L1-compensation/pre-gamut placement are unchanged. Original XML decimal
strings derive actual factors without quantization. No rawRPU/L8 equations,
new black/curve/compensation rules, fitting, interpolation or tuning are added.

For current absolute normalized-PQ IPT-I `y` and physical target bounds
`a=PQ(black)`, `b=PQ(peak)`, the only changed model arithmetic is:

    u = clamp(S*y + O, 0, 1)
    output = clamp(pow(u, P), a, b)

No target normalization or denormalization occurs. Both clamps are explicit OPEN
finite/nonnegative-input/output-volume policies, NOT normative patent/consumer
claims. Valid identity factors preserve the exact existing bypass after input,
domain and target validation. Unknown present domains reject before rendering.

`PL_DOVI_DM_SOP_ABSOLUTE_PQ` is appended to the domain enum. DVH3 variant3
is appended explicitly; old variants0/1/2 retain their meaning and old consumers
reject3. Private ABI364 is paired with rebuilt headers/consumer/library/runtime;
ABI363 observation code is not imported. Metadata remains frame-owned by value.
The existing frame-mixing signature already hashes SOP domain; shader domain
changes emitted source and parameter values remain uniforms. No user gate.

The old normalized embodiment's scalar/shader arithmetic is unchanged. Old303
results must be read with their original ABI362/frontend provenance, never
relabeled as new-source passes. `authored_master.py`, original inputs, reference,
all predecessor trees/builds and old pixels remain read-only.

## Evidence phases and limits

PhaseA executed the nine independently approved stage307/308 methods once in one
native Python process. All9 passed, no skips/failures/errors,0.055s unittest wall.
Reviewed source was top7a08ea21/tree81b78153, library9fb7cbf9/tree32e7ec19.
This tests retained observation machinery, not new ABI364 or full mapper fidelity.
Its original fixed final-linear exceedance and all earlier numerical failures
remain failures.

PhaseB writes and compiles scalar/domain/clamp/identity/invalid-domain, GPU/cache,
native protocol, authentic association and exact algorithm/domain/provenance
regressions. They remain unexecuted until full independent review. One new
source-bound authentic frame256 development render and one unchanged full-raster
BT.2124 comparison are authorized, with mean<=1 and p95<=3. No old render,
comparison or official-reference normalization is repeated; no vendor call,
new frame, metadata perturbation or result-driven tuning is authorized.

Actual nonzero chroma/detail remain unapplied with exact source strings;
selected_cm_name is null. Public embodiment implementation and even a passing
single development comparison would not establish full CM applicability,
held-out/content/temporal/rawRPU/L8/Windows/OEM/optical acceptance.

### Actual development result and compiler closure

On committed source `98e0ce9` / tree `976781cc`, library `e9869a0` / tree
`1d2f1187`, native full Vulkan/shaderc/DOVI and noDV builds each compiled125
warnings-as-errors commands,14 deferred executables and60 C/C++ header units.
The paired ABI364 consumer binds36 copied/generated headers,97 compiler
dependencies and35 runtime closure entries, including the exact private library
and CPU Vulkan ICD. Compilation is not unit/SPIR-V/pixel qualification.

The first compiler receipt failed closed because upstream computes API version
by dictionary key count: adding364 above362 yielded363. A reserved363 bookkeeping
entry fixes that cause without importing any observer code. Initial output/logs
remain retained; corrected ABI364 source was rebuilt and export replay matched.
The appended patch SHA256SUMS was deliberately regenerated for this source fix.

Exactly one new authentic frame256 variant3 render and one unchanged BT.2124
comparison ran. Across all8,847,360 pixels: mean9.611271870503995,
p9516.368383078915453, max26.04627366711356. Limits mean<=1/p95<=3 FAILED.
Render19.64s; comparison103.16s; maximum comparator RSS3,627,640KiB, no swap.
This is pre-review development evidence, not a passing acceptance or final
qualification receipt. No fitting or model/threshold change followed this result.
Original source/reference/control records and all prior303/289 failures remain.

The affected proposal is3 new Python methods plus5 genuinely invalidated methods
and the indivisible native `dovi_dm.c` scalar/GPU/cache executable. Six unchanged
303 method histories and77 baseline histories retain their original identities;
none is relabelled as a new-source pass. Recovery commissions that batch only
after the independent whole-batch source/evidence review and any fixes.
The [source/development receipt](../evidence/open-absolute-pq-source-phase.json)
contains source/compiler identities, actual numerical failure and private archive
hash. Large pixels and full compiler/runtime/log receipts remain private.

Current source export: `wip/libplacebo-dm/absolute-pq/SOURCE.json` and appended
patch against the exact existing library candidate. The old source pin/export
remains historical. Native source/header/ELF/runtime receipts are separate from
unit qualification. Recovery owns the later once-only affected batch and semantic
interpretation; the original whole-mapper review/validation gates stay open.
