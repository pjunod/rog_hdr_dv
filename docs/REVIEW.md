# Review — adversarial findings and the current implementation batch

**Updated:** 2026-10-10 UTC · **State:** fifth batch merged; sixth batch
(nativehdr5) reviewed, findings addressed, fast lane passed.

Companion to [status](STATUS.md) and [development](DEVELOPMENT.md). The initial
review was explicitly requested before the owner established the subsequent
pre-merge-only review workflow. Future batches use that workflow.

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
rewriting that existing public metadata is pending. New agent commits use
`Codex <codex@invalid>`. No credential from the conversation is stored here.

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
