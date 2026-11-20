# Image-quality source stimuli — chroma siting, scaling, dithering and cadence

The [generator](../scripts/generate_quality_stimuli.py) creates owned synthetic
YUV4MPEG2 (`.y4m`) sources for later image-quality qualification of a display
path. It invokes no Dolby tool and creates no Dolby metadata. Like the
[HDR reference corpus](HDR_REFERENCE_CORPUS.md), its output is a digital source
fixture. **These files prove nothing about a display, compositor, scaler or
decoder until they are played, captured and measured.** Frame cadence in
particular needs timestamped frame or refresh capture; no source file can show
it.

**November 20, 2026 — exact fractional cadence source support.** The generator,
capture planner and offline analyzer now retain exact rates such as
24000/1001, 30000/1001 and 60000/1001. Independent source review and all
54 focused checks passed (generator 26, runner 10, analyzer 18). An actual
FFprobe 9.0.2 decode of newly generated 192×108 sources verified exact rates,
integer PTS/time bases and frame counts 24, 23, 29 and 59 for one requested
second at 24, 24000/1001, 30000/1001 and 60000/1001 respectively. The planner
also refused nominal-24 substitution for 24000/1001. This is authored source
and software-decoder evidence; no new player, capture, panel-cadence or optical
acceptance is claimed. Repository publication checks are tracked separately.

## Generate

Use Python 3 and a new output directory outside the source repository. Its
parent must already exist.

```bash
python3 scripts/generate_quality_stimuli.py "$HDR_WORK/quality-stimuli" \
  --width 192 --height 108 --cadence-fps 24 25 30 50 60 --cadence-seconds 2
```

| Option | Default | Bound |
|---|---|---|
| `--width` / `--height` | 192 / 108 | even; width 192..3840, height 72..2160 |
| `--cadence-fps` | 24 25 30 50 60 | unique exact integers or `N/D`, value 1..120; at most 16 |
| `--cadence-seconds` | 2 | integer 1..10 |
| `--max-total-bytes` | 64 MiB | checked before anything is written |

Large `--cadence-fps` and `--cadence-seconds` trip the 64 MiB guard: at the default
192x108, five rates at 10 s need about 118 MB, so the run is refused unless
`--max-total-bytes` is raised (for example `--cadence-seconds 10 --max-total-bytes 134217728`).
The estimate counts stimulus files only, not `manifest.json`.

Fractional input is exact, so use `24000/1001` rather than `23.976`.
Equivalent rates are reduced before naming and hashing; aliases such as
`24` and `48/2` in the same run are refused. The reduced denominator is at
most 1001, and each ideal-refresh model is bounded to 2400 source frames
per repeat period; these bounds limit manifest work as well as media bytes.
The three broadcast fractions above fit all the existing refresh models.

```bash
python3 scripts/generate_quality_stimuli.py "$HDR_WORK/fractional-stimuli" \
  --cadence-fps 24 24000/1001 30000/1001 60000/1001 --cadence-seconds 2
```

Integer-only output retains `image-quality-stimuli-v1`, integer rate values
and existing filenames. A run containing a fractional rate declares
`image-quality-stimuli-v2`; its `cadence_fps` list holds integers and reduced
`N/D` strings. Older integer-only analyzers refuse this new schema. The
current analyzer supports both, verifies the exact generator/parameter/design
hashes and refuses a schema/rate mismatch. As before, a manifest from a
different generator source is not silently re-attributed to this source.


The minimum width is 192 because the cadence barcode is 24 blocks of 8 px. The
default set is about 24 MB. Output paths are never reused; staging is cleaned on
failure; generating twice produces identical bytes and an identical
`manifest.json`. Zone-plate samples use `math.cos`, so another C library could in
principle differ in a last rounding; the manifest hashes expose any such change.

## Encoding

Default files are 10-bit 4:2:0, header `C420p10 XYSCSS=420P10 XCOLORRANGE=LIMITED`,
unsigned 16-bit little-endian samples holding values 0..1023. Range is limited:
Y 64..940, chroma 64..960, neutral chroma 512. Matrix coefficients are BT.2020
non-constant luminance (Kr 0.2627, Kb 0.0593); the declared transfer is PQ and
primaries BT.2020. Values are code values, not luminances. Y4M has no standard
fields for matrix, transfer or primaries, and `XCOLORRANGE=LIMITED` is a
non-standard extension that only some tools read, so `manifest.json` is the
authoritative record: a consuming tool must be told explicitly. 8-bit variants
exist only for chroma siting (Y 16..235, chroma 16..240, neutral 128).

**Coordinate convention.** Everywhere in the manifest and this document, luma
pixel `i` covers `[i, i+1)` and its centre is at `i + 0.5`, in luma-pixel units
from the frame's top-left corner (manifest field `coordinate_convention`).
Siting midpoints are defined in the code-value domain, not in light.

`manifest.json` lists every file with `bytes`, `sha256` and an `expected` block
of per-stimulus values, plus hashes of the generator source, the parameters and
the design.

## 1. Chroma siting (`chroma_siting/`)

Each file holds two frames over a flat grey luma field: frame 0 has vertical
chroma step edges, frame 1 horizontal ones. The chroma plane steps between
chroma column `k-1` and `k` (row `j-1` and `j`) between two saturated colours
(8-bit Cb/Cr 94/195 and 188/94; the 10-bit file uses four times these codes).
The generator computes R'G'B' for both colours at the grey luma under the
declared BT.2020 matrix and refuses to run unless every component is inside
[0, 1]; the manifest records the values.

| File | Header tag | Implied siting (horizontal, vertical) | H.273 type |
|---|---|---|---|
| `chroma_siting_c420mpeg2_8bit.y4m` | `C420mpeg2` | left, centre | 0 |
| `chroma_siting_c420jpeg_8bit.y4m` | `C420jpeg` | centre, centre | 1 |
| `chroma_siting_c420paldv_8bit.y4m` | `C420paldv` | left, top | 2 |
| `chroma_siting_c420p10_10bit.y4m` | `C420p10` | left, top (manifest only) | 2 |

The three 8-bit files have identical luma and identical chroma arrays; only the
tag differs. The mpeg2 and paldv pair differs in vertical siting only; mpeg2 and
jpeg differ in horizontal siting only. The 10-bit chroma is the 8-bit chroma
times four. The 10-bit file carries no siting tag: it is recorded as H.273
chroma location type 2 (left, top, co-sited), the HDR10 / UHD Blu-ray
convention, but that is **not carried by the file** (ffprobe reports it as
unspecified). Any analysis of that file must state the assumed chroma location
type.

Ideal reconstructed transition midpoints, per edge, for chroma sample positions
in the pixel-centre convention above:

- Horizontal, left (co-sited) siting: chroma `i` sits at luma `x = 2i + 0.5`,
  midpoint `2k - 0.5`. Centre siting: `x = 2i + 1`, midpoint `2k`.
- Vertical, top siting: chroma row `j` at `y = 2j + 0.5`, midpoint `2j - 0.5`.
  Centre siting: `y = 2j + 1`, midpoint `2j`.

The manifest records both interpretations for every edge, and which one the
file's tag implies. The observable is the 0.5 source-pixel difference between
interpretations. It is in *source* pixels: multiply it by the scale factor of the
display path to get captured pixels (at 2x it is 1 px). Reading it needs an
upscaler that honours the tag and a capture sharp enough to place an edge to well
under a pixel; many paths ignore the tag, which is itself a finding once
captured.

## 2. Scaling (`scaling/scaling_p10.y4m`)

Three luma-only frames (chroma 512): zone plate, line gratings, slanted edge.

**Zone plate.** `Y = round_half_up(502 + 438 * cos(pi * r^2 / R))`, with `r` in
pixels from the frame centre sampled at pixel centres and `R = hypot(W, H)`. The
local frequency is `f(r) = r / R` cycles per pixel; along an axis
`f_x = |dx| / R` and `f_y = |dy| / R`. The source is alias-free (at most 0.5
cycle/pixel at the corner). After scaling by `(sx, sy)`, source frequency `f_x`
appears at `f_x / sx` cycles per output pixel, so the horizontal axis aliases
where `|dx| > 0.5 * R * sx` (`alias_boundary_abs_dx_source_px`) and the vertical
axis where `|dy| > 0.5 * R * sy` (`alias_boundary_abs_dy_source_px`), in source
pixels from the centre. Separate `sx` and `sy` are allowed. When a boundary
exceeds the half-size (`W/2` or `H/2`) that axis cannot alias; the manifest
flags this (`x_axis_can_alias`, `y_axis_can_alias`) for several scales. Compare
the observed onset of aliasing with the prediction.

**Line gratings.** Levels 64 and 940. Top-left: vertical 1 px stripes; top-right:
vertical 2 px stripes; bottom-left: horizontal 1 px stripes; bottom-right:
horizontal 2 px stripes, in absolute frame coordinates (even stripe index is
940).

**Slanted edge.** Hard edge, 5 degrees from vertical, slope `tan(5 deg)` =
0.087488663526 (dx per dy), 64 on the left and 940 on the right:
`Y = 940` when `(x + 0.5 - W/2) > slope * (y + 0.5 - H/2)`. The source has no
antialiasing.

## 3. Dither (`dither/dither_ramps_p10.y4m`)

Two frames of shallow horizontal ramps, constant down each column, chroma 512:
codes 64..96 (near black) and 448..480 (mid grey). The code at column `x` is
`low + floor(x * (high - low + 1) / W)`; the manifest lists every column's code.
Each of the 33 levels is at least 5 columns wide.

For each ramp the manifest records, under four models of an undithered
10-to-8-bit path, the expected number of distinct 8-bit levels and the exact band
boundaries (first and last column of each level):

| Model | Level |
|---|---|
| `limited_truncate` | `code >> 2` (9 levels, bands of about 4 codes) |
| `limited_round` | `(code + 2) >> 2` |
| `full_range_expand_round` | `round((code - 64) * 255 / 876)` (about 10 levels, bands of about 3.4 codes) |
| `full_range_expand_truncate` | `floor((code - 64) * 255 / 876)` |

To count levels in a capture, take one row, average away sensor noise and list
the plateaus (level and column range). Match them against the four recorded band
tables. A capture that matches one table exactly is an undithered path of that
kind; a full-range path is therefore not dithering. Only a capture that
matches none of them, with more and narrower or textured transitions whose local
mean still follows the ramp, suggests spatial or temporal dithering (temporal
dithering needs several captured frames). About 33 distinct steps means the
path kept 10 bits.

The near-black ramp is for digital (HDMI or framebuffer) capture only; under PQ
its single-code steps are optically unmeasurable.

## 4. Cadence (`cadence/cadence_<rate>fps_p10.y4m`)

One file per exact frame rate `f = N/D`, with header `FN:D` and
`floor(f × seconds)` complete frames. This rounding chooses the frame count,
never a replacement frame rate. Its actual duration is `frame_count × D/N`
seconds, at most the requested duration and less than one frame shorter.
For example, two seconds at 24000/1001 contains 47 frames and lasts
47047/24000 seconds; it is not 48 frames at nominal 24 fps. Integer-rate media
keep their existing frames, headers and names. Fractional filenames replace
`/` with `_`, for example `cadence_24000_1001fps_p10.y4m`.

Each cadence entry records reduced `frame_rate`, `frame_period_seconds` and
`duration_seconds` objects with integer `numerator` and `denominator` fields.
Each frame `n` has source PTS `n × D/N` seconds, black background (Y 64,
chroma 512) and:

- **Barcode** in rect `(x, y, w, h) = (0, 0, 192, 8)`: 24 blocks of 8 by 8 px,
  left to right, Y 64 for 0 and 940 for 1. Order: start marker `1,0`; 16-bit
  index, most significant bit first; 4-bit check nibble, most significant bit
  first, equal to the bitwise complement of the index's low 4 bits
  (`15 - index mod 16`); stop marker `0,1`. The index equals `n`.
- **Moving bar**, 8 px wide, Y 940, rows 16 to the bottom, left edge at
  `x(n) = (4 * n) mod W`, wrapping modulo the width.

**Decode.** For each captured frame, average each block. Reject the frame if any
block mean lies within the dead band, `|mean - 502| < 219` (25% of the 876-code
span, centred on the midpoint): such a block is blended, torn or mis-scaled.
Otherwise call a mean above 502 a 1, require the start and stop markers, rebuild
the index and verify the check nibble. Rejected frames must be discarded, not
interpreted; a blend of two adjacent frames is rejected at 30%, 50% and 70%
weight. Listing decoded indices in capture order shows a repeat as the same index
twice, a drop as a gap, and a regular repeat pattern as the cadence.

**Tear detection.** The barcode covers rows 0..7 only, so a tear below it is
invisible to the barcode. The moving bar is the tear detector: its position
(`x = 4n mod W`) must be one contiguous 8 px bar that agrees with the barcode
index; two bar segments or a position that disagrees with the index indicates a
tear or blend elsewhere in the frame. It also shows motion smoothness.

**Ideal model.** On a display refreshing at `r` Hz, an ideal path shows source
frame `n` from vsync `ceil(n*r/f)` to `ceil((n+1)*r/f) - 1`. For 24 fps on
60 Hz this alternates 3 and 2 refreshes (3:2); 25 fps on 60 Hz gives uneven
2 and 3 refresh runs. This is a model, not a measured result. The manifest records, for refresh rates
60, 50, 120 and 144 Hz, the integer hold lengths over one repeat period
(`refresh_runs`; for example 25 fps on 60 Hz is 3, 2, 3, 2, 2 and 24 fps on 60 Hz
repeats 3, 2). Measuring it needs
timestamped frame or refresh capture (a high-speed camera, photodiode or capture
card with timestamps); a screenshot or a software frame counter cannot show what
the panel displayed.

## Focused qualification

The [focused tests](../tests/test_generate_quality_stimuli.py) use an independent
Y4M reader and cover header tags, frame counts, little-endian samples, chroma
step positions and recorded midpoints, barcode decoding of every frame, bar
positions, dither column codes, a zone-plate formula spot check, manifest hashes,
upsampled-chroma crossings against the recorded midpoints, destination protection
(inside the repository, symlinks, existing paths, a racing destination), staging
cleanup on failure, lazy streaming, the byte guard, parameter bounds and
determinism. Fractional controls also decode every generated barcode, check
complete-frame durations and independently reconstruct ideal refresh runs. The
runner/analyzer tests cover exact-rate refusal, bounded capture requests, safe
scene names, manifest schema/source hashes and rational source-PTS association:

```bash
python3 -B -m unittest discover -s tests -p test_generate_quality_stimuli.py
python3 -B -m unittest discover -s tests -p test_iq_run.py
python3 -B -m unittest discover -s tests -p test_iq_analyze.py
```

**November 20 result:** all 54 focused checks passed after independent review
and its per-rate analyzer-binding correction. The mixed-rate control captures
integer 24 and fractional 24000/1001 independently, leaves 60000/1001 uncaptured,
and checks distinct source counts, timestamps and rational PTS. This prevents a
stale loop variable from attributing one source's captures to another rate.
The authored decode smoke above supplements these controls; it neither runs
mpv nor samples a display. The analyzer batch used its existing NumPy-capable
Python runtime; a default interpreter without NumPy cannot run that module.

## Capture and analyze a private compositor run

The [runner](../tools/iq_run.py) captures selected stimuli through Mutter's
PipeWire screen-cast interface. It requires an active, unlocked graphical
session and an owner-coordinated screen window. It does not unlock the session,
change display settings or monitor for a window. Use the session's system
Python with PyGObject/Gio; the analyzer also requires NumPy. Keep
`XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS` and `WAYLAND_DISPLAY` from that
session when invoking the tools.

Build the timestamped [crop helper](../tools/iq_pw_seq.c) in task-owned storage.
The inherited `pw-read` is a separate external prerequisite, not this helper;
it must produce packed XR30 BT.2020/PQ captures. Record its SHA-256 in the
private receipt.

```bash
mkdir -p "$HDR_WORK/tmp"
export TMPDIR="$HDR_WORK/tmp"
gcc -std=gnu11 -Wall -Wextra -Werror -O2 \
  $(pkg-config --cflags libpipewire-0.3) tools/iq_pw_seq.c \
  -o "$HDR_WORK/iq-pw-seq" \
  $(pkg-config --libs libpipewire-0.3)
python3 tools/iq_run.py "$HDR_WORK/run" \
  --stim-dir "$HDR_WORK/stim" --stim4k-dir "$HDR_WORK/stim4k" \
  --pw-read "$PW_READ" --pw-seq "$HDR_WORK/iq-pw-seq" --session-id auto
```

The output directory must be new. Repeat `--scene` to select scenes; omitting
it selects all supported scenes: `dither`, `siting-c420mpeg2`,
`siting-c420jpeg`, `siting-c420paldv`, `scaling4k`, `cadence-24`, `cadence-25`,
`cadence-30`, `cadence-50` and `cadence-60`. These remain the default set;
fractional captures are explicitly selected with, for example,
`--scene cadence-24000_1001 --scene cadence-30000_1001 --scene cadence-60000_1001`.
The source directory must contain those generated fractional files. Equivalent
scene spellings normalize to the same safe rate slug, and duplicate selected
scenes are captured once. The runner uses the fixed
2560×1600 monitor capture, 8× placement
for 192×108 stimuli, and 2/3 scaling preset. Still images are extracted into
one-frame Y4M files and played in fresh mpv processes, so end-of-stream cannot
leave the last scaling frame identical to the prior grating. mpv keeps the
normal user configuration and receives explicit BT.2020 non-constant-
luminance, limited-range and PQ tags because Y4M does not carry them.

The runner records source and helper hashes, arguments, capture statuses and
`run.json`. Its cadence files are timestamped software captures. For each
rate, the helper writes `cadence-<fps>.raw` and `.ts`; the request is up to
eight seconds (`floor(fps × 8)` complete frames), capped at the complete
frames available in the Y4M source. Header rates are compared by exact rational
equality; a 60000/1001 source cannot pass as nominal 60 fps. The default two-second source therefore requests only two
seconds. The receipt records the available source frames and actual requested
frame count, exact `frame_rate` and `requested_duration_exact_seconds`, plus a
floating-point duration for convenience. The exact fields govern interpretation;
the float does not select or normalize frames. The runner does not loop the source. This does not
sample panel refreshes or qualify optical output. Its cadence crop is only 160
output pixels high; the moving bar is visible there, but tears below that crop
remain unobserved.

Run the [analyzer](../tools/iq_analyze.py) into the same run directory. Supply
measured green-channel PQ10 levels from the known low and high barcode marker
blocks. These endpoints calibrate decoding; do not tune them to maximize the
number of accepted frames.

```bash
python3 tools/iq_analyze.py "$HDR_WORK/run" "$HDR_WORK/stim" "$HDR_WORK/stim4k" \
  --barcode-low "$LOW_PQ10" --barcode-high "$HIGH_PQ10"
```

The analyzer verifies the supplied manifests and source hashes, then creates
`analysis.json` exclusively; an existing report is an error. The 4K source is
used for scaling diagnostics only, not general 4K qualification.
It reports software diagnostics without a universal IQ threshold. Barcode
indices and timestamps can reveal software delivery repeats, drops and
sequence damage, but cannot establish panel cadence. A missing lower tear,
an RGB midpoint shifted by tone or gamut mapping, or a clean compositor capture
does not prove source-domain chroma siting, optical accuracy or Dolby Vision
acceptance. The cadence report also records the exact source frame period,
source duration, decoded-source PTS for every admitted barcode, and exact source
PTS deltas for observed transitions. Rejected samples retain a null source PTS;
sequence gaps and rejected samples still break timing intervals. These are
source-clock associations alongside software capture timestamps, not measured
panel presentation times.

The focused pre-merge lane runs after adversarial review. Its outcome belongs
in the PR receipt, separately from the measurements below.

```bash
python3 scripts/check_repository.py
PYTHONPATH=tests python3 -m unittest -v \
  test_check_repository test_generate_quality_stimuli test_iq_run test_iq_analyze
```

## November 16 digital capture — bounded findings

The [receipt](../evidence/image-quality-digital-20261116.json) records the first
normal-session compositor captures. The 33 source-code plateaus remain distinct
and increasing in both ramps; maximum green residual versus identity PQ is
4.00 codes near black and 1.20 codes at mid grey. These residuals include the
normal display mapping and do not classify bit depth or dithering. JPEG versus
MPEG-2 horizontal chroma edges shift by 0.488–0.512 source px; PAL-DV versus
MPEG-2 vertical edges shift by −0.488 to −0.512 source px. These are relative
RGB-midpoint diagnostics after mapping, not source-domain siting acceptance.

The original final scaling capture duplicated the preceding grating. It is
rejected, with its hash retained. An exact one-frame extraction in a fresh
player produced the missing edge. Fixed interior endpoint regions avoid the
visible desktop dock, and the edge search follows the manifest's expected
slant. Its median 10–90% width is 1.178 output px at 2/3 scaling; no filter
quality threshold is inferred.

Explicit measured start-marker endpoints decode all 192/200/240/400/480
captured frames at 24/25/30/50/60 fps. A few source-index gaps and repeats
remain in the capture stream. Median PTS intervals are about
41.655/40.008/33.344/19.987/16.646 ms: this stream follows content damage,
not 240 Hz refresh. Panel cadence, lower-screen tearing, temporal dither and
optical qualification remain open. No package or display configuration changed.

## Source-range preflight regression coverage

The capture runner supplies an explicit BT.2020/PQ/limited interpretation.
Its single-frame and cadence Y4M preflights reject an explicit incompatible
`XCOLORRANGE` declaration instead of relabelling it as limited. Authored helper
controls accept `XCOLORRANGE=LIMITED` and the legacy absence of this optional
tag, and refuse full/conflicting declarations before source data can be used
under that interpretation. This is a software input-contract regression,
not new mpv, compositor, screen-capture or optical acceptance. It does not
broaden the supported chroma formats or infer omitted physical colour tags.
