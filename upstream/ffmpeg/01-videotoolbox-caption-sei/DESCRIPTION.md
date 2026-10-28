# avcodec/videotoolboxenc: count RBSP bytes in SEI payloads

Count RBSP payload bytes while skipping emulation-prevention bytes in encoded
SEI NAL units. Locate the trailing byte without rewriting existing SEI data.

Jellyfin independently removed the SEI-merging logic in its fix. Upstream may
prefer that smaller approach. This proposal applies to the current FFmpeg base
but has not passed a Mac encode or FATE regression; no runtime result is
claimed.

Validation: [the included production-function reproduction](reproduction/README.md)
extracts the actual baseline and candidate parser bodies. Under Clang ASan and
UBSan, 13 of 21 expectations fail on the baseline and all 21 pass with the
candidate. Legal escaped UUID SEI NAL units reproduce incorrect offsets;
header-only input also exposes the original sanitizer failure. The actual
changed videotoolboxenc.o compiles with the H.264 VideoToolbox encoder enabled
and macOS SDK 27.0. Exact fixtures, source/function hashes, commands and logs
are in [the receipt](reproduction/receipt.json).

No real VideoToolbox encode, A/53 insertion, FATE integration, full FFmpeg link
or hardware decoder was run. The fixture does not execute destination-capacity
arithmetic in copy_replace_length_codes; that change has translation-unit
compile evidence only. This remains a Draft source proposal. Jellyfin's
smaller removal of SEI merging is compared in the reproduction README and may
be the preferable upstream approach; no preference is claimed from the parser
fixture alone.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
