# GStreamer Dolby transport — keep each RPU with its decoded picture

**Status:** native metadata-transport checks passed; unshipped, reconstruction
and normal-player rendering remain open · **Written:** 2026-11-07.

Companion to [shared display management](SYSTEM_DOLBY_VISION.md), which describes
the working consumer interfaces. This proposal carries original metadata through
GStreamer's native HEVC parser and decoder boundary. It changes no pixels and
provides no new playback route. Read the phase boundaries before connecting it
to a renderer: raw RPU presence does not establish reconstructed Dolby pixels.

## 1. Transport owns the bytes, never a previous picture

[The base series](../patches/ubuntu-gst-plugins-base-rpu/series) introduces the
proposed `GstVideoDoviRpuMeta`. Its fields are populated data only:

```c
GstMeta meta;
GBytes *rpu;             /* immutable bytes, excluding the HEVC NAL header */
guint width, height;    /* native visible picture dimensions */
```

The add function copies the original bytes. Whole-buffer copies retain the
immutable `GBytes`; partial-buffer copies and non-copy transformations drop the
meta. Its colorspace, size and orientation tags allow pixel-changing converters to remove
instructions that no longer describe their output. The decoder explicitly
accepts this one tagged meta when its output dimensions match the source.
Low-resolution decoder output does not receive it.

[The parser series](../patches/ubuntu-gst-plugins-bad-rpu/series) scans the
completed outgoing access unit after wrapping and header insertion. It removes
old copies of this meta before deriving a new one from the outgoing bytes.
Only AU-aligned output with one layer-0 RPU receives a meta. Duplicate RPUs,
unknown layer association and payloads over the local 65,536-byte allocation
bound are declined. Original encoded bytes remain unchanged.

There is no retained RPU field in parser stream state. A missing RPU, flush,
seek or dropped picture cannot select a metadata predecessor. The copy path is
`GstVideoCodecFrame.input_buffer` to that frame's `output_buffer` in
`GstVideoDecoder::finish_frame`. Software avdec associates its output through
FFmpeg's `opaque_ref`; Intel VA uses the reordered picture's codec frame before
calling the same finish function. Neither family overrides the meta-copy hook
on the pinned floor. The native qualification below verifies association through both decoder families.

The parser must be in the actual pipeline. This phase does not add a decoder
fallback extractor for an application that directly connects a demuxer to a
decoder without `h265parse`.

## 2. Reconstruction needs a separate complete snapshot

The raw meta does not reserve empty reconstruction fields. A later resolved
source snapshot must be a separate, complete value contract emitted only when
all required source reconstruction data are available. It must contain resolved
per-channel mapping curves, nonlinear/linear transforms, range and bit-depth
parameters, source profile/compatibility, and an explicit enhancement-layer
state. Copy public numeric values; do not serialize private parser layouts,
opaque handles, pointers or borrowed decoder frames.

| Producer | Authoritative source | Required work before emitting a resolved snapshot |
|---|---|---|
| `avdec_h265` | Public `AVDOVIMetadata` on the matched output `AVFrame` | Copy the decoder-resolved values before `av_frame_unref`, beside the original RPU |
| Intel `vah265dec` | Original RPU from the matched AU | A public libdovi-backed parser/resolver in decode order, with inherited mapping and DM metadata ID/static-block handling, producing the same canonical values |

The VA resolver must keep stream-owned decode-order state, resolve references
before publishing a picture snapshot, then clear that state at flush and stream
boundaries. Render order is never a metadata resolver. Missing or unresolved
references prevent publication of the resolved snapshot.

A resolved source snapshot still does not mean pixels are a reconstructed
master. The renderer must apply source reshaping and reconstruct the native
BT.2020/PQ RGB master before display mapping. FEL with an undecoded residual is
explicitly unsupported. Parsing its RPU does not reconstruct the enhancement
layer. Original metadata transport is allowed for unsupported profiles, while
claiming a reconstructed result is not.

The shared provider's raw-only callback also currently declines compressed or
indirected display metadata. A complete extension must either accept effective
resolved DM explicitly or use a public, verified serialization of a complete
self-contained RPU. Preserve the original RPU for identity and never infer its
effective state from whichever frame happened to render last.

## 3. The native sink owns the actual display target

A generic converter has no authority to invent the window's display peak or
gamut. The native sink must obtain its surface's preferred image description
from the toolkit's existing color-management integration, track its generation
through output moves and setting changes, and expose the actual target upstream
through a negotiated GStreamer query or context. The mapping cache must include
that generation. If the toolkit does not expose this information, a public
GTK/GDK target-data bridge is a prerequisite; competing ownership of the
surface's Wayland color-management object is not a substitute.

Normal Showtime uses GstPlay, `glsinkbin` when GL is available, and
`gtk4paintablesink`. Source reconstruction must happen before ordinary GL color
conversion, scaling and cropping discard or misinterpret the source signal.
The sink must preserve the mapped output's color state through GDK and support
an adequate HDR texture/encoding path. Installing a provider or app alone cannot
supply these missing stages. This proposal changes no application defaults,
plugin ranks, environment overrides or launch commands. It installs no apps.

## 4. Qualification is pending for each phase

The exact Ubuntu sources are base `1.28.7-1` and bad `1.28.6-1ubuntu1`, pinned in
[sources.json](../sources.json). The core/base SDK packages were unpacked in an
owned build directory and were not installed. The modified `gstvideo-1.0` and
`gstvideoparsersbad` targets compiled with `-Dwerror=true` and four jobs. Tests,
examples, introspection and documentation execution were disabled. The
[compile receipt](../evidence/gstreamer-rpu-transport-compile-20261107.json)
records this narrow evidence and output hashes. Patch hashes were added to
`SHA256SUMS` deliberately for the two new series.

Independent review found two defects in the first proposal: the probe waited
for a parser's queued SEGMENT before admitting the buffer that releases it,
and the raw meta omitted its orientation tag. The
[correction receipt](../evidence/gstreamer-rpu-corrections-compile-20261107.json)
records corrected source and probe compilation. Independent follow-up approved
those corrections for scoped runtime. The original compile receipt retains its
original candidate identity.

The [native pipeline probe](../packaging/gstreamer-rpu/rpu-pipeline-probe.c) is
executed after independent source and correction review. The final narrow
parameter-set HEADER classifier was independently reviewed as well.
It accepts `avdec_h265` or `vah265dec` plus a real MP4 HEVC fixture. Its two normal
`h265parse` stages surround an injection that removes selected RPU NALs while
retaining the old meta deliberately. An independent Annex-B scanner records the
expected remaining RPU. The second parser and decoded buffers must match it by
PTS. After 30 output pictures the probe performs a flushing seek. Its input epoch
advances at the upstream flush boundary; input reopens at FLUSH_STOP, while
decoder output remains excluded until the decoder's new SEGMENT. This allows
the parser to receive the first new buffer before releasing its queued segment.
The probe requires 60 further pictures, observed coded-order PTS reordering, RPU gaps and at least
two distinct original RPU values. A missing element or insufficient fixture is
inconclusive, not a pass. Optional `rotate-180` mode inserts the normal native
`vapostproc`, verifies its 180-degree direction setting, requires the same pixel
format and visible dimensions, and asserts that its output has no original RPU
meta. A negotiated conversion or resize is inconclusive for that orientation
negative because it could remove the meta for another reason. This is a test
instrument, not a product launch path.

The completed [native receipt](../evidence/gstreamer-rpu-transport-native-20261107.json)
records the following observed results:

| Native decoder/path | Matched pictures before/after flushing seek | RPU gaps | Other observations |
|---|---|---|---|
| `avdec_h265` | 30 / 60 | 12 | Reordered coded PTS; eight distinct original RPU values; no mismatches |
| Intel `vah265dec` | 30 / 60 | 12 | Same reorder/ownership contract; actual Intel i915/iHD path; no mismatches |
| Intel VA plus native `vapostproc` 180-degree rotation | 30 / 60 | 12 | 90 transformed buffers with unchanged format/dimensions and no original RPU meta |

A legitimate, separately emitted VPS/SPS/PPS HEADER exposed a probe defect on
the first software run. The final classifier accepts only no-PTS, explicitly
HEADER-marked, nonempty parameter-set-only buffers without RPU meta. Picture,
RPU-bearing or unknown untimestamped buffers still fail. Failed runs are
preserved in private receipts. This changed the probe, not the transport code.

Both source series also replayed cleanly from the authenticated, pinned Ubuntu
archives, reproduced their base and candidate trees and compiled from those
exact replay trees. Loaded runtime objects and the signed native package floor
were recorded; package file verification reported no differences. Tests used
isolated library/plugin staging and no display or host installation.

The following merge/release evidence remains required beyond this scoped run:

1. Check NAL-aligned output, duplicate/oversize RPUs, copied regions and
   dimension-changing output explicitly. Those paths must not publish a
   misleading per-picture meta; this supplementary matrix has not run.
2. Complete the normal-feature packaging, symbol and multiarch obligations
   below before treating this compiler/runtime candidate as an installable
   system update. Preserve the transport and its independent review when
   adding the reconstruction phase.

Rendering, optical agreement, protected streaming and system-wide application
coverage require their own later phase evidence. No source equation or private
mapper arithmetic is part of this transport change.

## 5. Durable packaging preserves the signed Ubuntu feature floor

This is a packaging scope, not a package-delivery receipt. The minimal feature
build establishes a compiler loop only and must not become a replacement for
Ubuntu's normal feature configuration.

| Source package | Planned candidate artifacts | Compatibility obligation |
|---|---|---|
| `gst-plugins-base1.0 1.28.7-1` | Normal base runtime/development packages, including additive GstVideo meta API | Keep the stock SONAME and all existing exported symbols/features; add the three new API symbols to the candidate symbols file |
| `gst-plugins-bad1.0 1.28.6-1ubuntu1` | Normal bad plugin packages, with the native HEVC parser change | Build and run against the exact matching candidate base runtime/development package |

The unpublished API creates an exact-version dependency between candidate bad
and base packages. A later stock base version cannot be assumed to contain it.
Declare that dependency in packaging; a global APT pin or forced plugin rank
is not a substitute. Preserve the exact signed stock `.deb` files, complete
source archives, build options, hashes and rollback transaction in durable
private output storage. Do not commit signed packages or signing material.

If the host co-installs a `Multi-Arch: same` base runtime for i386, qualification
and compatible candidate packages for both architectures are needed before a
transaction can replace it. Removing the other architecture to make an amd64
package install is not within this proposal. Simulate the eventual exact
transaction and inspect reverse dependencies before any host install.

Before packaging, perform a clean native source replay with the pinned archives
and both exported patch series. Require the base and candidate trees recorded
in the registry, then compile that exact replay. Preserve the source replay and
runtime qualification receipts with the packages. Runtime tests must identify
the actual loaded candidate GstVideo/parser and signed native decoder binaries;
plugin discovery or a successful compiler exit alone is insufficient.

The later reconstruction phase must consume the GTK owner's existing preferred
surface feedback snapshot and generation. Use the raw physical declared black,
peak, reference-white luminance and xy data coherently for pre-mapping and
output signalling. For example, a physical 616 cd/m² target at 142 cd/m²
reference white is not the normalized 880.6 cd/m² value another consumer might
report. Neither normalization nor a generic HDR default may replace the actual
physical target. This transport phase does not yet consume that bridge.

## 6. The next normal-player hook is reconstruction before conversion

Use the compatible floor already inspected: GStreamer core/base/libav
`1.28.7-1`, bad/extra `1.28.6-1ubuntu1`, FFmpeg `8.1.2-2ubuntu2`,
`libdovi3 3.3.2-3`, GTK `4.24.1+ds-1` plus the independently qualified target
snapshot extension, and `rust-gst-plugin-gtk4 0.15.2-1ubuntu2`. The latter builds
`gstreamer1.0-gtk4` with `gtk_v4_20`, Wayland EGL, DMA-BUF and GStreamer 1.28
features enabled in its normal Debian rules.

The next atomic source phase should publish a complete owned reconstruction
snapshot per codec frame, separate from the original raw RPU meta:

1. In `gst-libav/ext/libav/gstavviddec.c::gst_ffmpegviddec_video_frame`, capture
   the public decoder-resolved `AVDOVIMetadata` before `av_frame_unref`, using
   that output picture's existing `opaque_ref` association. Preserve canonical
   public values, not a private context dump or a borrowed `AVFrame`.
2. For native VA, resolve source mapping and static/reference metadata in
   decode order in the `GstH265Decoder` picture path, then retain that complete
   snapshot through the existing picture/codec-frame association and DPB reorder.
   Validate the public parser/header ABI against the exact libdovi source;
   raw parsing alone does not resolve inherited mapping or compressed/indirected
   DM state. Compare its snapshots with the software decoder on the same input
   and require explicit flush/missing-reference negatives. Neither native stock
   decoder is evidence that a FEL enhancement residual has been reconstructed.
3. A downstream renderer must negotiate both this resolved source contract and
   an available actual-surface target. Select the insertion point from the
   negotiated memory/format path. Do not blindly force `glcolorconvert` or assume
   a late RGBA buffer still contains the original coded Dolby signal.

The existing normal GTK sink entry is
`src/sink/imp.rs::PaintableSink::show_frame` (around line 786), which constructs
`Frame::new`. Its `src/sink/frame.rs::videoinfo_to_color_state` (around line 319)
sets only CICP range, matrix, transfer and primaries. GL, memory and DMA-BUF
texture builders later use that color state. A resolved Dolby master and a
correct target are required before those ordinary conversions/scales consume
or discard the coded signal. A matching output color-state/reference-white
contract is also required; the inspected CICP-only helper does not supply it.

The target extension is declared in `<gdk/wayland/gdkwayland.h>` through
`gdkwaylandsurface.h`:

```c
gboolean gdk_wayland_surface_get_color_target (GdkSurface *surface,
                                               GdkWaylandColorTarget *target);
```

Its caller-owned snapshot contains `generation`, `identity`, physical xy
primaries/white and black, peak and reference-white luminance in cd/m². Read it
on GTK's main context, then copy values into synchronized sink state. Handle
every `color-target-changed` signal: invalidation and subsequent ready state
can share a generation. When unavailable, only generation is meaningful.

Two GTK limits are prerequisites for an ordinary default player path. The
inspected stock GTK backend enables color-manager binding only under its
`color-mgmt` debug setting, so default target availability requires a separately
reviewed default/target-only binding policy; a user debug variable is not the
product solution. Also, DMA-BUF offload uses a private subsurface with another
`wl_surface`. Negotiate that actual owner or use normal composition for the
affected mapped frames. The parent surface's target cannot be assumed to apply,
and globally disabling offload is outside the contract. No host app has been
installed to claim normal Showtime playback from this transport work.

## Supplementary transport controls

A full buffer copy retained the RPU and partial copies dropped it. NAL-aligned parser output carried no picture-level metadata. Duplicate and oversized RPU inputs each produced 24 timestamp-matched pictures with stale metadata removed. The first VA resize also changed colorimetry, so it could not isolate resizing. The corrected fixture negotiated the decoder’s original colorimetry and pixel format. All 26 matched pictures changed dimensions and dropped their RPU. [Original controls](../evidence/gstreamer-rpu-supplementary-first-run-20261107.json) · [Isolated resize](../evidence/gstreamer-rpu-supplementary-va-run-20261107.json).
