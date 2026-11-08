# GStreamer resolved Dolby pictures

**Status:** independently reviewed producer scope passes native software and Intel
VA checks; unshipped. This qualification covers source metadata ownership,
configuration transitions and conformance geometry. It establishes no normal
player rendering, image-grade accuracy, package release or host installation.

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
