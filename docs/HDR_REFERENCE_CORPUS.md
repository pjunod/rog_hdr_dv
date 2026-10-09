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
sanitized evidence only. The first proposed experiment compares explicit
reference targets while holding source encoding constant. A single target
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

Implementation and syntax checks are complete; runtime tests and actual
reference-tool processing are pending. [Status](STATUS.md) records the current
acceptance boundary. No reference output has been produced or compared yet.
