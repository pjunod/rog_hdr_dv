# Fix menu property IDs after a menu refresh

Use the same index-to-ID translation for the empty-ID GetGroupProperties
response as for layouts, individual properties and click dispatch. Raw array
indices cease to identify the menu after its ID offset changes.

The new library regression checks that every returned ID maps back to the
matching item after an offset change. The root ID remains zero. A changelog
entry accompanies the fix.

Validation: `dbus-run-session -- cargo test --lib` — rustc 1.97.1: 38 passed, 0
failed with unchanged GTK dev dependency; new regression fails on unmodified
source.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
