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

The minimum width is 192 because the cadence barcode is 24 blocks of 8 px. The
default set is about 24 MB. Output paths are never reused; staging is cleaned on
failure; generating twice produces identical bytes and an identical
`manifest.json`. Zone-plate samples use `math.cos`, so another C library could in
principle differ in a last rounding; the manifest hashes expose any such change.

## Encoding

Default files are 10-bit 4:2:0, header `C420p10 XYSCSS=420P10`, unsigned 16-bit
little-endian samples holding values 0..1023. Range is limited: Y 64..940,
chroma 64..960, neutral chroma 512. Matrix coefficients are BT.2020
non-constant luminance (Kr 0.2627, Kb 0.0593); the declared transfer is PQ and
primaries BT.2020. Values are code values, not luminances. Y4M cannot carry
matrix, range, transfer or primaries, so `manifest.json` is the only record of
them: a consuming tool must be told explicitly. 8-bit variants exist only for
chroma siting (Y 16..235, chroma 16..240, neutral 128).

`manifest.json` lists every file with `bytes`, `sha256` and an `expected` block
of per-stimulus values, plus hashes of the generator source, the parameters and
the design.

## 1. Chroma siting (`chroma_siting/`)

Each file holds two frames over a flat grey luma field: frame 0 has vertical
chroma step edges, frame 1 horizontal ones. The chroma plane steps between
chroma column `k-1` and `k` (row `j-1` and `j`) between two saturated colours
(8-bit Cb/Cr 90/240 and 240/90; the 10-bit file uses four times these codes).

| File | Header | Siting |
|---|---|---|
| `chroma_siting_c420mpeg2_8bit.y4m` | `C420mpeg2` | left (co-sited) horizontally, centred vertically |
| `chroma_siting_c420jpeg_8bit.y4m` | `C420jpeg` | centred both ways |
| `chroma_siting_c420p10_10bit.y4m` | `C420p10` | left, recorded in the manifest only (the BT.2020/HEVC default, chroma location type 0) |

The two 8-bit files have identical luma and identical chroma arrays; only the
tag differs. The 10-bit chroma is the 8-bit chroma times four.

Ideal reconstructed transition midpoints, per edge, are recorded in the
manifest:

- Horizontal, left siting: chroma `i` sits at luma `x = 2i`, midpoint `2k - 1`.
- Horizontal, centre siting: chroma `i` sits at `x = 2i + 0.5`, midpoint `2k - 0.5`.
- Vertical, top siting: chroma row `j` at `y = 2j`, midpoint `2j - 1`; centre
  siting at `y = 2j + 0.5`, midpoint `2j - 0.5`.

The observable is the 0.5 px difference between interpretations. Reading it
requires an upscaler that honours the tag, and a capture sharp enough to place
an edge to well under a pixel; many paths ignore the tag, which is itself a
finding once captured.

## 2. Scaling (`scaling/scaling_p10.y4m`)

Three luma-only frames (chroma 512): zone plate, line gratings, slanted edge.

**Zone plate.** `Y = round_half_up(502 + 438 * cos(pi * r^2 / R))`, with `r` in
pixels from the frame centre sampled at pixel centres and `R = hypot(W, H)`. The
local frequency is `f(r) = r / R` cycles per pixel, so the source is
alias-free (at most 0.5 cycle/pixel at the corner) and the source Nyquist ring
is at `r = R / 2`, recorded in the manifest. After scaling by a factor `s`
(output size = `s` times source size), source frequency `f` appears at `f / s`
cycles per output pixel, so output Nyquist is reached at source radius
`r = 0.5 * R * s`. For `s < 1` expect aliasing beyond that ring; for `s >= 1`
the ring is outside the frame. Compare the observed ring with the prediction.

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

A path that drops 10 to 8 bits without dithering collapses codes in groups of
four: the 33 levels become 9 bands (`code >> 2`: 16..24 and 112..120), each
about `4 * W / 33` columns wide. To count levels in a capture, take one row,
average away sensor noise, and count distinct plateaus along it. Seeing about 33
steps means a 10-bit path; about 9 wide plateaus means 8 bits without dithering;
more than 9 narrower or textured transitions, with the local mean following the
ramp, suggests spatial or temporal dithering (temporal dithering needs several
captured frames to see). Compare against the manifest's per-column codes, not by
eye.

## 4. Cadence (`cadence/cadence_<fps>fps_p10.y4m`)

One file per frame rate, `fps * seconds` frames, header `F<fps>:1`. Each frame
`n` has black background (Y 64, chroma 512) and:

- **Barcode** in rect `(x, y, w, h) = (0, 0, 192, 8)`: 24 blocks of 8 by 8 px,
  left to right, Y 64 for 0 and 940 for 1. Order: start marker `1,0`; 16-bit
  index, most significant bit first; 4-bit checksum (`index mod 16`), most
  significant bit first; stop marker `0,1`. The index equals `n`.
- **Moving bar**, 8 px wide, Y 940, rows 16 to the bottom, left edge at
  `x(n) = (4 * n) mod W`, wrapping modulo the width.

**Decode.** For each captured frame, average each block, call it 1 above 502,
require the start and stop markers, rebuild the index and verify the checksum.
Frames failing markers or checksum are torn, blended or mis-scaled captures and
should be discarded, not interpreted. Listing decoded indices in capture order
shows a repeat as the same index twice, a drop as a gap, and a regular repeat
pattern as the cadence. The bar position is a second, redundant index
(`x = 4n mod W`) that shows motion smoothness.

**Ideal model.** On a display refreshing at `r` Hz, an ideal path shows source
frame `n` from vsync `ceil(n*r/f)` to `ceil((n+1)*r/f) - 1`. For 24 fps on
60 Hz this alternates 3 and 2 refreshes (3:2); 25 fps on 60 Hz gives uneven
2 and 3 refresh runs. This is a model, not a measured result. Measuring it needs
timestamped frame or refresh capture (a high-speed camera, photodiode or capture
card with timestamps); a screenshot or a software frame counter cannot show what
the panel displayed.

## Focused qualification

The [focused tests](../tests/test_generate_quality_stimuli.py) use an independent
Y4M reader and cover header tags, frame counts, little-endian samples, chroma
step positions and recorded midpoints, barcode decoding of every frame, bar
positions, dither column codes, a zone-plate formula spot check, manifest hashes,
existing-output protection, staging cleanup on failure, the byte guard,
parameter bounds and determinism:

```bash
python3 -B -m unittest discover -s tests -p test_generate_quality_stimuli.py
```
