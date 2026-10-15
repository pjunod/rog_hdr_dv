# Authored-master baseline adapter

Status (2026-10-15): implemented and native consumer compiled. Independent review
found a compile-input hash type error and unbounded result-output reads; both
are corrected in source, with re-review and coordinator-routed validation pending.
This is a bounded source/transport prerequisite, not recovery of full Dolby
mapping or numerical acceptance. [Harness](DOLBY_HARNESS.md) schema1/2 and DVH1
remain distinct. No library, player, compositor or metric equations change.

## Why a third interface

An acquired genuine authored master stores full4096×2160 P3D65/PQ/full RGB as
IEEE754 HALF, with unnamespaced XML2.0.5/DolbyEDR metadata. Integer normalization,
BT2020 source relabelling, cropping, fictitious contiguous sequence manifests,
raw-RPU fabrication and XML4 namespace replacement would be incorrect. Schema3
stage `authored-master-baseline` explicitly handles this different input.

The source EXR's HALF channel declarations and retained explicit vendor
source-format are storage authority. XML monitor BitDepth16 and a vendor's
`u16` summary of ColorEncoding are NOT evidence that these pixels are integers.
Producer publication binds P3D65/PQ/full; absent EXR transfer/chromaticity tags
are not a licence to assume scene-linear. A mastering peak4000nit does not
change PQ's10000nit signal scale.

The only acquired source frame is almost uniform near black. Any later passing
full-raster comparison is an alignment/black-region baseline only. It cannot
establish representative trim, highlight or chroma coverage, held-out agreement,
consumer CM selection, Windows/OEM equality, calibrated colour or optical
acceptance. No more frames or vendor executions are authorized by this card.

## Schema3 contracts

Input keys are `schema stage frame source target metadata`; schema is integer3.
Frame/target retain their schema2 shapes. Width1..4096, height1..2160 and their
product bound apply consistently to frame/result/native/EXR/sparse manifests.
Schema1/2 still stop at3840wide. No scaling, registration, crop, fit or clipping.

Source has exactly `system transfer primaries range sample_format layout
orientation mastering`, with values `rgb pq p3d65 full
ieee754-binary16-expanded-f32 c3-f32le top-left`. There is no integer `bit_depth`.
Source mastering (`min_nits max_nits primaries`) is checked against original
XML. Target (`id min_nits max_nits primaries`) is checked against the selected
original physical display, independently of the BT2020/PQ/full output encoding.
The acquired case is physicalP3D65/600nit/0black target27, not BT2020 target gamut.

Metadata has exactly `origin analysis original_analysis declaration_repair
source_manifest export frame_index pts`, origin `authored-master`. File envelopes
are `{file,sha256}` with bounded, hashed byte snapshots. Original producer XML
and actual rendered repaired XML are both required. The retained acquisition
receipt binds the original source and the exact declaration repair. Reversing
its algorithm insertion and then its source ColorEncoding insertion must recover
the original bytes exactly. Independent DOM checks require only those two source
locations to have been inserted. Every original shot/frame/trim remains intact.

The receipt's source-associated producer provenance and producer-global bytes
are hash checked, not treated as prose proof of execution. Historical receipts
are never edited for relocation: their nested artifact path resolves on its
recording host, or an explicitly retained byte-identical copy is stored at
`<manifest-directory>/retained/<sha256>`. Main input envelopes have no path
fallback. Hashes establish identity/association of retained evidence, not
publication authenticity or cryptographic ownership.

The sparse source manifest has exactly `schema kind source width height
edit_rate frames provenance`, schema3, kind `sparse-authored-master`, rational
positive `edit_rate={num,den}` and at most64 actual acquired entries. Each frame
has `index original normalized`, with unique nonnegative original indices and
bound file envelopes. The acquired case has exactly entry0, not the XML duration
and not a claimed complete sequence. Selected normalized bytes must equal the
input frame hash. Every supplied original EXR is independently decoded and
compared sample-for-sample against its normalized bytes. Rate/timecode fields
present in the original storage header are separately checked.

Sparse provenance has exactly `publication acquisition conversions authority`:
the first two are bound retained producer-association/acquisition receipts,
`conversions` has one bound storage-conversion receipt per frame, and `authority`
explicitly states the association/evidence limit. Actual decoder implementation,
historical interpreter hash/version, zlib version, process argv, entry point,
original/header/normalized hashes and absence of signal transforms are retained.
A conversion from another host is not relabelled as the current interpreter.

`master_pixels.py` supports only single-part version2 increasing scanline RGB
HALF, square pixels, zero-origin identical full data/display windows, and
uncompressed or ZIP storage. It refuses extra/subsampled channels, other storage,
nonfinite/out-of-domain samples, unsupported flags/compression, bad offsets,
truncation, overlap, gaps, trailing storage and decompression overflow. Byte
reordering, ZIP decompression and exact HALF expansion are storage operations,
not an EOTF, range divisor or gamut conversion. Output is tightly packed RGBf32le.

## XML2.0.5 mapping and unapplied records

`authored_master.py` accepts bounded strictUTF8 only, no DTD/entities, no namespace
substitution. It checks one output/video track, actual track/source rates,
unique source ParentIDs/targetIDs/shotIDs/frameIDs, ordered nonoverlapping shot
records and unique in-shot frame offsets. Selected PTS must equal original
index×rate-den/rate-num by exact integer cross multiplication. Original output,
track, shot, frame, source-parent/source-in, shot-in/duration and offset are bound.
There is no selected-frame fallback/interpolation or shot L1 inheritance.
Selected frame and shot L1 cannot conflict. Selected conflicting frame/shot L2
is unsupported rather than guessed. Later unselected still assets have duration1
but held edit shots; the parser does not invent a whole-sequence source-duration
mapping for them. The selected acquired movie source must be fully in range.

The actual track PluginNode/DolbyEDR/Characteristics MasteringDisplay and
TargetDisplay declarations are parsed, not XML4 Level254/Level9 assumptions.
Actual AlgorithmVersions0,0 are retained. Neither that pair nor XML schema2.0.5
identifies a named consumer CM: `selected_cm_name` remains strict JSON null.

Export keys are `schema stage analysis_sha256 original_analysis_sha256
 declaration_repair_sha256 source_manifest_sha256 source_sha256 frame_index pts
 parser xml_version algorithm_versions selected_cm_name mapping l1 records
 translation` (whitespace above only separates field names). Parser identity is
`{name,version,sha256}`. Mapping is `{output_id,track_id,shot_id,frame_id,
source_parent_id,source_in,shot_in,shot_duration,edit_offset,edit_rate}`. L1 is
`{min_pq,avg_pq,max_pq}`, finite/ordered in[0,1]. Records preserve level/scope,
targetID, XML attribute order and every original scalar field string/order;
L2 has `operator=not-implemented`. The entire original XML is also retained.
Exact export regeneration checks JSON types as well as values, so booleans and
floats cannot masquerade as integer schema/frame/version/algorithm fields.

Translation `dolby-xml205-l1-direct-baseline-v1` passes only existing normalized
max/average into the upstream baseline slots. Minimum is preserved/unimplemented.
No ST coefficient interpretation, raw SOP equations, invented neutral trims,
RPU serialization, /4095 quantization, L3 compensation, interpolation, clipping
policy or L2/L8 operation is introduced. This is not proven photometric CIE-Y
or consumer raw-RPU equivalence. A zero max/average retains the original baseline
fallback; no active-L1 qualification is invented from it.

## DVH2 and pinned native source trace

DVH2 contains exactly magic,width,height,sourcePrimariesCode, source volume
(min,max,eightxy), target volume(min,max,eightxy), max_pq_y,avg_pq_y. Code1 alone
means P3D65. There are no integer range/depth or reshaping tokens. DVH1 bytes and
schema1/2 semantics are unchanged. Full-raster RGBA32F textures/crops and the
explicit CPU Vulkan/clean runtime environment remain as in the qualified harness;
no dither, peak detection, display connection or implicit degraded render.

At pinned libplacebo7.360.1 commit
`cee9b076f2c63104ccfd497fa79c39a867293ec4`:

- `src/include/libplacebo/colorspace.h:215` defines DISPLAY_P3 as DCI-P3
  primaries with D65, independent of the transfer enum. `src/colorspace.c:1171–1175`
  gives the actual RGBxy and D65 white. Source uses that enum AND explicit
  `PL_COLOR_TRC_PQ`, never sRGB transfer or DCI white. Destination is explicitly
  BT2020/PQ; the library performs its ordinary colour-space transform internally.
- `src/colorspace.c:190–214` starts normalization at unity. Zero bit fields
  select equal effective depths for its ratio; full range therefore stays unity.
  `1814–1839` gives RGB full-range endpoints0/1 and zero black. RGB does not take
  the YCbCr chroma-centre branch. HALF is not divided by65535 or retagged linear.
- Requested PQ minima are retained but the unchanged baseline's effective
  nominal minimum policy remains PL_COLOR_HDR_BLACK, not a measured/applied floor.

The compiler prerequisite independently verified the frozen baseline ELF,
49header hashes and34runtime identities before C edits, without rebuilding any
library. One incremental consumer build used GCC15.3.0 and
`-std=c11 -O2 -fno-fast-math -Wall -Wextra -Werror`; both diagnostic streams are
empty. [Source/compiler receipt](../evidence/authored-master-adapter.json).
Python/test syntax compilation is not a unit pass. Later frontend-only changes
retain their own final source hashes; historical Python hashes in the compiler
receipt are not rewritten onto those bytes.

## Results, reference normalization and deferred execution

Result outer keys remain `schema role alignment encoding output provenance`.
Schema3 alignment carries all common source/frame/target/export identities plus
the export's declaration/parser/version/mapping/translation identities (not L1
or records, which are bound by export hash). There is no invented analysisVersion4.
Result validation rebinds alignment to the actual input/metadata snapshots.
Compile-input identities hash actual file bytes, not Path objects. For both
candidate and reference, after provenance checks it reads output only once,
with a width×height×12+1 byte cap, checks exact size and SHA256, then verifies
reference storage and decodes finite normalized samples from that same snapshot.
There is no unbounded legacy output reopen. The schema3 input's domain check
also consumes its bounded hashed snapshot; schema1/2 helpers remain unchanged.
Candidate compiler/ELF/runtime/frontend/control/log hashes and explicit baseline
semantics are retained. Reference provenance separately binds actual immutable
reference EXR, storage/sample hash, decoder, vendor argv/runtime identities and
normal validation/target/render log snapshots. It does not infer CM selection
from a pipeline timing label or a decoder's container defaults.

After independent review/fixes, coordinator recovery alone routes the one affected
unit batch and the one original frame0 candidate comparison. The private task
handoff supplies the exact input, prefix/ELF, proposed test IDs and per-ID retention
rationale; it is not a passing receipt. Set `TMPDIR` to durable task-owned storage,
`PYTHONPATH=tests`, `HDR_HARNESS_NATIVE` to the new ELF, `HDR_AUTHORED_INPUT` to the
real bound input, and existing schema2 corpus variables for the selected retained
interface checks. Missing genuine fixtures are failures, not synthetic replacements.
The revised proposal has40 selected methods (23 authored) and31 retained unchanged
historical methods, with their actual executing identities and review262 retention
rationale. Five new deferred regressions cover exact/short/oversize bounded reads,
output hash/domain checks and authentic candidate/reference result acceptance,
compile/frontend/control/log tamper rejection and output-hash rejection. The
small public storage controls contain no Dolby metadata or claimed render output.

Use `normalize_reference(manifest, immutable_reference_exr, new_private_directory)`
only after the review gate. It reads and normalizes the already acquired reference,
never invokes a vendor tool. Recovery's revised pending recipe normalizes that
reference and renders the original candidate ONCE before the ONE unit process,
so the genuine result tests can consume those actual artifacts without another
render. Set `HDR_AUTHORED_CANDIDATE` and `HDR_AUTHORED_REFERENCE` to those result
manifests. Then compare with the existing CLI; no metrics run inside the new tests.
This ordering proposal is not authorization to execute before review. No copying of alignment
without checking the actual source/target/frame/encoding is permitted. All raw
XML/EXR/conversions/numerical results stay private, outside Git.

`metric.py` is byte-unchanged: full raster, normative BT.2124 arithmetic,
nearest-rank p95, mean≤1/p95≤3. No excluded black pixels, sampled raster, exposure
fit, quantization-to-match or parameter sweep. Existing tuple allocation must be
observed within the native6GiB budget during the future batch; no streaming or
numerical substitution is smuggled into this adapter. Source/rawSOP/domain/
midcontrast/consumerCM/L8 and full acceptance remain the recovery thinker's work.

PR16 remains held. No push/publication, live display/ROG/AppleTV/AirPlay/CEC,
credential access, package/service/session operation or deployment is part of
this bounded source/review phase.
