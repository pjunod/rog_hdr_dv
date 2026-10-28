# vulkan/context: start Wayland swapchains pass-through

Start Wayland swapchains in pass-through colour space so driver WSI does not
claim the one colour-management surface before mpv. This independent port avoids
depending on an excluded display-management patch. Runtime toggling of target-
colorspace-hint still needs validation.

Validation: this independent unit builds on the recorded current upstream base
with Wayland and Vulkan enabled. All 17 upstream Meson tests pass. The test
prefix uses libplacebo 7.387.0, Wayland 1.26.90, wayland-protocols 1.49, Vulkan
loader 1.4.366, and current FFmpeg libraries. These are source/build tests;
Weston/NVIDIA session behavior and Profile 7 FEL playback were not rerun.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
