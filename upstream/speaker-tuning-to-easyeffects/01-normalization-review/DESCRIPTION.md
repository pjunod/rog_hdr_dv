# Existing normalization policy resolves both hypotheses

**Status:** excluded from upstream submission · **Checked:** 2026-10-28.
**Source:** commit `711e2d8673f170114fc6cdd08bb948bc0faa5b64`, tree `4559b2b4ff9868395ed10c955d85451b325a826a`.

rog_audio uses this converter unmodified. The two inventory observations
are existing, deliberate normalization choices with an already implemented
opt-in for retaining the requested levels; no new bug report is warranted.

| Inventory | Default behavior | Existing supported behavior | Disposition |
|---|---|---|---|
| ST-1 | Each channel is independently peak-normalized, so unequal flat channel gains become equal | `--enable level-restore` first references both filters to the louder peak, then restores the common gain; the requested left/right difference is retained | Excluded: existing opt-in and explicit policy |
| ST-2 | A wholly negative curve is also peak-normalized and therefore amplified relative to its requested attenuation | The same opt-in applies the negative restoration gain for an all-cut curve | Excluded: intentional normalization with existing restoration |

The relevant code is explicit: [FIR normalization](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/711e2d8673f170114fc6cdd08bb948bc0faa5b64/lib/preset/fir.py#L157),
[common channel reference](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/711e2d8673f170114fc6cdd08bb948bc0faa5b64/lib/preset/emit.py#L311),
and [restored gain](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/711e2d8673f170114fc6cdd08bb948bc0faa5b64/lib/preset/build.py#L184).
Current upstream also has dedicated `test_level_restore_re_references_both_channels`
and `test_level_restore_adds_the_fir_peak_to_the_static_boost` tests; they were
read as supporting source, not rerun here.

A bounded synthetic check used the actual `make_fir` and unchanged production
AST statements for the common-reference and restoration arithmetic. Four
cases passed: input channels -6/-12 dB and -6/-6 dB each produce 0/0 dB by
default; enabling restoration returns -6/-12 and -6/-6 dB within 1e-8 dB.
[The receipt](../evidence.json) records source hashes, method and outputs.
This is arithmetic/FIR evidence, not end-to-end CLI, acoustic, corpus or OEM
profile qualification. No OEM files were used and no report was filed.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via
Claude Code); human review remains with the submitter.
