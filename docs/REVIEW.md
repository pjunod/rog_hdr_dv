# Review — adversarial findings and the current implementation batch

**Updated:** 2026-10-09 UTC · **State:** findings addressed; candidate reviewed
and affected fast lane passed.

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
runner is also being made explicitly UID 1000; lack of Docker privileged mode
alone does not mean a process has a non-root UID.

Focused runtime tests are now executing after the findings and their
correction deltas were approved. The 11 new corpus tests passed on their first
run; both complete patch series reconstructed to their pinned source trees. Dolby executables have separately returned their
versions in an isolated CPU environment following the owner's installer action;
no reference frames have been processed.

The first runtime pass found a shutdown lifetime defect: qdata released the
colour manager after the compositor had already freed its outputs. A bounded
GDB run of the failed test identified the stale output access in signal
disconnection. Explicit colour-manager finalization now precedes output
teardown, after canonical shutdown has destroyed clients. The two new Wayland
fixtures also used nonconsecutive synchronization serials; their numbering is
corrected without weakening the helper. The eight native checks passed and
remain valid; only the three failed Wayland paths need qualification retries
after this correction is reviewed.
