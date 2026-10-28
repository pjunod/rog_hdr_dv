# Cavern — three independent audio fixes

**Status:** ready for human review · **Base:** `c233ce02bd4f93de43ff94df7609fab611ab870e` · **Checked:** 2026-10-28.

These fixes originated in rog_audio's probes. They are preparation artifacts,
not an Atmos fidelity claim. See [manifest](manifest.json) for exact files
and [evidence](evidence.json) for inherited versus new checks.

| Unit | Inventory | Change | Acceptance |
|---|---|---|---|
| 01 | CAV-1 | BlockBuffer deferred fetch | Synthetic regression; inherited 103 tests |
| 02 | CAV-2 | Frame-sized JOC timeslot wrap | Synthetic regression; inherited 104 tests |
| 03 | CAV-3 | Current-frame OAMD presence | Inherited 105 tests |

```bash
./upstream/cavern/submit.sh all --dry-run  # Apply to isolated current upstream checkouts.
./upstream/cavern/submit.sh 01            # Human: sign, fork, push and open the first PR.
```

A passing dry run proves source application only. Full suites above ran on
sequential tips; independent-unit source application is recorded separately.
Read the [custom licence](https://github.com/VoidXH/Cavern/blob/master/LICENSE.md)
before publication; retain attribution and the original licence.
