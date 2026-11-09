# Media contributions identified after the October inventory

**Status:** 19 inventory additions; upstream extraction and preparation remain
· **Reviewed:** 2026-11-09 · **Source snapshot:**
[ac82059c3ce8262689e8179436fcf2aeda2b62aa](https://github.com/pjunod/rog_hdr_dv/commit/ac82059c3ce8262689e8179436fcf2aeda2b62aa).

This note records public media-source changes absent from the October 28
inventory: eight held candidates, nine discussion drafts and two groups already
imported from upstream. It does not add ready submissions. The checked patches
and existing receipts are the evidence; this inventory pass did not rerun their
native tests. Read the [submission ledger](../../docs/UPSTREAM_SUBMISSIONS.md)
for the complete disposition of the work.

The source identities below are the exact frozen registry entries, not claims
about the latest upstream revisions. Ubuntu import commits identify locally
reconstructed source trees; obtain the recorded source archives and require the
base and candidate trees in [sources.json](../../sources.json). Do not expect an
Ubuntu import commit to be fetchable from the upstream project. [Reconstruction
and provenance](../../docs/DEVELOPMENT.md) describe the source boundary.

## Source pins

| Component | Source version | Base commit | Candidate commit |
|---|---|---|---|
| [libplacebo-fel-system-dv](../../patches/libplacebo-fel-system-dv/series) | libplacebo 7.387.0 | `275f7dea27924cdd34ab2e6c20e448b6bc4fab65` | `8d7b8055b55df5b7b66c3373d91df832ee1dec55` |
| [mpv-fel-system-dv](../../patches/mpv-fel-system-dv/series) | mpv 0.42.0 | `b0841e8c4d156b8403dc1876c4cbd9011eb583f3` | `12b007d41ea6510bc554233ac7f7224d5690d6bb` |
| [ubuntu-ffmpeg-system-dv](../../patches/ubuntu-ffmpeg-system-dv/series) | 7:8.1.2-2ubuntu2 | `310aa258610e3acf5cdab4ade2e19e3e1b6438e8` | `dd557039083719d00564bb95e69b623d9a920319` |
| [ubuntu-gst-libav-dovi-picture](../../patches/ubuntu-gst-libav-dovi-picture/series) | 1.28.7-1 | `a0c80a3a10d81e1b008d8b426a6e5543f4c984ab` | `0ba924e3719fbbf2940e1b1125262cafd3623892` |
| [ubuntu-gst-plugins-bad-rpu](../../patches/ubuntu-gst-plugins-bad-rpu/series) | 1.28.6-1ubuntu1 | `a1f686414dd0d7490c2fbf3438a2f58bfba25521` | `6a95f6a8aee5d1fb1e01b7033bba92d1953a5f7f` |
| [ubuntu-gst-plugins-base-rpu](../../patches/ubuntu-gst-plugins-base-rpu/series) | 1.28.7-1 | `1cafd2ac126252d2316dc67d8449bb717cfd3ece` | `4d7ff5c79950aef458a506395b4fe7b78345a2bd` |
| [ubuntu-gst-plugins-good-dovi](../../patches/ubuntu-gst-plugins-good-dovi/series) | 1.28.7-1build1 | `73d3a23875505394b9cbb0a7eca71050d0eeaaa3` | `7bf3d71a76fcb0697ed5bbe158e1c800b7ce1cf6` |
| [ubuntu-libdovi-ffi](../../patches/ubuntu-libdovi-ffi/series) | 3.3.2-3 | `18d1f8dd890dcb4934f457b08de7224e1dcfae38` | `2141cb69ab7a4e893154092ba7ce5f4c93cd7ebe` |
| [ubuntu-mesa-wayland-hdr](../../patches/ubuntu-mesa-wayland-hdr/series) | 26.2.4-1ubuntu1 | `bfe8881b713e285fcc2346eddfa7c89a753a1388` | `37efe938d1bf72ff3e5f1f27ac9bb067c4032876` |

A candidate pin represents the complete downstream series. A narrower submission
must extract the named source changes, preserve their attribution and establish
its own upstream base, commit explanation and focused regressions. Several saved
downstream exports contain distribution wrappers, placeholder contributor
metadata or no explanatory commit body. Their existence and a passing downstream
package test do not make those exports submission-ready.

## Candidate inventory

### MESA-1 — Validate and omit unavailable optional Wayland HDR metadata

**Disposition:** Held · **Component:** `ubuntu-mesa-wayland-hdr`.

Separate producer from MPV-1: Vulkan WSI emitted MaxFALL=0, rejected by Weston.
Source adds finite/quantized unsigned luminance bounds and optional-request
omission. Corrected driver accepted. Extract from Debian quilt/changelog, port
to current Mesa, add source regressions before submission.

**Source:** [0001-wsi-wayland-validate-optional-hdr-content-light.patch](../../patches/ubuntu-mesa-wayland-hdr/0001-wsi-wayland-validate-optional-hdr-content-light.patch).

**Evidence:** [shared-display-management-20261107.json](../../evidence/shared-display-management-20261107.json).

### MESA-2 — Keep Wayland FIFO deadlines in the compositor clock domain

**Disposition:** Held · **Component:** `ubuntu-mesa-wayland-hdr`.

About 4.1 seconds of false deadlines from CLOCK_MONOTONIC_RAW versus swapchain
clock. Separate internal deadline and public completion domains; retain
zero-time sentinel. Native timing controls and amd64/i386 packages qualified;
player output drops retained. Needs current upstream port/test/description.

**Source:** [0002-pace-FIFO-in-the-compositor-presentation-clock.patch](../../patches/ubuntu-mesa-wayland-hdr/0002-pace-FIFO-in-the-compositor-presentation-clock.patch).

**Evidence:** [mesa-wsi-presentation-clock.json](../../evidence/mesa-wsi-presentation-clock.json).

### FF-4 — Authoritative frame-owned Dolby metadata and a bounded public RPU resolver

**Disposition:** Discussion draft · **Component:** `ubuntu-ffmpeg-system-dv`.

New public resolver/strictness API: authoritative SPS rectangle, invalid-RPU
withholding, bounded/reserved config rejection, reset metadata on live config
change without resetting normal HEVC references. Native
reorder/gap/flush/lifetime/conformance/config and pixel controls exist. Discuss
upstream parser/side-data API, isolate local symbol/runtime plumbing. Follow-up
config checks repair the proposed resolver, not independent preexisting upstream
bugs.

**Source:** [0005-provide-strict-frame-owned-Dolby-metadata.patch](../../patches/ubuntu-ffmpeg-system-dv/0005-provide-strict-frame-owned-Dolby-metadata.patch) · [0007-bind-strict-RPU-state-to-the-SPS-visible-rectangle.patch](../../patches/ubuntu-ffmpeg-system-dv/0007-bind-strict-RPU-state-to-the-SPS-visible-rectangle.patch) · [0009-reject-reserved-Dolby-compression.patch](../../patches/ubuntu-ffmpeg-system-dv/0009-reject-reserved-Dolby-compression.patch) · [0011-preserve-video-references-on-Dolby-configuration-change.patch](../../patches/ubuntu-ffmpeg-system-dv/0011-preserve-video-references-on-Dolby-configuration-change.patch).

**Evidence:** [gstreamer-dovi-producers-native-20261107.json](../../evidence/gstreamer-dovi-producers-native-20261107.json) · [gstreamer-nvidia-picture-qualification.json](../../evidence/gstreamer-nvidia-picture-qualification.json).

### FF-5 — Explicit display-target mapping hook and export metadata replacement

**Disposition:** Discussion draft · **Component:** `ubuntu-ffmpeg-system-dv`.

Public adapter selects physical xy/luminance before generic conversion, replaces
obsolete source Dolby/HDR10+ side data with destination metadata and keeps named
fallback. Export/trim/crop and native chart controls exist. Current
implementation depends on private provider and private renderer namespace:
discuss/extract generic contract; private mapper equations and SDK
implementation remain excluded.

**Source:** [0001-ffmpeg-shared-display-management.patch](../../patches/ubuntu-ffmpeg-system-dv/0001-ffmpeg-shared-display-management.patch) · [0014-accept-physical-xy-with-an-optional-provider-v2.patch](../../patches/ubuntu-ffmpeg-system-dv/0014-accept-physical-xy-with-an-optional-provider-v2.patch).

**Evidence:** [shared-display-management-20261107.json](../../evidence/shared-display-management-20261107.json) · [ffmpeg-panel-xy-release.json](../../evidence/ffmpeg-panel-xy-release.json).

### MPV-6 — Preserve raw RPU ownership when inheriting matched enhancement-layer metadata

**Disposition:** Held · **Component:** `mpv-fel-system-dv`.

f_enhancement_pair refs raw RPU from matched EL onto BL, removes stale BL RPU
and handles allocation failure. Distinct from October MPV-2 split fallback.
Split this hunk from private provider/Wayland/build glue and add focused
current-upstream pairing/lifetime regression. Staged 4K FEL and flip/failure
controls are downstream evidence.

**Source:** [0001-match-enhancement-pictures-and-validate-Wayland-signals.patch](../../patches/mpv-fel-system-dv/0001-match-enhancement-pictures-and-validate-Wayland-signals.patch).

**Evidence:** [profile7-intel-dual-layer.json](../../evidence/profile7-intel-dual-layer.json).

### MPV-7 — Separate physical targets from PQ transport and retain mapped cached-capture state

**Disposition:** Discussion draft · **Component:** `mpv-fel-system-dv`.

Physical min/max/xy and reference-white transport are separate; paused/cache
window captures preserve displayed grade and invalidate state on source/target
change. Tagged PNG tests changed only authored edited frames; ordinary
HDR10/native-source controls byte-equal. Generic target/capture lifecycle
proposal requires agreement and extraction from optional private provider
integration. No optical claim.

**Source:** [0002-target-the-physical-display-and-retain-cached-PQ-signals.patch](../../patches/mpv-fel-system-dv/0002-target-the-physical-display-and-retain-cached-PQ-signals.patch) · [0003-retain-displayed-grade-in-tagged-window-captures.patch](../../patches/mpv-fel-system-dv/0003-retain-displayed-grade-in-tagged-window-captures.patch) · [0004-map-validated-physical-xy-with-optional-provider-v2.patch](../../patches/mpv-fel-system-dv/0004-map-validated-physical-xy-with-optional-provider-v2.patch).

**Evidence:** [mpv-window-grade-capture.json](../../evidence/mpv-window-grade-capture.json) · [sdk-api-v2-normal-products.json](../../evidence/sdk-api-v2-normal-products.json).

### LP-1 — Frame-owned display-mapping hook before ordinary scaling and conversion

**Disposition:** Discussion draft · **Component:** `libplacebo-fel-system-dv`.

Public renderer callback receives authoritative frame metadata and reconstructed
native master; propagates mapper failure before generic conversion. Discuss
generic hook/lifetime design and exclude private ABI namespace/build glue. LP-DM
private equation work remains excluded; no private provider implementation is
proposed.

**Source:** [0001-map-the-native-reconstructed-dolby-master.patch](../../patches/libplacebo-fel-system-dv/0001-map-the-native-reconstructed-dolby-master.patch).

**Evidence:** [shared-display-management-20261107.json](../../evidence/shared-display-management-20261107.json) · [profile7-intel-dual-layer.json](../../evidence/profile7-intel-dual-layer.json).

### LP-2 — Honor flipped enhancement planes and contributing-frame failure/target ownership

**Disposition:** Held · **Component:** `libplacebo-fel-system-dv`.

Source honors vertical flip, rejects failed contributing-frame acquisition and
avoids double release of borrowed mixer target. Native flip: three
composed/mapped frames; failing non-reference acquisition correctly fails
rendering. Extract upstream-generic fixes from the new hook fatal-state
behavior; add current-upstream regression.

**Source:** [0002-propagate-flipped-planes-and-contributing-frame-errors.patch](../../patches/libplacebo-fel-system-dv/0002-propagate-flipped-planes-and-contributing-frame-errors.patch).

**Evidence:** [profile7-intel-dual-layer.json](../../evidence/profile7-intel-dual-layer.json).

### GST-1 — Picture-owned original RPU metadata across reordering and flushes

**Disposition:** Discussion draft · **Component:** `ubuntu-gst-plugins-base-rpu`.

New GstVideo meta owns AU bytes and uses matched GstVideoCodecFrame rather than
last-picture state; only identity-compatible copies retain it. Native avdec/VA
gap/reorder/seek/lifetime/transform controls exist. New meta/tag/copy API needs
upstream agreement. Transport is not resolved metadata or FEL reconstruction.

**Source:** [0001-video-carry-owned-Dolby-RPU-with-matched-codec-frames.patch](../../patches/ubuntu-gst-plugins-base-rpu/0001-video-carry-owned-Dolby-RPU-with-matched-codec-frames.patch).

**Evidence:** [gstreamer-rpu-transport-native-20261107.json](../../evidence/gstreamer-rpu-transport-native-20261107.json).

### GST-2 — Attach original HEVC RPU only from completed access units

**Disposition:** Held · **Component:** `ubuntu-gst-plugins-bad-rpu`.

h265parse owns completed-AU bytes with parser/reset/flush safety; scoped
positive/negative transport controls exist. Depends on proposed GstVideo meta
API; requires upstream source port and native test harness.

**Source:** [0001-h265parse-attach-original-RPU-from-completed-access-units.patch](../../patches/ubuntu-gst-plugins-bad-rpu/0001-h265parse-attach-original-RPU-from-completed-access-units.patch).

**Evidence:** [gstreamer-rpu-transport-native-20261107.json](../../evidence/gstreamer-rpu-transport-native-20261107.json) · [gstreamer-rpu-supplementary-va-run-20261107.json](../../evidence/gstreamer-rpu-supplementary-va-run-20261107.json).

### GST-3 — Bounded reusable HEVC Dolby configuration parser in pbutils

**Disposition:** Discussion draft · **Component:** `ubuntu-gst-plugins-base-rpu`.

Reusable dvcC/dvvC parser validates version/flags/profiles/length and writes
output only on success; missing compatibility does not infer color space. New
public API needs upstream agreement; exclude distro ABI metapackage/symbol
packaging.

**Source:** [0002-parse-HEVC-Dolby-decoder-configuration-in-pbutils.patch](../../patches/ubuntu-gst-plugins-base-rpu/0002-parse-HEVC-Dolby-decoder-configuration-in-pbutils.patch).

**Evidence:** [gstreamer-dovi-isobmff-controls.json](../../evidence/gstreamer-dovi-isobmff-controls.json).

### GST-4 — Preserve authoritative Dolby configuration per MP4 sample entry

**Disposition:** Held · **Component:** `ubuntu-gst-plugins-good-dovi`.

qtdemux retains bounded sample-entry configuration with correct stream/caps
transition and shared validation. Native no-config/replacement controls exist.
Depends on pbutils API; compare current upstream and extract source-only patch
from packaging.

**Source:** [0001-carry-Dolby-configuration-per-sample-entry.patch](../../patches/ubuntu-gst-plugins-good-dovi/0001-carry-Dolby-configuration-per-sample-entry.patch) · [0002-use-the-shared-HEVC-configuration-parser.patch](../../patches/ubuntu-gst-plugins-good-dovi/0002-use-the-shared-HEVC-configuration-parser.patch).

**Evidence:** [gstreamer-dovi-isobmff-controls.json](../../evidence/gstreamer-dovi-isobmff-controls.json) · [gstreamer-dovi-live-clear-20261107.json](../../evidence/gstreamer-dovi-live-clear-20261107.json).

### GST-5 — Preserve bounded track-local Dolby configuration in Matroska

**Disposition:** Held · **Component:** `ubuntu-gst-plugins-good-dovi`.

Validates bounded BlockAdditionMapping payload/type, duplicates/conflicts and
independent track state. 25 focused controls pass; stock negative rejects
expected config; native P5 resolved 3 pictures. P7 check is config-only with no
residual/reconstruction claim. Prepare current upstream patch/test/description.

**Source:** [0004-matroska-preserve-bounded-track-Dolby-configuration.patch](../../patches/ubuntu-gst-plugins-good-dovi/0004-matroska-preserve-bounded-track-Dolby-configuration.patch).

**Evidence:** [gstreamer-matroska-track-config-20261108.json](../../evidence/gstreamer-matroska-track-config-20261108.json) · [gstreamer-matroska-distribution-replay-20261108.json](../../evidence/gstreamer-matroska-distribution-replay-20261108.json) · [gstreamer-matroska-normal-packages-20261108.json](../../evidence/gstreamer-matroska-normal-packages-20261108.json).

### GST-6 — Bind software libav decoder Dolby state to each decoded picture

**Disposition:** Discussion draft · **Component:** `ubuntu-gst-libav-dovi-picture`.

avdec consumes authoritative strict frame metadata, conformance geometry and
live config transitions without resetting ordinary video; transforms discard
stale provenance. Native mid-GOP/reset/equal-pixel controls pass. Current
gstdovipicture helper and FFmpeg resolver are local: agree upstream owned
snapshot API/dependencies first.

**Source:** [0001-bind-strict-Dolby-metadata-to-the-decoded-picture.patch](../../patches/ubuntu-gst-libav-dovi-picture/0001-bind-strict-Dolby-metadata-to-the-decoded-picture.patch).

**Evidence:** [gstreamer-dovi-producers-native-20261107.json](../../evidence/gstreamer-dovi-producers-native-20261107.json).

### GST-7 — Associate native VA Dolby state with the decode-order surface

**Disposition:** Discussion draft · **Component:** `ubuntu-gst-plugins-bad-rpu`.

Owned resolved snapshot follows VA surface through reordering, flush/config
generations and visible crop. Native gap/reorder/seek/lifetime/conformance and
transform controls exist. Depends on proposed public snapshot/resolver API; does
not itself establish mapped FEL output.

**Source:** [0002-bind-the-resolved-Dolby-picture-to-the-VA-surface.patch](../../patches/ubuntu-gst-plugins-bad-rpu/0002-bind-the-resolved-Dolby-picture-to-the-VA-surface.patch).

**Evidence:** [gstreamer-dovi-producers-native-20261107.json](../../evidence/gstreamer-dovi-producers-native-20261107.json).

### GST-8 — Keep picture-owned Dolby provenance and conformance geometry in NVDEC

**Disposition:** Discussion draft · **Component:** `ubuntu-gst-plugins-bad-rpu`.

Nine producer controls cover avdec/VA/NV; 95-picture config transitions retain
normalized pixels; ordinary HEVC gains no Dolby metadata; transformations drop
stale provenance. Depends on upstream snapshot/resolver design. Strip
dependency/quilt wrappers. Native GStreamer P7 FEL reconstruction remains
unfinished separately.

**Source:** [0004-nvcodec-preserve-resolved-Dolby-pictures-and-conformance-geometry.patch](../../patches/ubuntu-gst-plugins-bad-rpu/0004-nvcodec-preserve-resolved-Dolby-pictures-and-conformance-geometry.patch).

**Evidence:** [gstreamer-nvidia-picture-qualification.json](../../evidence/gstreamer-nvidia-picture-qualification.json).

### GST-9 — Preserve high precision through GL balance and invalidate changed color provenance

**Disposition:** Held · **Component:** `ubuntu-gst-plugins-base-rpu`.

glcolorbalance accepts RGBA64_LE; neutral passthrough retains input, transformed
pixels discard color-sensitive provenance. Saved patch mixes full Debian quilt
export/autogenerated placeholder metadata with 11 source lines: extract generic
source fix and add upstream precision/meta tests.

**Source:** [0004-preserve-through-GL-color-balance-and-package-the-quilt-series.patch](../../patches/ubuntu-gst-plugins-base-rpu/0004-preserve-through-GL-color-balance-and-package-the-quilt-series.patch).

**Evidence:** [gstreamer-gtk-mapper-negotiation.json](../../evidence/gstreamer-gtk-mapper-negotiation.json) · [gstreamer-gtk-final-packages-20261108.json](../../evidence/gstreamer-gtk-final-packages-20261108.json).

### FF-BACKPORT — Imported dovi_split, split-NAL length validation and HEVC EL configuration

**Disposition:** Superseded upstream · **Component:** `ubuntu-ffmpeg-system-dv`.

These are explicit upstream backports, not novel patches to send. Preserve
original Kacper Michajlow and Michael Niedermayer attribution/signoffs. Packet
identity is adapted from upstream 5f6dff5e7dbd9b1f3221f7c37225365dbf1e1038.
Local version/build glue is excluded.

**Source:** [0002-backport-dovi-split-bitstream-filter.patch](../../patches/ubuntu-ffmpeg-system-dv/0002-backport-dovi-split-bitstream-filter.patch) · [0003-check-length-of-split-NAL-units.patch](../../patches/ubuntu-ffmpeg-system-dv/0003-check-length-of-split-NAL-units.patch) · [0004-use-upstream-HEVC-configuration-packet-side-data.patch](../../patches/ubuntu-ffmpeg-system-dv/0004-use-upstream-HEVC-configuration-packet-side-data.patch).

**Evidence:** [profile7-intel-dual-layer.json](../../evidence/profile7-intel-dual-layer.json).

### DV-BACKPORT — Imported C-FFI ownership, recoverable parser errors and pivot bounds

**Disposition:** Superseded upstream · **Component:** `ubuntu-libdovi-ffi`.

Patch bodies explicitly backport upstream commits
4e6b263c35f08bca9efe919effac9c09c26fba70,
73daa31a8ecc76a4eedff8cb8f6197a3d66c3b3c and
f41b2809cd00f41118248fcd8a1a3dff6216efcf. Preserve Nomis101/quietvoid authors.
CRC-valid unsupported RPU aborts stock but patched parser returns error and
accepts subsequent valid input. Do not resubmit or conflate with DV-5 mixed
mapping.

**Source:** [0001-backport-upstream-C-FFI-ownership-fixes.patch](../../patches/ubuntu-libdovi-ffi/0001-backport-upstream-C-FFI-ownership-fixes.patch) · [0002-return-parser-errors-for-unsupported-interpolation.patch](../../patches/ubuntu-libdovi-ffi/0002-return-parser-errors-for-unsupported-interpolation.patch) · [0003-validate-reshaping-pivot-counts.patch](../../patches/ubuntu-libdovi-ffi/0003-validate-reshaping-pivot-counts.patch).

**Evidence:** [libdovi-unsupported-interpolation.json](../../evidence/libdovi-unsupported-interpolation.json).

## Existing entries and overlap

### MPV-1 remains one optional-light-level contribution

The [October submission
patch](../mpv/01-unknown-light-levels/0001-01-unknown-light-levels.patch) and
the [later Ubuntu
patch](../../patches/ubuntu-mpv-system-dv/0002-mpv-wayland-optional-content-light.patch)
address the same producer-side omission of unknown MaxCLL and MaxFALL. The later
source also validates finite, quantized version-one luminance bounds. Its
[downstream digital
receipt](../../evidence/shared-display-management-20261107.json) adds context;
it does not change the bytes or qualification of the October kit. Keep MPV-1 as
one entry. Mesa produces a separate image description, so MESA-1 is a separate
upstream fix.

### MPV-2 needs comparison with the newer upstream floor

The [October enhancement-layer
fallback](../mpv/02-enhancement-layer-fallback/DESCRIPTION.md) was prepared
against its recorded source floor. The newer system path uses mpv 0.42 and an
explicit upstream FFmpeg dovi_split backport. Before sending MPV-2, compare its
remaining compatibility problem with that newer upstream path and existing work.
This inventory does not prove that the complete old fallback is superseded, does
not rewrite its previously qualified bytes, and does not relabel its historical
test receipt as a new run. MPV-6 records different ownership/error-handling
changes in the matched-picture path.

## What stays local or private

MPV-3 and LP-DM remain excluded. The private closed-form mapping implementation,
provider source and SDK payload are not submission material. FF-5, MPV-7 and
LP-1 identify public adapter or lifecycle questions, not permission to submit
private equations or vendor material. A public adapter can still require a
private runtime; that is a dependency limit to resolve with an upstream design,
not a completed portable contribution.

Ubuntu-only package changes are delivery integration: augmented resolver symbol
versions, exact runtime/development dependencies, capability metapackages,
multiarch compatibility, provider ABI namespaces and release locks. Source
confined to debian/ is not counted as another media contribution. FFmpeg patch
0016 and mpv patch 0005 enforce the locally supplied provider SDK contract;
libdovi patches 0004–0005 verify the generated C header during local package
assembly. Extract source behavior from these wrappers before proposing it
upstream.

The imported FFmpeg and libdovi groups above retain their upstream authors and
recorded origin commits. They are tracked to prevent duplicate submissions. This
refresh does not alter their bytes, licences or existing third-party sign-offs
and does not invent a new owner sign-off.

## Active work outside the frozen snapshot

The older-based GStreamer native full-enhancement-layer effort is unfinished.
The November 9 continuation records Profile 7/full-EL configuration retained
across 140 NVIDIA-decoded 4K pictures and a flush seek, while every picture
remains marked unreconstructed. Configuration transport and decoded-picture
ownership do not establish residual pairing, reconstructed pixels or mapped FEL
output. Rebase that effort onto current main and obtain its own source and
runtime evidence before advancing it. No completed native GStreamer FEL
contribution is claimed here.

Later coordinator handoffs can advance package installation or visible
acceptance without changing this inventory’s source snapshot. They do not
silently qualify an upstream port. Keep optical calibration, new native
execution, retained downstream receipts and submission preparation as separate
evidence.
