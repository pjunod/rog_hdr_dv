# Review — adversarial findings and the current implementation batch

**Updated:** 2026-10-11 UTC · **State:** batches through PR 9 merged; ninth
batch (independent review fixes) reviewed, findings addressed, fast lane
passed.

Companion to [status](STATUS.md) and [development](DEVELOPMENT.md). The initial
review was explicitly requested before the owner established the subsequent
pre-merge-only review workflow. Future batches use that workflow.

## nativehdr10 — review corrections in progress

Astra and Fable independently reviewed repository `73918f3` and native
Mutter `fa7eb2cf` / tree `18ba4b5a`. Reports are retained on the HDR board
(`t_70a00674`, `t_b2750819`); neither review was a unit pass or source
acceptance. Fix/validation owner: `t_e5c490e6`.

| Finding | Disposition and current evidence |
|---|---|
| F1 P1: discontinuous onset from absolute Planckian anchoring | Fable decided factors must be ratios to the default temperature's Planckian white. Opus implements; focused Astra review gates it. Exact off-state identity and channel bounds remain, absolute Planckian xy acceptance is replaced by relative white movement. |
| F2 P1: restore wait never exits on retained idle ID | Opus replaces with bounded observable-state wait; no production idle-ID change solely for the test. |
| F3 / A3: override case mutates shared fixture | Add to Meson separate cases and give its exact generated name one manifest receipt. |
| F4 / A2: constructed capture state is not capture coverage | Opus adds real production paint/readback coverage; stream DMA-buffer and shared-memory paths must be named with actual exercised limitations. No source-demonstrated leak or speculative production fix. |
| F5 / A1: SIGTERM can orphan check sessions | Sol correction `56c0329` installs/restores termination handling, defers cancellation over launch, kills check group and reaps check, preserves nonpassing receipt, returns 143. Real descendant regression plus launch/restoration regressions are written and syntax-compiled, not executed. Focused Fable review pending. |
| F6: fallible adapted-state constructor lacks fallback | Opus adds warning/unadapted fallback before validation. |
| F7: unrelated end-parse and mirror fixes bundled | Opus owns drop/split or explicit rationale; final disposition pending source handoff. Preserve already-delivered authorship/history rather than silently rewriting it. |
| F8: disabled output retains configured override | Retain last-assignment declaration, consistent with existing colour-mode behavior; effective physical-target properties remain active-device-only. No new reset or alternate reporting policy. |
| F9: offscreen reallocated each uniform step | Separate upstreamable optimization `t_38887c3f`; not part of this correctness batch. Preserve framebuffer when required format/dimensions unchanged, including reference-luminance path. |
| F10: duplicate variant keys, gdctl readiness, installed fixture list | Verify fixture list statically; actual D-Bus/gdctl checks in the upcoming batch provide runtime evidence. No probe execution before freeze. |
| F11: agent copyright/upstream identity | Preserve authored copyright as provenance; upstream author/signoff mechanics remain an owner decision and no submission occurs. Do not invent owner attribution. |
| F12: PQ hotplug capability transient | Accept documented false-to-true NightLightSupported notification during rebuild-before-assignment; notify-on-change bounds traffic. No forced support or unrelated lifecycle redesign. |

Both focused reviews and fixes precede one affected batch through the
[receipt runner](NATIVEHDR10_VALIDATION.md). No units have run in this
fixing stage. PR16 remains held unmerged; no physical or Apple TV activity.

## Initial repository review

| Finding | Evidence | Disposition |
|---|---|---|
| P2: reordered patches passed integrity checks | Reviewer reversed four dependent library patches in a disposable copy; checker still passed because it compared sets. | Explicit `patch_order` in the source manifest; checker and mutation regression in implementation. |
| P2: public source reconstruction lacked inputs | Ubuntu entries had only local import IDs and historical directories; kernel lacked a repository URL. | Public package URLs, artifact SHA-256 values, base trees and extraction requirements now recorded; archive authentication remains distinct from maintainer signature verification. |
| P3: compositor candidate labelled as base plus patches | Inspected clean checkout was at the candidate named in the manifest. | Correct candidate/base wording in the quality investigation. |

The reviewer found no claim that the existing PQ sample qualifies full Dolby
Vision. Missing display management and optical measurements remain explicitly
open implementation/acceptance, not resolved by documentation corrections.

## Premerge review and validation

The independent adversarial review approved candidate `856e39c` after these
additional fixes:

| Finding | Resolution |
|---|---|
| Mutation fixtures omitted newly linked source files | Copy all tracked inputs, preserving symlinks and excluding untracked captures. |
| Unexpected dictionary-shaped D-Bus replies could raise `KeyError` | Validate outer and nested response shapes; add synthetic regressions. |
| Probe recipe could continue after network-disconnect failure | Fail closed on isolation assertions, require zero network attachments, use a non-root runtime UID, and stop the container on exit. |

`python3 scripts/check_repository.py` passed for 28 patches and five series.
`python3 -m unittest discover -s tests -v` passed all 45 tests in one run.
The probe's recorded warnings-as-errors build matches the reviewed source.
No imported patch bytes or compiler inputs changed after those checks.
Subsequent receipt/status documentation receives the repository/link check;
unchanged test suites are not rerun.

## Publication audit

Gitleaks 8.30.1 scanned the initial reachable Git history and current working
tree with redaction enabled: no leaks detected. A separate infrastructure/path
scan found no personal home paths, private IP addresses or private-key headers
in the published tracked files. Scanners do not establish that every future
capture is safe to publish; inspect each candidate tree and its metadata.

The initial commit used the owner's configured author email. A decision about
rewriting that existing public metadata is pending. Agent commits used
`Codex <codex@invalid>` until the fifth batch and `Claude Agent
<claude-agent@invalid>` since. No credential from the conversation is stored here.

## Validation boundary

The imported userspace series were previously checked for exact source-tree
reconstruction. Kernel import verification remains partial as documented in
[provenance](PROVENANCE.md). The current batch does not alter those C patches.
New Python tool regressions passed after final adversarial review. The
Windows probe compiler loop is isolated; activation is a separate experiment
and is not evidence of full playback or colour fidelity.

## Second batch — profile interpretation and Wine API isolation

Independent adversarial review approved `efcfcef` with no actionable findings.
It inspected ICC bounds/privacy and MHC2 semantics, the fixed API-only probe
and isolation recipe, and checked core colour-audit claims against the pinned
Ubuntu source. The coordinator verified the official Dolby product pages.

[Initial CI run](https://github.com/pjunod/rog_hdr_dv/actions/runs/37881782924)
passed repository integrity and 15 of 16 new ICC tests. The truncation fixture
mistakenly left enough bytes for its tag table, reaching a different valid
bounds rejection. Commit `ecc8215` physically removes the missing record word;
the parser and other tests are unchanged. The coordinator reviewed that delta.
[Focused CI retry](https://github.com/pjunod/rog_hdr_dv/actions/runs/37881876877)
passed only `test_inspect_icc.ProfileTests.test_header_and_tag_table_corruption_is_controlled`.
Every new test is green; the previously green suites were not rerun.

The source-bound API diagnostic compiled with warnings as errors and ran once
in the reviewed offline, non-root environment. Its documented missing-export
exit `3` is an observed compatibility boundary, not a successful Dolby result.
All four private OEM profile inspections succeeded. Only sanitized receipts
were added afterward; the documentation/link check covers those receipt edits.

## Third batch — additive native luminance API

Independent adversarial review approved `6c23e7f` with no findings. It checked
binary16 decoding, format bounds, per-field presence, lifetime and ABI scope,
Ubuntu hdr7 provenance, regression coverage and publication evidence. A focused
followup approved the fixture-only source commits recorded in the
[native API document](NATIVE_LUMINANCE_API.md).

Ten existing focused tests passed initially. The new regression failed in each
source variant because its synthetic CTA colourimetry byte set reserved MD0.
The parser correctly diagnosed that fixture; the product code was unchanged.
After correcting the byte and strengthening assertions, only the two failed
tests were rerun, once each, and passed. Both previously compiled consumers
also passed against the new libraries. Final complete-series reconstruction
matched both candidate trees. Compiler, test, legacy and reconstruction receipts
are linked from the native API document.

No i386 package build, install, live display change or optical qualification is
claimed. The original 28 imported patches remain byte-identical. The four new
exports are the API addition and its test-fixture correction on each source base.

The final repository integrity check passed for 32 patches, five series and
documentation links. Both owned library build containers were removed after
retaining source-bound receipts; source checkouts remain for consumer work.

## Fourth batch — native target feedback and reference preparation

Independent adversarial review of PR 4 requested three corrections in the
Mutter candidate before runtime tests:

| Finding | Required correction | State |
|---|---|---|
| Primary/topology changes can leave an unmapped surface's preferred target stale | Refresh records and preferred feedback after the Wayland output table changes; cover primary switch and removal | Addressed and approved |
| Two fallback assertions require exactly 10000 internally, while PQ encoding preserves minimum plus its 10000-unit swing | Compare against actual encoding luminance; keep the integer wire expectation separate | Addressed and approved |
| A physical range can collapse after maximum luminance is quantized to whole nits | Require a strictly positive published range and cover the equality boundary | Addressed and approved |

A correction-delta review also caught a fixture assumption: the global force-HDR
setting changes the second output. The fixture now expects those events and
uses a fresh second-output identity before topology changes, while retaining
the original immutable snapshot and unrelated-output silence checks for native
target-only updates. No test execution was needed to identify either fixture
issue. Independent delta review approved final source `a04bc3ecde3f425cd90d4017c57ad2840475682f`.

No additional actionable issues were found in the Wine wrapper/export,
synthetic corpus encoding, immutable description ownership, v2 identity
allocation or narrowly scoped public-certificate scan exception. The Mutter
runtime tests explicitly use UID 1000; dependency installation and compilation
use root only inside the owned guest. Lack of Docker privileged mode alone
does not mean a process has a non-root UID.

Focused runtime tests completed after the findings and their
correction deltas were approved. The 11 new corpus tests passed on their first
run; both complete patch series reconstructed to their pinned source trees. The owner separately accepted the official Dolby tools and a private offline
reference experiment completed. Proprietary processing details and results
remain outside the public repository.

The first runtime pass found a shutdown lifetime defect: qdata released the
colour manager after the compositor had already freed its outputs. A bounded
GDB run of the failed test identified the stale output access in signal
disconnection. Explicit colour-manager finalization now precedes output
teardown, after canonical shutdown has destroyed clients. The two new Wayland
fixtures also used nonconsecutive synchronization serials; their numbering is
corrected without weakening the helper. The eight native checks passed and
remain valid. After independent review of the correction, the existing Wayland
check passed including teardown. The two new checks exposed a synthetic-fixture
mode reset during forced-HDR reconfiguration; product policy correctly fell
back to the SDR target. A narrowly matched handler is now blocked only during
the synchronous test setting change and immediately restored, preserving
colour-device notifications. Independent review approved this fixed-route
fixture correction; it does not qualify real monitor reconfiguration. Only
the two failed protocol checks were retried; both passed on final source
`4db354c816e7ac72091a246b7b2eb8adee9a9412`. Its change from the final reviewed
semantic delta is official formatting only, with identical lexical tokens.
All eleven selected compositor paths now have valid passing evidence.

The Wine contract passed all 123 assertions with no failures or skips, using
the exact reviewed source, DLL and test executable. Its failed attempts were
private runner issues: malformed shell limit syntax, prefix truncation caused
by a process-wide file-size limit, then an ASCII locale unable to represent
the Unicode test filename. A diagnostic reproduced the latter through ordinary
CreateFileW as well as the new entry point before the fixture selected UTF-8.
Bounded log drainers replaced the global limit. The passing receipt identifies
the loaded module and function offset; no OEM execution is implied.

The owned Mutter build container was removed after source, binary and runtime
evidence verification. The independent source clone and private receipts remain
for subsequent packaging work.

Final repository integrity passed for 41 patches, six series and documentation
links. All earlier patch bytes remain unchanged. Gitleaks 8.30.1 found no leaks
in the candidate tree or reachable history. Infrastructure-pattern matches were
inspected: only the intentional path-redaction expression and synthetic privacy
fixtures matched; no real infrastructure identifier was found. Final evidence
and publication review approved the scoped claims after two stale tense
statements were corrected.

## Fifth batch — display contracts (PR 5)

Three independent reviewers examined the library chromaticity API and the
Wayland probe, the Mutter native-gamut candidate, and the Wine
DisplayMonitor candidate. None of them had seen the work being produced.
Each finding was verified before it was fixed.

| Finding | Severity | Disposition |
|---|---|---|
| Mutter: subprocess isolation could not start; a child compositor binds the fixed test display socket the parent holds | Blocker (reproduced with libwayland 1.26) | Replaced by per-case test invocations (`separate_cases`) that the D-Bus runner gives their own runtime directory, bus and socket. Target cases are skipped in the main invocation. |
| Mutter: no fixture fails if the raw-geometry check is removed | Should-fix (computed) | Added a white point exactly on the raw R–G edge that truncation would move inside. |
| Mutter: parser status depended on block order; unsupported and unusable were merged | Nit | Every block is classified first; a new unsupported status sits beside the recognized-but-unusable one. |
| Mutter: gaps in extension-failure, multi-extension and CIE 1976 coverage | Should-fix | Cases added. A revision mismatch between declarations counts as a conflict, as documented. |
| Wine: build cache and backup configure committed | Blocker | Removed. Patches are exported with `--no-numbered`, so appending leaves earlier bytes intact. |
| Wine: adapter LUID read as INT64, but win32u writes UINT64, so `DisplayAdapterDeviceId` never resolved | Should-fix | Reads UINT64. A real-topology test checks resolution when the LUID is present. |
| Wine: `DisplayName` always fell back to the generic description | Should-fix | The validated EDID product name now takes precedence. |
| Wine: reserved DisplayID product use was trusted | Should-fix | Such a section is opaque. |
| Wine: unlinked interfaces resolved; a lookup during a display rebuild could return an empty object | Should-fix | Only monitors with an enabled interface resolve, and the selector includes `InterfaceEnabled`. Resolution holds win32u's `display_device_init` mutex, which also guards the rebuild, so each snapshot reflects one configuration. |
| Wine: connector validity (HD15 is zero) and virtual origin untested | Should-fix | Table-driven cases added. The guessed usage kind for virtual monitors is removed. |
| Wine: most monitors have no DisplayID Display Parameters | Design | Base EDID 1.4 colour characteristics and a preferred timing that EDID 1.4 declares native now apply where DisplayID provides nothing. CTA desired-content luminance is still not a physical value. Getter behaviour for missing facts remains a native-Windows qualification gap. |
| Library: independence test could not detect a native-to-signal leak; header bits 3–6 untested; CIE 1976 per-point rule untested | Should-fix | Tests strengthened in both series (appended patches 0009 and 0020). |
| Probe: a full listen backlog failed immediately as a disconnect | Should-fix (reproduced) | Blocking connect bounded by `SO_SNDTIMEO` at the remaining deadline. |
| Probe: encoding and target assignment not pinned; 32-output boundary untested | Should-fix | Exact raw arrays asserted; 32-output success scenario and failure reasons added (23 cases). |

The reviewers confirmed as sound: the conversion and geometry arithmetic,
route gating, single notification, unchanged encoding state, Wayland record
immutability, library ABI and symbol files, Wine COM and async lifetimes, the
GDI ABI bump, and the probe's privacy and fd ownership. Two items stay open
because they need native Windows to settle: the identifier semantics and the
behaviour of getters with no data. The IDL could not be re-checked against the
pinned SDK in this session.

### Fifth batch validation

After the fixes, the affected fast lane ran once. The
[receipt](../evidence/batch5-fast-lane.json) holds commands, trees and hashes.

- **Library:** the four chromaticity groups passed on both series except
  `formats`. That check had expected an oversized block to drop the whole
  DisplayID extension, but the parser keeps the section with a recorded
  failure and no block. The pre-review test source fails the same way. Only
  the test expectation was corrected; only `formats` was rerun, and it passed
  on both series. Binaries built from the previous candidates passed against
  the new libraries.
- **Mutter:** `native-hdr` passed all ten cases. The main Wayland invocation
  and the four separate target-volume invocations each passed on the first
  run.
- **Probe:** all 23 cases passed in one run.
- **Wine:** `user32:displayconfig` passed (14 tests). The first
  `displaymonitor` run exposed a real defect. The enabled-interface check for
  instance IDs searched a device-only information set, which never contains
  interfaces, so every instance ID was refused. The check now finds enabled
  interfaces through the monitor interface class. After the prefix copy was
  refreshed, `displaymonitor` alone was rerun and passed 308 tests with none
  failing.

## Sixth batch — compositor colour input (nativehdr5)

The coordinator reviewed the first implementation and required four changes.
The installed Clutter headers and the signatures and behaviour of the existing exported functions had to stay unchanged; the ABI is extended only additively (seven new symbols at `+nativehdr5~`). Encoding and fallback
target primaries had to share one conversion. A wrong error code had to be
fixed. EDID-derived output primaries had to be validated at source rather
than left to a renderer fallback.

An independent adversarial review then confirmed one blocker and three
should-fix defects. All are fixed:

| Finding | Severity | Disposition |
|---|---|---|
| ICC reader skipped from the client's current file position and accepted short reads, passing an unfilled buffer to lcms | Blocker (reproduced) | `pread()` at the absolute offset; anything short of exactly the requested length is an operating-system error. The tests no longer depend on file position; a truncated-before-read case was added. |
| Nearly collinear primaries passed graphene's unscaled determinant test | Should-fix (measured: 0.107 identity error) | Round trip to identity within 1e-4, computed in double. Named spaces, AP0, AP1, ProPhoto and XYZ keep bit-identical matrices. |
| Descriptor-0 fixture failed when stdin starts closed | Should-fix | Handles the memfd already being 0, and restores over the stored descriptor with no window in between. |
| Non-physical white points accepted | Should-fix | White y must be positive, a positive mix of the primaries, and give positive cone responses. |
| Round-trip rule unpredictable beyond ±16; OS failure classed as unsupported; missing error-code test; overstated comment; housekeeping | Nit | Explicit ±16 bound, classification by stage, tests added, comment corrected, warnings once per state. |

The fast lane ran once over the affected suites. Every one passed except the
main Wayland invocation. There, the new protocol-error cases had not declared
the disconnect warning libwayland-server logs, so the harness aborted the
compositor and the client saw EPIPE. The cases now expect that warning, as
the other Mutter protocol-error tests do. Only that invocation was rerun,
and it passed ([receipt](../evidence/mutter-colour-input.json)).

## Seventh batch — HLG and highlight mapping (nativehdr6)

The coordinator ruled on the implementation's deviations from the
[contract](HDR_MAPPING.md). MaxFALL above MaxCLL is a protocol error when both
are known, as the protocol requires; zero means unknown. Mastering primaries
are not tested for containment. Instead, `extended_target_volume` is
advertised, which is truthful because target primaries are not used to map
gamut. The mapping never lifts black. Monitor screencasts are deliberately not
mapped.

An independent adversarial review then found two blockers and five should-fix
defects. All are fixed:

| Finding | Severity | Disposition |
|---|---|---|
| GPU-vs-CPU tests compared an 8-bit-quantized GPU input with exact CPU floats; they would fail on any GPU | Blocker (computed) | The CPU reference receives the value the GPU receives; tolerances kept |
| The transform cache used the 10%-tolerant colour-state equality, so a mapped and an unmapped surface could share a pipeline while scanout disagreed | Blocker | Exact cache equality and hash, including the target volume and display reference |
| Published reference white was the truncated integer of the internal float, so clients following the preferred description were mapped at any brightness other than 100% | Should-fix | The output state's reference white is rounded once, at its source |
| Client HLG black levels with β > 0.5 inverted the decode or divided by zero in the encode | Should-fix | One shared HLG validity check; invalid descriptions fail as unsupported |
| The hardware cursor re-evaluated mapping only on cursor updates | Should-fix | The view's colour-state changes invalidate it, and the next frame updates it |
| Extended-range (linear) encodings were capped by their nominal maximum and never mapped | Should-fix | Their effective peak comes from declared MaxCLL or mastering maximum; without one, no mapping |
| Missing tests at brightness factors other than 1 and for cache parity | Should-fix | Added |
| Double invalidation, duplicate peak definition, stale comment, bisectability, display-target predicate | Nit | Coalesced exact updates, one definition, comment fixed, history folded per slice, predicate requires a display reference |

The fast lane ran once over the affected suites. The main Wayland invocation
failed in three test-client defects, found one after another: a create-time
error was asserted on an interface the client had already destroyed, the
shared listener had no handler for version 2's `ready2`, and identities were
compared after the first description could have been released for reuse. Only
that invocation was rerun after each fix, and finally passed; the separate
invocations sharing that client were rerun once and passed
([receipt](../evidence/mutter-hdr-mapping.json)).

## Eighth batch — gamut compression (nativehdr7)

The coordinator ruled on the first implementation, in five points. Only the
boundary point that sets each channel's limit is guaranteed to land on the
target boundary. Compression requires the encoding gamut, and the mastering
gamut where declared, to exceed the target. Containment tolerates the
declaration's own quantization. Absolute colorimetry is used in the
compression space, with one shared conversion for pixels and limits.
Display-target primaries are validated when constructed.

An independent adversarial review found one blocker and three should-fix
defects. All are fixed:

| Finding | Severity | Disposition |
|---|---|---|
| Limits and containment used unadapted primaries while pixels are white-adapted, so non-D65 sources (ProPhoto, DCI-P3) ended beyond the target or escaped compression | Blocker (computed) | Limits and containment use the same adapted chain as the pixels; non-D65 tests added |
| Extended-range linear content with wide mastering primaries was never compressed | Should-fix | Unbounded encodings use declared mastering primaries; none declared, no compression |
| The tightened shared matrix check narrowed client and EDID acceptance | Should-fix (measured) | Client and EDID acceptance restored to the previous rule; the absolute check applies only to display targets |
| Points along source edges ended beyond the boundary | Should-fix (computed) | Limits include the edge points where two target channels are equal; boundary sampled densely in tests |
| Predicate true with no operation, non-finite input, loose CIE 1976 tolerance, private structure layout, predicate cost | Nit | Predicate requires a limit above 1; non-finite input unchanged and overflow-safe curve; per-primary tolerance with vertex clamp; field appended; early exit where it cannot desynchronise |

The fast lane passed on its first run: all affected Clutter, backend, native
and Wayland suites, including the new separate target-gamut invocation
([receipt](../evidence/mutter-gamut-compression.json)).

Process note for batches six to eight: by the coordinator's record,
`scripts/check_repository.py` ran and passed before each merge, but the batch
receipts did not record it.
Receipts from the ninth batch on record it.

## Independent plan review (2026-10-11)

At the owner's request, Fable reviewed the whole plan rather than the code:
strategy, design decisions, upstreaming, quality and process. Its top
recommendations, ranked:

1. Boot the laptop's own Windows once and trace the OEM Dolby pipeline (files,
   DisplayMonitor getters, media types, D3D device, sample attributes) before
   further Wine work. Owner decision (BitLocker install, coordinated window).
2. Make an open, RPU-aware display-management path (libplacebo reshaping and
   L1, plus L2 trims) the generally available Dolby Vision track. Validate it
   against the privately held Dolby reference renderer within a stated
   ΔE_ITP. Keep the OEM-under-Wine route as a time-boxed, lab5-only
   experiment. Owner decision on what counts as "actual Dolby Vision".
3. Settle KMS HDR metadata with the planned on-screen A/B, then bound the
   composition and declare the display's own values, as KWin and Windows
   do. Upstream sent zero after 10000-nit values broke monitors; declaring
   the panel's own values is different.
4. Reshape the upstream series for acceptance under the owner's identity,
   in slices, design discussions first. `@invalid` authorship cannot be
   submitted. Upstream libdisplay-info would likely prefer one Display
   Parameters struct to two narrow getters. The four kernel patches track
   an existing intel-gfx series that should be followed, not resubmitted.
5. Buy the instrument now, and build a small Wayland PQ patch client, because
   ArgyllCMS cannot drive a PQ surface.

Further findings: no per-output peak override for displays with wrong CTA
values; colord-assigned measured ICC should beat base EDID as the native SDR
target; Night Light is applied to PQ-encoded values (an
upstream defect); apps must not apply a display ICC on top of the compositor;
OLED ABL means full-frame scenes stay near 400 cd/m²; the test matrix lacks
an HDMI HDR TV on the NVIDIA output, the MUX route and any AMD hardware; the
ACES threshold was tuned for AP1 camera colours.

One finding was wrong on checking the code: the review said SDR white in
HDR mode is capped at 203 cd/m² and that the reference-white factor never
exceeds 1. The ref-white backlight's range is 10–210, so the factor reaches
2.1 and SDR white about 426 cd/m². The cap, and the corresponding owner
decision, were withdrawn.

Corrections applied: the stale nativehdr7 status line, the Dolby activation
qualifier (Wine 0001–0009 only; Profile 7 not registered), the
DisplayMonitor descriptor wording (sysfs by connector name is now an open
option), the ACES parameter provenance, and the dated baseline table.

## Tenth batch — general targets and upstream port

An adversarial Fable review covered the upstream-facing Mutter port, the
[general display targets](DISPLAY_TARGET_SOURCES.md) and the Ubuntu
`nativehdr9` port. It ran a scratch probe against the built tree. A Fable
re-review then checked the fixes and ran the Wayland colour cases at the new
head.

| Finding | Severity | Disposition |
|---|---|---|
| Gamut containment compared adapted source primaries with an unadapted target triangle. In native SDR, with the common EDID white (0.3135, 0.3291), the output's own encoding and every client following the preferred description were compressed and refused direct scanout (probe-confirmed) | Should-fix | The display target is adapted from its encoding's white to D65 before containment, limits and matrices (new commit "Judge gamut containment in the frame of the pixels"); tests fail with it reverted. BT.2100 targets move by under 3e-5 xy, inside their tolerance |
| A CTA peak below the display reference white highlight-mapped and dimmed all SDR content (probe-confirmed) | Should-fix | A target peak must exceed the encoding's nominal reference white for every declared source; failing sources fall through |
| Base EDID primaries as the BT.2100 gamut target risk desaturating wide-gamut content on displays that declare their SDR gamut there; the display may also tone-map on top, since KMS metadata stays unknown | Should-fix (design) | Base EDID is the native SDR gamut source only; BT.2100 keeps DisplayID-only gamut. Double mapping recorded as an evidence limit |
| The ported first commit's inherited validation paragraph lost its qualifier and read as validation of upstream main | Should-fix | Qualifier "on the Ubuntu 51.0 source adaptation" and "private" restored; the claim is the owner's inherited one, kept distinct |
| A minimum-only DisplayID declaration shadowed a CTA peak | Nit | DisplayID luminance needs the 10% window peak to be a source |
| Base EDID primaries lacked the chromaticity domain check | Nit | x ≥ 0, y > 0, x + y ≤ 1 required |
| Stale comments naming firmware as the only target source; contract doc behind the code | Nit | Corrected |
| Ubuntu port stale after the fixes | Should-fix | `nativehdr9` regenerated from the six final upstream commits; non-debian content identical apart from Ubuntu's `extra_suites` |

Checked and found correct by the reviewer: 38 of the 43 ported commits are
byte-identical to their Ubuntu originals, and the others differ only by the
documented squash, style fold and two style fixes. All subjects pass the
upstream commit rules. Whole-source selection, fall-through and CTA zero
semantics are correct (libdisplay-info leaves absent values 0). Integer
geometry is exact. Refresh on mode and EDID changes goes through one device
update. Wayland identity excludes provenance, so a provenance-only change
creates no new description. Ordinary sRGB clients in native SDR were already
composited, so there is no new scanout regression.

Recorded behaviour: in BT.2100 the brightness slider sets the reference-white
factor over 0.1–2.1 (`meta-backlight-ref-white.c`, brightness range
10–210), so SDR white reaches about 426 cd/m². On an output whose declared
peak is below that, for example an HDR400 monitor, the top of the slider
highlight-maps SDR toward the peak (already true on the native route). A
native SDR panel whose white lies far
from D65 can now compress sRGB content, which is the consistent result of
the encoding's own white adaptation.

The colour test set ran once at the final head: 23 of 23, including the two
new compositor cases, with every rewritten commit building on its own.
Every one of the 43 ported commits also builds with warnings as errors
([receipt](../evidence/general-targets-fast-lane.json)).

## Ninth batch — independent review and fixes

At the owner's request, three independent Fable 5.1 reviews covered the
compositor stack (`nativehdr4`–`7`), the library, Wine and Dolby activation
work, and the evidence, packaging and delivery kit. A Fable re-review then
checked the fixes. Findings and dispositions:

| Finding | Severity | Disposition |
|---|---|---|
| PQ content without a declared peak was tone-mapped from the 10000 cd/m² encoding capacity: plain HDR video was dimmed from about 150 cd/m², lost reference-white anchoring and lost direct scanout | Blocker (computed) | The encoding maximum counts as the content peak only for SDR-type encodings and HLG; PQ and linear need a declared peak, otherwise nothing is mapped (`nativehdr8`) |
| Published output and preferred descriptions used the 10%-tolerant equality while rendering is exact, so clients following them were mapped again after small brightness changes | Should-fix | Published on the renderer's exact identity |
| KMS static metadata stays zero while the compositor maps | Should-fix (design) | Kept: with unmapped plain PQ the composition is not bounded by the target, so declaring the target would be untrue; compare on screen after installation ([contract](HDR_MAPPING.md#kms-hdr-metadata-stays-unknown)) |
| Stale comments: mastering primaries "never map gamut" | Should-fix | Corrected |
| HLG system gamma used the extended formula everywhere | Nit | BT.2100-2 Table 5 within 400–2000 cd/m², extended form outside; independent test reference |
| Mapping predicate recomputed per frame and per pointer motion; display targets inferred from any target volume; curve relied on infinities | Nit | One decision per state pair shared by renderer, scanout and cursor; explicit display-target constructor; finite two-branch curve (its first test had a duplicated sample point, fixed and rerun) |
| Bounded-encoding proxy and the two D65 definitions undocumented | Nit | Documented in code |
| The compositor depended on a library version floor that an archive build would satisfy, so an archive library update could leave GNOME unable to start | Should-fix | The library provides `libdisplay-info3-native-hdr-api (= 2)` and the compositor depends on it; the install kit holds the six packages |
| A stale quilt entry in both packages was hidden by regenerated quilt bookkeeping | Should-fix | Removed (its attribution moved to `README.native-displayid`); the private packaging harness now refuses to build unless every series entry reverse-applies (the debian sources do not enforce this) |
| Wine Wayland driver supplies no monitor descriptor, so on the owner's desktop the processor sees no panel facts | Should-fix (plan) | Recorded as the governing prerequisite for the processor track ([Wine](WINE_DISPLAY_MONITOR.md#remaining-processor-boundary)) |
| GDI driver ABI deployment set unnamed (`wineps.drv` would break) | Should-fix | Coherent module set documented |
| DisplayMonitor read without the lock if the mutex failed; name coupled by string | Should-fix | Shared name; resolution fails closed |
| `GetDescriptor` returned unvalidated or over-long EDID bytes; three output technologies unmapped | Nit | Validated, exactly bounded copy; technologies mapped from SDK definitions |
| Dolby probe recipe stale; next step under-specified (descriptor source, device, oracle, getter traces); network-count wording inconsistent | Should-fix | Wine 11 fixture documented; four prerequisites listed |
| Upstream library API shape (narrow getters, reserved values not diagnosed) | Should-fix (upstream) | Recorded as upstream follow-up; the Ubuntu delivery keeps its compatible behaviour |
| Stale stock-kernel name in recovery notes; install kit lacked pre-flight checks, a package-state snapshot, holds and failure guidance; agent containers left on the laptop | Should-fix | Kit and operations notes corrected; containers listed for the owner's decision |
| Status pages and README inconsistent in places | Nit | Corrected |

The fast lane ran once over the affected suites. The Mutter run passed
except one new test, whose sampling loop visited one distance twice; after
that test-only fix, only it was rerun and passed. The Wine `displaymonitor`
and `displayconfig` tests passed with the rebuilt modules
([receipt](../evidence/review-fixes-fast-lane.json)).
`scripts/check_repository.py` passed before merge.

