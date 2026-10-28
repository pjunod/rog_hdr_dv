# edid: expose structured extension parsing failures

Today the only way for a caller to learn that an extension block failed to parse is
`di_info_get_failure_msg()`, which also carries descriptive warnings about the base block. A
compositor that wants to rely on DisplayID data has to reject the whole string, and so loses
valid DisplayID data on panels that only have unrelated base timing or range warnings.

This adds `di_edid_has_extension_failures()`, which reports known extension failures independently
of the log text: diagnostics raised while parsing an extension, extension blocks that were dropped
or could not be interpreted, checksum failures (including those that lead to a block being dropped
early) and size/block-count mismatches. Fatal base block checks are unchanged and base block
warnings do not set it. It reports known failures; it does not claim full conformance.

This is new public API, so I would especially like feedback on whether a boolean is the right
shape (versus, say, a per-extension status).

## How it was tested

On current `main` (`af382cf3`) with this series applied in order, every commit was built
and tested on its own in the four configurations of `.gitlab-ci.yml`:

```
meson setup build -Dwerror=true && ninja -C build && meson test -C build
CC=gcc-14 CFLAGS=" -Wnull-dereference -fanalyzer -O1" meson setup build-gcc --fatal-meson-warnings -Dwerror=true
CC=clang meson setup build-clang --fatal-meson-warnings -Dwerror=true -Db_sanitize=address,undefined -Db_lundef=false
UBSAN_OPTIONS=halt_on_error=1 meson test -C build-clang
# testing-check: edid-decode from v4l-utils 1316a80455ef (the CI pin) in PATH
meson setup build-gen && ninja -C build-gen gen-test-data && git diff --quiet
```

Result for this commit: Ok: 75 in each of the three build configurations, 0 failures, and
`gen-test-data` leaves the tree unchanged (the checked-in references match). Compilers:
GCC 13.3 and 14.2, Clang 18.1, meson 1.12.1. The docs job (gyosu) was not run.

## Hardware context

I use these on an ASUS ROG Zephyrus G16 whose eDP panel declares HDR only through DisplayID 2.0
(Display Interface Features with RGB BT.2020/ST 2084 and Display Parameters with luminance and
chromaticities, no CTA HDR static metadata block). Mutter changes that consume them are being
prepared separately (GNOME/mutter#4847 is the same symptom family). The tests here use synthetic
fixtures only; I have not added a real EDID of that panel.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code).
