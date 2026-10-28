# fix(config): reject duplicate node ids

Reject duplicate durable node IDs while permitting non-contiguous IDs. Looking
up the first matching node while counting duplicate entries as cluster members
yields inconsistent configuration.

This is the remaining duplicate-ID check, distinct from upstream PR #368, which
selected the local node by ID. Recovered exact-branch receipts include
formatting, default Clippy, a 22-configuration Clippy matrix, and the no-S3
suite (95 + 3 + 27 + 14 tests). The added regression failed on the unmodified
base and passed with this patch.

Upstream AGENTS.md requires explicit local human review before opening a Draft
PR; a human must later mark it ready. These recovered checks do not claim that
just verify, external S3, examples, or MSRV checks ran.

Validation: cargo fmt --check; cargo clippy -- -D warnings; no-S3 test feature
suite; 22 feature Clippy configurations — recovered exact-branch passes from
2026-10-27; not rerun.

Before submission: Explicit local human approval; open Draft and leave Ready for
Review to a human; Complete just verify or document its unrun S3/MSRV/example
checks.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
