# Proton — three recovered and qualified API candidates

**Status:** ready for human review; no submission has been made.
**Base:** `e60892cc2398b0a83c332a2078c7b85e47bdb42b` · **Checked:** 2026-10-28.

[Manifest](manifest.json) records complete prerequisite arrays;
[evidence](evidence.json) separates inherited builds from new runtime checks.

| Unit | Inventory | Change | Runtime |
|---|---|---|---|
| 01 | PR-1 | CreateFileFromAppW | New 123/123, zero skips |
| 02 | PR-2 | Monitor provenance plus EDID completeness | New exact-tip full build and displayconfig13/13 |
| 03 | PR-3 | DisplayMonitor; includes 02 | New 355/355, zero skips |

```bash
./upstream/proton/submit.sh all --dry-run  # Apply each current-base candidate unsigned.
./upstream/proton/submit.sh 01            # Human: sign, fork, push and open unit 01.
```

The owner selected ValveSoftware/wine proton_11.0 as the venue. The inspected
[Valve README](https://github.com/ValveSoftware/wine/blob/proton_11.0/README.md)
has no explicit AI prohibition. WineHQ prohibits LLM-generated code and is
not a destination; disclose the assistance in the Valve PR descriptions.

Fresh candidate-specific prefixes and wineboot -u resolved the inherited
invalid-prefix failures. Unit 01 also sets C.UTF-8 and a valid Windows TEMP.
No production code was changed for those test-environment corrections.
No AppContainer, actual Windows-reference, or physical display-backend
qualification is claimed. Unit 03 includes 02 until that prerequisite merges;
refresh the remaining patch onto upstream at that point.
