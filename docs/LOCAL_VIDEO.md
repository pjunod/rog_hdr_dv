# Local video — open files with the packaged HDR player

Companion to [software delivery](SOFTWARE_DELIVERY.md): this guide adds
**ROG HDR Video** as an installed application available through a Linux file
manager's **Open With → Other/All Applications** chooser. It uses the
installed plurx Player media engine directly, outside the Plurx web app.
The [desktop entry](../tools/local_video/rog-hdr-video.desktop) is a
per-user application choice. It declares no MIME types, so it does not request
video associations or default selection. The corrected entry passed the bounded real-target validation below.

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
**Open With Other Application**), then open **Other/All Applications** and select **ROG HDR Video**. The exact
chooser labels depend on the desktop. Leave any
"always use" or "set as default" option unchecked to preserve your existing
choice. The entry deliberately omits `MimeType`: it is an installed application
that accepts files through `%f`, rather than a registered recommended handler
for video types. Decoder support depends on the packaged player and the file.

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

## Target trial and remaining validation

The first real GNOME installation declared eight video MIME types. After the
per-user MIME cache refresh, all eight types that had previously resolved to
stock mpv through implicit defaults instead resolved to this per-user entry.
No explicit default assignment was needed for that change. The trial entry was
removed immediately; recovery material was retained.

The corrected entry removes the MIME declaration while retaining `%f` and its
visible application categories. No `mimeapps.list` edits or explicit default
pinning are part of this route. The corrected entry subsequently passed the target validation below. The failed
trial itself supplies no playback acceptance.

## November 7 corrected-entry target acceptance

The final desktop entry (SHA256
`0cf10770a381943f56ee1e103356d14005cbcd2f4a6e0265f7f3d63928d9e845`)
was installed and passed `desktop-file-validate`. GIO reported it installed,
visible, supporting files and present in All Applications. All eight previously
implicit video defaults remained `mpv.desktop`. A local filename containing
spaces reached the player as one operand.

A three-second silent Profile 5 fixture containing RPU reached EOF with exit 0,
using gpu-next P010 and the packaged GPU closed-form CM v2.9/L2 interpolated,
P3-D65 mapper. Logs also contained an initial unknown-size swapchain resize
and a brief `none (no Dolby Vision RPU)` mapper state; active-mapping evidence
applies only to frames reporting that mapping. The first remux lacked Dolby
Vision configuration and needed correction. GIO child inspection spans a
helper → mpv transition; complementary captures bind the actual filename
argument and packaged executable rather than assuming a single process snapshot.

The mapper reports brightness-relative 880.6 nits at reference white 142;
DisplayConfig declares effective 616 cd/m². The rendering convention reconciles
these as `616 × 203 / 142 ≈ 880.6`. Firmware-declared target, renderer convention
and optical measurements are distinct; no optical measurement or general-title
acceptance is claimed. This is a bounded, tested local-file Open With route,
not support in other applications. The separate animation correction is not
installed: the current on-device `nativehdr2` runtime errors remain open.

## Remove the menu entry

```bash
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/rog-hdr-video.desktop"
# Refresh the MIME cache after removing the application choice.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${XDG_DATA_HOME:-$HOME/.local/share}/applications"
fi
```

This removes the per-user menu choice. It leaves the installed player,
its package configuration in place. Refresh the cache after removal as shown
above; the corrected route passed the bounded target validation recorded above.
