# November display-stack contributions — what is new and what needs preparation

**Audited:** 2026-11-09 · **Source snapshot:** public main
[`ac82059`](https://github.com/pjunod/rog_hdr_dv/commit/ac82059c3ce8262689e8179436fcf2aeda2b62aa).
These eleven units extend the October inventory. The source and linked native
receipts already exist; this audit does not rerun their tests, move a source
base or turn a distribution package into an upstream submission. Start with the
[submission ledger](../../docs/UPSTREAM_SUBMISSIONS.md) and the
[project commands](../README.md).

**Held** identifies the upstream extraction, regression or source check still
needed. **Discussion draft** identifies a public interface or ownership
proposal that needs maintainer agreement before a code submission. Neither
state claims upstream review, personal sign-off or physical qualification.

| Unit | Destination | Change | State |
|---|---|---|---|
| MUT-N | Mutter | Compare declared mastering peaks at their Wayland wire precision | Held |
| MUT-O | Mutter | Match shared-memory screen capture to its negotiated format | Held |
| TA-1 | Tiling Assistant | Own synthetic animations independently of native Shell accounting | Held |
| GTK-1 | GTK/GDK | Publish copied preferred targets with lifecycle invalidation | Discussion draft |
| GTK-2 | GTK/GDK | Store each primary's Y coordinate in the correct field | Held |
| GTK-3 | GTK/GDK | Track a surface's HDR request and actual presentation precision | Discussion draft |
| GTK-4 | GTK/GDK | Query GLES readback format and type through supported state | Held |
| GTK-5 | GTK | Give each GtkVideo view its own target and retained source picture | Discussion draft |
| GLY-1 | Glycin | Preserve ICC gamut, alpha and precision in float textures | Held |
| TIFF-1 | Rust TIFF decoder | Read byte metadata under its actual byte budget | Held |
| WK-1 | WebKitGTK | Grade clear video for an explicit ordinary SDR page destination | Discussion draft |

## Mutter — two additional producer boundaries

**MUT-N:** [patch 0106](../../patches/ubuntu-mutter/0106-color-compare-client-mastering-peaks-at-their-wire-precision.patch)
records whether a mastering declaration came from integer Wayland fields.
Comparison uses the nearest representable target peak while the mapping curve
retains the original peak. Declaration provenance also belongs in the color
state cache keys. This extends the existing target-volume work; it does not
replace MUT-E with a second copy of the same proposal.

The [native qualification](../../evidence/mutter-wire-peak-qualification.json)
distinguishes 880, 881 and 882 cd/m² client declarations at reference white 203
from a display declared as 616 cd/m² at reference white 142. A rounded Wayland
881 declaration avoids another mapping, while an exact native 881 declaration
still maps. This is inherited source/package evidence for that fixture.
Extract the change against an agreed current upstream target-volume design and
retain its native regression before preparing a separate submission.

**MUT-O:** [patch 0107](../../patches/ubuntu-mutter/0107-screencast-memory-format.patch)
corrects monitor, area and virtual shared-memory capture paths that used
8-bit native ARGB readback for differently negotiated buffers. Detached repaint
also needs a framebuffer with the selected precision.

The [format qualification](../../evidence/mutter-shared-memory-color-formats.json)
covers XR30, XB30, half-float RGBA and SDR BGRx, including format changes on one
stream. XR30 and XB30 agree exactly after unpacking; sampled half-float values
differ by at most 0.574 of a ten-bit code. These are MemFd digital captures.
They establish neither DMA-BUF capture nor optical panel response. Extract a
current-upstream correction and focused regression; keep it distinct from the
color-mapping proposals.

Both changes are exported in the 107-patch Ubuntu Mutter series at base
`f8b113189f8c67beabf7475adf26f6ebcbf36684`, candidate tree
`1d20b861bc329c8a16623063bad2b4fed33bf4fe`. Those distribution pins are recorded
in the [source registry](../../sources.json); they are not an upstream MR base.

## Tiling Assistant — synthetic animation ownership

**TA-1:** the [six-patch series](../../patches/ubuntu-tiling-assistant/series)
uses actual upstream v56, base
`62b43228a8780bd435ec7a94892434e4950dcd41`, candidate tree
`e7a885c42f9470ff49661dbf639216bc687d5cdd`. The source route is
[ubuntu/Tiling-Assistant](https://github.com/ubuntu/Tiling-Assistant).
It separates synthetic overlays from Shell's native resize ownership, handles
cancellation and finite geometry intent, and respects Shell's callback-only
`ease()` API. Preserve the original authorship when preparing a submission.

The [ownership document](../../docs/TILING_ANIMATION_OWNERSHIP.md) and
[qualification](../../evidence/tiling-animation-qualification.json) retain
35 distinct valid offline cases for the earlier five-patch tree: 26 initial
passes and nine failed-only retry passes. They are not a fresh 35-case run of
the six-patch tree. The
[nativehdr3 build](../../evidence/tiling-animation-nativehdr3-build-20261107.json)
proves the additive callback correction's package/source binding. The
[bounded target observations](../../evidence/tiling-animation-target-20261107.json)
retain their original package versions and scope.

Prepare the final six-patch upstream history with explanatory commit bodies,
confirm its current target and run the affected callback/animation cases before
submission. Do not turn prior package construction or a bounded visible pass
into a claim about every fullscreen, cross-mode or native completion path.

## GTK/GDK — distinguish source bugs from interface proposals

The [twelve-patch Ubuntu GTK series](../../patches/ubuntu-gtk4-display-target/series)
starts at `06c57761c0d36e1301d11da4ac95cf21c7ceb99b` from Ubuntu
`4.24.1+ds-1`, candidate tree
`46ef2e57785d9651050e2f2620c913423eb8a980`. The
[display-target contract](../../docs/GDK_DISPLAY_TARGET.md) explains ownership
and normal rendering behavior. Submission requires a current GTK source port;
Debian symbols, version bumps and build-profile edits remain delivery material.

**GTK-1:** [patch 0001](../../patches/ubuntu-gtk4-display-target/0001-wayland-expose-preferred-color-target-snapshots.patch)
publishes a copied physical target and generation from the existing shared
Wayland color manager. Ordinary target discovery stays separate from
experimental content rendering. It handles a manager's initial roundtrip,
query replacement and safe invalidation/destruction. The
[build/replay](../../evidence/gdk-display-target-build-20261107.json) and
[native lifecycle](../../evidence/gdk-display-target-runtime-20261107.json)
receipts retain default startup, late-manager and reentrant destruction checks.
Agree the public API and per-output ownership semantics, then qualify moves,
spanning surfaces and physical hotplug on the eventual upstream candidate.

**GTK-2:** the same patch contains a smaller independent source correction.
Explicit primaries, named primaries and target-primaries listeners assigned
green, blue and white Y into red Y. Extract the three field corrections from
the larger API patch and add a listener regression against current upstream.
The combined build/replay proves the recorded source, not that separate port.

**GTK-3:** [patch 0003](../../patches/ubuntu-gtk4-display-target/0003-wayland-track-native-HDR-presentation-per-surface.patch)
adds a demand-scoped rendering lease and an actual presentation witness.
Target changes and draw-context replacement invalidate the witness; releasing
the last request restores ordinary SDR behavior. Native EGL four-patch PQ
readback and default Vulkan/introspection checks have scoped evidence in the
[contract](../../docs/GDK_DISPLAY_TARGET.md#requesting-high-precision-presentation).
Agree the public API, precision witness and graphics-offload ownership before
extracting an upstream proposal. A PQ label alone is not HDR presentation.

**GTK-4:** [patch 0005](../../patches/ubuntu-gtk4-display-target/0005-gdk-query-the-bound-read-framebuffer-format.patch)
uses `glGetIntegerv` for the bound read framebuffer's implementation format and
type, and gates the desktop GL path at 4.5. The previous framebuffer-parameter
query raised `GL_INVALID_ENUM` on GLES and returned transparent black after
NVIDIA declined EGL image export. A one-pixel normalized 16-bit PQ source then
recovered all four stored words through the corrected query. The
[readback section](../../docs/GDK_DISPLAY_TARGET.md#opengl-es-video-texture-readback)
and [combined product receipt](../../evidence/gtkvideo-final-combined-20261108.json)
retain source and consumer scopes. Prepare this generic fix separately with a
focused current-upstream regression.

**GTK-5:** patches 0008–0011 in the
[series](../../patches/ubuntu-gtk4-display-target/series) bind each realized
`GtkVideo` to its own copied target, lease and mapper. Original pictures are
retained before playsink conversion; obsolete stream, caps, view and target
generations cannot publish a worker result. The optional SDK is checked before
use, with ordinary SDR startup preserved when it is absent or incompatible.

The [normal package/product receipt](../../evidence/gtkvideo-view-normal-packages-20261108.json)
and [final combined controls](../../evidence/gtkvideo-final-combined-20261108.json)
cover two views, paused 616→308→616 regrading with exact return, source
replacement, one-view destruction and rejected SDK startup. Agree a generic
upstream mapper/destination interface. The public adapter does not authorize
publishing private renderer equations or implementation.

## Image colour — send fixes to the dependency that owns them

**GLY-1:** the [Loupe carrier series](../../patches/ubuntu-loupe-image-colour/series)
changes Glycin 3.1 embedded in Loupe 50. Its destination is
[GNOME Glycin](https://gitlab.gnome.org/GNOME/glycin), not an independent Loupe
application feature. ICC conversion writes linear BT.2020 float16/float32
textures rather than clipping into integer sRGB. Preserve CICP precedence,
alpha, row stride and transactional invalid-profile fallback. Fold the second
patch's alpha correction into this unit because it repairs the new conversion
path rather than demonstrating another stock application bug.

The source carrier is Ubuntu Loupe `50.0-0ubuntu2`, base
`27c57fc898a317ad8a7e3e3bd9a09c43c4d0c2eb`, candidate tree
`101752343b2c975d4d164a0e8b6b349c0b81e47c`. The
[image qualification](../../evidence/gnome-image-colour-20261108.json) covers
256 gray levels, RGB/RGBA 8/16-bit, associated U8/U16/F32, padded rows, CICP
precedence and malformed profiles through the normal sandboxed loader. Its
[ordinary viewer comparison](../../docs/GNOME_IMAGE_COLOUR.md) retains one-row
synthetic GPU samples; optical and external-monitor acceptance remain open.
Extract the real Glycin change and tests without distribution overrides,
vendored checksums or package changelogs.

**TIFF-1:** the [Glycin loader carrier patch](../../patches/ubuntu-glycin-image-colour/0001-read-TIFF-byte-tags-under-the-metadata-budget.patch)
changes the Rust `tiff` 0.11.3 crate at
[image-rs/image-tiff](https://github.com/image-rs/image-tiff).
BYTE and UNDEFINED metadata is read under its actual byte budget rather than
expanded into a per-element `Value` representation. Allocation grows only after
successful bounded reads. This is a decoder dependency correction, not a
second Glycin or libtiff implementation.

The carrier is Ubuntu Glycin `2.2.1+ds-1ubuntu2`, base
`e23a0f33d3f7ca6620fb58df20c074a984fe97b3`, candidate tree
`ab8f1af070c1a20a87ba2a040868bd3a95c33c67`.
[Qualification](../../evidence/gnome-image-colour-20261108.json) covers a
21,012-byte profile in 80, 320 and 1,024-pixel-square TIFFs, both byte tag types,
and invalid offset/excess-count fallback. Extract a crate-local current-source
patch and focused regression; omit package-specific Cargo and checksum changes.

## WebKitGTK — keep the browser boundary explicit

**WK-1:** the public
[clear Dolby/base-layer comparison](../../evidence/webkit-clear-dolby-base-comparison.json)
on WebKitGTK `2.52.6-1ubuntu1` showed identical pictures with and without the
Dolby carrier metadata. Codec acceptance therefore does not prove that the
browser used that metadata. The
[system playback document](../../docs/SYSTEM_DOLBY_VISION.md) records the wider
consumer boundaries.

The active browser source and build are private; this entry publishes no patch,
provider code, captures or private recipe. The next discussion is an explicit
ordinary SDR destination for clear video inside an SDR page. A resumed full
build and a standalone adapter control do not establish final browser product
acceptance. High-precision HDR page composition, typed per-view target
invalidation, ordinary accelerated/software controls and protected streaming
have separate unresolved requirements.

## Existing kernel entries and material that stays local

LNX-3 now has a real downstream patch and bounded target evidence. The
[updated Linux kit](../linux/README.md) preserves its held upstream preparation
state while replacing the obsolete missing-patch/missing-hardware description.
LNX-1 remains Cristian La Spina's work. LNX-2 keeps its exact October 28 upstream
base; later Ubuntu deployment does not move that qualified submission tree.

The Ubuntu security rebase retains an existing upstream fix; it is not a new
contribution authored here. Distribution package versions, recovery tooling,
Cargo overrides and vendored file checksums are not extra generic fixes.
The paused-subtitle investigation also adds no GTK fix: a remux had dropped
`dvcC`, and matched-configuration controls passed on the unchanged GTK source.
