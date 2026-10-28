# Autogain: add a maximum gain setting

Add a maximum amplification setting in dB to autogain, including QML, configuration, preset serialization, and documentation. Attenuation is unaffected. The default 100 dB preserves existing behavior; lowering the limit clamps the previous gain before smoothing so it takes effect immediately. Peak limiting remains in place.

This unit includes unit 01 as a prerequisite. Submit after that fix, then refresh against upstream with only the remaining commit. Rebased onto current master 7e314dc536481aa0426dbe68a603b30e65164e50. New full Debug build with -Wall -Wextra and CTest: 3/3 passed on 2026-10-28. Tests compare default smoothing against the prior implementation and cover gain limits, peak ceiling and invalid values. No listening or device qualification is claimed.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). Human review and responsibility remain with the submitter before publication.
