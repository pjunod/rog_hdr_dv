# Operations — inspect the laptop and preserve recovery

Use [status](STATUS.md) to understand the current installation and
[hardware](HARDWARE.md) to identify the panel. This repository does not contain
an automatic installer. The current HDR installation predates repository
creation and was not changed during the migration.

## 1. Read the live state

Run these on the laptop, as the logged-in desktop user where applicable:

```bash
uname -r                            # Identify the running kernel.
mokutil --sb-state                  # Verify Secure Boot state.
dpkg-query -W libdisplay-info3:amd64 libdisplay-info3:i386 libmutter-51-0 mutter-common
colormgr get-devices                # Inspect assigned display profiles.
colormgr get-sensors                # Discover currently attached sensors.
gsettings get org.gnome.settings-daemon.plugins.color night-light-enabled
```

The expected baseline is recorded in [status](STATUS.md), not hard-coded in
an activation script. An assigned profile does not prove its full transform
is used by every app or HDR compositor path. No attached sensor means this
inspection cannot make a fresh physical calibration measurement.

For the desktop user's display configuration:

```bash
gdbus call --session --dest org.gnome.Mutter.DisplayConfig \
  --object-path /org/gnome/Mutter/DisplayConfig \
  --method org.gnome.Mutter.DisplayConfig.GetCurrentState
```

Inspect active connector, mode and colour mode together. SSH sessions may
need the actual desktop user's session-bus environment; do not assume UID
1000 on another machine. Keep captures in `private/` or user-local state.

## 2. Protect the working installation

The laptop retains `~/native-hdr-test-2026-10-08/RECOVERY.txt` and its staged
bundle from the coordinated morning installation. Read that exact local
procedure and reverify its package/image hashes before using it. Historical
workstation procedures are in the previous HDR workspace; see
[provenance](PROVENANCE.md). Neither file location proves the artifacts are
still present or compatible after later upgrades.

Keep a bootable stock kernel, matching recovery userspace, sufficient `/boot`
space and a local way to use the boot menu. The test kernel was the persistent
GRUB default at the last morning receipt; inspect it before assuming rollback
will happen automatically.

Treat libdisplay-info and Mutter as a coordinated pair because the compositor
uses additive private APIs. Preserve Secure Boot. Kernel image signing and
NVIDIA module signing are separate checks; the original module-only trust
configuration did not automatically authorize the test image.

## 3. Run a bounded physical test

Capture settings before changing one variable. Use reproducible patches and
media, verify the colour description reaching the compositor, and record
brightness, refresh/VRR, power state and window/fullscreen state. Test SDR/HDR
transitions, screen blanking and resume separately from first playback.

For Dolby Vision, retain profile, content-mapping version, RPU/layer presence,
decoder, processor, actual output encoding and reference comparison. A Dolby
badge, successful P5 reshape or PQ output alone is insufficient.

Use the staged [quality acceptance criteria](DOLBY_VISION_AND_QUALITY.md#5-work-in-stages-with-observable-acceptance)
for calibration. Do not assign the recovered OEM CMDEF file globally until
its expected display mode and the Linux transform path are understood.

## 4. Prepared userspace package transaction

The [native package receipt](../evidence/baseline-native-packages.json) covers
the qualified hdr7 library and nativehdr3 compositor source. Both library
architectures and the compositor packages built in an isolated Ubuntu 26.10
environment with authenticated dependencies and tests disabled deliberately.
This is packaging evidence; it does not qualify active scanout or the later
gamut implementation. No package from this build is installed on the laptop.

The minimal runtime transaction has six packages: `libdisplay-info3:amd64`,
`libdisplay-info3:i386`, `libmutter-51-0`, `gir1.2-mutter-51`, `mutter-common`
and `mutter-common-bin`. The two library architectures require the same
version, and GIR requires the exact matching Mutter library. The current
GNOME Shell satisfies the candidate package compatibility bounds. APT
simulation reports six upgrades, zero additions and zero removals.

A private copy of the installed package database, with only those six candidate
control records substituted, also resolves the six saved recovery packages as
six downgrades without additions or removals. This is a modeled rollback, not
an executed recovery. Artifact hashes and exact local commands are retained
with the private delivery proposal. Reverify them against the final source and
current installed state before the coordinated maintenance window.

Log out of the Wayland GNOME session before replacement and start a fresh
session to load the new compositor library. Retain an independent text-console
or SSH recovery route; do not terminate the desktop automatically. The final
transaction must include the reviewed gamut implementation rather than
installing this intermediate baseline and immediately replacing it again.
