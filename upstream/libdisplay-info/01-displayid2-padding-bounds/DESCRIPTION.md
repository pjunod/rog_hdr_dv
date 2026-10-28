# displayid2: bound section padding scans to the remaining payload

A DisplayID 2 data block whose declared length is larger than what is left of the section made the
parser step past the end of the section payload, and the stale remaining length then made the
final padding scan read beyond it (out of bounds under AddressSanitizer).

This clamps a truncated block to the available payload and recomputes the remaining size before
the padding scan, which excludes the checksum byte. A new test (`displayid2-bounds`) builds exact-sized
sections through the public API: empty payloads, short headers, complete blocks and oversized
lengths. The corrected scan also drops a spurious padding diagnostic from the
`jdi-lpm135m467-edp` reference diff.

It applies on its own to `main` and is independent of the rest of my series.

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

Result for this commit: Ok: 70 in each of the three build configurations, 0 failures, and
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
