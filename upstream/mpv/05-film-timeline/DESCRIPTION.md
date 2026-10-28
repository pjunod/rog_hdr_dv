# osc: draw a film timeline the application provides

Add an optional embedding-application film timeline and osc-film-seek messages.
Document origin, duration and the application responsibility for out-of-stream
seeks, with an interface-change entry.

Validation: this independent unit builds on the recorded current upstream base
with Wayland and Vulkan enabled. All 17 upstream Meson tests pass. The test
prefix uses libplacebo 7.387.0, Wayland 1.26.90, wayland-protocols 1.49, Vulkan
loader 1.4.366, and current FFmpeg libraries. These are source/build tests;
Weston/NVIDIA session behavior and Profile 7 FEL playback were not rerun. The
OSC script also passes the Lua 5.2 syntax check. Its embedding API remains a
design proposal.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
