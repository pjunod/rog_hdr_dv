# Retain a shutdown notification when the request queue is full

Propose a retained terminal notification instead of best-effort try_send behind
a full request queue. Port the minimal change independently of supervisor policy
and demonstrate cancellation under queue saturation before sending code.

Validation: source preparation only; the missing checks below have not run.

Before submission: Upstream-only reproduction and focused port; discuss the
proposed contract first; Explicit local human approval.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
