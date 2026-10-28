# monitor-manager: Forget the restore handle once the restore runs

Rejecting a persistent configuration schedules `restore_previous_config()` once at idle and keeps
its source ID in `restore_config_id`, but nothing cleared the ID when the source ran. The next
applied configuration, or disposing of the manager, then removed a source that no longer
existed, which is a critical warning. The ID is now cleared in the idle callback.

I found this with a D-Bus test that rejects a configuration and waits for the restore; that test
is part of a larger, not yet proposed change, so this MR has no new test.

## Inherited validation (2026-10-27)

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

- Warnings-as-errors build of every commit: 1/1 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip: unit, monitor-storage-tests, monitor-config-tests, monitor-dbus-tests: 4/4 OK.
- `./check-style.py --dry-run` (allow-failure in CI): no suggestions.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code).
