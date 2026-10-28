# build: make S3 dependencies optional without losing the HTTP provider

Enable cryptr/s3 only through hiqlite's S3 feature. Initialize ring before
constructing the rustls-no-provider HTTP client, so removing incidental S3
dependencies does not remove the provider used by remote clients and helpers.
The coupled change is one commit; it has no intermediate provider gap.

Validation: cargo check -p hiqlite --no-default-features --features sqlite and
--features sqlite,s3 both pass for the original feature component and final
provider-enabled tree. The final tree's fresh-provider library regression passes
with --lib --no-default-features --features sqlite. The unchanged tree was
preserved when the two preparation commits were squashed.

The default full-feature provider test also passes before the change, so this is
dependency hardening for optional S3 rather than an independently reproduced
baseline provider failure. The SQLite-only integration target cannot compile
because its existing tests use unavailable cache APIs; it is not counted as a
pass. Full external-S3, MSRV, examples and feature-Clippy matrices have not run.
Maintainer agreement on feature topology remains a design prerequisite.

Upstream requires explicit local human approval before opening a Draft PR; a
human must later mark it ready.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
