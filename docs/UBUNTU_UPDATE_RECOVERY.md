# Ubuntu update recovery — preserving the browser and video patches

**State: recovery in progress · November 20, 2026.** This document answers
why WebKit lost the patches and how the browser/GStreamer update path is
being corrected. [Current status](STATUS.md) separates current installation
from earlier qualification; [APT operations](UBUNTU_APT_REPOSITORY.md) covers
repository setup.

## What happened

APT recorded replacement of `libwebkitgtk-6.0-4` and
`libjavascriptcoregtk-6.0-1` from `2.52.6-1ubuntu1+rogdv7` to
`2.52.6-1ubuntu1.1` on November 18, 11:35:23–11:35:57 Eastern. The newer
packages came from Ubuntu's updates archive. Debian version ordering places
the `.1` distribution revision above the older revision with `+rogdv7`.

This was an update-policy coverage failure. The patched WebKit family was
installed from a local build. The scheduled rebuild/publish scripts covered
Mutter and libdisplay-info, not WebKit, GTK or GStreamer. At inspection the
project APT index offered no WebKit candidate, so its origin preference could
not preserve this family. Installed package versions alone were insufficient
protection against a newer Ubuntu candidate.

The transaction records a desktop-user UID and no command line. PackageKit
started immediately beforehand, but its transaction database contains no
rows. Unattended-upgrades reported no available upgrades earlier that morning.
These facts do not establish which frontend or person initiated the update.
No deliberate rollback is inferred.

[Sanitized package-level receipt](../evidence/ubuntu-webkit-replacement-20261120.json).

## Confirmed effect

GNOME Web resolves the installed stock WebKit shared library. Package-file
verification is clean for that stock version, and ELF inspection finds none
of the project's native display-target/frame-mapping entry points. This
confirms replacement of the implementation, rather than only a stale version
label. November 15 browser/image comparisons still establish what the former
patched build did; they do not qualify the stock replacement.

## Additional update drift found

The signed-source audit found two waiting GStreamer security revisions:
base `1.28.7-1ubuntu0.2` and good `1.28.7-1ubuntu0.1`. Ubuntu's changes add
channel limits and RTP depayloader bounds checks for CVE-2026-111183 and
video-metadata stride/offset validation, including overlap handling, for
CVE-2026-86476. Replaying the Dolby patches must preserve these changes.
The GTK sink and Showtime carry exact dependency pins, so those consumer
packages must move with the refreshed libraries. Their old qualified bundle
cannot simply be relabelled as the new release.

The rebased base/good source passed 17 focused Check cases in seven Meson
groups: 16 against actual packaged libraries/plugins and one source-linked
RTP capacity regression. A separate synthetic
API probe passed 24 assertions for metadata ownership and public decoder
configuration. Neither check decodes real media or qualifies browser playback.
[Focused native test receipt](../evidence/gstreamer-security-fastlane-20261120.json).

## Recovery and acceptance

The replacement must retain Ubuntu's current source changes and replay the
reviewed native-video and image-colour series. Restoring the older package
without the distribution update would not close this work.

The managed update design covers coherent binary families, including the
six WebKit/JavaScriptCore runtime, development and GIR packages. Publication
must verify family completeness and immutable package contents. Setup must
check candidate availability before changing holds or installing packages.
Package-scoped preferences must preserve patched candidates, including an
explicitly qualified unavailable-registry case. They also protect separately
qualified mpv, FFmpeg, Mesa, extension and NetworkManager releases without
forcing their mixed source versions into browser-family publication. Equal priority-999
pins preserve a newer installed patch generation; numerical
downgrades require a separate reviewed exact-version transaction. Signed Ubuntu source metadata
must expose drift from reviewed source pins and missing current-source
publication as actionable CI failures;
changed source is never accepted merely because the patch applies.

Required remaining evidence: authenticated source replay, normal warnings-enabled
compile/package build, final independent review and affected fast lane,
coherent APT install/rollback rehearsal, publication and mirror verification,
then installed-library and normal sandboxed browser/GStreamer checks. Preserve
the desktop session and stock recovery packages. Optical calibration and
panel cadence remain outside software-only acceptance.
