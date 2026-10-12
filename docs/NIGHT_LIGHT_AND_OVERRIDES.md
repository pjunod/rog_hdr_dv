# Night Light in HDR, and per-monitor target overrides (nativehdr10)

**Status:** both parts implemented as Mutter patches 0050–0061; every
commit compiled with warnings as errors and the exported series replays to
the built tree. Adversarial review and unit validation are pending; no unit
test has run on this candidate ·
**Date:** 2026-10-11.

Two compositor changes for general availability, specified together because
both change how the colour device builds an output's rendering colour state.

## 1. Night Light applied in linear light in BT.2100

**Defect.** Night Light programs the CRTC gamma LUT, or the CTM where there
is no LUT, with blackbody channel scales (`meta-color-device.c`, the
temperature path from `meta_color_get_temperature_rgb_scales()`). That runs
after composition, on encoded values. In SDR modes the encoding is a gamma
curve, and scaling it is the long-standing, accepted approximation. In
BT.2100 the values are PQ code values. Scaling them is neither a white-point
shift nor a uniform dimming. A 20% scale of a PQ code value removes far more
than 20% of the light, unequally across the tonal range, and skews hue.
Nothing excludes BT.2100. Upstream has the same behaviour.

**Contract.**

- In BT.2100 the colour device never programs temperature scales into the
  gamma LUT or CTM. Both stay at identity (calibration ramps from an
  assigned profile are an SDR concept and are not applied to PQ either).
- The white-point shift is part of the output's rendering colour state.
  It uses diagonal von Kries channel factors in the output's linear RGB
  frame, derived from the Planckian white at the Night Light temperature.
  Negative factors are clamped to zero at parameter construction and the
  factors are divided by their largest value; no per-pixel clipping is added.
  This projects an out-of-gamut Planckian white (notably at 1000 K) into
  nonnegative output RGB, rather than claiming exact chromaticity there.
  Representable whites, including the 4000 K acceptance point, retain the
  requested chromaticity. It runs
  in the blending → output conversion before PQ encoding, wrapped in the
  output-RGB/linear-BT.2020 conversions, so that no output RGB channel
  exceeds its unadapted value. Night Light
  therefore warms and very slightly dims, as in SDR, but never brightens.
- One owner: the colour device sets it on the rendering colour state, next
  to the target volume. Every reader gets the same state, as with highlight
  mapping and gamut compression: the renderer, the direct-scanout predicate
  and the cursor plane. A surface is refused direct scanout while the
  adjustment is not identity, because its pixels need the conversion.
- Screencasts, screenshots and monitor streams do not carry it, which
  matches SDR, where the gamma LUT never reaches them.
- Temperature changes arrive in small steps during the transition. Each
  step is a uniform value, never a new shader. The rendering state is
  replaced only when the value changes exactly.
- At the default temperature (Night Light off), the adjustment is exactly
  identity and the state equals today's, bit for bit.
- SDR modes keep the existing gamma LUT/CTM behaviour. This change is
  limited to the mode where the existing behaviour is wrong.

**Acceptance.** Unit tests: identity at the default temperature (no
transform op, identical state); at 4000 K, the adapted D65 white lands on
the Planckian white within the matrix precision, and no channel exceeds 1;
in BT.2100, no gamma LUT or CTM is set for temperature; SDR is unchanged.
Compositor test: a surface on a BT.2100 output with Night Light active is
converted, not scanned out, and returns to scanout when it is turned off.
CPU and GLSL agree.

### Implementation (patches 0050–0054)

Patches 0050–0052 are the original work in progress, imported with their
authorship and content unchanged. Patch 0053 replaces their Bradford
adaptation with the diagonal method above. In the output's linear RGB the
Planckian white has components (r, g, b). Negative components are set to
0, and each is divided by the largest. The adjustment is
to_bt2020 · diag(r, g, b) · from_bt2020 in the existing linear-BT.2020
pipeline. For a BT.2100 output this is the diagonal itself. Its regressions
cover:

- 1000, 1700, 3990, 4000, 4700 and 10000 K, on BT.2020 and DCI-P3 outputs;
- finite factors in [0, 1], and no output channel above its unadapted value;
- the 4000 K white landing on the Planckian chromaticity;
- a representable white on an output whose own white is not D65.

At 1000 K the blue factor of a BT.2020 output is clamped, so that white is
projected rather than exact. The default temperature bypass stays exact.

Patch 0054 adds the mode-transition and capture regressions. Warm SDR
temperatures in both the LUT and the CTM path are followed by BT.2100 and a
return to SDR. The earlier stale-LUT hypothesis was not a defect: the
existing white-point tracking already resets the LUT, and the regression now
covers it. Forced HDR gets a white adaptation but no luminance or gamut
target.

**Capture inventory**, from the source at this tree. No change was needed.

- Monitor stream stage paint derives its blending state from the stream's
  own colour state, which never carries an adapted white.
- The pre-paint scanout copy runs only when the stream state equals the
  output state, and scanout is refused while adaptation is active.
- The pre-swap blit copies the view's offscreen only when the stream state
  equals the view's blending state. An adapted blending state never equals
  a stream state, because the adapted white is part of equality, so the blit
  falls back to stage paint.
- Window, area and virtual streams, `clutter_stage_paint_to_buffer`/`_to_framebuffer`
  and `meta_window_actor_paint_to_content` use the caller's or the actor's
  colour state, never the device's rendering state.
- The only adapted-to-unadapted transform is the stage view's offscreen
  pipeline to the output colour state, which is the intended output path.

The regressions assert that the stream blending state carries no adapted
white.

## 2. Per-monitor target overrides

**Why.** Display declarations are often wrong. Some monitors declare a CTA
peak of 1000 cd/m² and reach 400, and some laptops carry boilerplate
chromaticities. A user, or later a measurement, needs to correct an
output's target without a code gate.

**Precedence** for each component (luminance; BT.2100 primaries), the first
present and valid wins, as a whole source:

1. A measured characterization (the [deferred contract](HDR_MAPPING.md#output-characterization--defined-deferred-until-measured); not yet implemented).
2. The user's override for this monitor.
3. DisplayID.
4. CTA-861 (luminance only).
5. The encoding fallback.

**Override fields**, stored per monitor in the monitor configuration
(`monitors.xml`) and keyed like the monitor's other settings:

- `target-peak-luminance` (cd/m²) and optional `target-min-luminance`. The
  peak must pass the same validation as declared sources, including
  exceeding the nominal reference white. Without a minimum, black is the
  encoding fallback's.
- `hdr-gamut-source`: `auto` (the default: DisplayID, then fallback),
  `base-edid` (use the base EDID colour characteristics as the BT.2100
  target, for wide-gamut monitors that declare their gamut correctly
  there), or `none` (no gamut target).

The override gets its own provenance, `user-declared`. It changes only
target selection; it never blocks or forces a mode. The D-Bus monitor
configuration API accepts and reports the fields, and `GetCurrentState`
also reports the effective target and its provenance, so the choice is
visible from inside the system. `gdctl` gets matching options. A settings
UI is later work.

**Acceptance.** Unit tests for the precedence (override beats DisplayID and
CTA; an invalid override falls through; `base-edid` and `none` gamut
sources in BT.2100; native SDR unaffected by `hdr-gamut-source`).
Monitor-configuration tests for parse, store and round trip, including
configurations without the fields. A D-Bus test that applies an override
and reads back the effective target and provenance.

### Configuration and API semantics

Patches 0055–0060 (configuration, transport, API, gdctl and support
reporting) store
`<targetpeakluminance>`, `<targetminluminance>` and `<hdrgamutsource>` under
each `<monitor>`; unset fields are omitted. Zero is an explicit black level,
not a reset sentinel. XML and D-Bus reject nonfinite values, wrong D-Bus types,
duplicate declarations, unknown gamut enums, minimum without peak, peak at or
below nominal PQ white (203 cd/m²), and ranges outside the target wire limits.
The optional black must be below the integer part of the peak. Validation
uses nominal white, not brightness-scaled white: a 400 cd/m² peak remains
valid at reference-luminance factor 2.1 (~426 cd/m² white).

ApplyMonitorsConfig replaces override fields, like colour mode: omitted peak
removes the luminance override, omitted minimum restores encoding black,
and omitted gamut source restores `auto`. VERIFY does not change the output.
Persistent requests use the existing confirmation and restore lifecycle.
Configuration copies retain colour mode, RGB range and overrides; generated
layouts recover each monitor's declarations through existing configuration
history. This is separate from explicit D-Bus replacement semantics.

gdctl performs read-modify-write of configured fields, preserving colour mode,
RGB range and overrides when changing unrelated layout options. Per-monitor
options are `--target-peak-luminance CD_M2|auto`,
`--target-min-luminance CD_M2|auto` and
`--hdr-gamut-source auto|base-edid|none`. Clearing peak with `auto` clears the
whole luminance override; clearing only minimum keeps peak. There is no zero
sentinel. `show --properties` and `show --verbose` print effective targets and
provenance. They do not label declarations as measurements.

GetCurrentState reports configured peak/minimum as doubles and configured
gamut source as a string (automatic/unset fields are absent). Its effective
properties come from the applied colour device, only when active and with an
initialized colour state:

| Property | Type and meaning |
|---|---|
| `target-luminance` | `(dd)`: minimum, maximum in cd/m² |
| `target-min-luminance-source` | string: minimum provenance |
| `target-max-luminance-source` | string: maximum provenance |
| `target-primaries` | eight doubles: CIE1931 xy for R, G, B, W |
| `target-primaries-source` | string: gamut provenance |

The shared provenance names are `encoding-fallback`, `firmware-declared`,
`cta-declared`, `edid-declared` and `user-declared`.

**Selection (patch 0061).** Luminance applies in BT.2100 only. The user's
peak, with its optional minimum, is the first candidate, ahead of DisplayID
and CTA. It is taken as a whole and validated like a declared source,
against the nominal reference white, so the brightness factor never removes
it. It needs no EDID. Without a minimum, black is the encoding's, never a
display declaration's. An unusable override falls through to the next
source. Gamut in BT.2100 follows this decision table:

| `hdr-gamut-source` | Target primaries |
|---|---|
| `auto` | DisplayID native chromaticities, else encoding fallback |
| `base-edid` | Base EDID characteristics as `user-declared` when usable; otherwise DisplayID, else fallback |
| `none` | Encoding fallback, suppressing both declarations |

Native SDR keeps its base-EDID encoding target with `edid-declared`
provenance. The default SDR mode and forced HDR keep the fallback whatever
the override. Regressions: `/native-hdr/target-luminance-override`,
`/native-hdr/target-primaries-override`,
`/wayland/display-targets/user-override` (published target, blending state,
highlight mapping, factor 2.1, none, native SDR, forced HDR, clearing), and
Sol's D-Bus case.

Known compatibility limit: a client that does not know these properties
(including today's Settings) drops overrides when it replaces the layout.
The Settings UI is later work. Older compositors reject the new monitor XML
children rather than ignoring them; see [rollback preparation](OPERATIONS.md#2-protect-the-working-installation).

The integrated candidate is compiled and replay-verified, not unit-qualified.
Both source parts still need the agreed adversarial reviews and fixes, then
one affected unit batch, before acceptance. Ubuntu packaging, deployment and
optical measurement are separate later stages.
