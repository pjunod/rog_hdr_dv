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
still present or compatible after later upgrades. That note names the stock
kernel `7.3.0-8-generic`, which has since been removed; the installed stock
fallback is `7.3.0-9-generic` (check with `dpkg-query -W 'linux-image*'`).
The temporary visible-menu GRUB setting it describes is still in place.

Keep a bootable stock kernel, matching recovery userspace, sufficient `/boot`
space and a local way to use the boot menu. The test kernel was the persistent
GRUB default at the last morning receipt; inspect it before assuming rollback
will happen automatically.

Treat libdisplay-info and Mutter as a coordinated pair because the compositor
uses additive private APIs. Preserve Secure Boot. Kernel image signing and
NVIDIA module signing are separate checks; the original module-only trust
configuration did not automatically authorize the test image.

For a future rollback from nativehdr10, preserve a compatible pre-override
`monitors.xml` before the coordinated deployment window. Older compositors
reject the new `<targetpeakluminance>`, `<targetminluminance>` and
`<hdrgamutsource>` children under `<monitor>`; they do not safely ignore them.
Prepare a compatible recovery configuration (or deliberately remove those
fields from a recovery copy), alongside the matching recovery packages.
Unset fields are omitted by the new writer, but that does not make a saved
override compatible with the old parser. No live configuration is changed
by this source stage.

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

The [current package receipt](../evidence/hdr9-nativehdr8-packages.json)
covers the hdr9 library (the reviewed hdr8 code with packaging fixes) and the
`nativehdr8` compositor, which contains every earlier compositor batch and
the independent-review fixes. Both library architectures (i386 cross-built)
and the compositor packages were built from the exact recorded source trees
in a disposable Ubuntu 26.10 environment, with tests disabled deliberately.
This is packaging evidence; it does not qualify active scanout. These
packages were installed and held on 2026-10-11
([receipt](../evidence/install-2026-10-11.json)). Earlier receipts and builds were superseded
before installation.

The minimal runtime transaction has six packages: `libdisplay-info3:amd64`,
`libdisplay-info3:i386`, `libmutter-51-0`, `gir1.2-mutter-51`, `mutter-common`
and `mutter-common-bin`. The two library architectures require the same
version, and GIR requires the exact matching Mutter library. The compositor
depends on `libdisplay-info3-native-hdr-api (>= 2)`, which only the private
library provides, so an archive library update cannot satisfy it. A
simulated newer archive library (above the version floor, without the
virtual package) could only be installed by removing the compositor library
and the desktop, which a routine upgrade does not do.
On the laptop, APT simulation reported six upgrades, zero additions and zero
removals, and the real transaction matched.

A private copy of the installed package database, with only those six
candidate control records substituted, resolves the six previously installed
hdr6/nativehdr2 packages as six downgrades without additions or removals.
This is a modeled rollback, not an executed one. The packages, their hashes
and step-by-step install and recovery notes are staged privately on the
laptop. The install notes check both package sets' hashes, save the package
state, and hold the six packages; the recovery notes unhold them first.

Log out of GNOME before replacement, then restart the display manager so a new
GNOME Shell loads the new library. Retain an independent recovery route; SSH
is the practical one, because a failing login screen keeps reclaiming the
console. Do not terminate the desktop automatically.
