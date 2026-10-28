# displayid2: parse Display Interface Features data block

This decodes the DisplayID 2.0 Display Interface Features data block (tag 0x26, section 4.5) into a
low-level API owned by the parsed DisplayID: per-encoding bit-depth masks, the minimum 4:2:0 pixel
rate, audio sample-rate flags, the standard colour space/EOTF combinations and the additional
combinations (`di_displayid2_data_block_get_interface_features()`). The fixed payload and the
declared number of additional combinations are checked before any field is read; reserved
encodings are diagnosed, known fields are kept, and reserved additional combinations are kept
verbatim without being reported as capabilities. `di-edid-decode` prints the block in edid-decode's
format (the `asus-ux3405` diff shrinks). It adds a synthetic fixture and direct C tests.

### Relation to !210

!210 (Sean Paul, open, needs a rebase) parses the same block and also feeds it into
`di_info_get_hdr_static_metadata()` and `di_info_get_supported_signal_colorimetry()`. I am not
trying to route around it; I would like this to be read as review input on !210 or as an
alternative, whichever the maintainers prefer:

- Scope: this MR is low-level only and does not change the high-level getters. Mutter's use of
  the block (an RGB BT.2020/ST 2084 combination on eDP panels without a CTA HDR static metadata
  block) needs the exact tuple, and a high-level fallback that turns the block into
  `hdr_static_metadata` without luminance data is a policy decision I would rather leave to
  !210's discussion.
- Representation: !210 exposes the combinations as one list of (colour space, EOTF) pairs; this
  MR keeps the standard-combination bitmask and the additional pairs separate, keeps reserved
  values instead of dropping them, and validates the declared pair count against the block size.
- Bit depths: !210 uses signed `int32_t` masks; this MR uses `uint8_t` masks with separate enums for
  4:4:4 and 4:2:x, since their bit assignments differ (6 bpc exists only for 4:4:4).
- Tests: this MR adds a fixture with `.edid`/`.diff`/`.ref`/`.print` files plus a C test for malformed blocks.

If !210 is the preferred base, I am happy to rebase the rest of my series (units 03 to 06) on top
of it and contribute the malformed-block tests there instead. Units 05 and 06 only need the data
block plumbing, not this particular API.

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

Result for this commit: Ok: 73 in each of the three build configurations, 0 failures, and
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
