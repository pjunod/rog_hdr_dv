# Stage-1 headless display-management harness

Status: implementation in progress; Python contracts/metric/CLI and regression
source are written and syntax-compiled. Native API compiler prerequisite and
renderer implementation are pending. No units or rendering probes have run.
This is the first stage of [the open track](OPEN_DV_DISPLAY_MANAGEMENT.md),
not a Dolby Vision processor, reference agreement or certification claim.
Programme-wide status and README indexing belong to the integration lane.

## Scope and interfaces

The harness accepts one progressive, already decoded frame plus explicit source,
mastering, target and optional **already parsed** real Dolby metadata. It drives
libplacebo 7.360.1 baseline rendering without a window, swapchain, compositor or
physical device. It does not decode video, parse a binary RPU or implement trims.
A private extraction step must supply the existing `pl_dovi_metadata` fields,
as produced by the pinned upstream `pl_map_avdovi_metadata` adapter. The full
original RPU is retained privately and hash-bound beside that exported JSON;
level-2/8 trims are not applied by this baseline. Export provenance is a caller
attestation, not a claim that the harness can authenticate ownership or prove
that exported coefficients match the original RPU.

Public fixtures contain no RPU, fake metadata, identity trims or Dolby tool
outputs. No absent metadata silently falls back to RGB or HDR10 when the source
system says `dolbyvision`. No private reference is required to build stage 1.

### Frame manifest (schema 1)

See `tools/dolby_harness/contracts.py` for exact fields and rejection rules,
and `tools/dolby_harness/make_fixture.py` for a complete metadata-free example.
Unknown fields, duplicate JSON keys and nonfinite numbers are errors.

- `frame`: `input` (`file`, lowercase SHA256), width, height, index, exact
  rational `pts` (`num`, `den`), and a content identity. Width is 1..3840 and
  height 1..2160. No cropping, resizing, alignment search or interlacing.
- Input layout `c3-f32le`: tightly packed three-component IEEE754 binary32,
  little endian, top row first, left-to-right pixels. The components are RGB,
  Y/Cb/Cr or the Dolby base-layer channels according to `source.system`.
  Values are finite normalized digital samples in [0,1], with no automatic
  normalization or clipping. `source.bit_depth` is 8, 10, 12 or 16 and records
  the original normalization divisor `2^bit_depth-1`; it is passed to
  libplacebo for exact limited-range and chroma-centre interpretation. Float
  storage does not assert that samples were quantized at this nominal depth.
- `source`: system `rgb`, `bt2020nc` or `dolbyvision`, PQ transfer, BT.2020
  primaries, explicit full/limited range, bit depth, layout, orientation,
  and `mastering` (`min_nits`, `max_nits`, eight raw chromaticities).
- `target`: descriptive id, minimum and maximum in cd/m², and eight raw
  chromaticities in order rx/ry/gx/gy/bx/by/wx/wy. Finite physical xy values,
  nondegenerate primary triangle and an interior white are required. No EDID
  is read and no panel properties are invented.
- `metadata`: null for non-Dolby input; otherwise the contract below.

The output encoding is always full-range PQ BT.2020 RGB-f32le, top-left origin.
Target mastering-volume declarations are separate from the BT.2020 signal
encoding. A target gamut is not relabelled as the encoding. All source/target
values and frame/source/metadata hashes are carried into the candidate receipt.
The harness supplies zero minima unchanged to libplacebo; upstream treats zero
as unknown and may infer its nominal black. This upstream inference is recorded
as a baseline limitation, not a measurement of zero black.

### Private parsed metadata contract

`metadata` contains:

- `export`: file and SHA256 for parsed JSON below.
- `rpu`: file and SHA256 for the original, real frame-associated RPU.
- `origin`: `owned-real-content` or `dolby-tools` (caller provenance assertion).
- `frame_index` and `pts`, exactly equal to the decoded frame identity.

The exported schema-1 JSON fields map directly to `pl_dovi_metadata` in the
7.360.1 public header: `nonlinear_offset` [3], row-major `nonlinear` and `linear`
[3][3], and three `comp` objects. The export also records actual RPU `profile`
(5 or 8), `residual_disabled: true` and `bl_bit_depth` matching source bit depth;
the baseline adapter only enables this path when residuals are disabled. Source
mastering minima/maxima must be the actual header source_min/max_pq converted
from /4095 PQ to cd/m², as the upstream adapter does. Each component has 2..9
strictly increasing normalized `pivots` and one fewer `segments`, or zero pivots
and zero segments if the real parser reports no reshaping for that channel.
Polynomial segments carry `method`
`polynomial` and three coefficients in x^0/x^1/x^2 order (unused coefficient
zero supplied by the real parser). MMR segments carry `method` `mmr`, order
1..3, constant, and [order][7] coefficients. Coefficients are already normalized
as documented upstream. The export also carries `max_pq_y` and `avg_pq_y` in
[0,1] from real level-1 analysis, not estimates from test frames. Pivots that
collapse at float32 precision are refused. All arrays have exact shapes.

The harness consumes only upstream-supported reshaping/matrices and level-1
maximum/average. Level-1 minimum and level-2/8 trims remain in the original
private metadata but are not implemented here. Profile 7 FEL reconstruction,
chroma subsampling reconstruction and decoder/extractor qualification are not
part of this interface. For subsampled source, supply an explicitly converted
co-sited 4:4:4 frame and record that conversion in private extraction evidence;
the source-byte identity then refers to that exact 4:4:4 frame.

### Private reference image contract

A reference is a schema-1 result manifest with fields `role: reference`,
`alignment`, `encoding`, `output` (file and SHA256), and a nonempty `provenance`
object identifying actual reference renderer version and options. Copy the
candidate's **alignment object only when it genuinely matches the reference**:
content identity, decoded source bytes, geometry, frame index, rational PTS,
source interpretation/mastering, complete target, parsed metadata hash and
original RPU hash. A reference image for another target or frame is rejected,
even if the dimensions and filenames look similar. This is an input contract,
not proof that a caller's provenance assertions are true.

Reference pixels must be display-referred PQ BT.2020 full-range RGB-f32le.
Convert private CM Offline output explicitly, preserving original render and
conversion hashes/options. Do not let an image library silently apply an ICC
profile, exposure, SDR transfer, row reversal or range inference. Every
comparison validates exact byte counts, hashes, pixel domain and identities.
Absence, wrong encoding, wrong hash or mismatch is an error, never an empty or
zero-difference success. Private frames, RPU, parsed exports, reference manifests
and numerical comparisons must stay outside version control.

## Metric

`tools/dolby_harness/metric.py` implements ITU-R BT.2124-0 Annex 1 in Python
binary64: inverse PQ to absolute BT.2020 RGB cd/m², the normative RGB→LMS
matrix, PQ on LMS, then I/CT/CP and **T = CT/2**. The difference is 720 times
Euclidean distance in ITP. PQ constants are exact rational values. The code
reports per-frame/per-target pixel mean, p95 and maximum; p95 is explicitly
nearest rank `ceil(0.95*N)` (one-based), not interpolated. No registration,
exposure fit, per-image normalization or post-render gamut clipping is applied.

Supported metric inputs are nonnegative PQ BT.2020 code values in [0,1]. XYZ,
negative-light, HLG and scene-referred extensions are deliberately unsupported,
rather than silently clamped or treated as PQ. This is a software image metric,
not optical calibration or measured display accuracy. The open track's proposed
mean≤1/p95≤3 threshold is a future private baseline decision, not a pass claimed
by this stage. No reference statistics have been produced by this implementation.

## Source and public inputs

Inspected upstream tag v7.360.1 is commit
`cee9b076f2c63104ccfd497fa79c39a867293ec4` at
<https://github.com/haasn/libplacebo>. Matching Ubuntu amd64 runtime/dev packages
are 7.360.1-1, extracted into a private prefix, never installed. Their public
archive origin is <https://archive.ubuntu.com/ubuntu/pool/universe/libp/libplacebo/>;
exact observed SHA256/SHA512 and dependency/header receipts are to be delivered
with compiler evidence. Archive bytes were compared to fresh official HTTPS
retrieval; this does not claim a signed Release verification.

Vulkan headers are v1.4.354 from KhronosGroup/Vulkan-Headers, matching the CPU
ICD's advertised API revision. The header closure includes `vk_platform.h`,
`vulkan.h`, `vulkan_core.h` and their twelve `vk_video` includes. Preserve their
Apache-2.0 notices in the private dependency stash. The implementation does not
vendor or relicense libplacebo/Khronos source; [repository terms](../LICENSES.md)
remain unchanged for original utility code.

## Build and deferred validation

Native compiler commands, exact source hashes, ELF/runtime dependency bindings
and review handoff are pending and will be appended before this implementation
card completes. No units may run until the existing adversarial review card
approves the completed candidate and any findings are fixed.

The proposed affected batch is only `tests/test_dolby_harness.py`, using the
compiled native binary through `HDR_HARNESS_NATIVE`. It covers public metric
vectors, transfer endpoints, chromatic weights, nearest-rank semantics,
invalid inputs, explicit source interpretation, missing/mismatched metadata and
reference handling, row/channel alignment and repeatable headless CPU rendering.
No real Dolby metadata fixture is present: the metadata-bearing path can compile
and validate its interface but genuine corpus execution belongs to the separate
private baseline milestone. No compositor, package, existing historical suite,
physical or Apple TV check is requested by this harness batch.
