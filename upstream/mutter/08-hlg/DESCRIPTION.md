# clutter/color: Add the HLG transfer function

Adds `CLUTTER_TRANSFER_FUNCTION_HLG` following Rec. ITU-R BT.2100-2 (inverse OETF, black level
lift and OOTF in the state's own primaries, with the Table 5 system gamma for 400-2000 cd/m² and
the BT.2390 extended formula outside), CPU and GLSL implementations, CICP 18, and
`transfer_function.hlg` on the protocol (accepted and advertised; luminances whose black lift the
decoder cannot invert fail with `unsupported`). The tests compute their expected values from the
standard's formulas independently of the code under test, and check the shader against the CPU
path. I found no existing HLG work in Mutter.

## Inherited validation (2026-10-27)

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

- Warnings-as-errors build of every commit: 3/3 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip (19 invocations): `actor-color-state`, `color-hdr`, `color-pipeline`, `color-state-transform`, `monitor-color-tests`, `monitor-config-tests`, `edid`, `color-management`, `color-management-profile-conflict`, `native-hdr`, `wayland-color-management`, `wayland-color-representation`; separate `wayland-color-management` cases: `target-luminance-v1`, `target-luminance-v2`, `target-primaries-v1`, `target-primaries-v2`, `sdr-native-unusable-edid-primaries`, `custom-primaries-info-round-trip`, `icc-file-zero-descriptor`: 19/19 OK.
- `./check-style.py --dry-run` (allow-failure in CI): only suggestions from uncrustify re-indenting isolated chunks (parameter alignment of unchanged continuation lines, the closing parenthesis of `CLUTTER_TEST_SUITE`, a label), which contradict the surrounding upstream style; not applied.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.


The commands and results above are inherited from the handoff's original
branches. Preparation review subsequently fixed a luminance conversion in
unit 06 and its unit 09 caller; dependent branch identities therefore changed.
Fresh checks and exact source identities are recorded in
[Mutter preparation review](../PREPARATION-REVIEW.md). The earlier per-commit
and release results have not been repeated for every revised descendant.

## The series

Overview of the whole series, its hardware evidence and the coordination questions with !5068 and !5177: @SERIES_ISSUE@.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code).
