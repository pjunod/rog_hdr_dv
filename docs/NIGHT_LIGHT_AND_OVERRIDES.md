# Night Light in HDR, and per-monitor target overrides (nativehdr10)

**Status:** configuration/API source stage compiled and exported; complete
source integration, adversarial review and unit validation pending ·
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

The [unreviewed source stage](../wip/mutter-target-overrides/README.md) stores
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
`cta-declared`, `edid-declared` and (after selector integration)
`user-declared`. In BT.2100, a valid explicitly chosen base-EDID gamut is
user-declared. An unusable base-EDID candidate falls through to DisplayID,
then encoding fallback. `none` is a valid terminal request for encoding
fallback, suppressing other gamut candidates. Native SDR is unaffected.

Known compatibility limit: a client that does not know these properties
(including today's Settings) drops overrides when it replaces the layout.
The Settings UI is later work. Older compositors reject the new monitor XML
children rather than ignoring them; see [rollback preparation](OPERATIONS.md#2-protect-the-working-installation).

This stage is compiled and replay-verified, not unit-qualified. Its effective
override assertions await Opus's target selector. Both source parts require
the agreed adversarial reviews and one affected unit batch before acceptance.
