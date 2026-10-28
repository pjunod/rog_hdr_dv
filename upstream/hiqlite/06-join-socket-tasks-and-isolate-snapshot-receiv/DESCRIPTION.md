# Join socket tasks and isolate snapshot receive execution

Coordinate with upstream PR #373, which already adds AbortOnDrop. Isolate only
the remaining terminal-path joins and snapshot receive executor; a fresh
upstream-only reproduction is required.

Validation: source preparation only; the missing checks below have not run.

Before submission: Upstream-only reproduction and focused port; discuss the
proposed contract first; Explicit local human approval.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
