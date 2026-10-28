# frames: Use the GTK interface color scheme property

`mutter-x11-frames` sets `GtkSettings:gtk-application-prefer-dark-theme`, which GTK 4.20 deprecated
in favour of `GtkSettings:gtk-interface-color-scheme`. This sets the new property from the desktop
colour scheme with the same mapping as before (dark when the desktop prefers dark, light
otherwise).

The enum and property only exist since GTK 4.20, so the GTK 4 requirement goes from 4.14 to 4.20.
That is the one thing to decide here: the alternative is a `GTK_CHECK_VERSION (4, 19, 0)` branch
that keeps 4.14 as the minimum, which I can switch to if you prefer not to raise the requirement
yet. GTK 4.20 shipped with GNOME 49, and the distributions that will carry this Mutter already
have it.

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
- Tests on the tip: none run; no test covers `src/frames`; build only.
- `./check-style.py --dry-run` (allow-failure in CI): no suggestions.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code).
