# Speaker converter — unmodified dependency, resolved normalization questions

**Status:** ST-1 and ST-2 excluded from submission · **Checked:** 2026-10-28.
**Current commit:** `711e2d8673f170114fc6cdd08bb948bc0faa5b64`.

The [source-backed disposition](01-normalization-review/DESCRIPTION.md)
explains both observations. Current upstream intentionally peak-normalizes
filters by default. Its existing `--enable level-restore` option retains
the requested channel difference and all-cut attenuation. Four synthetic
FIR/arithmetic cases confirm the relevant production paths; the
[evidence receipt](evidence.json) records exact source hashes and limits.
No converter patch exists downstream, and no speculative bug report is owed.

The upstream is [antoinecellerier/speaker-tuning-to-easyeffects](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects).
[Manifest](manifest.json) records this exclusion and current source identity.

```bash
./upstream/speaker-tuning-to-easyeffects/submit.sh all --dry-run  # Print the resolved exclusion.
```

No OEM profiles or captured proprietary data were used. This does not
establish acoustic accuracy or recommend changing an installed preset.
