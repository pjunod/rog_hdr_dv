# GStreamer Dolby transport — keep each RPU with its decoded picture

**Status:** compile-only candidate; independent review and runtime qualification
pending · **Written:** 2026-11-07.

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
meta. Its colorspace and size tags allow pixel-changing converters to remove
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
on the pinned floor. This is source evidence; runtime association remains open.

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

The [native pipeline probe](../packaging/gstreamer-rpu/rpu-pipeline-probe.c) is
written and compiled, not executed. Review it and the source before running it.
It accepts `avdec_h265` or `vah265dec` plus a real MP4 HEVC fixture. Its two normal
`h265parse` stages surround an injection that removes selected RPU NALs while
retaining the old meta deliberately. An independent Annex-B scanner records the
expected remaining RPU. The second parser and decoded buffers must match it by
PTS. After 30 output pictures the probe performs a flushing seek; it requires
60 further pictures, observed coded-order PTS reordering, RPU gaps and at least
two distinct original RPU values. A missing element or insufficient fixture is
inconclusive, not a pass. This is a test instrument, not a product launch path.

After independent review, record these checks before merge:

1. Run the probe against the exact candidate parser/video library and each
   native decoder, with no fallback decoder substitution. Record loaded library
   identities, source/fixture hashes, commands and full logs.
2. Observe both reorder and flush/gap negatives passing, including the retained
   stale upstream meta being removed from an AU with no RPU.
3. Check NAL-aligned output, duplicate/oversize RPUs, copied regions and
   dimension-changing output explicitly. Those paths must not publish a
   misleading per-picture meta.
4. Reconstruct both patch series from the signed artifacts and run the
   repository fast lane after review. Do not convert compile-only receipts into
   runtime acceptance.

Rendering, optical agreement, protected streaming and system-wide application
coverage require their own later phase evidence. No source equation or private
mapper arithmetic is part of this transport change.
