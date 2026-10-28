# fix(hiqlite-wal): restore the purge boundary for a single WAL file

Recover the missing purge boundary from the first retained log even when its WAL
file number is one. The retained index already distinguishes a new log from a
snapshot-installed tail.

The recovered regression writes one entry at index 10000, restarts, and checks a
purge boundary of 9999. It fails on the unmodified base and passes with this
change.

Validation: cargo fmt --check; cargo clippy -p hiqlite-wal --features auto-
heal,migration -- -D warnings; cargo test -p hiqlite-wal --features auto-
heal,migration — rustc 1.97.1: formatting and library Clippy passed; 15 upstream
tests passed; inherited baseline/fixed purge regression also recovered.

The broader optional oversized-entry-error WAL tests contain an unchanged
upstream closure-signature compile error. Extra all-targets Clippy also reports
unchanged upstream test/bench lints. Those failures were not suppressed or
counted as passes. External S3, MSRV and example checks from just verify have
not run.

Upstream requires explicit local human approval before opening a Draft PR; a
human must later mark it ready.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
