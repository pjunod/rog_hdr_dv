# Expose current-frame OAMD presence

ObjectAudioMetadata retains its last values when a frame has no OAMD payload. Its object count therefore cannot indicate whether this frame carried metadata. Add HasOAMD, set only when OAMD was decoded for the current frame, and exercise reset/presence behavior.

Inherited 2026-10-27 sequential-tip suite: 105 passed. This API reports payload presence; it makes no fidelity claim.

Offered under the existing [Cavern licence](https://github.com/VoidXH/Cavern/blob/master/LICENSE.md), including its attribution and public-use restrictions. No licence conversion is proposed.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). Human review and responsibility remain with the submitter before publication.
