# Autogain: make analyser ownership safe across threads

The worker creates/replaces libebur128 state while process() and the UI use it. The latter held the plugin mutex; the worker did not. Rapid sample-rate changes could also publish an old-rate state. Move state ownership into a synchronized AnalyserState, build outside its lock, and publish only the latest generation. Check initialization/channel/history/frame return values and reset both current and previous gain.

The fake-state regression exercises ownership and stale publication without libebur128. Rebased onto current master 7e314dc536481aa0426dbe68a603b30e65164e50. New full Debug build with -Wall -Wextra and CTest: 2/2 passed on 2026-10-28. No audio-device/session changes or physical listening tests were performed.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). Human review and responsibility remain with the submitter before publication.
