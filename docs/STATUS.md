# Status — what is working and what remains

**Updated:** 2026-10-12 (America/New_York) · **State:** hdr9 library and
`nativehdr8` compositor installed on 2026-10-11; the owner's HDR session runs
on it and the owner accepted the picture. The tenth batch (`nativehdr9`,
general display targets, and the upstream-facing Mutter port) is reviewed
and packaged. It is installed on the second test machine `lab6`, where
native SDR mode publishes the panel's EDID gamut as its target. Full Dolby
Vision and measured image-quality acceptance remain open.

The [visual status page](STATUS.html) shows the workboard. [Provenance](PROVENANCE.md)
distinguishes inherited evidence from new work, [development](DEVELOPMENT.md)
defines validation, and [review](REVIEW.md) records findings and their resolution.
Source qualification is separate from package delivery and physical measurement.

## nativehdr10 — reviewed source batch and validation

### Source-grounded public RGB correction (2026-10-17)

Done: immutable original/reference/compiler preparation; two distinct complete
public contracts and continuous XML bridge; cached34560-pixel diagnostics;
ABI365 actual scalar/GPU RGB-pre-PQ SOP/color/rational-Y implementation with
frame/cache identity and one physical gamut stage. Native full/noDV -Werror and
matched consumer/header/runtime compilation passed; new regressions are compiled
but not executed. One actual new GPU development render succeeded.

Current: accuracy still FAILS. DoViBaker sampled mean71.124/p95151.445;
MPC continuous-XML1.72847/3.89322; one target-native-basis correction1.72471/3.88528;
actual GPU1.72787/3.89401. Samples do not meet the unchanged1/3 bar and are not
full-raster acceptance. The negligible basis effect and signed dark/neutral
residuals guide source-stage analysis, not parameter fitting. Original reference,
baseline pixels and prior failures remain unchanged; old tests were not repeated.
Subsequent one-at-a-time source discriminators: curve-before-SOP order alone
1.75578/3.72667 FAIL (black improves, nonblack neutral worsens); scalar PQ-Y
pre-SOP domain alone1.42408/2.97567 still FAILS mean. Its separate ABI366 SG0-only
scalar/GPU implementation is now compiled full/noDV and with the matched consumer
using warnings as errors (library5a7500f, native request11df1b13). One actual
frame256 development render94c753eb gives sampled1.42340/2.97584, still FAIL mean;
scalar/GPU deltaEITP mean.001175/p95.002912/max.007141. It is not final acceptance.
The complete target-PQ-normalized scalar post-curve composition also FAILS
1.98229/4.50778, including its predeclared adverse black/midtone behavior; no
black/bright splice followed. Cached exact-input reference dispersion is small
in the limited repeated nonblack population, not evidence of a recovered detail
stage. A scalar API marker null-callback hazard was corrected and compiled
full/noDV with -Werror; new regressions remain deferred. Current analysis is the
documented coupled intensity/chroma path, not a coefficient sweep. Later genuine
shots require explicit shot-inheritance provenance support in the strict adapter
before independent held-out comparisons; the parser2/export4 extension and four
genuine-XML regression definitions are now written/syntax-checked, not executed.
No metadata/frame identity was invented. The coupled HPE/IPT/Eq8 chain also fails:
one invalid final PQ-domain pixel makes the full primary metric unavailable;
partial34559 diagnostics1.93870/4.47002 are not acceptance. No failed diagnostic
was promoted into the GPU or used to replace older qualification receipts.
One predeclared direct-LGG versus retained wire-composition convention test on
the unchanged pre-Y chain FAILS5.53573/9.05053. Improved blacks do not offset its
worse midtones; no intermediate factor or black/bright splice was selected.

The joint thinkers' reconciled v2 audit ran ONCE on the unchanged34560 cache:
8527 reference-floor flags, zero source-SOP clamp/floor activations,22387 failed
channel-scale overlaps,3 active/undefined physical-P3 rays,3646 eligible diagnostic
samples. Original black8439/nearblack-neutral155/nonblack-neutral33/chroma25933
groups are unchanged. Nineteen occupied1/8-decade bins supply one predeclared
quadruple; CRx1.0045260613 is inside conservative CRy[.9922560170,1.0079000635],
so this interval test does not refute the family. Exact rational W sanity passed;
floating discrepancy2.22e-16. No fitted coefficients, replacement quadruple or
subset acceptance. All-sample WpreY1.4240802336/2.9756704295 remains FAIL.
That historical frame256 audit initially exceeded the shared4MiB export cap
after successful analysis; its native JSON was retained, not recomputed.
The preselected genuine frame714/target27 is now acquired once, with producer
global-sequence/source202 association, actual ordinary reference logs and a REAL
parser2/schema4 export. Its complete existing nonzero-SG W MpreRGB scalar diagnostic
FAILS mean6.0153292786/p9511.0634485591/max16.2296053817 on the new34560 lattice;
invalid0, affine/PQ-floor/rational-clamp0. This reports raw pre-final-GPU-volume
output, not a GPU or full-raster acceptance result:414 outputs leave physical P3
(409 negative,5 above600nit), while all reference samples are inside. Exact v2
interval columns plus sourceP3PQ/linearBT2020/sourceY/referencePQ/referenceY are
retained locally, with actual714 SOP/curve/cache identities and no fitted values.
SG0-only Y preparation explicitly rejects714; no fallback or Y image evaluation.
714 is DEVELOPMENT evidence on inspection. Thinkers reserve untouched1200/target48
for final frozen-candidate acceptance; this task did not acquire or inspect it.
No old render/build/unit was repeated; no new mapper/source change is accepted.

ABI367 mastering-black continuation is compiled full/noDV/consumer with -Werror
(library62e3651, nativecf927164). The additive zero-low-knee/mastering-black Y
operator applies actual PQ color after RGB ratio restoration; older variants
remain distinct. Frame256 exact-cache lattice ran once: double mean1.123974/
p952.719644/max7.345998, native C1.123865/2.719393/max7.345998, still FAIL mean.
The guard contradiction is resolved by Fable's recorded MB-only rule: SOP stays
within PQ1 over declared L1; scalar out-of-range pixels fail closed, while the
GPU has an explicit finite SOP cap. Library77894e1/treec595a7b4 compiles full/noDV
and with the matched ABI367 consumer using -Werror (nativeffa70dbd). The missing
714 lattice ran once: double2.4188421987/5.5534202192, native2.4188631814/5.5532675763.
No successful256 lattice was repeated. One GPU render per shot gives sampled
2561.1229053/2.7193929 and7142.4176843/5.5502988. GPU-versus-double means
.00162194/.00294441, p95.00395024/.00656558, maxima.01286384/.02725629;
these are not a universal .003 bound. Zero domain violations establish only
evaluated-lattice safety; no full-raster domain-counter claim is made.

Completed full-raster development comparisons (8,847,360 pixels each):
256 mean1.1182596908/p952.7077148379/max9.6359169016;714 mean2.4148650269/
p955.5495142923/max51.9004941175. BOTH FAIL unchanged mean<=1/p95<=3.
The original open_dm.compare attempt stopped before metric evaluation because
prepared-curve tuples serialize as JSON lists. A separately source-hashed
comparison-only driver, authorized by the coordinating thinker, rechecks the
exact archived rendering frontend/compiler closure and every original result/
reference check, canonicalizing ONLY expected algorithm JSON. Unchanged
metric.compare_pixels ran once per raster; this is NOT old open_dm.compare
success or a new-source render. Future algorithm metadata is JSON-native;
regressions are written, unit execution still deferred. Original outputs,
frontend, failures and partial receipts remain immutable. See
[completed evidence](../evidence/public-mapping-mastblack-completed-development.json)
and [current hypotheses](MAPPING_HYPOTHESES_ASTRA_20261018.md).
1200/48 remains untouched, not development evidence. No tuning or SG drop.

Latest bounded analysis: independent source audit completed with no supported
next-chain contract (not final acceptance review). Its forward-only HK shoulder
argument was corrected by including the algebraic inverse. The new complete
fixed diagnostic ran once per34560-point development lattice:256 mean1.177968/
p952.870972;714 mean2.071912/p954.277430. Both still FAIL and are not renderer
changes or full-raster results. Newly retrieved double-rational midpoint rules
have an explicit zero-black domain gap; one labelled metadata-only extension
overshoots midtones and was not run on image populations. Sol's bounded public
source retrieval is now complete with no new automatic contract. Two additional
metadata-only preparations (mastering-black default spline and standard-offset
BT2390) were rejected before pixels. The explicit display-endpoint/content-knee
hybrid subsequently ran once per retained lattice, all34,560 samples valid:
256 mean1.306632/p953.107560;714 mean2.095011/p954.435191. Both FAIL; the chain
is rejected with no extra endpoint variants or renderer promotion. One new
scalar-HK trim-placement preflight on synthetic colours has too little714
midtone effect to justify a population run; it is not a measured accuracy result.
The bounded detail-control collection is complete: actual ninth-Trim carrier
serialization is established, but its pixel operator remains unresolved. A new
root-resaturation synthetic preflight resolved the complete-product black limit
but has adverse midtone direction and one downstream domain failure; no image
run follows from it. The fixed source-example edge-aware spatial diagnostic
subsequently completed once per lattice with zero invalids/center mismatches:
256 mean1.072781/p952.521025 and714 mean3.249286/p959.970671, both FAIL. Its
small literal derivative weights barely change the rejected Gaussian; no
gain/weight variant or renderer promotion follows. XML detail-0.75 remains
unresolved/unapplied. The US9613407 primary-source check is complete: textual
Eq9/reconstruction supplies no identity-chroma repair, while Fig5 wire
connectivity remains unverified. No silent unity term is added. The same
source's distinct sqrt-sum automatic-curve preparation has now had one
metadata-only preflight: plausible714 midtone/shoulder correction and a retained
below-Crush extrapolation failure. The complete frozen hybrid subsequently ran
once per retained lattice:256 mean0.5603548662/p951.1879074668 and714
mean0.7419340669/p952.0535960357, each34,560 valid/zero invalid. BOTH SAMPLE-PASS
the unchanged1/3 limits;256 remains reconstructed-source prospect evidence.
The714 referenceY[100,600) stratum still has p953.40413, and input-tail/zeroY
branches were unexercised. Current: the exact chain is selected for additive
ABI368 scalar/GPU implementation, now completed and compiled full/noDV/matched
consumer with warnings as errors. Exact ORIGINAL-source full-raster development
qualification ran once per shot, 8,847,360 pixels each:256 mean0.5542771866/
p951.1767793301/max6.3258488471;714 mean0.7337404231/p952.0160825394/
max16.0386581163. BOTH PASS unchanged mean<=1 AND p95<=3. Every downloaded
GPU pixel has valid alpha, invalid0 each; this is actual full-raster domain
evidence, not sampled inference. The exact-source256 result supersedes only
the reconstructed-source prospect limitation, not its historical receipt.

Frozen library f3b1d3f/treefb4c3879 and frontend f8980e78 retain compiler,
source/reference/candidate, control and generated-shader closure. Source/native
ownership was explicitly released after verified closeout. Scalar/GPU sampled
means .001493629/.002943773 and p95 .003744749/.006502622 are separate precision
evidence, not a universal .003 bound. Full-raster endpoint/zeroY branch counts
are unmeasured; negative-domain/endpoint regressions are compiled, not run.
The earlier714 bright-stratum residual and unresolved XML detail remain visible.
See [frozen implementation and evidence](SQRTSUM_PQ_Y_POST.md).

Current: advance this SAME numerical candidate to the independently preselected
global1200/source283/original target48. Necessary original-target selection and
strict reference-provenance plumbing must be committed and frozen BEFORE any
reserved output inspection; no tuning or alternative curve. The independent
comparison is not yet acquired or passed at this checkpoint. Development
passes are not official CM identity or final programme acceptance. No successful
render/comparison or unit batch is repeated for this handoff.

Remaining: passing frozen independent official reference, completed
batch adversarial review/fixes, one affected unit batch/repository gate, merge-ready
substantial PR and versioned Ubuntu source/binary package delivery with isolated
install/rollback evidence. No support-email prerequisite, full-Dolby/CM/rawRPU/L8,
chroma/detail/temporal/seek or physical acceptance claim. See
[public RGB mapping](PUBLIC_RGB_MAPPING.md). Earlier ABI364 software qualification
is retained319, distinct from its failed image agreement; checkpoints below are
historical, not the current review gate. No deployment; PR16 remains held.

### Isolated OPEN XML205 diagnostic (2026-10-15)

Current follow-up: the corrected original source was independently approved301;
its once-only affected batch303 passed but all three authentic frame256 numerical
comparisons FAILED the unchanged1/3 mean/p95 bar. Observation307 was independently
reviewed308 and its nine new methods passed once310 on OLD307 source. Original
final-linear bound exceedance remains a failure, not proof of a compiler defect.
New [absolute-PQ SOP alternative](OPEN_ABSOLUTE_PQ_SOP.md) is written in isolated
ABI364, preserving normalized arithmetic and old histories. Done: native full/noDV
whole-batch and matched consumer -Werror compilation, export replay, and ONE
authorized development render/comparison. The new result FAILED unchanged limits:
mean9.611271870503995/p9516.368383078915453 across8,847,360 pixels. No tuning.
Current: independent whole-batch source/evidence review. Remaining: recovery-owned
approved affected batch (3 new+5 invalidated Python methods and native dovi_dm),
then semantic disposition. Six303 and77 baseline histories retain actual identities.
New/invalidated units are deferred until after review. Full mapping is incomplete;
this unqualified source is excluded from parallel merged Ubuntu packaging.

Historical original source-phase checkpoint (not the current review gate):

Done (source only): additive DVH3 consumer/frontend/provenance, exact original
decimal SOP derivation, analytic public improved PQ-Hermite core/shader and typed
target-PQ SOP after existing L1 compensation/before final gamut once; explicit
private ABI362 and value-keyed frame/target cache. Original adapter/stock source
remain byte-identical. Retained full compiler361 prerequisites are reused.
Native compiler: full Vulkan/shaderc/DOVI and separate no-DV builds passed with
warnings as errors, each14 deferred executables/60 C/C++ header translation units;
separate matched DVH3 ABI362 consumer/header/loader/CPUICD closure passed.
Current: round1 review identified mixed-precision decimal L1 ordering and incomplete
no-SOP unapplied-field reporting. Source fixes and11 deferred Python method definitions are written;
affected consumer recompilation passed natively with -Werror and matched ABI362
source/header/library/loader closure. Corrected-source re-review is next. Valid
unchanged library/full/noDV compiler receipts are retained, not repeated.
No unit/render/metric execution or approval. Compilation of generated
shader C is not SPIR-V/runtime shader or pixel acceptance.
Remaining: independent review/fixes, then recovery-owned one affected batch and
fixed-variant comparisons against retained genuine original reference.
Primary public Hermite is distinct from named nits-rational ablation. Nonzero
chroma/detail, rawSOP/CM/L8/temporal rules and full content/OEM/optical acceptance
remain open; hypotheses/unapplied fields are machine-readable result fields.
See [OPEN candidate contract](OPEN_XML205_CANDIDATE.md). PR16 held; no deployment.
The [source/compiler receipt](../evidence/open-xml205-source-phase.json) records
actual build/loader identities, source replay and explicit unexecuted boundaries.

### Isolated authored-master adapter (2026-10-15)

Follow-up checkpoint: the reviewed frame0 recipe completed with40/40 selected
units and31 retained histories, but numerical acceptance FAILED
(mean10.742194879314294/p9510.745346596543353 versus unchanged1/3 limits).
No equation or threshold was changed to fit that near-black frame. A separate
owned branch now implements strict v2 nonzero-frame receipt binding while
retaining v1; one ordinary authentic frame256/target27 reference was acquired
with unchanged original metadata/declaration repair and exact256 output/log
identity. Original/storage bytes were imported without re-download or decoding.
All native compile inputs/ELF/runtime are unchanged; no rebuild was needed.
Current: complete source/reference candidate ready for independent review;
Python syntax and hash/AST applicability inspection passed, six new regressions
remain unexecuted. Per-ID71-history applicability proposes14 affected methods
and63 retained histories, not fresh unit passes.
Remaining: source approval, then coordinator-routed one affected unit batch and
one frame256 candidate/full-raster comparison. No new units/candidate/comparison
have run, no namedCM/rawSOP/L8 or full-mapping/optical claim. The frame has real
variation, not demonstrated highlight/full-content coverage. The earlier adapter
notes below are historical implementation-phase evidence, not the current gate.

Historical frame0 implementation checkpoint (superseded by the above execution
and follow-up state):

Done: verified the frozen source base and retained native compiler/header/runtime
identities without rebuilding libraries; implemented schema3/DVH2 full-raster
P3D65/PQ HALF, strict XML2.0.5/sparse association and storage-only decoder;
compiled the native consumer with warnings as errors and zero diagnostics;
prepared the actual original private source manifests on both durable hosts.
Independent review262 found a Path/bytes compile-hash defect and unbounded
result reads; corrected both, using single bounded candidate/reference output
snapshots and the same input snapshot for domain checks. Five new deferred
regressions extend the proposal to40 selections/31 retained histories; unchanged
C/build/library inputs reuse the successful ELF without recompiling.
Current: complete-candidate corrective re-review. Remaining: coordinator-routed
one original frame0 render, one affected unit batch consuming those actual
candidate/reference artifacts, then one comparison. No units, candidate
render, metric or vendor execution has run in this implementation phase.
The acquired frame is nearly uniform near-black: even a later passing comparison
cannot establish representative trims/highlights/chroma or full Dolby agreement.
PR16 remains held; no publication, installation or physical/display action.
See the [bounded adapter contract](AUTHORED_MASTER_BASELINE.md) and
[source/compiler-only receipt](../evidence/authored-master-adapter.json).

The owned collaboration clone starts at the exact final handoff
`7c78457581906a43377f8dbb0d8dc95b438f30d3`; PR 16 remains unmerged.
Astra and Fable approved the design; Sol and Opus implemented the two source
parts. The pinned upstream Mutter tree
`3f238d2e9227dacd578f5a673c04ac10de5caac8` and library tree
`72626245922181526fbcb990de3eb7f575efa56b` were reconstructed and compiled
natively on x86_64 with warnings as errors in this task (164.61 seconds).

**Initial source checkpoint (compiled):** both parts became Mutter patches 0050–0061
in `patches/mutter`, originally pinned as candidate
`fa7eb2cf55dd39464ef04042e3f085a5d6c18e5f`, tree
`18ba4b5a752f4ee383541757b20116060f18daf9`. Patches 0001–0049 are unchanged.

- 0050–0052: the original Night Light work in progress, imported with
  authorship and content unchanged (tree `14ce390c…` reproduced).
- 0053: bounded diagonal factors in the output's linear RGB replace Bradford.
  Negative factors are clamped at construction, so 1000 K is projected.
- 0054: warm LUT/CTM SDR→BT.2100→SDR transitions, capture exclusion and
  forced-HDR regressions. The capture inventory found no capture path that
  applies the adaptation, so no fix was needed.
- 0055–0060: Sol's configuration, persistence, copy/history, DisplayConfig,
  gdctl and NightLightSupported commits, rebased unchanged after the
  renderer.
- 0061: target selection with `user-declared` provenance. The luminance
  override comes before DisplayID and CTA, needs no EDID and is validated
  against nominal white. The BT.2100 gamut source is auto, base-edid or none;
  native SDR is unaffected.

Every commit was built individually with warnings as errors, with 0
diagnostics. The exported series replays onto the base to the same tree.
`check_repository.py` passes. See the
[candidate receipt](../evidence/nativehdr10-source-candidate.json), the
[earlier stage receipt](../evidence/nativehdr10-sol-stage.json) and the
[contract and implementation notes](NIGHT_LIGHT_AND_OVERRIDES.md).

**Done (validation tooling, compiled):** Sol's runner, 24 regression
methods and [instructions](NATIVEHDR10_VALIDATION.md) are integrated with
authorship kept (Sol's commit `e0742e8`, cherry-picked as `b9837a4`). The
runner executes a reviewed manifest of affected checks, one argument vector
per check, with an explicit environment. It keeps receipts tied to the
source tree and its own bytes. Later runs skip receipts that still match and
retry failures. Changed inputs stop the whole batch until the affected checks
are invalidated with a reason. Its files were only syntax-compiled; the
regressions had not run at integration. The later 29-method Linux batch passed
every method (see below). The Mutter source and native build tree were
unchanged by tooling integration, so no rebuild was needed for it.

**Done (review):** Astra and Fable delivered independent reviews of
`73918f3` / native `fa7eb2cf`. Changes are required: continuous default-anchored
Night Light factors, a bounded observable-state restore wait, isolated
user-override registration, real headless capture/readback coverage and
SIGTERM child cleanup. Review completion is not candidate acceptance.

**First batch (historical result):** the single affected batch executed 71 checks on native
`9570f9bb` / tree `ac02a18f`: **69 passed, 2 failed** in 134.99 seconds.
All 29 individual Linux runner methods passed; 40 of 42 native checks passed,
including the real capture case, isolated override case, gdctl, remaining
monitor/backend and cursor cases. The failures are `mutter:color-hdr`
(near-zero channel-bound assertion) and `mutter:monitor-dbus-tests`
(restored-peak wait timeout). That first candidate was **not accepted**.
The [first batch receipt](../evidence/nativehdr10-validation-attempt1.json)
records every original attempt, command, source identity and log hash.
All 71 original logs were retrieved and hash-verified and remain preserved.

Review corrections 0062–0068 are integrated and pinned at native
`9570f9bb` / tree `ac02a18f`, with unchanged 0001–0061 prefix, individual
warnings-as-errors builds and replay equality. See the
[correction receipt](../evidence/nativehdr10-review-corrections.json).
Focused Astra review approves the default-anchored production design;
Opus completed the requested successful/nonempty capture readback sanity
in 0068 and released native source/build ownership to Sol. Fable confirmed
runner `cc82113`; Sol folded the scoped mask/replay hygiene into `e4f981d`
before freezing it. Documentation precision is fixed in `4846eda`.
Fable's
recorded decision anchors the diagonal factors at the default temperature's
Planckian white, preserving exact off-state identity and continuous onset;
absolute Planckian-white accuracy is no longer the acceptance claim.

**First retry candidate:** reviewed corrections 0069–0071 are integrated and pinned at native
`a8847717` / tree `9111578e`, with individual -Werror builds and replay equality.
0069 corrects the float32 near-zero test allowance; 0071 holds the test shell's
synchronous confirmation so rejection actually runs. 0070 fixes the pre-existing
upstream restore-idle lifecycle bookkeeping, separately from the HDR feature;
it has no upstream-acceptance claim. Prefix 0001–0068 is unchanged; hashes were
deliberately appended. See the [correction receipt](../evidence/nativehdr10-failure-corrections.json).

The approved two-check retry passed `mutter:color-hdr`; `monitor-dbus-tests`
passed the new target-overrides case, then failed on a fatal existing-colord-device
lookup in `/backends/monitor/has-external-monitor` after disabling the external
monitor. Latest required receipts: **70 passed, 1 failed** (29 runner methods,
41 native invocations passed). The candidate is **not accepted**.
All 73 execution logs were hash-verified and all 69 non-retried histories remain
unchanged; see the [retry receipt](../evidence/nativehdr10-validation-attempt2.json).
Fable `t_bedcc81f` attests retention of the 40 original native passes: exact binary
identity for 0069/0071, source unreachability for 0070's changed idle callback.
Those passes stay at their actual executing tree `ac02a18f`, never rewritten
as passes on `9111578e`. This is reviewer interpretation, not automatic runner
reuse across whole-tree changes. Sol's transport postcheck assumed history length
2 instead of original + invalidation + retry (3); its export assertion failed
after both checks ran. A retrieval-only request preserved the actual ledger/logs,
without reexecution or runner edits.

**Colord correction checkpoint:** Opus delivered and Fable `t_6b592492` approved 0072–0074
at native `980bb21` / tree `41605eb0`, individually built with -Werror and replayed.
0072 binds colord unregister to the manager's removal rather than the last reference;
0073 removes old devices before creating replacements on connector moves. These
are distinct fixes to pre-existing upstream lifecycle defects, not HDR features or
upstream acceptance. 0074 adds unplug-with-reference and connector-move regressions.
Sol owned integration/native validation during this retry. The approved retry
is exactly 17 checks whose mocked-colord traffic changes; 25 native and 29 runner
histories retain their actual executing trees under Fable's two-tier decision.
**Actual required gate:** on `41605eb0`, `monitor-dbus-tests` failed in 2.59 seconds
with exit 245 after reconnect/HasExternalMonitor TRUE; the target-overrides case
passed, and no earlier fatal-colord warning was printed. The signal/root cause
is not established by this log. `color-management` passed all 20 cases, including
the new unplug-with-reference and connector-move regressions. The remaining 15
TEST-context checks did **not** run after the required gate failed. Raw ledger:
70 recorded passes, one failure; current-candidate validity: **55 passes, one
failure, 15 pending invalidated checks**, not acceptance. All 75 execution logs
are hash-verified; 69 histories are unchanged. See the
[gated retry evidence](../evidence/nativehdr10-validation-attempt3.json) and
[colord correction receipt](../evidence/nativehdr10-colord-corrections.json).
Opus `t_ef832f3b` delivered compiled corrections 0075–0077 at native
`de09d575` / tree `058bbf97`; Fable `t_c88207c7` approved them. Source analysis
identifies base async callbacks casting borrowed user data before cancellation
checks, made reachable by 0072; no core frame was observed. The corrections
check cancellation first and add an unplug-during-setup regression. Sol now
owns released native source/build/retry-ledger and Mac integration/evidence/status.
The same exact 17 checks required retry; color-management's `41605eb0` pass was
genuinely invalidated. Retain 25 native and 29 runner histories at their actual
executing trees under Fable's recorded source/equivalence decision. Canonical
full 77-patch replay gives tree equality; prefix 0001–0074 is unchanged and
three SHA256SUMS entries were deliberately appended for the reviewed corrections.

**Done (unit validation): all17 approved retries passed** on `058bbf97`, required
pair then dependent fifteen, same persistent ledger/frozen runner. Monitor-dbus
passed as a complete invocation; color-management passed21/21 cases including
unplug-during-setup. Every one of the **71 required unit checks** has a valid
pass:42 native invocations plus29 runner methods. All92 execution logs are
hash-verified;54 retained histories remain unchanged. See the
[final scoped retry evidence](../evidence/nativehdr10-validation-attempt4.json)
and [cancellation correction receipt](../evidence/nativehdr10-cancellation-corrections.json).
The wrapper returned1 only from an erroneous postcheck after both phases rc0 and
export; schema-aware independent verification confirmed all histories/hashes,
without test reexecution or frozen-runner edits. The final source bundle and
full evidence archive are preserved under owned `.peer-linux/deliverables`.

Final repository integrity binds the final evidence/docs commit `b7d6583` in
an external receipt at `.peer-linux/deliverables/final-integrity`, avoiding
receipt-in-tree circularity.

**Done (delivery verification, Fable `t_2b0d5704`, 2026-10-12):** the final
evidence was verified read-only; no unit check, build or probe ran. Clean
`b7d6583` / tree `e70f190c` matches the integrity receipt and its recomputed
log hash. `SHA256SUMS` verifies. The 28 tracked patches 0050–0077 equal the
canonical replay inputs that gave tree `058bbf97`, and 0001–0049 and every
other series are unchanged since the handoff head. All 71 latest execution
logs and all 92 logs in the persistent ledger (`b370ff84…`) hash-verify from
the retained archive; the 17 retries executed on `058bbf97`, 24 retained
native receipts stay at `ac02a18f` and `color-hdr` at `9111578e`, as recorded.
The saved required-phase TAP shows 21 `color-management` cases including
unplug-during-setup; monitor-dbus keeps its source-bound exit 0 and Meson
summary only. Gitleaks and the publication scan are clean over `main..HEAD`.
See the [delivery receipt](../evidence/nativehdr10-delivery-verification.json).
Repository integrity ran once more on the delivery commit.

**Publication (stacked on the held PR 16):** public `main` (`eb41b16`) has
not moved since PR 16 branched, so the candidate history contains PR 16's
three commits. The substantial PR is therefore opened as a draft from
`codex/team-hdr-nativehdr10-20261011` against `codex/open-dv-track`, PR 16's
head. It cannot merge independently: merging it into `main` would land PR 16,
and merging it into `codex/open-dv-track` would move PR 16's head. It stays
reviewable and unmerged until the owner releases PR 16. It is
[PR 17](https://github.com/pjunod/rog_hdr_dv/pull/17) (23 commits, head
`004a9fb`); `main` and `codex/open-dv-track` were not moved.

**Remaining:** no second candidate-wide batch. Separate optimization
`t_38887c3f` and base async lifetime assessment `t_3502f623` are released by
this delivery and must not edit the frozen source/build. Ubuntu port (0062+)
and packaging, physical deployment, optical accuracy and Dolby Vision remain
separate qualification stages. No laptop or display configuration change is
authorized in this source batch.

## Installation — hdr9 and nativehdr8 (2026-10-11)

In a coordinated window with the owner logged out, the six packages were
installed (6 upgraded, 0 added, 0 removed), held, and the display manager
restarted. The new login screen runs on the installed compositor with no
colour or EDID warnings; it is in SDR mode and publishes a coherent
description ([receipt](../evidence/install-2026-10-11.json)). The kernel,
boot selection, Secure Boot, profiles and display settings are unchanged.
The previous hdr6/nativehdr2 packages remain the hash-verified rollback.
The owner's HDR desktop session then started on the new compositor in
BT.2100 mode. It now reports the panel's firmware-declared target to clients
(primaries and 0.0004–616 cd/m², not a measurement) separately from the
BT.2020/PQ encoding, with no colour warnings in the session journal. The owner then
checked the picture and accepted it ("the picture looks awesome"); that is
a subjective check, not an optical measurement. At the owner's request, the old agent build
containers from earlier batches were removed.

## Tenth batch — general availability: targets and upstream port

Until now only an internal panel whose DisplayID declares native RGB
BT.2020 PQ (the ROG route) had a declared colour target; every other output
used the encoding fallback, so nothing was tone-mapped or gamut-compressed.
[Display target sources](DISPLAY_TARGET_SOURCES.md) widens target selection
in the colour device. In BT.2100, the peak and black come from DisplayID
physical luminance (10% window peak required), else from CTA-861 HDR static
metadata. A peak at or below the encoding's nominal reference white is not
a target. The BT.2100 gamut still comes only from DisplayID. In the native
SDR mode, the base EDID gamut (the encoding's own) is the target, so wider
content is compressed rather than clipped. Gamut containment is now judged
after adapting the target to D65, in the frame the pixels use. Otherwise a
native SDR output whose white is not D65 judged its own encoding out of
gamut.

The whole colour programme was also ported to upstream Mutter main
(`d82671c`) as the upstream-facing series (`patches/mutter/`, 49 patches):
43 ported commits, debian excluded, with messages in upstream form, plus
the six target commits. Every commit builds with warnings as errors against
the upstream-facing libdisplay-info series. That series needed no rebase:
upstream libdisplay-info is still at its base. Neither series has been
submitted upstream. The Ubuntu series gained the same six commits as
`nativehdr9` (Mutter patches 0053–0061).

An adversarial Fable review found the white-point containment defect (by
executing a probe), the low-peak risk and the base-EDID-gamut-in-HDR risk,
plus smaller items. All were fixed or decided, and a Fable re-review found
no remaining code defects ([findings](REVIEW.md#tenth-batch--general-targets-and-upstream-port)).
The colour test set (23 invocations including two new compositor cases) passed on
the upstream-facing head ([receipt](../evidence/general-targets-fast-lane.json)).

A second test machine, `lab6` (ThinkPad X1 Extreme, Intel UHD 630, an SDR
panel with base EDID only), was inspected read-only
([hardware](HARDWARE.md#second-test-machine-lab6)). It cannot use BT.2100 on
its built-in screen. It tests the native SDR target path on Intel graphics.

`nativehdr9` was installed on `lab6` in a coordinated window: 5 upgrades, 0
added, 0 removed, held, with a stock rollback set. The login screen and the
owner's session run on it with no colour messages. In the default mode, the
session publishes sRGB with the fallback target. In native SDR mode
(selected with `gdctl`), the encoding and target primaries are the panel's
base EDID gamut ([receipt](../evidence/install-lab6-2026-10-11.json)). The
owner then looked at it and reported that the image looks great; that is a
subjective check, not a measurement.

An independent Fable review of the whole plan followed (strategy, design,
upstreaming, measurement, process). Its recommendations and the decisions it
puts to the owner are in [review](REVIEW.md#independent-plan-review-2026-10-11).

## Ninth batch — independent review and fixes

At the owner's request, independent Fable 5.1 reviews covered the whole
compositor stack, the library, Wine and Dolby activation work, and the
evidence, packaging and install kit ([findings](REVIEW.md#ninth-batch--independent-review-and-fixes)).
The most important finding: plain PQ video without a declared peak was being
tone-mapped from the 10000 cd/m² encoding capacity, which would have dimmed
ordinary HDR. `nativehdr8` (Mutter patches 0044–0052) now leaves such content
unmapped, publishes descriptions on the renderer's exact identity, and
applies the other fixes. The Wine DisplayMonitor took three fixes (lock, EDID copy, output
technologies; patches 0010–0017). A Fable re-review found no blockers and
approved the fixes (recorded in [review](REVIEW.md#ninth-batch--independent-review-and-fixes)),
and the affected fast lanes passed (synthetic headless tests;
[receipt](../evidence/review-fixes-fast-lane.json)).

The delivery set was the hdr9 library (hdr8 code; it provides the native
HDR API as a virtual package the compositor depends on) with `nativehdr8`
([receipt](../evidence/hdr9-nativehdr8-packages.json)). The install kit holds
the six packages, checks the rollback packages first and snapshots the
package state. The `nativehdr6` comparison set was dropped: it lacks the
review fixes. The hdr9 + `nativehdr8` set was installed on 2026-10-11 (see
above).

## Eighth batch — gamut compression and delivery (merged, PR 8)

`nativehdr7` (Mutter patches 0039–0043) compresses colours outside the
panel's declared gamut into it, using the ACES reference gamut compression
with limits derived from the source and target gamuts
([contract](HDR_MAPPING.md#gamut-compression-nativehdr7)). It applies only
when the content can exceed the declared gamut, so sRGB content on a
panel whose declared gamut contains sRGB, and P3 masters on a P3 panel, are
untouched. It was reviewed adversarially and
passed its affected fast lane on the first run (synthetic headless tests,
software rendering; [receipt](../evidence/mutter-gamut-compression.json)).
Whether the panel itself clips out-of-gamut input, and so how much this
changes on screen, needs the installed system and an instrument.

## Seventh batch — HLG and tone mapping (merged, PR 7)

`nativehdr6` (Mutter patches 0028–0038) implements the
[HLG and tone-mapping contract](HDR_MAPPING.md): HLG decoding with its OOTF,
validated source mastering metadata, and BT.2390 highlight mapping to the
panel's declared target luminance. Mapping is applied once per surface and
only when content exceeds that target. It was reviewed adversarially and
passed its affected fast lane (synthetic headless tests, software rendering;
[receipt](../evidence/mutter-hdr-mapping.json)).

## Sixth batch — colour input and processor activation (merged, PR 6)

With DisplayMonitor merged, the recovered OEM processor now **activates**
under Wine in the isolated fixture. It returns an `IMFTransform` that reports
one input and one output stream. It offers P010/NV12 input and 10-bit RGB,
half-float or 8-bit RGB output.
[The activation section](DOLBY_ACTIVATION_PROBE.md#displaymonitor-follow-up--the-processor-activates)
records what that does and does not prove. No media type has been set and no
frame has been processed. The next stage negotiates the offered types and
traces the metadata the transform requests. It has not started and awaits the
owner's scope confirmation.

The compositor's colour-input defects from the
[audit](COLOUR_PIPELINE_AUDIT.md#implementation-status) are fixed in
`nativehdr5`, which was reviewed and passed its affected fast lane
([receipt](../evidence/mutter-colour-input.json)).

## Fifth batch — display contracts and delivery (merged, PR 5)

Before this batch, the qualified Wine candidate loaded the exact recovered
Dolby DLL but its factory request stopped at the missing Windows
`DisplayMonitor` runtime class
([evidence](DOLBY_ACTIVATION_PROBE.md#wine-11-follow-up--the-dll-loads-displaymonitor-activation-is-missing)).
The batch delivered a [generic monitor contract](WINE_DISPLAY_MONITOR.md)
backed by actual display data, and native
[physical-target gamut reporting](NATIVE_TARGET_GAMUT.md) in the library
(hdr8 and upstream series) and the compositor (`nativehdr4`). It also added
the bounded read-only Wayland colour inspector
([guide](DISPLAY_DIAGNOSTICS.md#inspect-the-compositors-actual-colour-descriptions)).
The [optical measurement procedure](PANEL_MEASUREMENT.md) defines conditions,
initial accuracy goals and held-out validation; this unit has not been
measured.

Baseline packaging preceded the batch. The exact qualified hdr7 library
source produced amd64 and i386 packages, and nativehdr3 compositor packaging
completed in the isolated native builder. The
[package receipt](../evidence/baseline-native-packages.json) records source
identities and the six runtime artifacts. Read-only APT simulations found a
coherent six-package upgrade and modeled six-package rollback, with no
additions or removals. Recovery artifacts are hashed and retained privately;
the live installation is unchanged. Delivery now targets the newer reviewed
candidates instead of installing this baseline.

The adversarial review found two blockers and a set of should-fix defects;
all are addressed ([review](REVIEW.md#fifth-batch--display-contracts-pr-5)).
The pre-merge fast lane then passed: library groups and legacy consumers,
Mutter `native-hdr` and all Wayland target-volume invocations, 23 probe
cases, and the Wine `displaymonitor` and `displayconfig` tests
([receipt](../evidence/batch5-fast-lane.json)). Nothing was installed at that point.

On 2026-10-10 the previous agents' macOS temporary clones were gone and two
local commits had never been pushed. Every unfinished change was recovered:
the probe test selectors are byte-identical to their recorded hash, the
library, nativehdr3 and Wine baselines reproduce their recorded trees, the
Mutter edit was replayed from the implementing agent's log, and the Wine
component was copied from the retained offline compiler container. Recovered
work keeps its original authorship; corrections are separate commits.

## Fourth batch — native target feedback and processor prerequisites

[PR 4](https://github.com/pjunod/rog_hdr_dv/pull/4) adds three components:

| Component | Qualified evidence | Remaining delivery or acceptance |
|---|---|---|
| [Mutter physical-target feedback](MUTTER_TARGET_LUMINANCE.md) | Compiled with warnings as errors; independent review corrections addressed; all eleven selected checks passed across initial runs and focused retries | Package and verify active physical output |
| [Wine file API](WINE_FILE_FROMAPP.md) | Reviewed, compiled; 123 focused assertions passed with no failures or skips; loaded module identity verified | Continue processor activation investigation |
| [Synthetic HDR corpus](HDR_REFERENCE_CORPUS.md) | Eleven new tests passed; private official-reference experiment completed | Creative-trim and consumer-profile comparisons |

Mutter now keeps firmware-declared physical target luminance separate from PQ
encoding and renderer state. Immutable Wayland descriptions preserve old
snapshots and notify clients of target changes. The first test pass exposed a
shutdown lifetime defect; explicit manager cleanup before output destruction
fixes its demonstrated cause. Synthetic forced-HDR tests preserve
their manually selected output mode while testing target policy. This fixed-route
fixture does not qualify real monitor reconfiguration.

Wine is used to investigate the Windows Dolby processor recovered from the
factory image. The missing file function now passes its desktop API contract.
DLL loading now passes; actual processor activation remains open; Wine is a candidate compatibility
route, not a confirmed requirement of the final Linux solution. The HDR and
colour-management changes are native Linux code.

The owner supplied and accepted official Dolby Professional Tools v5.6.4.
Private offline reference processing has completed. Proprietary tools,
documentation, generated metadata, rendered outputs and numerical comparisons
remain private. This establishes a reference workflow, not general playback,
creative-trim fidelity or calibrated panel accuracy. Its processing container
and owned runtime image were removed after retaining private evidence.

No host package, live display setting, boot selection or calibration changed
in this batch. Mutter remains ARM64 source qualification; delivery needs amd64
Mutter and matching amd64/i386 library packaging.

## Overall remaining work

| Area | State | Remaining work or acceptance |
|---|---|---|
| Native HDR detection | Implemented and installed | Wider hardware and upstream acceptance |
| Kernel and AUX brightness | Test kernel booted with Secure Boot | HDR/SDR transitions, DPMS, suspend/resume, brightness and display-mode coverage |
| Physical luminance library | hdr9 (hdr8 luminance and gamut API) installed for amd64 and i386 | Wider hardware and upstream acceptance |
| Compositor feedback | nativehdr8 (target luminance and gamut, colour input, HLG, highlight mapping, gamut compression, review fixes) installed; nativehdr9 (targets on CTA HDR outputs and native SDR panels) packaged | Install and check nativehdr9 on lab5 and lab6; optical verification needs an instrument |
| Upstream | Upstream-facing Mutter series (49) and libdisplay-info series (10) current on upstream main | Owner decides submission (merge requests under the owner's identity) |
| Full Dolby Vision | OEM processor activates and describes its transform under Wine (proven with Wine patches 0001–0009; the review-fix modules 0010–0017 passed the DisplayMonitor tests but have not been re-run against the processor); reference workflow available; the OEM plugin does not register Profile 7, so P7 FEL is outside this route | Negotiate types, establish the device and metadata contract, process frames, validate profiles and trims, integrate playback |
| General colour quality | Audit complete; input defects fixed (nativehdr5); HLG and BT.2390 highlight mapping (nativehdr6); gamut compression (nativehdr7); all reviewed with fast lanes passed | Output characterization (contract defined; needs a measurement, see [HDR mapping](HDR_MAPPING.md#output-characterization--defined-deferred-until-measured)), SDR/HDR consistency and cross-application checks; optical verification (the owner's visual check passed) |
| Exact-panel tuning | Four factory profiles inspected privately | Obtain measurement equipment and measure this unit, then implement the [output-characterization contract](HDR_MAPPING.md#output-characterization--defined-deferred-until-measured) |
| Applications | Shared platform path first | Qualify independent consumers; Plurx integration belongs in its separate repository |

The owner has no colourimeter or spectrophotometer yet and is open to obtaining
one. Software work continues independently. Define the measurement procedure
and OLED correction before choosing equipment. Firmware and factory-profile
values are not measurements of this particular unit.

## Completed source batches

1. **Repository, diagnostics and activation probe:** ordered patch provenance,
   public source reconstruction inputs, read-only diagnostics and an isolated
   activation probe. Review findings resolved; 45 Python tests and repository
   integrity passed. Live capture reported BT.2100 at 2560×1600/240 Hz, but the
   display was powered off, so active scanout remains unqualified. The original
   Wine 9 probe initialized COM/WinRT/Media Foundation and stopped at DLL loading.
2. **Profile interpretation and colour audit:** four factory ICC variants were
   parsed privately. MHC2 transforms are identity; standard characterisation
   differs by GPU route. All 16 new ICC tests passed across the initial run and
   one corrected-fixture retry. Stock Wine 11 isolated the missing file export.
3. **[Native physical-luminance API](NATIVE_LUMINANCE_API.md):** merged in
   [PR 3](https://github.com/pjunod/rog_hdr_dv/pull/3). Additive API preserves
   fractional physical luminance and field presence separately from CTA metadata.
   ARM64 and emulated amd64 builds passed with warnings as errors; 12 selected
   checks passed with only the corrected synthetic fixture retried. Previous
   consumer binaries passed against the new libraries; both series reconstructed.

## Installed baseline and inherited evidence

- libdisplay-info `0.3.0-1ubuntu1~hdr9` (amd64, i386) and Mutter
  `51.0-1ubuntu3+nativehdr8`, installed and held on 2026-10-11.
- Kernel `7.3.0-rc5-nativehdr1`, from Ubuntu `7.3.0-8.8` plus four patches. The
  installed stock fallback kernel is now `7.3.0-9-generic` (the `7.3.0-8`
  image named in the older recovery notes has been removed).
- Replaced on 2026-10-11 and kept as the hash-verified rollback:
  libdisplay-info `0.3.0-1ubuntu1~hdr6` (amd64, i386) and Mutter
  `51.0-1ubuntu3+nativehdr2`.
- NVIDIA `615.71.09`; Secure Boot remains enabled.
- mpv `0.41.0`, libplacebo `7.360.1`, FFmpeg `8.1.2` at inspection.

Historical receipts record upstream library GCC/Clang suites at 75/75, Ubuntu
library suites at 40/40 per architecture, ABI/export checks and actual package
install/offline rollback. Mutter's six focused regressions passed; its ordinary
package batch had 190 passes and five expected failures. A marked-flaky batch
had one unresolved `map-after-headless` failure; isolated passes did not establish
that it was unrelated.

Kernel receipts record affected DRM/i915/xe compilation, sparse, four KUnit
groups, full package builds, signature checks and delivered-header NVIDIA
builds. Initial physical boot and working HDR10 were subsequently reported.
These are scoped historical results, not freshly repeated tests.

## Next work

`nativehdr9` is ready to install, in a coordinated window, on `lab6` (stock
26.10, native SDR path) and then `lab5`. An external HDR monitor on `lab6`
would test the CTA path. Submitting the upstream-facing series is the
owner's decision. Two further steps wait on the owner, and one comparison
is optional. The KMS
metadata question can be settled by an on-screen comparison if the owner
wants it; the owner's subjective check of the current picture passed. The Dolby processor's next
stage waits for the owner's scope confirmation and, before it can say
anything about this panel, a monitor descriptor source in Wine
([prerequisites](DOLBY_ACTIVATION_PROBE.md#displaymonitor-follow-up--the-processor-activates)).
Output characterization waits for a measurement instrument (owner to
obtain).
The staged acceptance criteria remain in
[Dolby Vision and display quality](DOLBY_VISION_AND_QUALITY.md#5-work-in-stages-with-observable-acceptance).

## Owner decisions (2026-10-11)

- The generally available Dolby Vision track is open, player-side
  RPU-aware display management validated against Dolby's reference renderer
  ([contract](OPEN_DV_DISPLAY_MANAGEMENT.md)). The OEM processor under Wine
  is a time-boxed experiment with a one-frame go/no-go.
- The owner will boot the laptop's Windows installation for a coordinated
  trace of the OEM Dolby pipeline (private results).
- KMS HDR metadata: run the on-screen comparison on `lab5`, then bound the
  composition and declare the display's own values if the comparison
  supports it.
- Upstream submission: yes, under the owner's identity, in slices, design
  discussions first.
- Measurement: a Calibrite ColorChecker Display Plus / X-Rite i1Display Pro
  Plus class colourimeter (supported by ArgyllCMS; not an "HL" model), plus
  one spectrophotometer session for a panel-specific correction, is the
  recommendation; purchase pending.
- A measured colour profile takes priority over EDID declarations.

## Decisions taken without the owner

Recorded for review; each can be revisited.

- Since the fifth batch, agent commits use `Claude Agent <claude-agent@invalid>`
  with a co-author trailer, and implementation and review agents are Claude
  agents. Earlier agent commits used `Codex <codex@invalid>`; recovered work
  keeps its original authorship.
- Compositor and library builds, compositor tests, the Wine fast lane and the
  packages run in disposable agent containers off the laptop (native amd64;
  the i386 library is cross-built; Wine tests use WineHQ 11.0 with the
  candidate modules overlaid). The Wine compiler and the Dolby activation
  probe run in agent-owned containers on the laptop (`lab5`) with no network,
  mounts or GPU. Package simulations and staging happened on the laptop
  before the coordinated installation of 2026-10-11; agent build containers
  from earlier batches were removed at the owner's request that day.
- The Wine DisplayMonitor uses base EDID 1.4 facts where DisplayID declares
  none.
- HLG is decoded for its declared nominal peak and then fitted by the common
  tone mapper, rather than rendered for the panel's peak.
- The BT.2390 tone mapper applies only when the content's effective peak
  exceeds the panel's declared peak. It never expands or raises black, and
  monitor screencasts are not mapped.
- `extended_target_volume` is advertised; declared mastering primaries set
  gamut-compression limits when compression applies.
- Gamut compression uses ACES reference gamut compression with limits derived
  from the source and target gamuts, tolerating the declaration's own
  quantization.
- Output characterization is not applied until a measurement exists.
- The delivery set is hdr9 with `nativehdr8`; the earlier `nativehdr6`
  comparison set was dropped because it lacks the review fixes.
- PQ content without a declared peak is not tone-mapped; its overshoot is
  left to the panel.
- KMS static metadata keeps zero ("unknown") luminance fields; whether to
  declare the target is decided by an on-screen comparison on the
  owner's HDR desktop session.
- Display targets use CTA-861 desired content luminance as the BT.2100 peak
  where DisplayID declares none. Its own provenance is `cta-declared`. It
  is a content preference, not a measurement, but most HDR displays declare
  no other peak.
- A target peak at or below the encoding's nominal reference white
  (203 cd/m² for PQ) is no target, so a bogus low peak cannot dim SDR. The
  rule uses the nominal value, not the brightness-scaled one, so a target
  does not appear and disappear with the brightness setting.
- Base EDID primaries are not a BT.2100 gamut target. Many HDR displays
  declare their SDR gamut there, so compressing toward it risks visible
  desaturation without a measurement. They are the native SDR target only.
- The upstream-facing Mutter series is a port of the reviewed Ubuntu series
  to upstream main, with commit messages rewritten to upstream rules
  (authorship, trailers and inherited validation claims preserved). A
  separate test machine, `lab6`, was added for general-availability
  checks; it stays a stock Ubuntu 26.10 baseline and is not used for builds.
