# Defer BlockBuffer frame fetch until samples are requested

BlockBuffer.Read currently fetches the following frame as soon as an exact-sized read finishes. Metadata then describes that next frame while the returned PCM belongs to the previous one. Defer that fetch until a caller actually requests the next samples, preserving end-of-stream behavior.

The regression tests cover exact and unaligned reads, continuity, and end-of-stream padding. The recovered 2026-10-27 sequential-tip suite passed 103 tests; reverting fixes made the exact-read test fail. Removing the zero-pointer end-of-stream guard also fails one of five BlockBuffer tests. These are inherited results, not new hardware measurements.

Offered under the existing [Cavern licence](https://github.com/VoidXH/Cavern/blob/master/LICENSE.md), including its attribution and public-use restrictions. No licence conversion is proposed.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). Human review and responsibility remain with the submitter before publication.
