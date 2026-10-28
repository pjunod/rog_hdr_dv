# backends/color: Colour device, colord and store lifecycle robustness

**Hold: obsoleted if !5177 lands**, since it removes the colord / `MetaColor*` code these commits
fix. Prepared for reference.

Fixes for colour devices and the colour store when monitors are unplugged, moved or the colour
manager is disposed while asynchronous work (colord device and profile creation, profile
generation, ICC store reads) is in flight, with tests. The lifecycle tests use a test-only hook at
the asynchronous callback boundaries (`meta-color-lifecycle-test-private.h`, compiled only with
tests enabled); I could not find an existing Mutter facility to park and replay a GIO
asynchronous delivery, and I expect this seam to need discussion. Stacked on unit 03.

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
- Tests on the tip (37 invocations): `actor-color-state`, `color-pipeline`, `color-state-transform`, `monitor-color-tests`, `monitor-config-tests`, `edid`, `color-management`, `color-management-profile-conflict`, `native-hdr`, `wayland-color-management`, `wayland-color-representation`, `color-lifecycle`; separate `wayland-color-management` cases: `target-luminance-v1`, `target-luminance-v2`, `target-primaries-v1`, `target-primaries-v2`, `sdr-native-unusable-edid-primaries`; separate `color-lifecycle` cases: all 20: 37/37 OK.
- `./check-style.py --dry-run` (allow-failure in CI): suggestions not yet reviewed in detail (some are real alignment slips in the new code); to be addressed when this unit is taken up again.

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
