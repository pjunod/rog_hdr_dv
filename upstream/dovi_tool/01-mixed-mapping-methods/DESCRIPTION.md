# dovi/rpu: reject mixed mapping methods within one component

Reject a reshaping component whose pieces switch between polynomial and MMR
mapping. The representation stores one mapping method for the component, and
writing a mixed component can index coefficient vectors inconsistently.

The regression constructs the bitstream directly: the unmodified parser accepts
the mixed component, while the fixed parser rejects it with a specific error.
The complete dolby_vision crate suite passes. End-to-end Profile 7 conversion
was not rerun. Other parser-bound changes from the earlier downstream series
were superseded by upstream PR #430 and are deliberately excluded.

Validation: cargo test --manifest-path dolby_vision/Cargo.toml — 10 passed, 0
failed (macOS aarch64, rustc 1.98.0).

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
