# Native target gamut — retain physical colour declarations

**Status:** library implementations compiled; compositor integration and final
review/runtime qualification in progress.
**Date:** 2026-10-09.

Companion to [target luminance](MUTTER_TARGET_LUMINANCE.md) and the
[colour-pipeline audit](COLOUR_PIPELINE_AUDIT.md). This extends physical-target
feedback with firmware-declared RGB primaries and white point. It does not
apply a display profile or change rendered pixels.

## Problem and decision

BT.2020 identifies the encoding used to send HDR pixels to this display. Its
triangle is not evidence of the panel's physical gamut. The existing output
description repeats encoding primaries as target primaries, even when native
DisplayID contains a separate physical declaration.

Add an independent, lossless library accessor for that declaration, then
consume it on the compositor's already validated native HDR route. Preserve
encoding state, renderer identity and the default-signal library API. Keep
firmware declarations distinct from measurements of this unit.

| Alternative | Decision |
|---|---|
| Reuse the default-signal primaries getter | Rejected: its documented semantics and sRGB precedence describe signal encoding. |
| Replace the output's BT.2020 encoding primaries | Rejected: would change pixel interpretation rather than describe the physical target. |
| Add independent target RGBW state | Selected: truthful application feedback with explicit provenance and immutable descriptions. |

## Library contract

Introduce new types and a borrowed
`di_displayid2_data_block_get_native_chromaticities()` accessor without
extending existing public structures. Its lifetime follows the parent parsed
EDID object. Preserve each pair of unsigned 12-bit counts, their denominator
4096, the declared coordinate system and block revision. Do not replace raw
counts with rounded xy values.

The format evidence is the
[pinned upstream decoder](https://raw.githubusercontent.com/gjasny/v4l-utils/1316a80455ef70889bea89491f37cd69170f3ee7/utils/edid-decode/parse-displayid-block.cpp)
and [NVIDIA's pinned parser](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/src/common/modeset/timing/nvt_displayid20.c).
The implementation must preserve their source identity in its receipt. These
implementations support the layout; complete independent verification against
the VESA specification remains open.

Display Parameters has a 29-byte payload. Revisions 0 and 1 use four packed
pairs at block-relative offsets `0x0c`, `0x0f`, `0x12`, `0x15`. For each pair:

```text
a = byte[0] | ((byte[1] & 0x0f) << 8)
b = (byte[1] >> 4) | (byte[2] << 4)
coordinate = count / 4096
```

Feature bit 6 selects CIE 1976 u′v′ rather than CIE 1931 xy. Luminance-class
bits must not suppress independent chromaticity parsing. Recognized image-size
unit flags are independent too; unsupported revisions or reserved header bits
do not silently inherit a known interpretation.

Return no declaration for an incompatible tag, unsupported format or malformed
length. For a recognized declaration, retain every raw count even when a point
is mathematically unusable. Per-point validity means only that interpreted xy
has `x >= 0`, `y > 0`, and `x + y <= 1`. It proves neither a complete RGB gamut
nor calibrated accuracy. The evidence does not establish a special zero-value
sentinel: an individual zero coordinate is not automatically absent.

For CIE 1976, conversion uses
[the standard inverse equations](https://github.com/colour-science/colour/blob/v0.4.6/colour/models/cie_luv.py):

```text
D = 6u′ - 16v′ + 12
x = 9u′ / D
y = 4v′ / D
```

Require a positive denominator and finite valid coordinates. Prefer exact
integer inequalities on raw counts for domain checks, preserving boundary
points such as `x + y == 1`. Keep complete-gamut geometry in the consumer.
Optional-field failures must not change legacy extension diagnostics or CTA
metadata. Package this as a new API generation after hdr7; consumers check for
the function explicitly rather than trusting a distribution version string.

## Compositor contract

Copy native declarations separately from default-signal primaries, capability
and luminance. Scan every Display Parameters block. Identical whole
declarations can agree; conflicts, or an unsupported/malformed declaration
alongside a supported one, withdraw native target primaries. Never assemble a
gamut from different blocks.

Convert a supported complete RGBW declaration to xy. Require usable points,
a non-collinear RGB triangle and a white point strictly inside the triangle.
Primary points on the `x + y == 1` boundary are allowed. Quantize the eight xy
coordinates to the protocol's signed integers scaled by 1,000,000, then
revalidate geometry with 64-bit integer cross products. Reject collapsed
triangles and a white point on or outside the quantized boundary. Fall back as
a complete RGBW set; never add an assumed D65 white to incomplete native RGB.

Select this physical target only for active BT.2100 on the existing validated
native BT.2020/PQ internal eDP route, with supported encoding and no forced HDR.
SDR, CTA and other ineligible routes keep encoding-derived targets. Luminance
and gamut availability are independent; one missing component does not invent
or erase the other.

The colour device computes both target components before one target-volume
notification. State records carry effective values and firmware-declared or
encoding-fallback provenance. Target-only changes preserve the exact encoding
state object and do not invalidate shaders or scanout encoding comparisons.

Extend the existing immutable Wayland record with the eight published target
coordinates. Hash and compare encoding plus published luminance and primaries;
provenance-only and sub-quantization changes remain quiet. Retained descriptions
keep their original information. Output and preferred feedback share current
identities, including primary-monitor fallback and output removal. Use the
existing topology-complete refresh and `wl_output.done` handling.

The [Wayland 1.48 contract](https://github.com/wayland-mirror/wayland-protocols/blob/1.48/staging/color-management/color-management-v1.xml)
requires separate encoding and target-primary events. Client-created
parametric descriptions retain their encoding-derived targets; ICC information
remains on its existing ICC path. No ICC state may be cast to a parametric state.

## Qualification and remaining work

Establish the compiler loop against the qualified source before editing. Build
the library and affected compositor binaries with warnings as errors. Keep the
baseline package environment unchanged until its artifacts are exported.

At the final premerge review, inspect parser ABI, mathematical boundaries,
route selection, immutable-record lifetimes and notification ownership. Then
run the affected fast lane once, retrying only failed or invalidated checks:

- Synthetic packing, extremes, revisions, lengths and coordinate systems;
  independent luminance validity and unchanged legacy signal semantics.
- Whole-declaration duplicate/conflict handling in both orders; complete RGBW
  geometry and quantization failures, including valid primary boundary points.
- Native selection and every fallback; independent target components;
  unchanged BT.2020/PQ normalization, reference white and encoding identity.
- Wayland versions 1 and 2: target-only changes, immutable old snapshots,
  output/preferred agreement, unchanged outputs, primary switch, removal and
  teardown; existing input and ICC regressions.

No raw panel EDID or OEM profile belongs in the public fixtures. Runtime
acceptance must later verify the actual output descriptions on the laptop.
Tone/gamut mapping, ICC output characterization, HLG and optical calibration
remain separate implementation and measurement work. This correction supplies
target information to consumers; it does not claim those consumers use it.

## Current implementation receipt

The Ubuntu hdr8 candidate is `805d07b9116cd1fc7bcc7446617ef13f92857b9c`;
the upstream candidate is `1462cebeac89a5f5f5b7fa475b7501eb21158b53`. The
[compiler receipt](../evidence/native-chromaticities-compile.json) records that
production libraries and synthetic test binaries compile on native amd64 with
GCC 15.3.0, Meson 1.10.1 and warnings as errors. No new runtime checks have
executed yet. The appended patches and updated hashes preserve all earlier
series bytes.

The public header, new test source and added parsing functions agree across
these candidates, but their surrounding parser implementations differ. Final
qualification therefore runs the four new test groups on both source series
and verifies previous consumer binaries against the new libraries. A literal
packed-byte fixture provides a check independent of the fixture encoder.
