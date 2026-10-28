# ffmpeg — upstream submission kit

**Prepared:** 2026-10-28 · **Submitted:** nothing.

Repository: `FFmpeg/FFmpeg` · target: `master` · base:
`16efe6927d850d23766aee15820abedcb1219121`.

| Unit | Inventory | State | Remaining |
|---|---|---|---|
| [01](01-videotoolbox-caption-sei/DESCRIPTION.md) | FF-1 | ready-for-human-review (draft) |  |
| [02](02-static-vulkan-probe/DESCRIPTION.md) | FF-2 | ready-for-human-review |  |
| [03](03-rasl-frame-thread-report/DESCRIPTION.md) | FF-3 | superseded |  |

```bash
./submit.sh 02 --dry-run  # Fetch the current target and apply unsigned patches.
./submit.sh 02            # Human-reviewed eligible unit: sign off and publish.
```

Read each description, including validation limits, before publishing. The
dry run never adds a sign-off, forks, pushes, opens a PR or contacts a
maintainer. It retains its source checkout for inspection. A moved upstream
target requires refreshed validation; clean application alone does not qualify
it. Live submission refuses held units and preserves different existing
commits. Closed or merged PRs are reported without resubmission.

Publication uses code.ffmpeg.org and a token in
`~/.config/upstream/code.ffmpeg.org.token`, authenticated as `pjunod`. The
API and fork Git transport refuse redirects, and the token never appears in
a Git URL or command argument. GitHub pull requests are not the FFmpeg venue.
