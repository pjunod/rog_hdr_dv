# GStreamer resolved Dolby pictures

**Status:** independently reviewed producer scope passes native software and Intel
VA checks; unshipped. This qualification covers source metadata ownership,
configuration transitions and conformance geometry. It establishes no normal
player rendering, image-grade accuracy, package release or host installation.

## Normal GNOME playback

The staged Showtime, GTK4 paintable sink and shared mapper compiled on Ubuntu. Ordinary Showtime opened a genuine Profile 5 title and selected NVIDIA's HEVC decoder on the ROG. That decoder omitted the Dolby configuration at its output after the upstream MP4 demuxer and HEVC parser had carried it correctly. The player used its ordinary rendering path. The separate software decoder kept the configuration. The corrected NVIDIA producer subsequently retained all 95 decoded pictures across configuration changes, matched software decode for the crop control and reached the mapper through ordinary Showtime’s default decoder selection. [NVIDIA controls](../evidence/gstreamer-nvidia-picture-qualification.json). A rendered-grade claim requires the default decoder to preserve its own decoded picture and the authored change to reach the measured window. [Implementation and build evidence](../evidence/gstreamer-gtk-consumer-source-freeze-20261108.json).

### Rebuild the GNOME consumers

Use fresh Ubuntu source extractions for `rust-gst-plugin-gtk4` and `showtime`. The pinned input inventory records the exact Ubuntu versions and hashes of their source descriptors. Put the extracted Rust source at `source/` and Showtime at `showtime-50.0/` under one build directory. [Pinned Ubuntu metadata](../packaging/gstreamer-gtk-dovi/package-inputs/provenance.json).

From each extracted source root, import each listed patch into its Debian quilt series and apply it with `QUILT_PATCHES=debian/patches quilt push`. The ordering below matters because the paused-frame code builds on the paintable’s native-picture support.

| Source | Patches in application order |
|---|---|
| Rust GTK4 paintable sink | [16-bit textures](../packaging/gstreamer-gtk-dovi/0002-gtk4paintablesink-preserve-16bit-rgba.patch), [native-picture retargeting](../packaging/gstreamer-gtk-dovi/0003-gtk4paintablesink-retarget-visible-native-pictures.patch), [visible overlay compositions](../packaging/gstreamer-gtk-dovi/0005-gtk4paintablesink-retain-visible-overlay-compositions.patch) |
| Showtime | [Bind the surface target before conversion](../packaging/gstreamer-gtk-dovi/0001-showtime-bind-native-target-before-gl-conversion.patch) |

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
