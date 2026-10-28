# fix(raft-client): keep snapshot peer errors as RemoteError

Preserve a peer SnapshotMismatch as RPCError::RemoteError for SQLite and cache
snapshot installation. OpenRaft can then restart chunk transfer at offset zero
instead of retrying an offset the peer has rejected.

Recovered tests for both SQLite and cache fail on the unmodified base and pass
on this exact branch. The full current-branch upstream verification matrix has
not run.

Validation: cargo fmt --check; cargo clippy -p hiqlite --features
cache,counters,dlock,listen_notify,macros,toml,external-state-machine -- -D
warnings; TEST_SKIP_S3_RESTORE=true cargo test -p hiqlite --features
cache,counters,dlock,listen_notify,macros,toml,external-state-machine — rustc
1.97.1: formatting/library Clippy passed; no-S3 upstream unit and cluster suites
passed.

The broader optional oversized-entry-error WAL tests contain an unchanged
upstream closure-signature compile error. Extra all-targets Clippy also reports
unchanged upstream test/bench lints. Those failures were not suppressed or
counted as passes. External S3, MSRV and example checks from just verify have
not run.

Upstream requires explicit local human approval before opening a Draft PR; a
human must later mark it ready.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
