# wayland/color-management: Protocol input robustness

Fixes for client input to `wp_color_manager_v1`, each with tests:

- signed custom primaries were wrapped through `uint32_t` and clamped to [0, 1]; they are now
  parsed as signed, limited to ±16 (the range that survives single precision exactly), and
  unusable colorimetry fails the description with the `unsupported` cause;
- ICC files: descriptor 0 counted as unset, `offset + length` could wrap in 32 bits, and every
  failure was reported as `operating_system`; profile content that cannot be used now fails as
  `unsupported`;
- `meta_read_bytes()` read relative to the shared file position and accepted short reads; it now
  uses `pread()` at the absolute offset and fails on short reads;
- `set_mastering_display_primaries`/`set_mastering_luminance` posted the colour manager's
  `unsupported_feature` code (0, which on the creator means `incomplete_set`) instead of the
  creator's own code (2).

**Overlap**: !4604 clamps custom primaries to [0, 1], the opposite of the first commit; the
issue asks which behaviour is wanted. !5313 (merged) changed the lifetimes of the same ICC
objects; this is rebased on it. These are bug fixes against current main in substance, but
textually the series is stacked on the native target MR (unit 06); I can rebase them onto main
separately if you would rather take them first.

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

- Warnings-as-errors build of every commit: 7/7 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip (18 invocations): `actor-color-state`, `color-pipeline`, `color-state-transform`, `monitor-color-tests`, `monitor-config-tests`, `edid`, `color-management`, `color-management-profile-conflict`, `native-hdr`, `wayland-color-management`, `wayland-color-representation`; separate `wayland-color-management` cases: `target-luminance-v1`, `target-luminance-v2`, `target-primaries-v1`, `target-primaries-v2`, `sdr-native-unusable-edid-primaries`, `custom-primaries-info-round-trip`, `icc-file-zero-descriptor`: 18/18 OK.
- `./check-style.py --dry-run` (allow-failure in CI): no suggestions.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## The series

Overview of the whole series, its hardware evidence and the coordination questions with !5068 and !5177: @SERIES_ISSUE@.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
