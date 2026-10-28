# gemm — upstream submission kit

**Prepared:** 2026-10-28 · **Submitted:** nothing.

Repository: `sarah-quinones/gemm` · target: `main` · base:
`86102c5b712737978371ac9ef7a11982f686d7bc`.

| Unit | Inventory | State | Remaining |
|---|---|---|---|
| [01](01-fp16-target-features/DESCRIPTION.md) | GM-1 | upstream-overlap-hold | Review the existing upstream PRs and post validation to #47 or coordinate with #39; do not open a duplicate PR |

```bash
./submit.sh 01 --dry-run  # Report the existing-PR overlap without publishing.
```

Read each description, including validation limits, before publishing. The
dry run never adds a sign-off, forks, pushes, opens a PR or contacts a
maintainer. It retains its source checkout for inspection. A moved upstream
target requires refreshed validation; clean application alone does not qualify
it. Live submission refuses held units and preserves different existing
commits. Closed or merged PRs are reported without resubmission.

Publication requires Git, Python 3 and `gh` authenticated as `pjunod`.

Review the validation draft for upstream PR #47 and coordinate with the existing
#39/#43 proposals. The live script refuses a duplicate pull request.
