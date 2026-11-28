# Ubuntu update recovery — preserving the browser and video patches

**State: v9 colour/subtitle correction installed; runtime acceptance in progress · November 20, 2026.** This document answers
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

At the initial November 20 inspection, GNOME Web resolved the installed stock WebKit shared library. Package-file
verification is clean for that stock version, and ELF inspection finds none
of the project's native display-target/frame-mapping entry points. This
confirms replacement of the implementation, rather than only a stale version
label. November 15 browser/image comparisons still establish what the former
patched build did; they do not qualify the stock replacement.

## Ordinary-video colour correction after restoration

The v8 recovery exposed two independent ordinary-YUV source defects. Matrix
selection compared the complete colourimetry tuple, so known matrix metadata
could be discarded when primaries or transfer were unspecified. The DMA path
also omitted range, while its conversion always used limited-range coefficients.
Applying that conversion to full-range samples shifts black and white levels.

The reviewed v9 candidate retains independent matrix, range and transfer fields
and uses the actual R8 or P010-in-R16 sample representation. Each video wrapper
passes an immutable colour description to a cached layer for that draw, so
recycled buffers do not leak one view's metadata into another. Unknown producer
layouts retain their prior fallback; no global shader clamp hides the defect.
The focused compiler/test loop also found insufficient YUV sampler/matrix
precision. The candidate uses the existing supported high-precision qualifier
only for YUV conversion; RGB/default precision and natural fallback stay as
before. Twenty-four of the initial twenty-five native cases passed. The precision
correction then passed the failed P010 case and affected NV12 case with
unchanged assertions: 23 retained plus two current passes qualify all 25.
The actual context is OpenGL ES 3.2 Mesa; a naturally ES2-only provider remains
uncovered. The normal six-package build passed and the two runtimes are installed.
All ten refreshed installed-browser core cases now qualify: seven retained
initial passes plus three corrected analyses, with no recapture. The corrections
use the declared CSS reference shape and source-only exact-frame spatial
references; the native/control discriminator keeps its original region and
minimum difference. The broader transition cohort remains separate.
[Bounded core qualification](../evidence/ubuntu-browser-core-20261120.json).

The ordinary paused-subtitle check also reproduced a separate GstPlay defect:
changing selection while paused did not present a new frame. The correction
uses the existing coalesced seek machinery after accepted stream selection,
with source/stop/error cancellation and explicit-seek precedence. A public
synthetic caption fixture fails against the old installed library and passes
against the correction: disable, re-enable, alternate track, exact restoration
and an overriding explicit seek. No compensating test seek follows a toggle.
The normal bad-family v10 build passed; only GstPlay differs among 178 packaged
runtime ELFs. The other 177 retain identical allocated code/data sections.
This is API/package qualification; three normal Showtime active/disabled/restored captures now demonstrate
caption removal and exact restoration at the same paused mapped-video frame.
The first combined caption/target acceptance attempt (November 20, after the
last recorded checkpoint) failed, and was reconciled on November 26 from its
retained captures without a rerun. Two causes are distinct. First, 223 of 2,701
glyph-core pixels fall up to 27 RGB10 codes below the derived white bound in
every active state. All 223 lie on the core's outer edge and none is too bright.
The caption glyphs use subpixel antialiasing, and the mask chose core texels by
alpha alone, which admits edge texels whose dimmest colour channel is below
white. An earlier reading blamed the 1.5x downscale footprint; that reading is
superseded ([corrections](RUNTIME_ACCEPTANCE_CORRECTIONS.md#1-caption-mask-v2)).
Second, only the first
active picture differs, by one code in about 0.9% of viewport pixels, from every
later presentation of the same frame. The target, mapped-video samples and
compositor image descriptions are identical, so the difference arises after the
mapper, in GTK composition, Mutter or the capture path; a staged diagnostic
attributes it ([corrections](RUNTIME_ACCEPTANCE_CORRECTIONS.md#2-first-presentation-attribution)). Later target
round trips and caption toggles restored exactly. Caption geometry/colour and
target-change acceptance therefore remain open. Its matching v5.15 package retains exact bad v10 dependency pins.
Application/resources are unchanged; the normal package additionally includes
the source-bound upstream manual page. The reviewed eight-package follow-up
is installed with no removals, unchanged APT configuration and owner session.
[Sanitized follow-up install receipt](../evidence/ubuntu-colour-subtitle-install-20261120.json).

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

The first exact APT rehearsal caught a second packaging defect before any
host change: `1.28.7-1ubuntu0.2+rogdv4` sorts below the existing custom API
floor `1.28.7-1+rogdv1`. Allowing a numerical downgrade cannot satisfy those
reverse dependencies. The corrected package revision is
`1.28.7-1+rogdv4.ubuntu0.2`; its authenticated Ubuntu source origin remains
`1.28.7-1ubuntu0.2`. Source-declared ABI minima stay intact. Four generated
symbol entries recover those minima after the first candidate's version
ordering caused debhelper to clamp them.

The original native-test receipt keeps its actual first-candidate version,
`1.28.7-1ubuntu0.2+rogdv4`; it is not relabelled as a run against the final
metadata revision. All 49 packaged base ELFs have identical non-NOTE allocated
sections, and all 300 runtime data files match. Source replay and a fresh
source-package extraction match all 1,442 source paths and modes. Sink and
Showtime payloads and non-control files are byte identical; only their exact
base dependency controls changed. Source-declared minima are unchanged; four
generated symbols were restored. The original seventeen cases and 24 API
assertions were retained rather than rerun for this metadata correction.

The reviewed forward/inverse APT rehearsal passed before the exact thirteen
installed packages were upgraded. The transaction installed the two WebKit
runtimes at `2.52.6-1ubuntu1.1+rogdv8`, eight base packages at
`1.28.7-1+rogdv4.ubuntu0.2`, good at `1.28.7-1ubuntu0.1+rogdv4`, sink at
`0.15.2-1ubuntu2+rogdv5.8` and Showtime at `50.0-2+rogdv5.14`. No development
companions were added. The owner session and unrelated package marks remained
unchanged. Original packages and exact rollback candidates are retained.
The final read-only bundle inventory passes for 33 packages across nine
families. [Sanitized install receipt](../evidence/ubuntu-recovery-install-20261120.json).

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

The policy/packaging fast lane now qualifies 70 methods cumulatively: 66
retained valid passes plus four selected methods passed once on
`0a1dd856a6711f8e7ddd51510ddf8498af5ab28f`. Earlier failed attempts remain
recorded. This is aggregate qualification, not a clean full-suite rerun on
that commit. The earlier [policy fast-lane accounting](../evidence/ubuntu-update-policy-fastlane-20261120.json)
retains its historical 69-method checkpoint; the
[install receipt](../evidence/ubuntu-recovery-install-20261120.json) records the final increment.

Authenticated replay, normal compile/package builds, independent review,
affected fast lane, forward/inverse rehearsal and the exact host installation
are complete. Scoped priority-999 fallback protection is installed; the
existing Mutter 15 local exception is preserved. The twelve paired
sandboxed browser cases passed evaluation in one boot. Showtime
caption/target qualification, final installed-package verification and
whole-family publication remain pending. Preserve the desktop session
and rollback packages. Optical calibration and panel cadence remain
outside software-only acceptance.
