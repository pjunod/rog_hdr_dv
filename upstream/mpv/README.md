# mpv — upstream submission kit

**Prepared:** 2026-10-28 · **Submitted:** nothing.

Repository: `mpv-player/mpv` · target: `master` · base:
`ad5877edabdb05c0c62aad444722938d37666e2d`.

| Unit | Inventory | State | Remaining |
|---|---|---|---|
| [01](01-unknown-light-levels/DESCRIPTION.md) | MPV-1 | ready-for-human-review |  |
| [02](02-enhancement-layer-fallback/DESCRIPTION.md) | MPV-2 | ready-for-human-review (draft) |  |
| [04](04-initial-pass-through/DESCRIPTION.md) | MPV-4 | ready-for-human-review (draft) |  |
| [05](05-film-timeline/DESCRIPTION.md) | MPV-5 | design-hold | Maintainer agreement on the embedding interface; propose the design before a merge request |

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
