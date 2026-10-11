# Display target sources — general HDR and wide-gamut targets (nativehdr9)

**Status:** implemented as the last six commits of the upstream-facing Mutter
series and Ubuntu patches 0055–0060 (`nativehdr9`); adversarially reviewed,
fast-lane qualified (synthetic headless tests) and packaged; not installed ·
**Date:** 2026-10-11.

The compositor maps highlights toward an output's declared peak and compresses
out-of-gamut colour toward its declared gamut ([HLG and tone
mapping](HDR_MAPPING.md)). Until now, an output only had a declared target on
one route: an internal eDP panel whose DisplayID 2 extension declares native
RGB BT.2020 PQ, in BT.2100 mode. The ROG panel takes that route. Most HDR
hardware does not: external monitors and most HDR laptops declare their HDR
capability through CTA-861 HDR static metadata, and their gamut only through
the base EDID colour characteristics. On those outputs the target was always
the encoding fallback, so nothing was mapped. Wide-gamut SDR panels in the
native SDR mode had no declared gamut either. General availability needs the
same behaviour on that hardware, as far as its declarations can be trusted.

## Sources, in order

The colour device selects luminance and gamut independently. Each comes from
one source as a whole; fields are never combined across sources. The first
usable source wins.

| Target | 1st | 2nd | Otherwise |
|---|---|---|---|
| Luminance (BT.2100 only) | DisplayID 2 physical luminance (Display Parameters): the 10% window peak, and the minimum when declared | CTA-861 HDR static metadata: desired content maximum luminance as the peak, desired content minimum luminance as black | Encoding fallback |
| Primaries (BT.2100) | DisplayID 2 native chromaticities only | — | Encoding fallback |
| Primaries (native SDR) | Base EDID colour characteristics only, the encoding's own declaration | — | Encoding fallback |

- **Eligibility.** An active output in BT.2100 or native SDR mode, with HDR
  not forced by the debug control. The default SDR mode renders into an
  assumed sRGB encoding and keeps the fallback. The native DisplayID eDP route
  keeps its existing capability rules; only target selection widens.
- **DisplayID physical luminance** is used wherever its declaration is
  firmware-declared and usable, not only on the native eDP route. It must
  declare the 10% window peak. A missing minimum is filled from the encoding
  fallback, never from CTA. A minimum-only declaration is not a source, so
  it does not hide a CTA peak.
- **CTA luminance** is used when the HDR static metadata block is present and
  declares a desired content maximum. A missing or zero desired minimum leaves
  black at the encoding fallback. CTA-861 defines these as the content range
  the display considers optimal, not a physical measurement. In practice it is
  the only peak most HDR displays declare. It gets its own provenance,
  `cta-declared`, distinct from the DisplayID `firmware-declared` physical
  value.
- **Base EDID primaries** get the provenance `edid-declared` and are used in
  the native SDR mode only. They pass the same validation the native SDR mode
  applies before rendering with them (complete RGBW, a usable non-degenerate
  triangle, protocol representability), plus the chromaticity domain
  (x ≥ 0, y > 0, x + y ≤ 1) and geometry checked after quantization. Their tolerance is one 10-bit EDID
  step. In native SDR mode the encoding primaries are these same values, so
  the target equals the encoding. Colour from wider sources is then compressed
  into the panel's gamut instead of clipped at its edges. DisplayID
  chromaticities are not used there: the encoding cannot express a different
  gamut, so compressing toward one would still clip.
- **No base EDID gamut in BT.2100.** Many HDR displays declare their SDR
  gamut in the base EDID and show a wider one in HDR. Compressing BT.2020 or
  P3 content toward it could visibly desaturate it, and no measurement says
  which displays do this. BT.2100 keeps the DisplayID-only gamut.
- **Validation** of every luminance source is the existing rule (finite,
  ordered, representable on the wire, and a peak of at least 1 cd/m² above a
  lower minimum), plus one more: the peak must exceed the encoding's nominal
  reference white (203 cd/m² for PQ). A declared HDR peak at or below
  reference white cannot present HDR, and mapping toward it would dim all
  SDR content. The nominal value is used, not the brightness-scaled one, so
  a target does not appear and disappear with the brightness setting. A
  source that fails falls through to the next source, not straight to the
  fallback.
- **Containment frame.** Clutter adapts a display target from its encoding's
  white to D65, the same adaptation the pixels undergo, before judging
  containment and computing limits and matrices. A native SDR output whose
  EDID white is not D65 is then never judged outside its own gamut, and
  clients that follow its description are neither compressed nor refused
  direct scanout. BT.2100 targets move by under 3e-5 xy, inside their
  tolerance.

## What does not change

- KMS HDR metadata stays zero ("unknown"), as [decided](HDR_MAPPING.md#kms-hdr-metadata-stays-unknown).
- PQ content without a declared peak is still not tone-mapped. The mapping
  predicates, the BT.2390 curve and the ACES compression are unchanged. Only
  the outputs that have a declared target grow.
- Forced HDR (the debug control) keeps the fallback target.
- No panel model, vendor or luminance constant enters the compositor. The
  behaviour follows from the declarations alone.
- A change that only affects provenance or another unpublished field creates
  no new Wayland description identity. The published values and identity
  rules are those of the [target feedback contract](MUTTER_TARGET_LUMINANCE.md).

## Provenance and inspection

`MetaColorTargetSource` grows two values, `CTA_DECLARED` and `EDID_DECLARED`,
next to `FIRMWARE_DECLARED` (DisplayID) and `ENCODING_FALLBACK`. The
rendering colour state treats any declared source as a target. The fallback is
never one. The colour device's debug output names the source of each target,
so it is visible which declaration an output used.

## Acceptance

Synthetic, headless tests on the upstream-facing series and the Ubuntu
package series:

1. A CTA-only external HDR monitor (desired maximum 600, minimum 0.05 cd/m²)
   in BT.2100 publishes 0.05–600 with CTA provenance. Its blending state
   carries the peak, and PQ content mastered at 1000 cd/m² is highlight
   mapped toward 600.
2. A CTA block with no desired maximum keeps the fallback. A desired minimum
   without a maximum is ignored.
3. DisplayID physical luminance beside a CTA block wins. A peak-only
   DisplayID declaration does not borrow the CTA minimum. A minimum-only
   declaration falls through to CTA. A peak at or below 203 cd/m² falls
   through.
4. In BT.2100, base EDID primaries are never the target gamut. DisplayID
   native chromaticities are, when usable.
5. In native SDR mode, the target primaries equal the encoding primaries with
   EDID provenance, also when DisplayID declares chromaticities. BT.2020
   content is compressed toward them. The output state and a client built
   from its colorimetry are not mapped, with a white other than D65. In the
   default SDR mode the target stays the fallback.
6. Unusable base primaries (rejected by the native SDR validation) leave the
   fallback in both modes.
7. The existing native-route, mapping, gamut and Wayland tests pass. Two
   phases that left the native route while keeping DisplayID declarations
   and expected the fallback now expect the DisplayID target to stay. They
   then withdraw the declarations to reach the fallback, because the route
   restriction is what this change removes. Their client expectations are
   unchanged.

Physical acceptance on a second machine follows separately. Whether a display's
CTA or base EDID values describe what it actually shows needs an optical
measurement. Until there is one, these targets are firmware declarations, not
calibration.
