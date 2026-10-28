# avfilter/tonemap_videotoolbox: expose Hable reference white

Normalize Hable using the caller's reference-white option, retaining the 203-nit
default. The proposal is a quilt patch appended after the existing queue.

Validation: quilt queue apply; make libavfilter/vf_tonemap_videotoolbox.o —
baseline and fixed compile on Xcode 27 SDK; render/default-compatibility
comparison not run.

These are scoped source and synthetic checks. They do not claim a complete x265
package build, general image-quality acceptance, or calibration.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
