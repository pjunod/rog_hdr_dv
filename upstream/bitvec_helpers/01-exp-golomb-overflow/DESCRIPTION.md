# reader: bound Exp-Golomb codes and preserve integer precision

Decode unsigned and signed Exp-Golomb values through shared private integer
arithmetic. Both bitvec-backed public readers and the bitstream-io reader reject
overflowing prefixes or payloads without shifts by 64 or floating-point
rounding. The bitvec cursor remains unchanged when decoding fails.

Support the complete u64 and i64 endpoints: 64 leading zeroes, a marker and
payload zero encodes u64::MAX; payload one encodes i64::MIN in the signed
mapping. The positive signed overflow is rejected. Public APIs are unchanged;
writer arithmetic is outside this input-parser patch.

Validation: cargo test (default backend, 8 passed); cargo test --all-features
(16 passed); cargo test --no-default-features --features bitstream-io (8 passed)
on macOS aarch64, rustc 1.98.0. On the original upstream production code, 3 new
default-backend regressions and 9 combined regressions fail. Endpoint, overflow,
truncated-payload and cursor checks exercise the actual public reader
implementations.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
