# Image-quality source stimuli — chroma siting, scaling, dithering and cadence

The [generator](../scripts/generate_quality_stimuli.py) creates owned synthetic
YUV4MPEG2 (`.y4m`) sources for later image-quality qualification of a display
path. It invokes no Dolby tool and creates no Dolby metadata. Like the
[HDR reference corpus](HDR_REFERENCE_CORPUS.md), its output is a digital source
fixture. **These files prove nothing about a display, compositor, scaler or
decoder until they are played, captured and measured.** Frame cadence in
particular needs timestamped frame or refresh capture; no source file can show
it.

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
| `--cadence-fps` | 24 25 30 50 60 | unique integers 1..120, at most 16 |
| `--cadence-seconds` | 2 | integer 1..10 |
| `--max-total-bytes` | 64 MiB | checked before anything is written |

Large `--cadence-fps` and `--cadence-seconds` trip the 64 MiB guard: at the default
192x108, five rates at 10 s need about 118 MB, so the run is refused unless
`--max-total-bytes` is raised (for example `--cadence-seconds 10 --max-total-bytes 134217728`).
The estimate counts stimulus files only, not `manifest.json`.


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

## 4. Cadence (`cadence/cadence_<fps>fps_p10.y4m`)

One file per frame rate, `fps * seconds` frames, header `F<fps>:1`. Each frame
`n` has black background (Y 64, chroma 512) and:

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
determinism:

```bash
python3 -B -m unittest discover -s tests -p test_generate_quality_stimuli.py
```
