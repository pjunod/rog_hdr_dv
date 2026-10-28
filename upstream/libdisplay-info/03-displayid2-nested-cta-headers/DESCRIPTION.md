# displayid2: reject unsupported nested CTA headers

The CTA DisplayID data block has a revision and header flags byte that was ignored, so a block of
an unsupported format had its children interpreted anyway, and an empty or audio-only block of
unknown format looked the same as one that really carries no HDR or colorimetry metadata.

This diagnoses and skips CTA DisplayID data blocks with an unsupported revision or flags before
reading their children. Valid empty and audio-only blocks are still accepted, and complete
earlier children of a supported block are kept when a later one is malformed. A public API test
covers both block and extension orders, presence and counts, short headers and malformed tails,
and checks that the existing high-level getters are unchanged. It builds on !202 and !212.

This is stacked on unit 02 only because of `test/meson.build` context; it does not use its API.

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

Result for this commit: Ok: 74 in each of the three build configurations, 0 failures, and
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
