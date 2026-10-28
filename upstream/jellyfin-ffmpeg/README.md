# jellyfin-ffmpeg — upstream submission kit

**Prepared:** 2026-10-28 · **Submitted:** nothing.

Repository: `jellyfin/jellyfin-ffmpeg` · target: `jellyfin` · base:
`e965dc63b4642af56f1d48b0a8b5d5f103440bfa`.

| Unit | Inventory | State | Remaining |
|---|---|---|---|
| [01](01-bwdif-buffer-index/DESCRIPTION.md) | JF-1 | ready-for-human-review |  |
| [02](02-hable-reference-white/DESCRIPTION.md) | JF-2 | ready-for-human-review (draft) |  |
| [04](04-apple-libtool/DESCRIPTION.md) | JF-4 | ready-for-human-review |  |
| [03](03-subtitle-filter-design/DESCRIPTION.md) | JF-3 | design-hold | Maintainer agreement on filter and overlay API; Split the command protocol from generic filter plumbing; Mac render and lifetime tests |

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
