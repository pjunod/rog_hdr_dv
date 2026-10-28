# EasyEffects — analyser safety, gain control and routing discussion

**Status:** two units built on current upstream; routing design held.
**Base:** `7e314dc536481aa0426dbe68a603b30e65164e50` · **Checked:** 2026-10-28.

Audio source originated in rog_audio. [Manifest](manifest.json) records units;
[evidence](evidence.json) separates recovered history from this run.

| Unit | Inventory | Submission | State |
|---|---|---|---|
| 01 | EE-3 (safety half) | Analyser ownership | Ready for human review; full build + 2/2 CTest |
| 02 | EE-3 (feature half) | Maximum gain | Ready for human review; includes 01, full build + 3/3 CTest |
| 03 | EE-1, EE-2 | Device-route discussion | Held for upstream design and current-device reproduction |

```bash
./upstream/easyeffects/submit.sh all --dry-run  # Apply unsigned; print held discussion disposition.
./upstream/easyeffects/submit.sh 01            # Human: publish the independently useful fix.
```

Submit 01 first. Unit 02 includes it for reproducible pre-merge validation;
refresh 02 onto upstream once 01 merges so its PR does not duplicate 01.
The Debian echo-canceller build patch is third-party distribution packaging,
not an upstream candidate. No app rebranding is included.
