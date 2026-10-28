# ksni — upstream submission kit

**Prepared:** 2026-10-28 · **Submitted:** nothing.

Repository: `iovxw/ksni` · target: `master` · base:
`2397cc2ce535ba4e7ed77fecd94731c5239923e7`.

| Unit | Inventory | State | Remaining |
|---|---|---|---|
| [01](01-menu-property-ids/DESCRIPTION.md) | KS-1 | ready-for-human-review |  |

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

Publication requires Git, Python 3 and `gh` authenticated as `pjunod`.
