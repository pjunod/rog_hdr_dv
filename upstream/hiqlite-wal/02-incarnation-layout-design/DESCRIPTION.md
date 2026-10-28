# WAL incarnation and layout guard follow-up

Upstream PR #367 already records id_from in the memo. The downstream claims
about stale mmap identity, suffix rewrite identity and reader/path-reuse
serialization need a fresh upstream-only reproduction before proposing
additional locking or identity APIs. No unverified full vendor delta is
included.

Validation: source preparation only; the missing checks below have not run.

Before submission: Reproduce stale same-path mmap or suffix identity reuse on
unmodified upstream; Split the remaining fix from upstream PR #367.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
