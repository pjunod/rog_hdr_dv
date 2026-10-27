# backends/color: Take display targets from CTA-861 and base EDID declarations

Extends the target sources beyond DisplayID: the CTA-861 HDR static metadata desired content
range becomes the target luminance of any BT.2100 output that declares it (most external HDR
monitors and many laptops), and in the native SDR mode the base EDID colour characteristics
become the target gamut, so wider content is compressed into the panel's gamut instead of being
clipped. Each target records its provenance, shown in the colour debug output.

Hardware: the Lenovo ThinkPad X1 Extreme gen 1 (AUO B156ZAN03.2 eDP, Intel UHD 630): an SDR panel with a base EDID only. In `sdr-native` mode the base EDID gamut is published there as both the
encoding and the target primaries (Mutter 51 build of the same change). Related: [#5001](https://gitlab.gnome.org/GNOME/mutter/-/issues/5001).

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

- Warnings-as-errors build of every commit: 5/5 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip (24 invocations): `actor-color-state`, `color-hdr`, `color-pipeline`, `color-state-transform`, `monitor-color-tests`, `monitor-config-tests`, `edid`, `color-management`, `color-management-profile-conflict`, `native-hdr`, `wayland-color-management`, `wayland-color-representation`; separate `wayland-color-management` cases: `target-luminance-v1`, `target-luminance-v2`, `target-primaries-v1`, `target-primaries-v2`, `sdr-native-unusable-edid-primaries`, `custom-primaries-info-round-trip`, `icc-file-zero-descriptor`, `mapping-blending-target`, `mapping-target-gamut`, `published-reference-factor`, `display-targets-cta`, `display-targets-sdr-native`: 24/24 OK.
- `./check-style.py --dry-run` (allow-failure in CI): no suggestions.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## The series

Overview of the whole series, its hardware evidence and the coordination questions with !5068 and !5177: @SERIES_ISSUE@.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
