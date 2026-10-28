# hiqlite — upstream submission kit

**Prepared:** 2026-10-28 · **Submitted:** nothing.

Repository: `sebadob/hiqlite` · target: `main` · base:
`493f980562766f0ce5645e015557bc39501f9a5b`.

| Unit | Inventory | State | Remaining |
|---|---|---|---|
| [01](01-duplicate-node-ids/DESCRIPTION.md) | HQ-1 | ready-for-human-review | Explicit local human approval; open Draft and leave Ready for Review to a human; Complete just verify or document its unrun S3/MSRV/example checks |
| [02](02-private-triage/DESCRIPTION.md) | HQ-RP | security-hold | Paul must decide the private reporting route before any public patch or reproduction |
| [03](03-snapshot-remote-errors/DESCRIPTION.md) | HQ-8 | ready-for-human-review | Explicit local human approval before Draft PR |
| [04](04-optional-s3-provider/DESCRIPTION.md) | HQ-17, HQ-19 | design-hold | Maintainer agreement on the feature topology; Explicit local human approval before Draft PR |
| [05](05-bounded-websocket-writes-and-flushes/DESCRIPTION.md) | HQ-9 | design-hold | Upstream-only reproduction and focused port; discuss the proposed contract first; Explicit local human approval |
| [06](06-join-socket-tasks-and-isolate-snapshot-receiv/DESCRIPTION.md) | HQ-10 | design-hold | Upstream-only reproduction and focused port; discuss the proposed contract first; Explicit local human approval |
| [07](07-retain-a-shutdown-notification-when-the-reque/DESCRIPTION.md) | HQ-11 | design-hold | Upstream-only reproduction and focused port; discuss the proposed contract first; Explicit local human approval |

```bash
./submit.sh 01 --dry-run  # Fetch the current target and apply unsigned patches.
./submit.sh 01            # Human-reviewed eligible unit: sign off and publish.
```

Read each description, including validation limits, before publishing. The
dry run never adds a sign-off, forks, pushes, opens a PR or contacts a
maintainer. It retains its source checkout for inspection. A moved upstream
target requires refreshed validation; clean application alone does not qualify
it. Live submission refuses held units and preserves different existing
commits. Closed or merged PRs are reported without resubmission.

Upstream requires explicit local human approval before opening a Draft PR.
Marking the PR ready remains a separate human action. `just verify` includes
S3 and MSRV/example checks beyond the scoped receipts; unrun checks are named
in the unit descriptions. The management-client candidate is kept private
pending reporting-route triage.

Publication requires Git, Python 3 and `gh` authenticated as `pjunod`.
