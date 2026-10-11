# Night Light in HDR, and per-monitor target overrides (nativehdr10)

**Status:** specified · **Date:** 2026-10-11.

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
  It is a chromatic adaptation from the encoding white (D65) to the
  blackbody white at the Night Light temperature, in linear light. It runs
  in the blending → output conversion before PQ encoding, and it is
  normalised so that no channel exceeds its unadapted value. Night Light
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
