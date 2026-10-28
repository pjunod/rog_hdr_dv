# Wrap JOC timeslots at the frame boundary

The JOC mixing matrices have frameSize / 64 timeslots. The applier wrapped its timeslot after the input channel count, reusing early matrices during the same frame. Wrap at the PCM frame boundary instead.

A synthetic regression exercises a complete frame; inherited 2026-10-27 sequential-tip suite: 104 passed. This does not establish Dolby Atmos/JOC fidelity or replace listening/reference validation.

Offered under the existing [Cavern licence](https://github.com/VoidXH/Cavern/blob/master/LICENSE.md), including its attribution and public-use restrictions. No licence conversion is proposed.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). Human review and responsibility remain with the submitter before publication.
