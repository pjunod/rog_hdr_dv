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

Independent review found two defects in the first proposal: the probe waited
for a parser's queued SEGMENT before admitting the buffer that releases it,
and the raw meta omitted its orientation tag. The
[correction receipt](../evidence/gstreamer-rpu-corrections-compile-20261107.json)
records corrected source and probe compilation. The original compile receipt
retains its original candidate identity. Fresh review remains pending.

The [native pipeline probe](../packaging/gstreamer-rpu/rpu-pipeline-probe.c) is
written and compiled, not executed. Review it and the source before running it.
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
