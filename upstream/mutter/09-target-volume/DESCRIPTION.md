# color: Target colour volume, mastering metadata and light levels

Gives parametric colour states a target colour volume (mastering primaries and luminance, MaxCLL,
MaxFALL) held privately in `ClutterColorStateParams`, and accepts the four corresponding creator
requests with the protocol's validation (`already_set`, `invalid_luminance`, v1-only light level
checks), advertising `set_mastering_display_primaries` and `extended_target_volume`. The target
volume takes part in identity, but two states that differ only in it need no conversion, so
direct scanout is unaffected. Nothing renders it yet. Luminance serialization uses the saturating conversion
from unit 06, including accepted protocol maxima near `UINT32_MAX`.

**Overlap**: !5068 also completes these requests; see the design-discussion issue (@SERIES_ISSUE@).

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
- `./check-style.py --dry-run` (allow-failure in CI): no suggestions.

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
