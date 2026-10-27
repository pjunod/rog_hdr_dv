# clutter/stage-view: Reuse compatible offscreen buffers on state changes

Every colour state change of a stage view dropped its offscreen framebuffer and allocated a new
one, even when the new state needs a buffer of the same size and format. Uniform-only changes (a
reference luminance step, a Night Light temperature step) therefore reallocated an fp16 buffer
on every step. This keeps the current offscreen when its size is unchanged and its format is one
of the acceptable formats for the new state (all candidates are checked, since allocation may
have used a fallback format). The output pipeline is still invalidated and a full redraw still
requested on every change, and the offscreen is still released when direct painting becomes
possible again.

The second commit adds `/stage-views/offscreen-color-state-reuse`, which holds strong references
to the buffers (so allocator address reuse cannot fake identity) and checks coalesced
intermediate states, an incompatible format change, a 10-step reference luminance ramp and the
removal of the conversion.

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
- Tests on the tip: the whole suite (294 tests): 288 OK, 5 expected failures (the known cogl `*known-failure*`/`*should-fail*` cases), 0 failures, 1 timeout: `input-capture` timed out at 180 s under the parallel full run; rerun alone on this tip it passed in 3.2 s, and it also passes alone on unmodified `main`.
- `./check-style.py --dry-run` (allow-failure in CI): no suggestions.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
