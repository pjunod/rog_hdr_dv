# color: Map highlights toward the output's declared target luminance

Adds the Report ITU-R BT.2390 EETF (highlight compression only, on max(R, G, B) so hue ratios are
kept) and applies it in the surface-to-blending conversion when the source's effective peak
exceeds the output's declared target peak. One predicate decides it, used by the renderer, direct
scanout and the hardware cursor plane, so they cannot disagree; the transform cache is keyed by
exact identity so near-equal states cannot share a mapped transform. The colour device builds the
rendering colour state from the declared target, and the published reference white is rounded so
a client copying the published values is not mapped.

**Overlap**: !5068 tone-maps toward display capabilities; see the design-discussion issue (@SERIES_ISSUE@).

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

- Warnings-as-errors build of every commit: 4/4 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip (20 invocations): `actor-color-state`, `color-hdr`, `color-pipeline`, `color-state-transform`, `monitor-color-tests`, `monitor-config-tests`, `edid`, `color-management`, `color-management-profile-conflict`, `native-hdr`, `wayland-color-management`, `wayland-color-representation`; separate `wayland-color-management` cases: `target-luminance-v1`, `target-luminance-v2`, `target-primaries-v1`, `target-primaries-v2`, `sdr-native-unusable-edid-primaries`, `custom-primaries-info-round-trip`, `icc-file-zero-descriptor`, `mapping-blending-target`: 20/20 OK.
- `./check-style.py --dry-run` (allow-failure in CI): only suggestions from uncrustify re-indenting isolated chunks (parameter alignment of unchanged continuation lines, the closing parenthesis of `CLUTTER_TEST_SUITE`, a label), which contradict the surrounding upstream style; not applied.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## The series

Overview of the whole series, its hardware evidence and the coordination questions with !5068 and !5177: @SERIES_ISSUE@.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
