# backends/monitor: Per-monitor display target overrides

**Hold: needs design discussion; collides with !5177**, which adds colour configuration to the
display config. Prepared for reference and review input only.

Adds a per-monitor target override (peak, black level, BT.2100 gamut source) stored in
`monitors.xml`, exposed and set through `org.gnome.Mutter.DisplayConfig`, supported by gdctl, and
selected by the colour device as a "user-declared" target ahead of the firmware sources. New D-Bus
API and a new `monitors.xml` element, so it needs an agreed design first. It is stacked on unit 04
(restore handle fix).

Not yet checked visually on hardware.

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

- Warnings-as-errors build of every commit (the 8 commits of this branch, including the 1 of the units it is stacked on): 8/8 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip (31 invocations): `actor-color-state`, `color-hdr`, `color-pipeline`, `color-state-transform`, `monitor-color-tests`, `monitor-config-tests`, `edid`, `color-management`, `color-management-profile-conflict`, `native-hdr`, `wayland-color-management`, `wayland-color-representation`, `unit`, `monitor-storage-tests`, `monitor-dbus-tests`, `monitor-gdctl`; separate `wayland-color-management` cases: `target-luminance-v1`, `target-luminance-v2`, `target-primaries-v1`, `target-primaries-v2`, `sdr-native-unusable-edid-primaries`, `custom-primaries-info-round-trip`, `icc-file-zero-descriptor`, `mapping-blending-target`, `mapping-target-gamut`, `published-reference-factor`, `display-targets-cta`, `display-targets-sdr-native`, `display-targets-user-override`, `night-light-bt2100-scanout`, `night-light-bt2100-capture`: 31/31 OK.
- `./check-style.py --dry-run` (allow-failure in CI): suggestions not yet reviewed in detail (some are real alignment slips in the new code); to be addressed when this unit is taken up again.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## The series

Overview of the whole series, its hardware evidence and the coordination questions with !5068 and !5177: @SERIES_ISSUE@.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
