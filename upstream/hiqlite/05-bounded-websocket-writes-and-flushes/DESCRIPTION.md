# Bounded WebSocket writes and flushes

Propose one write-and-flush deadline per frame and a backpressure regression
using a real TLS stream. The downstream implementation spans nine files and has
not been isolated and requalified against this upstream base.

Validation: source preparation only; the missing checks below have not run.

Before submission: Upstream-only reproduction and focused port; discuss the
proposed contract first; Explicit local human approval.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
