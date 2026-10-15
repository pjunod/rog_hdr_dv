# Colour asynchronous shutdown lifetime follow-up

This is a separate, unpublished source follow-up to the frozen nativehdr10
candidate `de09d575e81799a1a75fe34a44d69f04caf2e727`, tree
`058bbf9758c65798d4d0010685e32e8e76da9d3d`. It does not invalidate or replace
its accepted historical receipts. PR 16 remains held; no device deployment,
packaging, optical or Dolby qualification is part of this work.

## Source finding and design

Waiting ensure-device GTasks already own their store. The hypothesized direct
generation-store use-after-free is disproved; no redundant store ownership
or callback early-return bypassing waiter draining is added. The retained
store/device does not own its manager, however. Manager shutdown previously
left generation active until store finalization, and retained profiles used
a borrowed manager to obtain their colord client at final release. Three
startup callbacks also cast borrowed manager data before consuming their
asynchronous result.

The scoped design moves startup finish/cancellation handling before manager
access. Version-matched colord 1.4.8 and GLib 2.90.0 source were traced by the
design reviewer: their default GTask finish propagation checks cancellation,
including an earlier successful result delivered after disposal. This is
reference-source evidence, not a full reconstruction of Ubuntu library
source packages or universal equivalence of every patched binary.

Manager disposal now shuts down its store before dropping devices/client/LCMS
resources. Shutdown cancels the existing store token and stops monitoring,
but keeps pending entries until callbacks drain every waiter. A caller's
cancellation does not cancel another caller's shared generation. Both ensure
finish functions reject successful results delivered after store shutdown.
Directory requests own their callback store reference; profile-ready signals
are object-bound and drain without publication after shutdown. Generation,
EFI and assigned-profile continuations consume results then check relevant
cancellation before using borrowed resources or starting dependent work.
The directory-creation callback releases its transferred task on cancellation.
Profiles own their CdClient instead of their manager, and manager disposal
balances its original client reference. No ownership cycle or production
teardown wait is introduced.

The successful ensure-device result remains borrowed from its profile tables,
as expected by the device caller. Its scoped temporary reference is released
after insertion; that is not a dangling result because the tables own it.
The assigned-profile ensure finish retains its existing owned-result contract.

LCMS retained-handle final release is covered by the planned regression, not a
new context-ownership subsystem. The inspected manager uses a default context
without plugins. Arbitrary post-teardown profile operations/custom allocator
contexts are not claimed supported.

## Current phase

### Final scoped qualification — source-ready, unpublished

Astra completed independent-of-builder review t_63560e90 of exact native
`e2d7cfbad8d3a44dd1a9a9d89a124444e44e9bb9` / tree
`1a92b068c246b127fed721e78b4fbbd16a8d5d2b`, inheriting whole0078–0086 review
t_79ec36bd. Actual reviewer was Astra via quota routing from Fable, with prior
design involvement disclosed; not Fable/independent-model approval. The approved
manifest is immutable. Recovery t_5791ca76 verified both runtime bindings and
supplied the strict receipt; the coordinator resumed original validation.

Exactly one new serial no-rebuild run selected IDs9–24 and returned **16 PASS,
0 FAIL, 0 NOT RUN** in25.887526s. Eight retained actual passes1–8 remain at their
executing `45a2f20` / `ec795540` identities; all24required invocations now have
valid passing receipts. No retained selection was rerun or reattributed. IDs9–20
execute12deterministic lifecycle cases; controls execute21colour-management,
1literal `/color-manegement/profile/conflict`,2monitor-dbus and20Wayland cases.
The15explicit Wayland exclusions remain skips, not accepted execution coverage.
Before/after clean source, configs, all24registrations and BOTH complete runtime
bindings match (22ELF paths). All64new output/JSON/text/JUnit hashes and132old
log hashes verify. [Final evidence](../evidence/colour-async-lifetime-validation-attempt3.json)
binds commands, actual paths/assertions, outcomes, retention grounds and identities.

Passing ID9 exercises the existing real write-delivery barrier, both shared
waiters, cancelled caller vs surviving NULL-token profile, pending-table draining,
publication/readiness and eventual device release; ineligible callback count
remains0 after actual generation/teardown. Passing remaining lifetime selections
assert actual callbacks/finishes after manager weak-finalization or store shutdown,
publication suppression and eventual task/store/device/client/profile release.
Retained startup selections assert the three actual queued callbacks after weak
manager finalization. These are reviewed assertion-based proofs, not just no-crash
observations, and do not prove every race or general leak-freedom.

Evidence corrections R3/R4: raw normalized registrations differ only in loader
search order; reviewed equivalence is identical directory sets with no conflicting
different-byte library basenames, not raw identity as the older compiler checkpoint
wording implied. A required supplemental binding covers the already-built Wayland
client omitted from the base binding. Both verified before/after qualification.
Full87canonical replay/-Werror receipts remain valid inherited evidence; no new
source edit, compilation or replay occurred in this validation phase. The earlier
builder G_ENABLE_DIAGNOSTIC=1 deviation remains explicit and was adopted in the
approved policy; fatal warnings/debug casts remain enabled, no suppression.

Operational issues: two local command-size preflights failed before submission,
then compact SHA-bound metadata permitted the unchanged commands/scope. The
wrapper summary output was tail-truncated, but complete local raw output recovered
the32,080byte archive with verified hash, zero native recovery/test reruns. One
local summary hash variable was corrected to the already verified archive digest;
actual receipts/logs were unchanged. No existing mailbox evidence moved/deleted.

Current: scoped software source qualification complete, unpublished. Remaining:
coordinator decides later publication/integration; this task authorizes neither.
Separate offscreen/frozen branches/receipts stay untouched, PR16held. Packaging,
devices/AppleTV/AirPlay/CEC, optical/physical/Dolby and inherited native keymap
reference/queued-input cleanup are not qualified. Another evidence reviewer must
reuse these receipts, not trigger a successful-suite repeat.

### Historical ID9 fixture correction — compiler checkpoint before review

Recovery t_457bd73c executed exactly one authorized private diagnostic of failed
ID9 on unchanged production and existing test operation order/semantics. It
failed at the original30s child bound. The last breadcrumb is immediately before
wait_for_delivery: eligible and ineligible devices are the same pointer and ID,
with queue0/pending0 despite eligible EDID/gamma. Already-cancelled completion
returned once and ineligible.calls remained0. No write-wait return was observed.
This establishes the bounded identity-reuse/unreachable-write class; it does not
claim an uninstrumented pass or capture every later asynchronous state.

Monitor setup copies outputs[0].serial into MetaOutputInfo.serial; absent serial
defaults to the same per-test synthetic identity. Manager update_devices keys by
vendor/product/serial/connector and updates a matching device's monitor instead
of recreating it. The test must keep its two eligibility scenarios distinct.
Patch0087 changes only test_shared_caller_cancel: stable synthetic ineligible
serial "lifecycle-ineligible" and an explicit distinct-device assertion before
the existing write barrier. No production policy, shared helper, Meson/private API,
extra wait, sleep, timeout inflation or assertion suppression changes. Ineligible
FALSE/no-callback before and after real dispatched work, cancelled NULL-device,
both shared waiters, surviving NULL-token publication/readiness, finalization and
release checks all remain. The old ineligible device reference remains held
through teardown; distinct identity does not introduce a borrowed dangling ref.

Native `e2d7cfbad8d3a44dd1a9a9d89a124444e44e9bb9`, tree
`1a92b068c246b127fed721e78b4fbbd16a8d5d2b`, compiled the affected object and linked
with-Werror in0.664s. Full87 canonical replay matches;0001–0086 and historical
SHA256SUMS entries are unchanged, only0087 and candidate pins deliberately append.
The fresh compiler loop and existing controls/support closure were built before
the diagnostic. All24 emitted registrations are bound, along with21ELFs,398fixture
inputs,161runtime libraries, configurations, compiler commands and wrappers.
Config.h/build options are identical; all3476 compile commands and registrations
are equivalent after source/build path normalization. Production/shared-helper
source, fixture inputs, system libraries/Python/services/schema are unchanged.
Private instrumentation is reverted/excluded from the exported candidate.

Current: compile-only, not source-ready or self-approved. Child t_63560e90 reviews
the complete candidate and binds a NEW scoped manifest. Per-ID proposal retains
eight actual attempt2 passes on their real historical source; none executes the
changed ID9 function, and common production/helpers/runtime are equivalent.
Binary hashes differ after isolated recompilation; that alone is not path-based
invalidation. ID9 needs retry and10–24 need first execution on this recovery
lineage. No corrected acceptance unit ran here. Recovery t_5791ca76 verifies
prerequisites and supplies the coordinator receipt; only coordinator resumes the
original validator. Never invoke consumed run_reviewed_retry.py or run_batch.py.
Historical6PASS18FAIL/96logs and8PASS1FAIL15NOTRUN/36logs remain immutable.
See [public-safe compiler/diagnostic evidence](../evidence/colour-async-lifetime-caller-cancel.json).

Operational failures are preserved: the new-clone wrapper was not watched, so
the released fixed owned-integration wrapper slot was claimed without source
edits or transport changes. Mailbox aggregate4MiB return failed after successful
compile/export/replay; the exact existing archive was recovered in3chunks, no
reexecution. Static fixture hashing initially included generated Python bytecode;
only that static probe resumed after excluding path-specific generated .pyc.
No new diagnostic budget, broad retry, cross-lane integration or publication.

### Historical reviewed validation — stopped at shared/caller-cancel

Done: independent reviewer Astra, quota-routed from Fable, approved the whole
0078–0086 candidate on t_79ec36bd. Astra is independent of builder Sol, with prior
design role disclosed; this is not Fable/independent-model approval. Controls
were compiled by t_066fb5f2 without tests; the final manifest binds source, ELF,
build configuration, registration, wrappers, runtime libraries and schemas.
Recovery t_3664fbd1 verified the original episode/ownership and all identities;
codex-coordinator performed the supported unblock, then Sol claimed original
t_8eee5d9f. The immutable review manifest's operational gate is resolved by the
recovery sidecar, not by changing the review or historical receipts.

Actual outcome: **8 PASS, 1 FAIL, 15 NOT RUN**, 44.11s, zero repeats. IDs1–8 report
their exact intended non-skipped TAP paths: two startup and six generation cases.
ID9 `/color-lifecycle/shared/caller-cancel` timed out in its fresh child at the
30s failure bound. Parent failed at tests.c:134, Meson recorded exit250 and its
invocation exited1. Child output contains only startup/surfaceless-renderer
messages. No exact wait frame or shared-waiter success is established. IDs10–24,
including controls and retained-profile release tests, remain unexecuted on this
repair. The batch stopped immediately; it did not continue or retry the failure.

All36 new per-check output/JSON/text/JUnit hashes verified; before/after clean
native45a2f20/treeec795540 and every bound runtime category match. Original
6PASS/18FAIL and96 logs remain immutable. G_ENABLE_DIAGNOSTIC=1 is explicit
reviewed recovery policy; its original deviation is preserved, not suppressed.
Transport returned an aggregate4MiB export error after execution. Existing
receipts were recovered without reexecution, preserving six hash-verified own
already-returned repair mailbox files elsewhere in owned native storage. Frozen
and offscreen exports/source/builds/ledgers were not changed.

Current: runtime qualification incomplete, not source-ready. Remaining: automatic
recovery thinker determines the exact ID9 wait and bounded correction scope.
Static lead only: shared/caller-cancel adds ineligible then eligible monitors
using the same base setup; manager update_devices reuses device identity while
profile setup is initiated at device creation. Its on_profile_written barrier
may be unreachable, but that is not a captured timeout cause. No extra diagnostic
run or source edit was authorized here. Any correction needs owned compilation,
export/replay and independent review, with explicit per-ID retention/resumption:
retain IDs1–8 absent actual invalidation, retry ID9 and execute pending IDs10–24.
No timeout inflation, sleeps, dropped assertions or successful-suite reruns.
See [new stopped-attempt evidence](../evidence/colour-async-lifetime-validation-attempt2.json).

### Completed bounded repair t_36b12839 — historical compiler checkpoint

Native `45a2f20ade8d85664a7a99f49026a5c2ec540b40`, tree
`ec79554021bb1ce99de1b230044385493cf2cb0b`, adds only native-seat disposal
disconnection and startup/cancelled assertions to the prior store/backend repair.
Incoming cached-keymap, impl and backend signal handlers with this seat's data
are detached at disposal start, before field/impl release. The non-NULL impl
guards one-time cleanup; partial-init NULL checks avoid a lazy getter, and second
dispose does not revisit the borrowed backend. Normal signals and prepare-shutdown
ordering remain. The captured keymap-to-seat failure is observed evidence;
sibling raw impl/backend handlers are same-class source hazards, not new observed
crash causes. No new API, registry, gate, retained seat, sleeps or waits are added.

The existing cancelled-startup selection now holds a separate keymap reference,
records weak seat finalization and saves the seat address solely as opaque
handler-data identity. G_SIGNAL_MATCH_DATA finds a handler before teardown and
none after asserted seat finalization. The saved pointer is never dereferenced.
Only the test-owned keymap ref is released. The three real startup completions
still arrive after manager finalization with cancellation/return/client-release
assertions; this is not a substitute synthetic reproducer. All20 selection IDs
and existing Meson/private-hook registration remain unchanged. Tests are compiled,
not executed by this source-repair card.

Inherited adjacent limitation: meta_seat_impl_get_keymap returns a reference;
the seat caches it and impl constructs another reference. Neither current seat
disposal nor impl finalization drops those references. Queued keymap-update data
borrows that retained keymap; the demonstrated dangling target was the seat.
Do not infer general input leak-freedom or casually clear those references:
that requires a complete queued callback/ref audit in separately owned work.
meta-keymap-native.c and meta-seat-impl.c are unchanged in this repair.

Done: affected enabled production/test objects compiled and lifecycle executable
linked with-Werror; disabled-build seat object compiled. Full86 canonical replay
equals the exact native tree and the temporary replay is removed. 0085–0086
append deliberately without changing any0001–0084 patch/checksum bytes. Prior
store/backend changes0082–0084 remain byte-identical. Returned whole-candidate
source/diff, compiler commands, configurations and all20 identities are hash-bound.
See [completed compile-only evidence](../evidence/colour-async-lifetime-repair-complete.json).

Failures preserved: generated-script SyntaxError preceded any source action;
after successful compilation a registration-name prefix postcheck failed, so
only the corrected postcheck ran. Individual build durations were not persisted
before that exception; the entire apply/two-compile/postcheck request took1.69s.
Full export exceeded aggregate4MiB after successful replay; its preserved native
receipt was recovered with a compact archive and only this card's already-returned
context moved out of the mailbox. No successful compile or replay was repeated.
Zero diagnostic/acceptance invocations occurred here; earlier exhausted diagnostic
budgets and original six passes/eighteen failures remain immutable.

At that compiler checkpoint: complete implementation for this bounded recovery, compile-only, NOT
source-ready or self-approved. Then remaining: independent adversarial review of the
whole0078–0086 candidate, then source-bound retry authorization on original
t_8eee5d9f. All18 original failures need reviewed retries. Historical passes
1/13/14/20 execute changed backend/seat disposal through destroy_manager;22/24
through HEADLESS context cleanup. Their provisional invalidation requires final
reviewer confirmation, not blanket24-check execution authority. Keep historical
result/reason/new source/new result separate, never invoke original run_batch.py,
and never repeat successful suites for another reviewer. G_ENABLE_DIAGNOSTIC=1
remains explicit recovery policy; the original deviation is not hidden.
The existing recovery t_3664fbd1 owns review/manifest arrangement. No publication,
parallel-lane integration or device activity; PR16 stays held.

### Prior partial checkpoint t_1da8e97b (superseded implementation state)

Three additional instrumented diagnoses (original failed IDs2/3/11 exactly
once each) captured the causal child frames; all remain diagnostic failures,
not acceptance. GLib2.90 source and installed disassembly were inspected first.
A post-g_test_init forwarding default log handler and interposition of both
assertion entry points preserve the originals' fatal behavior, including the
child exit(1). No diagnostic helper is part of the production series.

IDs3/11: clutter_source_prepare (meta-backend.c1143) calls
clutter_events_pending after confirmed manager/context destruction. The new
partial candidate retains the source's original reference and destroys/unrefs
it at the start of backend dispose, before any dependency release. Attach
context and dispatch semantics are unchanged, the backend pointer remains
borrowed, and NULL/partial-init/repeated-dispose are safe.

Store repairs sequence a saved cancellable lookup before transferring exactly
one store reference to the file-read callback, and check active eligibility
before allocating a callback-bearing task. Shutdown/already-cancelled requests
still create/tag/complete one CANCELLED task before borrowed device access,
including NULL devices. Existing cancellation checks and waiter semantics stay.
The existing shared/caller-cancel selection now also asserts active ineligible
FALSE/no callback and already-cancelled NULL-device behavior; all20 original
selection identities and weak-finalization/release assertions remain.

ID2: update_keymap_in_main (meta-keymap-native.c240) emits to
on_keymap_changed (meta-seat-native.c216), which uses a destroyed seat as a
signal instance. This is outside the approved source scope; no seat/keymap fix
or startup readiness workaround is added. Astra owns the minimal follow-up
decision. Consequently this candidate is explicitly PARTIAL/compile-only,
not ready for adversarial review or acceptance. Native `b230080` / tree
`c5e7c673` compiled/linked the affected lifecycle executable with warnings as
errors in92.89s; separate test-disabled store/backend objects also compiled
and contain no lifecycle-hook symbols. Patches0082–0084 append without changing
0001–0081 or any historical checksum entry; full84 canonical replay exactly
equals that source tree. Source/binary/config hashes and original20 identities
are verified. Original source/build/config/receipts remain read-only.

Transport failures are explicit: an oversized request was rejected before
native execution and timed out; two smaller commands were rejected by the
separate16384-byte command bound. Compact hash-checked diffs recovered without
changing the transport. A postcheck incorrectly expected a boolean define's
trailing1 after successful replay and guard-disabled compilation; inspection
confirmed the actual bare define, so only the postcheck resumed. Export then
exceeded the aggregate4MiB transport cap; a smaller artifact recovered the
completed work. Neither successful compilation nor replay nor any unit was
repeated for those failures. See [partial repair receipt](../evidence/colour-async-lifetime-repair-partial.json).

The historical checkpoints below describe the original candidate, not successful
runtime qualification of the repair. No passing check is repeated here.

Done: isolated source/build directories created from the exact frozen native
head; fresh whole-tree warnings-as-errors baseline compiled in 278.16 seconds;
production commit `769c2a375e51f79facb66efe36c2120d0a181bf4`, tree
`8919379f8737c8597a494fd15a3eeddd09e5973e`, compiled in 3.93 seconds.

Done: the complete candidate is native
`ef2f85ae14ad4ed68060e79515a6638ef4d9422b`, tree
`2f6324d764063b057ba1ae57b69571abacfb82f2`. Patches 0078–0080 are exported
with normal authored commits; prefix 0001–0077 is byte-identical. The full80
canonical series replays from `d82671c` to the exact candidate tree. Three new
SHA256SUMS entries were deliberately appended; historical hashes are unchanged.
The complete test-enabled candidate compiled with warnings as errors. In a
separate configuration, the four affected guard-disabled production objects
also compiled; hook symbols are absent there. Generated config defines the
test guard only when the existing `mutter_tests` build setting is enabled.

Done (R1 correction): Astra's adversarial review found that the fixture released the same
context reference twice: `meta_context_destroy()` already disposes and unrefs.
Corrective native commit `65b5c00a35f675a84658c52c4cd80cf89b1c4947`, tree
`648f28ce4e22e014098a803bc453841abb9eaad9`, now transfers it with
`meta_context_destroy (g_steal_pointer (&test_context))`, preserving the manager
weak-finalization assertion. Its single destroy call and final main clear were
audited: the transferred global becomes NULL, so later conditional fixture
cleanup and the final clear do not release the consumed reference again.
The affected lifecycle object/executable compiled and linked with warnings as
errors. Production files, binaries and generated test-guard configurations are
unchanged; successful production compilation is reused, not rerun for review.
Patch0081 is exported with prefix0001–0080 byte-identical; one new SHA256SUMS
entry deliberately binds its bytes. Full81 canonical replay matches the corrected
exact tree and the owned temporary replay is removed. All ten changed-source
SHA256/Git blobs match the native compiler receipt, Mac mirror and archive.
The earlier candidate was rejected for R1; Astra approved the corrected candidate
on the same review card `t_a26a1173`, without claiming runtime acceptance.

Historical correction evidence: source/compiler/export/replay and emitted registration
were supplied for rereview on the same card `t_a26a1173`. The transport failure was repaired by
the coordinator; read-only recovery confirmed no correction had executed before
retry. A generated-request SyntaxError was fixed before native application. All
transport/compiler/script failures and earlier receipts remain preserved in
[R1 evidence](../evidence/colour-async-lifetime-r1.json), without fabricating native
execution state or rerunning successful checks.
Done: the approved 24-invocation batch executed once on the exact corrected tree:
6 PASS, 18 FAIL, zero retries, 37.23 seconds. The source, binaries, generated
configurations and registration matched before and after execution. All 96
per-check Meson output/JSON/text/JUnit hashes were verified. Actual non-skipped TAP
was required; primary Wayland's 15 emitted policy exclusions were intentional.
A no-crash result before callback delivery is not coverage.

Historical original result: runtime qualification failed; not source-ready.
Eleven lifecycle invocations fail with a Clutter default-context assertion;
startup/cancelled fails with an invalid GObject class pointer; directory/read,
local-ready/shutdown, local-ready/finalize and profile/create-after-finalize fail
with SIGSEGV and no captured stack. Colour-management and monitor-dbus fail on
an unreturned ensure-device GTask. The builder explicitly enabled
`G_ENABLE_DIAGNOSTIC=1` beyond the standard tests.sh recipe, in addition to fatal
warnings. This environmental deviation requires thinker adjudication; it is not
grounds to conceal the real task error or discard the failed attempt.

Static diagnosis: store:605 constructs a callback-bearing GTask before its
no-EDID/no-gamma branch:619–620 returns FALSE without completing the task.
An eligibility-before-task-construction repair must preserve the synchronous
FALSE/no-callback contract and shutdown-before-borrowed-device-access ordering.
The fixture calls context setup but not context start; exact initialization or
post-teardown callback frames behind the Clutter/startup/SIGSEGV failures remain
unknown. No unsupported stack inference, source fix or retry is claimed.

Remaining at that historical checkpoint: automatic thinker recovery must determine precise crash causes,
repair design/file ownership and retained-pass/scoped-retry accounting; builder
compilation/export and independent review precede failed/genuinely invalidated
retries. Six passes remain recorded, not automatically invalidated: startup
queued-success, queued-assigned finish, directory query, retained-assigned profile,
profile-conflict and primary Wayland. No successful suite is rerun for a reviewer.
See [runtime failure evidence](../evidence/colour-async-lifetime-validation-attempt1.json).
This document and the
isolated branch status pages are the follow-up status surface; frozen
nativehdr10 source, builds and receipt ledgers remain unchanged.

## Deterministic regressions and runtime limits

`src/tests/color-lifecycle-tests.c` registers 20 separately selectable cases.
Each actual lifecycle fixture executes in a fresh subprocess, without an outer
compositor test loop using a destroyed context. A process timeout is a failure
bound, never the race barrier. The private hook captures real asynchronous
source/result references before task ownership adoption and preserves unchanged
callback-data ownership. It never references the manager. Each capture is
consumed once with hooks detached, and the real callback return is counted.

| Cases | Boundary/assertions written and compiled; failed batch above is not blanket coverage |
|---|---|
| Startup queued-success/cancelled | All three actual startup callbacks; manager weak finalization before replay, cancellation at finish, callback returns and client release |
| Generation directory-query/directory-create/write-result/profile-result | Actual pending request or completed worker/write/profile before delivery; two independent waiters (one NULL token), repeated shutdown, CANCELLED results, no publication, pending drain and task/device/store weak release |
| EFI success/fallback | Synthetic local ICC or missing synthetic path, actual EFI completion captured before shutdown; no firmware/device access |
| Shared caller-cancel | One cancelled waiter while manager/store live, surviving NULL-token waiter succeeds and publishes normally |
| Queued device/assigned ensure finish | Actual successful task result retained by the test callback before shutdown; finish rejects it once after shutdown; new requests cancel before borrowed-device access |
| Assigned connect/read | Synthetic AddSystemProfile fixture, real service/read result, independent store shutdown even with NULL caller token, no publication and task/store release |
| Directory query/read | Real monitored synthetic file, captured request owns store independently of fixture, callback after manager finalization releases final store ref |
| Local-ready shutdown/finalize and profile creation after store finalize | Retained profile independently owned while pending and live; actual readiness-producing callback after teardown; retained-store drain/no insertion or finalized-store object-bound disconnection |
| Retained owner/assigned | Normal successful creation controls; generated EDID CdIcc/calibration final release after manager LCMS context teardown, non-owner release, profile/ICC/client weak notifications |

No new mock behavior, profile/device/manager header API, production timing,
blocking teardown or public HDR policy was introduced. The private header is
not installed or added to public introspection. Its guard is build-test-only,
not a compositor feature gate. Exact file/API permissions were adjudicated on
tasks `t_b6656cef` and `t_2450026c`; the latter authorized one explicit template
declaration needed by the existing templated config generation.

## Compiler failures and evidence limits

The initial source-context archive named a nonexistent test header; the valid
other files were recovered and the actual header was discovered. The first
guarded-seam checkpoint `da1929e` compiled with its guard disabled: a Meson
configuration key alone does not emit a macro absent from `config.h.meson`.
After narrowly approved template plumbing, the new test link identified an
unexported profile readiness getter. Tests now observe the actual ready signal,
without extending profile headers. Both compiler failures and their corrected
builds are retained. The complete replay applied successfully before a quoting
error in its evidence postcheck; recovery inspected the already-replayed tree,
verified equality and removed the owned temporary replay without rerunning it.

See [compile-only receipt](../evidence/colour-async-lifetime.json) for exact
identities, request/log hashes and patch inventory. Compilation, static source
reasoning and replay are not new runtime reproduction or leak evidence. The
20 cases were selected by the approved manifest after corrected-source approval. Astra selected
20 separately registered lifecycle invocations plus `mutter:color-management`,
`mutter:color-management-profile-conflict`, `mutter:monitor-dbus-tests` and the
primary `mutter:wayland-color-management`: 24 exact invocations executed once.
The approved manifest binds corrected exact source and emitted registration;
the failed runtime outcome remains distinct from source approval. The historical
manifest bound to the rejected tree is preserved. The earlier builder proposal incorrectly described `native-hdr` as
HEADLESS startup; it is a pure g_test parser/policy executable without a context
and is excluded. The empty lifecycle primary is also excluded. No old17 list or
historical accepted ledger is copied or mutated. The parallel
offscreen lane is not included, even though its separate series also begins at
0078; any later combined integration must serialize and renumber exports.
