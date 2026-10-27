# displayid2: expose native chromaticities from Display Parameters

The Display Parameters data block also declares the native RGB primaries and white point as
packed 12-bit fractions, in CIE 1931 xy or CIE 1976 u'v'. This exposes them losslessly with
`di_displayid2_data_block_get_native_chromaticities()`: the raw 12-bit counts (denominator 4096),
the coordinate system and the block revision. Each point has a `valid` flag that only means it is
mathematically usable as xy (x >= 0, y > 0, x + y <= 1; the u'v' domain check is done in
integers so exact boundaries are not lost to rounding). Zero counts are not an "unavailable"
sentinel, and a recognised declaration is returned even when every point is unusable; gamut
validation is left to the caller. The default signal primaries are unchanged and the tests check
that native points do not leak into the signal colorimetry API.

The packing was cross-checked against edid-decode at the CI pin (and NVIDIA's open parser); a
check against the VESA text for every revision by someone who knows it well would be welcome.

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

Result for this commit: Ok: 80 in each of the three build configurations, 0 failures, and
`gen-test-data` leaves the tree unchanged (the checked-in references match). Compilers:
GCC 13.3 and 14.2, Clang 18.1, meson 1.12.1. The docs job (gyosu) was not run.

## Hardware context

I use these on an ASUS ROG Zephyrus G16 whose eDP panel declares HDR only through DisplayID 2.0
(Display Interface Features with RGB BT.2020/ST 2084 and Display Parameters with luminance and
chromaticities, no CTA HDR static metadata block). Mutter changes that consume them are being
prepared separately (GNOME/mutter#4847 is the same symptom family). The tests here use synthetic
fixtures only; I have not added a real EDID of that panel.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
