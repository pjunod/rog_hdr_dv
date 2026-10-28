# displayid2: expose native luminance from Display Parameters

The DisplayID 2.0 Display Parameters data block (tag 0x21) declares the panel's native minimum
luminance and maximum luminance at full and at 10% coverage, as binary16 values. Panels that
describe themselves only through DisplayID 2.0 have no other source for them.

This adds `di_displayid2_data_block_get_luminance()`, with a presence flag per value. Only the 29-byte
payload, revisions 0 and 1 (with the image-size unit flag) and the minimum-guaranteed luminance
class are supported; anything else returns NULL. A negative, infinite or NaN value, or the
"do not use" sentinel, only clears its own presence flag; zero and subnormal values are kept.
These are physical declarations, not CTA desired-content metadata, and imply no transfer
function. The existing high-level HDR getters are not changed, which the tests check with and
without a CTA extension.

Design question: one Display Parameters struct may fit the library better than narrow getters for luminance and chromaticities (unit 06). I kept them
separate because their format rules differ slightly (feature bits 3-4 versus 5), but I can merge
them into a single `di_displayid2_display_params` if that is preferred.

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

Result for this commit: Ok: 76 in each of the three build configurations, 0 failures, and
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
