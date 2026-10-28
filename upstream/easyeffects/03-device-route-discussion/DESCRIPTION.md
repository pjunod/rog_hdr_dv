# Discuss device-route persistence without product rebranding

The downstream experiment binds speaker correction to an exact route and retains route choices across device return, late profile bindings and sink arrival. It also changes the application identity; that rebranding is intentionally excluded from this proposal.

Questions for design review: should route identity include both device and profile? Which component owns restoring a saved physical sink when the effects sink is the default? How should disconnect/reconnect and late profile enumeration interact with preset autoload?

Current upstream has preset-autoload startup/reset and device-exclusion changes, including fb2d0e65, 1f526a13 and 83baf8cb. A production patch needs a fresh transition reproducer against those changes and an agreed ownership model. No port or current-upstream hardware test exists. The downstream series against v8.2.8 is not offered as a current master patch.

A related four-channel ROG routing observation is also open: the physical speaker DAC consumes PCM channels 2/3 while a stereo FL/FR mapping can select channels 0/1. It needs a route/profile reproducer before proposing a generic mapping change.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). Human review and responsibility remain with the submitter before publication.
