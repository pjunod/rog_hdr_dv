# color: Apply Night Light in linear light in BT.2100

**Hold: needs design discussion; collides with !5177**, which moves Night Light into linear space
as part of its colour management rework. Prepared for reference and review input only.

In BT.2100 the CRTC gamma LUT holds PQ code values, so scaling it for Night Light removes far more
light than intended and skews hue ([#3687](https://gitlab.gnome.org/GNOME/mutter/-/issues/3687)). This adapts the output's white in linear light in the
rendering colour state instead (diagonal von Kries factors anchored at the default temperature's
Planckian white, never brightening a channel), refuses direct scanout and the cursor plane while
it applies, and keeps captures unadapted. It is stacked on unit 02 (offscreen reuse) as well,
since its last commit checks buffer reuse across a Night Light ramp.

Not yet checked visually on hardware.

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

- Warnings-as-errors build of every commit (the 13 commits of this branch, including the 2 of the units it is stacked on): 13/13 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip (27 invocations): `actor-color-state`, `color-hdr`, `color-pipeline`, `color-state-transform`, `monitor-color-tests`, `monitor-config-tests`, `edid`, `color-management`, `color-management-profile-conflict`, `native-hdr`, `wayland-color-management`, `wayland-color-representation`, `stage-views`; separate `wayland-color-management` cases: `target-luminance-v1`, `target-luminance-v2`, `target-primaries-v1`, `target-primaries-v2`, `sdr-native-unusable-edid-primaries`, `custom-primaries-info-round-trip`, `icc-file-zero-descriptor`, `mapping-blending-target`, `mapping-target-gamut`, `published-reference-factor`, `display-targets-cta`, `display-targets-sdr-native`, `night-light-bt2100-scanout`, `night-light-bt2100-capture`: 27/27 OK.
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
