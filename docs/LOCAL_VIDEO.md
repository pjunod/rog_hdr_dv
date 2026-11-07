# Local video — open files with the packaged HDR player

Companion to [software delivery](SOFTWARE_DELIVERY.md): this guide adds
**ROG HDR Video** to a Linux file manager's **Open With** menu. It uses the
installed plurx Player media engine directly, outside the Plurx web app.
The [desktop entry](../tools/local_video/rog-hdr-video.desktop) is a
per-user application choice; installation leaves your default applications
unchanged.

## The installed player supplies Dolby Vision mapping

You need the plurx Player package and its executable at
`/usr/lib/plurx-player/bin/mpv`. That packaged mpv contains the closed-form
Dolby Vision mapping and uses the patched libplacebo delivered with it. An
ordinary distribution mpv is not a substitute for this dependency. The entry
names the exact executable in both `Exec` and `TryExec`; it never searches
`PATH` or silently falls back to another mpv. If the executable is missing,
a desktop may hide the entry or report that it cannot launch it.

This is an application playback route, not a system-wide Dolby Vision
switch. It does not add mapping to other players. Display-stack requirements
and the retained playback acceptance limits remain those in
[software delivery](SOFTWARE_DELIVERY.md). Installing a menu entry supplies
no new playback or optical evidence and makes no panel calibration claim.

## Install the menu entry for your user

Run these commands from the repository root on the Linux desktop where
plurx Player is already installed:

```bash
# Install only when the packaged player exists and is executable.
test -x /usr/lib/plurx-player/bin/mpv && \
    install -Dm644 tools/local_video/rog-hdr-video.desktop \
    "${XDG_DATA_HOME:-$HOME/.local/share}/applications/rog-hdr-video.desktop"
# Refresh the per-user MIME cache when the desktop utility is available.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${XDG_DATA_HOME:-$HOME/.local/share}/applications"
fi
```

If the first command fails, install the required player before continuing.
The install command creates the application directory if needed. It copies
one desktop file and requires no administrator privileges. If the menu does
not refresh immediately, reopen the file manager or log in again.

## Choose Open With for a local file

In your file manager, right-click a local video, choose **Open With** (or
**Open With Other Application**), then select **ROG HDR Video**. Leave any
"always use" or "set as default" option unchecked to preserve your existing
choice. The entry advertises MP4, Matroska, WebM, QuickTime, AVI, MPEG,
MPEG transport stream and Ogg video; decoder support still depends on the
packaged player and the file.

The file manager passes one local filename through the desktop entry's
`%f` field. There is no shell wrapper: spaces and shell metacharacters remain
part of the filename. The `--` separator ends mpv option parsing before the
filename. The entry registers no URL scheme and does not handle Plurx links.

The launch uses `--no-config` for consistent player options,
`--vo=gpu-next --gpu-api=vulkan` for the intended renderer,
`--hwdec=auto-safe` for automatic supported decoding,
`--target-colorspace-hint=yes` for target colour information, and `--ytdl=no`
for local-file playback without a downloader integration. It adds no forced
panel peak, colour profile or display override. Playback support and visual
acceptance must be assessed on the actual file and display; selecting this
entry alone does not establish full Dolby Vision fidelity.

## Remove the menu entry

```bash
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/rog-hdr-video.desktop"
# Refresh the MIME cache after removing the application choice.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${XDG_DATA_HOME:-$HOME/.local/share}/applications"
fi
```

This removes the per-user menu choice. It leaves the installed player,
its package configuration and your existing default choices in place.
