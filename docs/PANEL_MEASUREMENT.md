# Panel measurement — qualify this unit before calling it calibrated

**Status:** procedure defined; equipment and optical execution outstanding ·
**Written:** 2026-10-09.

Companion to [operations](OPERATIONS.md) for the controlled display window and
[the quality plan](DOLBY_VISION_AND_QUALITY.md) for overall acceptance. This
procedure separates emitted-light evidence from source metadata, screenshots
and numerical reference processing. The ASUS GU605MZ's firmware declarations
and factory profiles are starting inputs, not a measured calibration of this unit.

## 1. Establish the measurement chain

Use a supported emissive colourimeter with an appropriate spectral correction,
preferably profiled against a reference spectroradiometer on this panel. Record
instrument model, serial privately, firmware, driver version, correction-file
hash, observer and integration settings. A generic OLED correction cannot be
assumed to represent this Samsung panel's emission spectrum.

[ArgyllCMS documents](https://www.argyllcms.com/doc/instruments.html) supported
instruments and spectral-sample corrections. Its listed i1 DisplayPro and
ColorChecker Display family are candidates to evaluate. A similar product name
or a manufacturer's macOS/Windows support statement does not establish support
for a newer instrument revision on Linux. Verify the exact model with the
selected driver before buying or promising compatibility. No purchase has been
made or instrument selected by this project.

A reference instrument can be borrowed or supplied by a calibration service;
this project does not require purchasing a laboratory spectroradiometer. The
owner currently has no measurement instrument. Software development continues
while optical qualification remains explicitly open.

## 2. Record one repeatable display condition

Record the following before each run; keep identifying captures private:

| Condition | Required record |
|---|---|
| Software | Exact kernel, driver, compositor/library packages, renderer and pattern-source hashes |
| Output | Connector, active GPU route, native resolution, refresh rate, VRR state, buffer format and colour description |
| Colour pipeline | Application transform, compositor transform, output encoding, active ICC/calibration hashes and LUT/CTM state |
| Controls | SDR/HDR mode, reference white, brightness, Night Light/comfort adjustments and auto-brightness state |
| Power | AC/battery, power profile and panel warm-up duration |
| Environment | Ambient illumination at the screen, reflection control, instrument position and viewing geometry |
| Pattern | Source encoding, RGB code values, nominal luminance, window area, background, dwell and sequence position |

Begin with the Intel internal-display route and a fixed refresh rate. Qualify
other routes and VRR later as distinct conditions. Preserve the original
settings and package recovery path before changes. A fixed baseline does not
mean silently overriding the owner's saved settings outside the test window.

Use a 30-minute initial warm-up as the starting procedure. Verify stability
with repeated reference patches rather than assuming the elapsed time proves
stability. If repeated mid-grey/reference-white readings differ by more than
1% in luminance over three measurements, extend warm-up and record the drift.
These are project procedure choices, not claims of an external certification.

## 3. Prove the software path before measuring light

The pattern renderer must explicitly declare its transfer function and primaries.
Verify the application's submitted values and the compositor's target/output
state. For PQ, preserve absolute 10000 cd/m² encoding normalization; the panel's
physical target is separate. For SDR, record the chosen reference-white mapping.
A PNG shown in an ordinary image viewer is not automatically an absolute HDR
measurement pattern.

Use the [synthetic corpus](HDR_REFERENCE_CORPUS.md) for numerical pipeline
checks, not as a claim that its small images form a complete optical chart.
Use native-resolution, precisely sized measurement patches for the physical
run. Confirm scaling, range conversion and overlays cannot alter the sampled
region. Cross-check the same encoded patch through two independent consumers
before treating an application disagreement as a panel calibration problem.

## 4. Measure capability, then validate a separate calibration set

Keep characterisation and validation patches separate. Record individual
readings, timestamps and repeatability; do not retain only averages.

1. Measure black, near-black steps, mid-grey, reference white and RGB/secondary
   patches at low and moderate luminance. Establish the instrument's usable
   floor; report a bound or unqualified reading below it rather than zero.
2. Measure peak response at 1%, 10%, 25% and 100% window areas, with recorded
   backgrounds and dwell. Start with brief high-luminance exposures, then record
   time-dependent output separately. Do not treat one short peak reading as a
   sustained full-frame capability or as a Dolby target model.
3. Measure white chromaticity, grey balance, EOTF response and colour patches
   for SDR and PQ independently. Characterise the usable gamut at several
   luminances, not only the most saturated primary at one brightness.
4. Fit only the correction appropriate to the established pipeline domain.
   Keep characterisation, calibration, gamut mapping and comfort adjustments
   distinct. Do not load an SDR VCGT into a PQ path without a proven transform
   domain and reset behavior.
5. Validate using held-out patches, changed patch ordering and repeated anchors
   to detect drift. Compare applications, window/fullscreen paths and supported
   display transitions with the same source and measurement conditions.

## 5. Define the accuracy goals before fitting

These are initial project engineering targets for in-gamut reproducible patches,
not certification thresholds or promises about the panel. Record failures and
measurement uncertainty rather than adjusting the limits after seeing results.

| Check | Initial target and interpretation |
|---|---|
| SDR colour difference | Mean CIEDE2000 ≤ 2 and maximum ≤ 5 on the held-out set, with the reference white and adaptation assumptions recorded |
| PQ colour difference | Report ΔE_ITP mean, 95th percentile and maximum; initial goals mean ≤ 3 and 95th percentile ≤ 6 for patches within the measured reproducible volume |
| Luminance tracking | Within 5% of the declared target for non-tone-mapped patches at or above 1 cd/m²; lower levels need absolute error and instrument-floor reporting |
| Neutral ordering | No measured reversal larger than combined repeatability/uncertainty; no invented near-black pass below instrument capability |
| Cross-application agreement | Same declared source patch agrees within combined measurement uncertainty and the relevant colour/luminance limits |
| Stability | Report anchor drift and repeatability; changes exceeding 1% luminance trigger investigation before fitting |

[ITU-R BT.2124](https://www.itu.int/rec/R-REC-BT.2124-0-201901-I) defines ΔE_ITP
for visibility of colour differences, including HDR. It does not prescribe the
project limits above. Gamut coverage, peak capability and mapped out-of-gamut
appearance must be reported separately from accuracy within the reproducible
volume. Do not delete failing patches from the validation set to improve a mean.

## 6. Preserve the qualification result

The private receipt includes raw instrument samples, all conditions above,
source/patch hashes, reference values, uncertainty/floor handling, correction
versions and before/after validation. Publish only reviewed summaries without
serials, local paths or OEM payloads. A screenshot or a successful profile save
cannot replace that receipt.

Final acceptance also requires HDR/SDR switching, brightness changes, screen
blanking/resume, AC/battery and the chosen refresh/VRR combinations. The complete
solution remains unqualified until package recovery, processor-reference checks,
application consistency and this optical procedure each have their own evidence.
