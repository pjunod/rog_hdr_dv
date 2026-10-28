# configure: probe a symbol when linking static Vulkan

Use vkGetInstanceProcAddr as the link probe for the pkg-config static Vulkan
path, matching the fallback link check. A preprocessor expression is not a
function symbol for check_pkg_config's link test.

The one-line patch applies to the current base. Static-MoltenVK configuration
has not been exercised.

Validation: real configure on the recorded base with an isolated static Vulkan
library, official Khronos headers, and a pkg-config file whose library name
differs from libvulkan. The original pkg-config symbol probe fails (exit 1),
while the proposed vkGetInstanceProcAddr probe passes (exit 0). This directly
exercises the link-probe path; it is not a MoltenVK or GPU rendering test.

The included verify_static_probe.py preserves the supplied source checkout and
runs both configure variants in a new owned directory:

```bash
python3 verify_static_probe.py --source /path/to/FFmpeg-git \
  --headers /path/to/Vulkan-Headers/include --work-root /path/to/owned-work
```

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
