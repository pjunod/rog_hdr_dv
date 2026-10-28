# hiqlite-wal — upstream submission kit

**Prepared:** 2026-10-28 · **Submitted:** nothing.

Repository: `sebadob/hiqlite` · target: `main` · base:
`493f980562766f0ce5645e015557bc39501f9a5b`.

| Unit | Inventory | State | Remaining |
|---|---|---|---|
| [01](01-single-file-purge-boundary/DESCRIPTION.md) | WAL-1 | ready-for-human-review | Explicit local human approval before Draft PR |
| [02](02-incarnation-layout-design/DESCRIPTION.md) | WAL-3 | design-hold | Reproduce stale same-path mmap or suffix identity reuse on unmodified upstream; Split the remaining fix from upstream PR #367 |

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

This project shares hiqlite's human-review policy: obtain explicit local
human approval, open a Draft PR, and let a human mark it ready.

Publication requires Git, Python 3 and `gh` authenticated as `pjunod`.
