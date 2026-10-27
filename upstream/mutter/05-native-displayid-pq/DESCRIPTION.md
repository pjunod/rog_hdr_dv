# backends/native: Support native DisplayID RGB BT.2020 PQ on eDP

Some eDP panels declare HDR only through a DisplayID 2.0 Display Interface Features data block
that lists RGB BT.2020 with SMPTE ST 2084, without a CTA-861 HDR static metadata block, so Mutter
never offers BT.2100 on them. This records that capability separately from the CTA-derived
fields and maps it to native PQ only on eDP connectors with colour mode support, an HDR output
metadata property and BT.2020 colourspace support. CTA declarations stay authoritative where they
exist, known extension parsing failures disable it, and no static metadata or luminance is
invented. Synthetic EDID tests cover the decision table.

**Blocked on libdisplay-info**: it needs `di_displayid2_data_block_get_interface_features()`,
`di_displayid2_data_block_get_cta_data_blocks()` with the nested-header checks and
`di_edid_has_extension_failures()` (libdisplay-info units 02-04, the first overlapping
libdisplay-info!210), checked with a `cc.links()` probe in meson.build, so CI cannot pass until a
libdisplay-info release has them.

Hardware: on the ASUS ROG Zephyrus G16 (GU605MZ, Samsung ATNA60DL01-0 OLED eDP, Intel Meteor Lake): its EDID declares HDR only in DisplayID 2.0 (Display Interface Features RGB BT.2020/ST 2084; Display Parameters 400 cd/m² full, 616 cd/m² 10% window, native primaries), no CTA HDR block. it makes `bt2100` available (tested on a Mutter 51 build of the same
change). Related: [#4847](https://gitlab.gnome.org/GNOME/mutter/-/issues/4847) and the closed #5093 describe the same symptom on other laptops; whether
it fixes those depends on what their DisplayID blocks contain.

## How it was tested

On lab5 (Ubuntu 26.10 container: GCC 15.3, meson 1.10.1, GLib 2.90, GTK 4.24.1, Mesa 26.2.4
llvmpipe), on `main` b48811767 with the stacked units below this one, against libdisplay-info
`main` plus the libdisplay-info units 01-06 installed in a prefix:

```
PKG_CONFIG_PATH=<prefix>/lib/x86_64-linux-gnu/pkgconfig meson setup b -Dremote_desktop=true -Dwerror=true
git checkout <each commit>; ninja -C b        # every commit, oldest first
meson setup b-rel -Dremote_desktop=true -Dwerror=true -Dbuildtype=release; ninja -C b-rel   # tip
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe META_DBUS_RUNNER_DISABLE_LOGIND_PASSTHROUGH=1 \
  meson test -C b --setup mutter:default --no-rebuild --num-processes 4 --timeout-multiplier 3 <tests>
```

- Warnings-as-errors build of every commit: 1/1 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip: edid, native-hdr, monitor-color-tests, monitor-config-tests, color-management: 5/5 OK.
- `./check-style.py --dry-run` (allow-failure in CI): no suggestions.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## The series

Overview of the whole series, its hardware evidence and the coordination questions with !5068 and !5177: @SERIES_ISSUE@.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
