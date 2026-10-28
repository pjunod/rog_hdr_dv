# rpi-ffmpeg — upstream submission kit

**Prepared:** 2026-10-28 · **Submitted:** nothing.

Repository: `jc-kynesim/rpi-ffmpeg` · target: `test/8.1.2/main` · base:
`f60aae17021abae85b1ba9759e8b2da33f723902`.

| Unit | Inventory | State | Remaining |
|---|---|---|---|
| [01](01-v4l2-object-review/DESCRIPTION.md) | PI-1 | validation-pending | Show a configuration that fails without explicitly selecting v4l2_fmt.o |

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
