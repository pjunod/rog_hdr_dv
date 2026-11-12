# GStreamer resolved Dolby pictures

**Updated November 9, 2026.** The native picture contract carries frame-owned metadata through software, Intel VA and NVIDIA decoding. The uninstalled NVIDIA/GTK Profile 7 FEL candidate now pairs decoded enhancement planes with the exact base picture and passed private-compositor pixel and seek controls. Its producer is part of the active five-patch Ubuntu source series. The coherent 18-package candidate family built normally and remains uninstalled; it is separate from the installed 45-package November 9 release. [Native FEL scope and controls](../evidence/gstreamer-native-fel-20261109.json) · [Current installation status](STATUS.md).

## Browser destination interface in development

The source candidate adds an explicit logical100nit BT709/sRGB destination
without changing the native DISPLAY_PQ witness requirement. The additive
destination API preserves the existing core ABI and legacy entry points.
Retained pictures keep their original dimensions and picture identity when a
later destination requests a different output layout. The marked reverse caps
query now derives each input candidate through its actual graded output before
intersecting downstream constraints; unmarked passthrough remains unchanged.

The extended negotiation probe exercises actual linked pad queries, normalized
peer answers, output format/memory/width restrictions, and separate marked
configurations. Runtime and normal-package qualification of this new source
remain pending. These source changes do not grant native HDR browser delivery
or physical panel acceptance. Browser source/track/CDM lifecycle qualification
and stream-qualified VA selection are separate required parts of that work.

## Normal GNOME playback

The staged Showtime, GTK4 paintable sink and shared mapper compiled on Ubuntu. Ordinary Showtime opened a genuine Profile 5 title and selected NVIDIA's HEVC decoder on the ROG. That decoder omitted the Dolby configuration at its output after the upstream MP4 demuxer and HEVC parser had carried it correctly. The player used its ordinary rendering path. The separate software decoder kept the configuration. The corrected NVIDIA producer subsequently retained all 95 decoded pictures across configuration changes, matched software decode for the crop control and reached the mapper through ordinary Showtime’s default decoder selection. [NVIDIA controls](../evidence/gstreamer-nvidia-picture-qualification.json). A rendered-grade claim requires the default decoder to preserve its own decoded picture and the authored change to reach the measured window. [Implementation and build evidence](../evidence/gstreamer-gtk-consumer-source-freeze-20261108.json).

### Rebuild the GNOME consumers

Use fresh Ubuntu source extractions for `rust-gst-plugin-gtk4` and `showtime`. The pinned input inventory records the exact Ubuntu versions and hashes of their source descriptors. Put the extracted Rust source at `source/` and Showtime at `showtime-50.0/` under one build directory. [Pinned Ubuntu metadata](../packaging/gstreamer-gtk-dovi/package-inputs/provenance.json).

From each extracted source root, import each listed patch into its Debian quilt series and apply it with `QUILT_PATCHES=debian/patches quilt push`. The ordering below matters because the paused-frame code builds on the paintable’s native-picture support.

| Source | Patches in application order |
|---|---|
| Rust GTK4 paintable sink | [16-bit textures](../packaging/gstreamer-gtk-dovi/0002-gtk4paintablesink-preserve-16bit-rgba.patch), [native-picture retargeting](../packaging/gstreamer-gtk-dovi/0003-gtk4paintablesink-retarget-visible-native-pictures.patch), [visible overlay compositions](../packaging/gstreamer-gtk-dovi/0005-gtk4paintablesink-retain-visible-overlay-compositions.patch), [HDR or SDR redraw destinations](../packaging/gstreamer-gtk-dovi/0006-gtk4paintablesink-declare-HDR-or-SDR-redraw-destinations.patch) |
| Showtime | [Bind the surface target before conversion](../packaging/gstreamer-gtk-dovi/0001-showtime-bind-native-target-before-gl-conversion.patch), [explicit SDR producer destination](../packaging/gstreamer-gtk-dovi/0007-showtime-start-the-shared-producer-with-an-explicit-SDR-destination.patch) |

Run `python3 packaging/gstreamer-gtk-dovi/prepare-ubuntu-packages.py BUILD_DIRECTORY` from this repository. It derives the control, rules and changelog files from the pinned inputs. Build the native mapping core and development package first, then build the sink and Showtime with their declared dependencies and `dpkg-buildpackage`. The mapper and the sink must use the same core ABI. The mapper accepts eleven system-memory pixel formats. On the ROG it also reads NV12 and P010 through GStreamer’s CUDA and VA allocators. Both accelerator paths produce full-range RGBA64 BT.2020/PQ in system memory. [Native mapper package and GPU checks](../evidence/gstreamer-gtk-mapper-negotiation.json).


## What the producer publishes

`packaging/gstreamer-dovi/bridge` owns immutable `GstDoviPicture` values. Public
libavutil allocators/accessors copy complete metadata into owned storage;
original escaped RPU bytes remain owned beside it. Helper ABI2 and pkg-config
version 0.2.0 depend on exact SDK/runtime versions. No FFmpeg structures are added
to the public GstVideo ABI.

The FFmpeg extension exposes an opaque RPU resolver and opt-in HEVC
`dovi_metadata_strict`. CRC and missing-reference errors clear Dolby state while
ordinary video keeps its existing error policy. Default FFmpeg metadata has no
strict provenance and cannot create a picture. The v2 marker accompanies exact
current-frame raw RPU plus coded size and SPS conformance rectangle, captured
before generic frame cropping. Ignored cropping or extra display-window crops
prevent that marker. The bridge never parses RPU through libdovi.

avdec copies the matched received AVFrame **before** unref. It requires the full
active image, validates chroma sample alignment, and materializes conformance
crops from the actual cropped AVFrame planes. Low-resolution, rounded/partial
cropping and sample-depth mismatches prevent publication. VA resolves the matched
AU in decode order and owns the result on the exact GstH265Picture through
reordering. Its snapshot is attached only after output geometry is validated.
An RPU gap emits no snapshot. Neither constructor claims verified FEL residual
participation; consumers must decline an unreconstructed residual.

## Profile 7 native source and digital qualification

The active [NVIDIA producer patch](../patches/ubuntu-gst-plugins-bad-rpu/0005-nvcodec-decode-and-bind-matched-profile7-enhancement-pictures.patch) follows the four existing patches. The bridge and GTK mapper support progressive, single-track Profile 7 with a half-resolution Main10 enhancement layer and compatibility ID 6. The full Ubuntu source import reproduces the pinned base and preceding four-patch tree. [Source pins](../sources.json) identify all five patches and the complete resulting source tree; they do not advertise the local import commit as a fetchable upstream revision.

The decoder sends each extracted enhancement AU with a reference to the exact resolved base picture. FFmpeg returns that reference through picture reordering. The producer retains decoded planes on the output buffer and full-buffer copies, while still reporting the residual as unreconstructed. Flush, discontinuity and configuration changes release pending references. Default file playback reserves one 16-picture HEVC reorder window and drains the secondary decoder at EOS. An explicit NVIDIA display-delay setting or live input retains the requested latency.

Ordinary decodebin selected the candidate NVIDIA decoder and paired all 70 pictures before and all 70 after a flushing seek. Full-buffer copies retained their decoded enhancement pixels. Direct bridge controls preserved all 70 per-picture pixel hashes with duplicate or absent presentation timestamps. A missing enhancement AU and an invalid enhancement NAL header each left the affected picture unpaired. Resetting with ten pending pictures produced no stale pairs, and replay restored all 70 expected hashes.

The actual GTK path uploaded both layers, and the provider accepted a composed 3840×2160 master at a declared 616 cd/m² destination. At the same one-second picture, a flush seek preserved both the RGBA64 output and the independent ten-bit PQ compositor capture byte for byte. The missing-EL control retained all 70 original coded base pictures, RPU bytes and timestamps; only enhancement NALs were removed. It reached ordinary base conversion without provider mapping. FEL and missing-EL output differed across 2,667,662 of 2,764,800 visible channel samples. Profile 5 still mapped without an enhancement layer, and SDR selected no Dolby mapping. [Aggregate digital receipt and limitations](../evidence/gstreamer-native-fel-20261109.json).

The normal Ubuntu builds produced 18 amd64/all packages: bridge `0.2.0+rogdv2`, core/mapper `0.1.0+rogdv4`, bad plugins `1.28.6-1ubuntu1+rogdv3`, sink `0.15.2-1ubuntu2+rogdv4.2` and Showtime `50.0-2+rogdv4.2`. The normal public package preparer uses the actual bad/extra outputs and advances the exact client dependencies together. Complete private rollback archives preserve the prior build slots and package outputs.

A separate GtkVideo trial used the extracted bridge/core/bad packages and reached its 2.999666-second EOS in 3.069 seconds after explicit play. Visible native redraws mapped pictures from the beginning through the end of the clip. This diagnostic rendered seven sink frames and dropped thirteen while LOG-level code hashed and scanned every visible 4K frame. It establishes clock progression and no delayed-output hang, not clean 24 fps. The upstream per-stream baseline conversion is expected before each view applies its own grade. Normal-logging throughput and runtime qualification of the matching rebuilt clients remain open; further GPU trials are stopped.

## Browser runtime fixes (November 11)

Qualifying ordinary WebKit `<video>` found five producer and mapper defects that no earlier
client exercised. Each is fixed at its cause:

- **VA stream-lock deadlock.** [0008](../patches/ubuntu-gst-plugins-bad-rpu/0008-va-renegotiate-qualified-output-without-the-stream-lock.patch)
  removes the `src_event` handler, which took the decoder stream lock on RECONFIGURE. That lock
  deadlocked against a downstream queue that was answering the decoder's serialized allocation
  query. Qualified output is now recomputed on every negotiation.
- **Shallow accept-caps.** [0010](../patches/ubuntu-gst-plugins-bad-rpu/0010-va-prove-marked-output-against-the-whole-linked-consumer-chain.patch)
  proves a marked output against the whole linked chain with a filtered CAPS query.
  Both queries are issued directly, so a linked peer that fails either query counts as
  a rejection (the pad helpers would read a failed query as acceptance).
  Passthrough converters answer ACCEPT_CAPS from their pad templates, so a tiled DMABuf that
  the mapper must refuse had been accepted. The VA producer is versioned `1.28.6-1ubuntu1+rogdv6`.
- **Identity allocation.** The mapper core (`0.1.0+rogdv6`) now forwards an identity allocation
  query downstream. Previously it answered the query itself, and VA/DMABuf producers lost
  VideoMeta even for ordinary SDR video.
- **Negotiation before stream start (`0.1.0+rogdv7`).** decodebin answers a producer's
  pre-exposure queries through playbin's sink, before any stream event reaches the mapper.
  - A marked query is therefore qualified by an identical clear proof of the current revision
    until a stream starts.
  - Unfiltered reverse answers also offer the importable domain, marked with its exact
    configuration, because deinterlace forwards queries without their filter.
  - A newer revision that only awaits the started stream's own restart (a browser advances
    per seek) no longer triggers renegotiation inside the flush.
- **Explicit SDR destination.** This path had never rendered. libplacebo cannot sample a
  download-only render target, so the graded PQ intermediate now has its own sampleable
  textures.
- **One Vulkan device per process (`0.1.0+rogdv8`).** Every mapper used to create its own
  Vulkan instance and device on its first picture. In the browser, the compositor's mapper did
  so on the first visible frame, which took about 450 ms on the ROG. The pipeline waited, and the
  decoder dropped the opening 14–16 pictures as late. Mappers now share one device and one shader
  cache, because the Vulkan `pl_gpu` is thread-safe. Renderers, textures and the provider stay
  per mapper, and a GPU that is not thread-safe keeps a device per mapper. Showtime's sink-side
  mapper shares the device in the same way.
- **Decoder pictures released off the consumer's thread (`0.1.0+rogdv9`).** A retained native
  frame holds the decoder's own picture, and a consumer drops it on its presentation thread. The
  last reference to an NVDEC picture finalizes the decoder's CUDA context. On WebKit's compositor
  thread, that left later ordinary video in the same web process unpresented. The core now releases
  decoder pictures on a thread of its own.
- **SDR-mode displays in the GTK sink (`0.15.2-1ubuntu2+rogdv5.5`).** The sink requested a PQ
  redraw destination whenever the view had all native witnesses, including a display in SDR mode
  (target peak 80 cd/m²). The mapper grades PQ only above the 203 cd/m² reference, so Profile 5
  failed in Showtime with "Profile 5 cannot use ordinary base-layer color conversion". The sink
  now requests the SDR destination for a target at or below the reference. Showtime moves to
  `+rogdv5.7` for the exact pin.
- **Intel-decoded Dolby video in Showtime (good `1.28.7-1build1+rogdv3`).** Playsink puts its
  deinterlacer between the decoder and the mapper. The deinterlacer asked downstream what it
  accepts without the decoder's candidates, so the mapper could only answer for unknown input
  and did not offer VA memory for a marked stream. The VA decoder then chose DMABuf, which the
  mapper cannot import, and the stream stopped. The deinterlacer now forwards the candidates,
  relaxed only by what it can change itself (interlacing, field order, frame rate and the
  interlaced-format feature).
- **Subtitles over Dolby video (`0.1.0+rogdv10`, base `1.28.7-1+rogdv3`).** Playsink's subtitle
  overlay offers each memory domain with and without the overlay composition meta. The mapper
  accepted only the plain domains, and playsink's converter bin then dropped the caps features
  of each candidate before asking downstream, so VA memory with an overlay was asked about as
  system memory. With VA decoding and subtitles the stream failed to negotiate. The mapper now
  accepts each native domain with the meta too, paired with a graded output that declares it, and
  carries the overlays to the sink; the converter bin keeps the candidates' features. The sink
  and Showtime moved to `+rogdv5.6` and `+rogdv5.9` for the exact pins (`+rogdv5.8` was a
  withdrawn candidate that bypassed playsink's converters and therefore also its subtitles and
  deinterlacing).
- **Intel VA picture copies (bad `1.28.6-1ubuntu1+rogdv8`).** GStreamer's VA allocator copies a
  decoded picture with `vaCopy` whenever the driver answers the copy-capability query, without
  reading the answer. iHD on Meteor Lake answers that it supports no copy mode and then crashes
  inside `vaCopy`. WebKit deep-copies the current picture at every flush, so a seek or source change
  with Intel decoding could kill the web process. The allocator now uses `vaCopy` only when a copy
  mode is reported, and otherwise copies through a VA image. Showtime moves to `+rogdv5.10` for the
  exact pin. The driver side (iHD crashing in an operation it reports as unsupported,
  instead of returning an error) belongs upstream at intel/media-driver.
- **NVDEC pictures stay on the GPU in Showtime (bad `rogdv8`).** The NVIDIA decoder chose its output
  memory from downstream's answer for its unmarked template. Behind playsink, the mapper answers
  unmarked caps for the ordinary path behind it (GL memory), which a marked stream cannot take, so
  Dolby pictures fell back to system memory and were downloaded before mapping. For a Dolby stream
  the decoder now asks about the marked output it will produce, and the mapper receives CUDA memory.
- **Vulkan devices destroyed off the consumer's thread (`0.1.0+rogdv10`).** The last mapper out
  destroyed the shared Vulkan device on whatever thread freed it. Destroying the instance unloads
  the NVIDIA driver library, which releases that thread's current EGL context; on WebKit's main
  thread that left Skia without a context and crashed the tile painter after a source change. The
  core now destroys devices on a thread of its own, one at a time.

The [negotiation probe](../packaging/gstreamer-gtk-dovi/negotiation-probe.c) passes 169 checks,
including the pre-start, unfiltered-reverse and overlay-pairing controls. The coherent family is
core `0.1.0+rogdv10`, sink `0.15.2-1ubuntu2+rogdv5.6` and Showtime `50.0-2+rogdv5.10`, with the
base `rogdv3`, good `rogdv3` and bad/extra `rogdv8` pins in [qualified-pipeline.json](../packaging/gstreamer-gtk-dovi/package-inputs/qualified-pipeline.json).
Browser results are in [WebKitGTK clear video and native HDR](WEBKIT_NATIVE_HDR.md#runtime-qualification).

These runs used private process overlays and owned GPU-backed compositors, not the user's desktop. They establish digital composition and same-picture retention, not physical panel accuracy or browser playback. No candidate package was installed on the host; the installed 45-package release is unchanged.

## Which geometry reaches the mapper

`GstDoviGeometry` contains coded width/height and active x/y/width/height in luma
pixels. `get_dimensions()` returns the active dimensions. This rectangle is an
SPS source fact, independent of later transformations.

avdec cropped output is materialized at 0,0 with active caps. VA also advertises
active caps, but GstVideoMeta may retain coded storage dimensions and
GstVideoCropMeta the source active rectangle. The consumer must bound reads by
the mapped storage and honor that crop once. When VA already copied the active
image, no crop remains and its VideoMeta dimensions equal active caps. Applying
the original source offset again would crop the image twice. Size, orientation
and colorspace tags prevent ordinary transformed buffers from retaining this
source snapshot; native 180-degree rotation was checked explicitly.

## Normal package producer checks

Nine checks passed with the actual software, Intel VA and NVIDIA modules from the rebuilt packages on the ROG. All three decoders preserved the same 95 pictures across a change of configuration. A native NVIDIA pixel transform cleared the original color metadata. The NVIDIA decoder also left ordinary HEVC free of Dolby metadata. The [pipeline probe](../packaging/gstreamer-dovi/tests/picture-pipeline-probe.c) accepts each of these decoder names. [Package check scope](../evidence/gstreamer-nvidia-picture-qualification.json).

## High-precision GL color balance

Ubuntu’s GL color balance previously accepted only RGBA8. The normal GStreamer base package now also accepts normalized RGBA64. Neutral processing preserves the native picture and all 4,096 levels in a 12-bit ramp. Nonneutral brightness, contrast and saturation produce more than 256 levels and clear the original picture’s color-dependent metadata. The versioned source package carries the change in its Debian quilt series. The public reconstruction produces the complete unpacked source tree of `gst-plugins-base1.0 1.28.7-1+rogdv2`. [Measurements](../evidence/gstreamer-gtk-private-development-20261108.json) · [Source registry](../sources.json).

## How container configuration stays attached

The common GstPbutils parser validates exact `dovi-configuration` GstBuffer
payloads from each dvcC/dvvC sample description. Payloads 4–24 bytes are transported
losslessly; the ABI2 bridge conservatively qualifies a complete public record
only at 24 bytes. Abbreviated or absent records remain UNKNOWN, including
compatibility. The profile getter otherwise reports an RPU-header guess.

avdec stores record, bytes and generation on the originating CodecFrame. Every
HEVC AU receives an explicit AV_PKT_DATA_DOVI_CONF: absent/incomplete configuration
sends a zero record, never an ambiguous no-update. A strict decoder resets only
Dolby state when that tuple changes. Metadata-only caps changes do not reset
ordinary HEVC references; all other existing reset fields remain effective.
Raw output caps follow the matched output frame's configuration through reorder.

VA handles successful CAPS after its parent updates input_state, resets old
snapshot generations on configuration transitions, and rebinds the resolver and
output state even without new SPS geometry or SEGMENT. Flush invalidation occurs
in serialized callbacks. The next SEGMENT revalidates explicit caps for a seek
within the same stream; new-stream/caps absence cannot inherit an old record.
Nonserialized FLUSH_START does not race plain streaming-state flags.

## What was qualified

The [final compile receipt](../evidence/gstreamer-dovi-producers-final-compile-20261107.json)
binds source trees, actual compiler-source bytes and artifact hashes. A stale
warm-build src symlink was detected and corrected before final qualification;
earlier provisional clean-chain claims are superseded by that explicit proof.

The [direct controls](../evidence/gstreamer-dovi-producers-direct-20261107.json)
cover missing references, unmarked default frames, owned resolver reset/refresh,
complete/abbreviated/absent records, reserved 2 versus defined extended 3, and
conformance/geometry rejection. A genuine Profile5 clip and its SPS-only crop
mutation exercise uncropped 1920×1080 and active 1888×1078 at (32,2). An odd 4:2:0 origin of 1 pixel
was rejected during fixture writing; forged odd/overflow/missing geometry and
IGNORE_CROP cannot publish. These mutations are structural regressions, not
new authored Dolby image references.

The [native receipt](../evidence/gstreamer-dovi-producers-native-20261107.json)
records software and Intel VA association, gaps, reorder, flushing seek,
retained-picture lifetime, conformance and rotation negatives. Same-SPS CAPS-only
removal/replacement preserves 95 inputs and 95 outputs in both decoders; each control
and transition has identical normalized pixel hashes and correct per-picture
and raw-caps configuration. The failing 95→63 witness before correcting the
existing libav reset comparison is retained. The
[live-clear negative](../evidence/gstreamer-dovi-live-clear-20261107.json) also
proves that mapping ID 0 from before a configuration clear cannot satisfy a later
reuse instruction, while ordinary decoded pixels remain unchanged.

## How the frozen sources enter the package chain

The [source registry](../sources.json) records the Ubuntu base, bad, libav and FFmpeg series. The video and pbutils library provides `rog-gstreamer-dovi-base-api (= 1)`. Both 32-bit and 64-bit codecs provide `rog-dv-hevc-runtime (= 2)`. The bridge package requires these capabilities for per-frame ownership and configuration transitions. Its development package includes the public header and pkg-config file. [Source and dependency contract](../packaging/gstreamer-dovi/DEPENDENCIES.json).

Normal rendering remains a separate consumer qualification: native source
reconstruction must precede ordinary GL color conversion, and mapping must use
the actual surface target with reference white, physical peak and generation
kept distinct. A resolved snapshot alone never establishes reconstructed pixels.
