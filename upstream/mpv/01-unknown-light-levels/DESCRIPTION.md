# wayland: don't send an unknown MaxCLL or MaxFALL

Omit optional zero MaxCLL and MaxFALL values that violate older color-management
protocol luminance constraints. Preserve independently known values.

Validation: this independent unit builds on the recorded current upstream base
with Wayland and Vulkan enabled. All 17 upstream Meson tests pass. The test
prefix uses libplacebo 7.387.0, Wayland 1.26.90, wayland-protocols 1.49, Vulkan
loader 1.4.366, and current FFmpeg libraries. These are source/build tests;
Weston/NVIDIA session behavior and Profile 7 FEL playback were not rerun.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
