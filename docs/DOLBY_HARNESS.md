# Stage-1 headless display-management harness

Status: **source reviewed; public software harness qualified**.
The native API prerequisite compiled before C/build edits; the complete C
consumer compiled/linked with warnings as errors, zero diagnostics. Python
contracts/metric/CLI and all 27 regression methods were executed once after
Astra approved corrected `2ab8332` / tree `69c59f2`. The result was **26 passed,
1 failed, no skips**; all 25 subtests passed. Astra's original review required R1–R3; the corrections retain the
unchanged native consumer/build inputs and passing ELF, with new Python source
bindings in the [correction receipt](../evidence/dolby-harness-corrections.json).
All native rendering/range/depth/target/gamut/minimum/provenance/negative-input
methods passed. The sole initial failure was independently reconciled against
normative BT.2124 arithmetic, corrected without changing production code and
approved by Astra. The **one failed-only retry passed** on corrected `64e8949`
/ tree `dc816dd`; all **27 required methods now have valid passing receipts**,
with 25 retained passing subtests. The 26 successes were not repeated: their
original execution identities remain explicit under reviewed source equivalence.
The [final qualification receipt](../evidence/dolby-harness-qualified.json)
binds the actual retry and every retained method. No renderer or compiler reran.
The [actual first-batch receipt](../evidence/dolby-harness-qualification-attempt1.json)
retains their executing identities; it does not relabel passes onto future trees.
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
  libplacebo for explicit non-Dolby range/chroma-centre interpretation. Float
  storage does not assert that samples were quantized at this nominal depth.
  Dolby input must retain **original base-layer digital codes divided by that
  divisor**, not samples with a prior limited-to-full expansion. The RPU matrices
  and offsets already carry range normalization; doing it again is incorrect.
- `source`: system `rgb`, `bt2020nc` or `dolbyvision`, PQ transfer, BT.2020
  primaries, explicit full/limited range, bit depth, layout, orientation,
  and `mastering` (`min_nits`, `max_nits`, eight raw chromaticities). For Dolby,
  `range` is a base-layer **attestation**, not an independent range-expansion
  selector: upstream forces full sample normalization and lets the RPU own
  levels. The receipt separately records requested/attested and effective policy.
- `target`: descriptive id, minimum and maximum in cd/m², and eight raw
  chromaticities in order rx/ry/gx/gy/bx/by/wx/wy. Finite physical xy values,
  nondegenerate primary triangle and an interior white are required. No EDID
  is read and no panel properties are invented.
- `metadata`: null for non-Dolby input; otherwise the contract below.

The output encoding is always full-range PQ BT.2020 RGB-f32le, top-left origin.
Target mastering-volume declarations are separate from the BT.2020 signal
encoding. A target gamut is not relabelled as the encoding. All source/target
values and frame/source/metadata hashes are carried into the candidate receipt.
Input/output textures are ordered RGBA32F with only RGB exported. Internal
shader arithmetic and any intermediate FBO selection retain pinned libplacebo
defaults (which prefer 16-bit floating-point intermediates); this is not a claim
of an entirely binary64 or 32-bit-only rendering pipeline. Any reported renderer
fallback/error flag is a failure, not a successful degraded comparison.
### Requested versus effective baseline semantics

The harness preserves supplied source/target declarations in control and
alignment. This does **not** mean every declaration is honored as a mapping
endpoint by the unmodified baseline. Candidate `provenance.baseline_semantics`
records the following pinned libplacebo behaviors:

- `src/colorspace.c:812–814` replaces **all PQ metadata minima**, including
  positive values such as 0.0004 cd/m², with `PL_COLOR_HDR_BLACK` (1e-6 cd/m²,
  `src/include/libplacebo/colorspace.h:298`) for nominal luminance bounds.
  Source/target requested minima are retained separately from that effective
  nominal minimum. It is not a measured panel black, an applied black floor,
  or a promise of black adaptation. No new black mapping is implemented.
- `src/colorspace.c:177–180,1842–1848` makes Dolby range normalization RPU-owned;
  the full/limited attestation does not apply a second range expansion. RGB and
  BT.2020-NC still use the explicit range and bit-depth selector. Full-range NC
  chroma uses the upstream MAX_INT=1 convention with midpoint `2^(b-1)/(2^b-1)`
  and a positive half-range ending at 1; limited codes use scaled 16/219/224.
- `src/colorspace.c:466–480,798–801` recognizes CIE-Y L1 maximum/average only
  when **both** values are nonzero at native float32 precision. Either zero
  falls back to mastering/color-space baseline metadata, not fabricated L1.
  The receipt records requested values, native float32 values and recognition.

These are source-verified semantics with public metadata-free qualification.
The passing public positive-min case compares zero/positive declarations and
rejects a fabricated 0.0004 black-floor claim. No synthetic RPU is needed.

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

The harness consumes only upstream-supported reshaping/matrices and eligible
level-1 maximum/average. If either L1 value is zero, CIE-Y L1 is unrecognized
and mastering/color-space metadata supplies the baseline. Level-1 minimum and level-2/8 trims remain in the original
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

The comparison report binds the exact candidate/reference manifest **byte
snapshots that were parsed**, not a later reread. It preserves both renderer
provenance objects (including reference version/options), binds the comparator,
contracts, metric and provenance implementation source hashes and Python
interpreter identity, and also retains the output hashes and alignment.
Reference provenance is still a caller attestation, not authenticated Dolby
tool evidence. Public test reference images remain explicitly synthetic.

## Execution provenance

Every render requires the actual `compile-receipt.json` beside its native ELF
(or the explicit `--compile-receipt` path). This is implementation identity,
not a feature opt-in or new schema framework. The renderer snapshots that
receipt privately and binds its exact bytes and complete compiler/header/source
identities into the candidate. It verifies the current C consumer, build recipe
and dependency manifest against the retained compile hashes and verifies ELF
equality. Historical Python/test hashes inside the original compile receipt
remain historical; current Python control/contracts/metric/provenance source
and interpreter hashes are separately bound and source changes since import
are rejected. A fresh interpreter must load the exported candidate.

Before and after rendering, native and CPU-ICD `ldd` resolution plus actual
file hashes must equal the compile receipt's runtime closure. The ICD JSON must
name the expected CPU library. The dependency inspection and native child share
the same clean, allowlisted environment: no inherited LD/VK/Mesa/layer or
display-server settings, fixed CPU ICD, all Vulkan layers disabled, two CPU
threads and private HOME/XDG cache/config/data directories. Nonempty system
loader preloads are refused. Environment and actual verified runtime hashes
are retained; a hard-coded version string is not the identity proof. The native
device/version/options log is separately hash-bound.

This detects changed inputs/resolution around the invocation in the controlled
owned builder; it is not a signature/authentication scheme or protection against
hostile concurrent mutation of the compiler/runtime. New verification code is
written/syntax-compiled before review, then **runtime-qualified** by the single
approved public batch. Its retained receipts bind the original executing source.

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

### Annex-4 input: normative numeric oracle correction

BT.2124-0 recommends the Annex-1 calculation; Annex 4 is explicitly informative.
The official [BT.2124-0 publication](https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.2124-0-201901-I!!PDF-E.pdf)
(01/2019, editorial amendments February 2020) supplies the digital codes
296/201/582 and divisor 1023 in Annex 4 section 1. Annex 2 conversion 3 defines
the full-range PQ decode; Annex 1 section 2 steps 1–4 define RGB→LMS, PQ on LMS,
I/CT/CP and T=CT/2. The fetched PDF SHA256 is
`cad1e382516da511811c5205e5abe1b0b97999cf4722d4854a439389eff54470`;
the copyrighted PDF stays private and is not vendored.

The independent [rational/Decimal derivation](../evidence/dolby-harness-annex4-oracle.py)
imports no harness, test or renderer implementation. Its
[mathematical receipt](../evidence/dolby-harness-annex4-oracle.json) retains the
exact rational constants/matrix coefficients and all intermediate values at
80 and 120 decimal digits. Nonlinear powers use Decimal, not binary64; light
is computed relative to 10000 cd/m² (which cancels through the PQ round trip),
with absolute RGB/LMS values retained for inspection. The two precisions agree
in ITP to better than 1e-70; this is numerical convergence, not an exact-real
interval proof or a unit/render receipt.

For the exact codes divided by 1023, the independently derived values rounded
to 16 decimal places are:

| Component | Normative calculation |
| --- | ---: |
| I | 0.3557205250540512 |
| T | 0.1346466873449306 |
| P | -0.1613950695752067 |

Absolute linear RGB is approximately 8.75818211436527 / 2.29415607753754 /
181.31806454725429 cd/m². The Annex-4 displayed normalized intermediates
0.2893/0.1964/0.5689 instead explain its displayed linear values near
8.753/2.291/181.3. However, applying Annex 1 to even that displayed linear RGB
gives I≈0.35569814587136, not the example's I=0.3554. Thus the example's ITP
triple is not the four-place rounding of the normative result for these codes;
the derivation demonstrates an arithmetic inconsistency, not its historical
cause or an official ITU erratum. No divisor substitution or tolerance
weakening is justified. The normative result rounds to 0.3557/0.1346/-0.1614
at four places, rather than 0.3554/0.1346/-0.1613.

Only `MetricTests.test_annex4_public_vector` changes: it retains the original
input and full-component assertion, uses the independent literals above and
**tightens** absolute tolerance from 1e-4 to 1e-12. This permits binary64
transcendental/accumulation rounding without treating the displayed example as
a precise oracle. Production `metric.py`, all other front-end files, C, build
recipe, dependencies and all other test methods/helpers/module initialization
are unchanged. AST equivalence excluding this one method and SHA256 equivalence
of all eight production inputs are recorded in the
[static correction receipt](../evidence/dolby-harness-vector-correction.json).

Astra review `t_a844cca4` approved exact corrected `64e8949` / tree `dc816dd`
and retention of the 26 actual passes and 25 actual passing subtests at
their original executing `2ab8332` / tree `69c59f2`: the changed method is never
called by those selections, and its local expected tuple has no module/global,
shared fixture or production effect. Do not relabel them onto the new source
tree. The successful compile remains applicable to unchanged C/build/dependency
bytes; no compiler or renderer rerun is warranted for this correction.

After that approval and an explicit integration mailbox grant, qualification
`t_dcc3a830` ran exactly this selection once from the corrected source in a new
isolated native snapshot:

```bash
PYTHONPATH=tests python3 -B -m unittest test_dolby_harness.MetricTests.test_annex4_public_vector -v
```

This command imports the harness normally but invokes no native renderer.
The qualification platform was native x86_64 Linux in the existing
lane: Python execution there still requires the fixed `.peer-linux/run.py`
wrapper and negotiated mailbox ownership, not a renderer rebuild or probe.
No successful selection was invalidated by the fixture-only edit. The actual
retry returned exit 0, `Ran 1 test`, `OK`, with all nine source hashes equal
before and after. Python 3.14.8 and its binary hash, the exact argv/environment,
logs and exit are bound in the final receipt. Historical runtime bindings remain
historical; no renderer/runtime probe or recompile occurred for this metric retry.

## Source and public inputs

Inspected upstream tag v7.360.1 is commit
`cee9b076f2c63104ccfd497fa79c39a867293ec4` at
<https://github.com/haasn/libplacebo>. Matching Ubuntu amd64 runtime/dev packages
are 7.360.1-1, extracted into a private prefix, never installed. Their public
archive origin is <https://archive.ubuntu.com/ubuntu/pool/universe/libp/libplacebo/>;
exact observed SHA256/SHA512 are in
[`dependencies.json`](../tools/dolby_harness/dependencies.json), and every actual
header/runtime hash is in the [compiler receipt](../evidence/dolby-harness-compile.json).
Archive bytes were compared to fresh official HTTPS
retrieval; this does not claim a signed Release verification.

Vulkan headers are v1.4.354 from KhronosGroup/Vulkan-Headers, matching the CPU
ICD's advertised API revision. The header closure includes `vk_platform.h`,
`vulkan.h`, `vulkan_core.h` and their twelve `vk_video` includes. Preserve their
Apache-2.0 notices in the private dependency stash. The implementation does not
vendor or relicense libplacebo/Khronos source; [repository terms](../LICENSES.md)
remain unchanged for original utility code.

## Build and qualified validation

Native API baseline request `724a9edda55240cca112d7ced905ba05` passed before
production C/build edits. Completed candidate request
`7a44f44372974c9f97aaa369544fc38a` passed natively on x86_64 (0.94 seconds for
compile plus hash-bound receipt/export). Compiler is Ubuntu GCC 15.3.0; flags
are `-std=c11 -O2 -fno-fast-math -Wall -Wextra -Werror`, linking the owned
libplacebo prefix and libm. The exact argv and source bindings are in the
receipt. All eight source files, all 49 pinned headers and the actual ELF
were independently verified after export; upstream/Khronos headers match the
inspected source bytes (generated config separately bound). ELF SHA256:
`14f23387883cbf3baaa29405b5e8be7d4ca580ca76da55c7a9992d5e7f37d84e`.
CPU ICD and loader/LLVM/Mesa dependency bytes are also bound. This is static
compiler evidence, not a successful Vulkan render or a passing unit receipt.

Public dependency acquisition/import is now complete, using the coordinator's
hash-verified read-only stash. The earlier compact transport imported matching
runtime/dev packages successfully; only the missing twelve video-header files
needed a subsequent 13,044-byte archive. No credentials, network in the native
builder, host package installation or inherited source/build modification.

Reproduce compilation only in an owned native x86_64 Linux lane with the
recorded headers and extracted package prefix:

```bash
python3 tools/dolby_harness/build.py --prefix "$LANE/prefix" \
  --output "$LANE/build/new-candidate"
```

The build tool creates a new output directory and records actual source,
header, binary, compiler and loader/CPU ICD hashes; it executes no units or
GPU probe. Reuse the delivered binary/receipt if native C/build inputs are unchanged rather
than rerunning a successful compile solely for a reviewer. Native commands in
this collaboration must continue through the fixed `.peer-linux/run.py`
transport and negotiated mailbox ownership.

Existing review `t_a5a08679` approved corrected `2ab8332` (Astra, not Fable).
Qualification `t_dcc3a830` ran this one affected batch from a new isolated source
directory, preserving the original ELF, compile receipt and prefix:

```bash
export HDR_HARNESS_NATIVE="$LANE/build/candidate1/headless-render"
python3 -B -m unittest discover -s tests -p test_dolby_harness.py -v
```

All **27 actual methods** must receive a valid passing result (12 are new or
revised versus the original module; see the correction receipt). Coverage adds
asymmetric in-gamut BT.2020-NC full/limited independent matrix/range oracles at
8/10/12/16 bits; 300/616/1000 peak upper **and lower** bounds plus distinct target
responses; synthetic BT.709 target gamut with chromatic in-gamut preservation,
out-of-gamut response and unchanged PQ BT.2020 encoding; ignored positive PQ
minimum behavior; direct malformed/trailing/truncated native controls and
invalid pixel rejection with no output; table-driven source/target/metadata
identity mismatches; exact parsed-manifest snapshots, front-end/ELF/source/runtime
tampering and inherited-loader/ICD environment isolation. All are public,
metadata-free fixtures; invalid non-Dolby metadata identities are rejection
controls, not fabricated RPU data. A missing native binary/compile receipt is a
failure, not a skip. Rerun only failed
or genuinely invalidated checks. No existing compositor/corpus suite is
requested again. No historical receipt claims that these new tests passed.

After the same review gate, the CLI usage is:

```bash
python3 tools/dolby_harness/make_fixture.py "$PRIVATE/new-public-fixture"
python3 -m tools.dolby_harness.harness render "$PRIVATE/new-public-fixture/frame.json" \
  --native "$HDR_HARNESS_NATIVE" --output "$PRIVATE/new-render"
python3 -m tools.dolby_harness.harness compare "$PRIVATE/new-render/candidate.json" \
  "$PRIVATE/reference.json" --report "$PRIVATE/new-comparison.json"
```

Reports are exclusively created at the requested private path and numerical
comparisons never print to stdout. Each report has its exact source/target/frame
alignment, exact input-manifest and implementation/provenance bindings, output
hashes and pixel mean/p95/max. Failed rendering retains
private staging diagnostics and produces no finalized candidate receipt.

The executed affected batch was only `tests/test_dolby_harness.py`, using the
compiled native binary through `HDR_HARNESS_NATIVE`. It covers public metric
vectors, transfer endpoints, chromatic weights, nearest-rank semantics,
invalid inputs, explicit source interpretation, missing/mismatched metadata and
reference handling, row/channel alignment and repeatable headless CPU rendering.
No real Dolby metadata fixture is present: the metadata-bearing path can compile
and validate its interface but genuine corpus execution belongs to the separate
private baseline milestone. No compositor, package, existing historical suite,
physical or Apple TV check is requested by this harness batch.

### First public qualification receipt (2026-10-13)

Fresh preflight verified all nine executing source hashes, the preserved ELF and
compile receipt, and all 34 actually resolved runtime bindings. The batch ran in
22.257 seconds (unittest time). Evidence-only observation outside tracked source
recorded every method/subtest and copied temporary fixtures, controls, native
diagnostics and candidate manifests before normal cleanup. All 562 retained file
hashes were verified after retrieval. No successful compiler or unit suite was
rerun. The transport's 4 MiB export cap failed after execution; two bounded
retrieval chunks recovered the complete 548,358-byte evidence archive without
reexecution. SHA256:
`2c4f9a3416c6f4989457efac0ea9064acd68bc3f068c9698a098c03393d8d9d7`.

The archive and detailed logs remain in the private collaboration qualification
lane. Only the sanitized public-synthetic receipt is committed. Programme-wide
status remains integration-owned. Genuine Dolby metadata/private agreement,
mapping/trims, preferred-description handoff and optical acceptance remain
separate unmet milestones; passing public native renders do not qualify them.

### Final public qualification and downstream handoff (2026-10-13)

All 27 method requirements are satisfied: 26 actual method passes and 25 actual
subtest passes retain executing HEAD
`2ab8332c7f1638741620347729352f32b9c0c241`, tree
`69c59f253a54240859ea166f4b7cd2a9b4fa4c5c`; one corrected metric method passed
at HEAD `64e894901dfdf7670962c577599fafa936ed4802`, tree
`dc816dd1084eaff9b77bb0bee3183323f286f3dc`. Astra independently verified
unchanged production and whole-module AST equality outside that isolated,
uncalled failed method. This is applicability of actual earlier passes, not
execution of all tests on the corrected tree. The original failed assertion is
preserved, not erased. The expected tuple comes from two independently arranged
high-precision normative derivations; tolerance tightened to 1e-12.

The failed-only retry used fresh Python 3.14.8 (Ubuntu GCC 15.3.0), interpreter
SHA256 `6afce98b1e5ce89dc1c5dfca9672276a9486bc318855c7554cbe6da62d073e10`.
Native request `76ed256ca45346e4926039b6cf653903` returned exit 0; selected-test
process wall time was 0.09319043159484863 seconds. Stderr SHA256 is
`376b881a738fc12dc4659571f6cc79b0445c2fb10b516e34b2e9cac5b5913849`;
stdout is empty. The raw retry receipt SHA256 is
`01cc37a45eddd32e7d9e8acbeb0fcf2a7adc982cdcb2feee5273c9c6e233f52c`.
Static delivery verification compared all 563 first-batch archive regular files
and all 562 receipt-bound hashes (555 event artifact files, plus seven retained
execution/source/observer files). Original source, runtime, compiler and ELF
evidence are preserved. One batch and one failed-only retry occurred in total.

The private collaboration delivery contains the complete source bundle/archive,
the reused native ELF/compile receipt and the already-generated public
metadata-free fixture. Use the render/compare commands above from this corrected
source, not the obsolete candidate1 Python directory. For the preserved native
builder, `HDR_HARNESS_NATIVE` is
`/work/hdr-nativehdr10-20261011/dolby-harness-t_8c7a6c12/build/candidate1/headless-render`;
the matching prefix and runtime closure stay read-only. New native calls still
require the fixed wrapper and explicit mailbox coordination. No extra smoke
render is requested simply to repeat passing qualification.

Baseline worker `t_041c7d41` must now locate the actual protected corpus and
reference manifests, then supply matched decoded frames, real parsed metadata
and original RPU hashes for genuine reference comparisons. The public software
receipt is not private Dolby agreement. Mapping/trims worker `t_c2f72953` remains
gated on that baseline: no fabricated metadata or guessed curve is authorized
by this qualification. Programme status is integration-owned; PR16 stays held,
and no publication, device/Apple TV, installation or physical acceptance occurs
in this handoff.
