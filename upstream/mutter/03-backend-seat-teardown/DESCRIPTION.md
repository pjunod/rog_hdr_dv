# backend, seat/native: Release event sources and signal handlers on dispose

Two teardown fixes found while testing cancelled startup and colour manager shutdown:

- `backend`: `init_clutter()` attached the Clutter event source and dropped its reference, so the
  source outlived a disposed backend and could dispatch into it while the main context kept
  running. The backend now keeps the reference and destroys the source on dispose.
- `seat/native`: notifications already queued on the seat implementation, keymap or backend could
  reach a disposed native seat through its handlers. The seat now disconnects them before
  releasing any state.

Neither has a dedicated test in this MR; the test that showed them (a cancelled-startup case in
a colour lifecycle test) depends on test infrastructure that is not part of this MR.

## How it was tested

On lab5 (Ubuntu 26.10 container: GCC 15.3, meson 1.10.1, GLib 2.90, GTK 4.24.1, Mesa 26.2.4
llvmpipe), on `main` b48811767 with the stacked units below this one, against libdisplay-info
`main` plus its units 01-06 in a prefix (this unit does not use libdisplay-info):

```
PKG_CONFIG_PATH=<prefix>/lib/x86_64-linux-gnu/pkgconfig meson setup b -Dremote_desktop=true -Dwerror=true
git checkout <each commit>; ninja -C b        # every commit, oldest first
meson setup b-rel -Dremote_desktop=true -Dwerror=true -Dbuildtype=release; ninja -C b-rel   # tip
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe META_DBUS_RUNNER_DISABLE_LOGIND_PASSTHROUGH=1 \
  meson test -C b --setup mutter:default --no-rebuild --num-processes 4 --timeout-multiplier 3 <tests>
```

- Warnings-as-errors build of every commit: 2/2 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip: unit, stage-views, monitor-config-tests, color-management: 4/4 OK.
- `./check-style.py --dry-run` (allow-failure in CI): no suggestions.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
