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
