# builder: use Apple libtool when merging x265 archives on macOS

Use /usr/bin/libtool for the macOS multi-depth archive merge so GNU libtool
earlier in PATH cannot select the wrong tool.

Validation: native Apple libtool merge with conflicting PATH tool and three
synthetic static archives — PATH-selected fixture exits 72; /usr/bin/libtool
exits 0 and nm finds all three depth markers; full x265 build not rerun.

These are scoped source and synthetic checks. They do not claim a complete x265
package build, general image-quality acceptance, or calibration.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
