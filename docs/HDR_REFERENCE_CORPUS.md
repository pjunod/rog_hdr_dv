# HDR reference corpus — reproducible source images without private assets

The [generator](../scripts/generate_hdr_corpus.py) creates six original synthetic
frames for numerical display-processing checks. It invokes no Dolby tool and
creates no Dolby metadata. Its output is a source fixture, not an optical panel
measurement, calibration profile or full Dolby Vision qualification.

## Generate and interpret the inputs

Use Python 3 and a new output directory outside the source repository. Its
parent must already exist. For example:

```bash
python3 scripts/generate_hdr_corpus.py /tmp/hdr-reference-corpus \
  --width 192 --height 108 --fps 24
```

The default corpus is 192×108 at 24/1 fps, with zero-indexed filenames
`frame_000000.tif` through `frame_000005.tif` and `manifest.json`. Output paths
are never reused. The generator stages the files before publication and cleans
its own staging on failure. Dimensions and frame rate are explicit and bounded;
the tool is intended for compact numerical fixtures rather than panel-sized
measurement patterns.

| Frame | Content |
|---|---|
| 0 | Display-linear neutral ramp from 0 to 1000 cd/m² |
| 1 | Near-black neutral steps |
| 2 | Neutral highlights including 100, 203, 400, 616 and 1000 cd/m² |
| 3 | Primary/secondary RGB channel patches at 203 cd/m² |
| 4 | Primary/secondary RGB channel patches at 1000 cd/m² |
| 5 | Dark background with a smaller 1000 cd/m² peak window |

The files are classic little-endian TIFF: unsigned 16-bit, uncompressed,
interleaved RGB, full digital range. Absolute display-linear BT.2020/D65 RGB
channel values are encoded with the inverse ST 2084 EOTF. PQ normalization
remains 10000 cd/m²; this corpus's synthetic content is bounded at 1000 cd/m².
The formula follows [ITU-R BT.2100](https://www.itu.int/rec/R-REC-BT.2100).

TIFF tags describe RGB storage only. Transfer function, primaries and source
intent are declared in the manifest, so a consuming tool must receive the
matching encoding explicitly. A generic SDR image viewer is not a numerical
reference for these pixels. Coloured RGB channel intensity is different from
photometric Y; the manifest records both and identifies its BT.2020 weighting.
The small peak window is a synthetic scene feature, not a 10%-coverage panel
measurement claim.

The manifest includes dimensions, rational frame rate, patch rectangles,
linear channel values, quantized codes, frame labels, scene boundaries,
source/mastering intent and SHA-256 hashes of generator source, canonical
parameters, design and every TIFF. It includes no host identity, external
input, OEM data or proprietary processing metadata.

## Official reference workflow

Dolby's public [analysis workflow](https://professionalsupport.dolby.com/s/article/Longplay-analysis?language=en_US)
describes generating metadata from PQ source images and using CM Offline to
render reference outputs. Use tool-generated metadata and its validation
workflow; do not fabricate proprietary trim fields or bypass validation.
Record the exact source interpretation, version, frame alignment, target and
processing options separately from this generic input manifest.

Official tools, documentation, generated processing metadata and reference
outputs remain private. Public repository code supplies generic inputs and
sanitized evidence only. The first private reference experiment completed
successfully with explicit target comparisons and fixed source encoding. A single target
peak is not a model of the panel's complete area-dependent luminance response.
Tool-based numerical comparisons and physical calibration are separate stages.

## Focused qualification

The [focused tests](../tests/test_generate_hdr_corpus.py) include independent
TIFF decoding, known PQ values, bounds and monotonicity, deterministic hashes,
manifest agreement, existing-output protection and failure cleanup. Run them
only after final adversarial review:

```bash
python3 -B -m unittest discover -s tests -p test_generate_hdr_corpus.py
```

All 11 focused tests passed on the first run after independent review; the
[test receipt](../evidence/hdr-corpus-tests.json) binds the checked source.
The separate private reference experiment has completed. Its tool-generated
metadata and rendered outputs were retained with source and artifact hashes;
the owned processing container and runtime image were removed. Proprietary
processing details, outputs and numerical comparisons remain private. This
establishes a reference workflow, not a real-time playback processor, creative
trim qualification or measured panel accuracy. [Status](STATUS.md) records the
current acceptance boundary.

## Restoration checkpoint (2026-10-13)

The historical experiment above is an inherited receipt, not an available
corpus: its only known Mac temporary directory was lost. The explicitly
authorized restoration uses a new private durable lane, not that old receipt.
The unchanged reviewed generator produced six 192×108, 24/1-fps source TIFFs.
Official Linux tools 5.6.4 ran unprivileged, CPU-only, in the existing offline
native x86_64 builder, with no GPU, display, activation network or host install.
CM Analyze generated genuine CM4 longplay metadata; Metafier validation passed.
No RPU, coefficients or trims were supplied by hand.

CM Offline produced six references each for the declared panel target
(616 cd/m², 0.0004 black, firmware-declared primaries), a documented custom
300 cd/m² BT.2020 target and preset 28 (600 cd/m² BT.2020). Preset 49 at
1000 cd/m² was refused because it equals the mastering display's peak;
that failure is retained and does not count as reference coverage. No bypass,
identity substitute or rerun of successful targets was used. The original
analysis also contains tool-generated L2/L3/L9, but no L8; the official
validation's missing-L8 warning and rounded-aspect-ratio warning remain explicit.
Output encoding was explicitly full-range PQ BT.2020 RGB, distinct from the
custom physical target gamut.

Original TIFFs, XML, command vectors, tool/analysis/source/frame hashes and logs
are preserved privately in a verified durable archive and extracted directory,
outside Git. Explicit unsigned RGB16-code normalization to RGB-f32le changes
storage only, not gamut, PQ transfer, exposure, geometry or ICC processing.
This is new authentic reference generation, not yet open-renderer agreement.
The separately reviewed post-reshape interface and its affected qualification
remain pending; numerical baseline, consumer-RPU reshaping, L8/creative trims
and optical acceptance are not established by these official renders.
