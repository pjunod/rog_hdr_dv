# Native-gamma HDR — output contract

**Status:** contract frozen 2026-11-11; implementation pending its compiler
loop · **Owner:** Claude (coordinator: design, review and integration) ·
**Machine of record:** the ThinkPad X1 Carbon Gen 6 described in
[its inspection ledger](THINKPAD_X1_CARBON_GEN6.md).

This contract lets Mutter show HDR content on an internal panel whose only
encoding is gamma 2.2 over native primaries, with no PQ link and no HDR
metadata. It reuses the existing native SDR colour mode and the existing
per-monitor target override. It adds no colour mode, capability flag or
EDID fiction. The numbers below are public illustrations; none is a
measurement of this panel.

## 1. Three quantities, three sources

| Symbol | Meaning | Source in Mutter | Provenance |
|---|---|---|---|
| `P` | Physical peak at the backlight Mutter holds while this route is active | The monitor configuration's target `peak` override | User-declared. On the ThinkPad, Lenovo's nominal 500 cd/m² (an OEM specification) or the Windows driver's reported 270 cd/m²; neither is a measurement |
| `B` | Physical black | The override's `min`, when present | User-declared; otherwise the explicit ideal-zero fallback, never inferred from a contrast specification |
| `W` | SDR reference white | `203 × f` in whole cd/m², where `f` is the reference-white brightness factor, kept strictly between `B` and `P` | Compositor policy; follows the brightness control |

`P` is defined at maximum backlight. The route therefore uses the
reference-white backlight that BT.2100 mode already uses: the sysfs backlight
is held at its maximum and the brightness control moves `W`, so `P` stays
the quantity the user declared. A route that left the hardware backlight
user-controlled would make `P` a function of an unmeasured backlight curve,
which this contract refuses to guess.

The reference-white backlight spans `f` from 0.1 to 2.1, so `203 × f` can
exceed a declared peak below 426 cd/m². SDR white then stops one cd/m² below
`P`, and the top of the brightness range has no further effect: brightness
above the peak has nothing physical to show. At the bottom, SDR white stays
at least one cd/m² above `B`.

## 2. Activation is a declaration, not a gate

The route is active exactly when the monitor is a built-in panel in the
native SDR colour mode (mode 2), HDR is not debug-forced and the monitor
configuration declares a target peak above 203 cd/m². Only built-in panels
qualify: `P` is defined at a backlight the compositor holds, and an external
monitor has none. An external monitor's saved override keeps its previous
meaning, so no existing configuration changes behaviour. Without a declared peak the native SDR mode
keeps its current encoding (gamma 2.2, 0.2–80 cd/m², reference 80) bit for
bit. Firmware supplies no physical luminance for this panel, so the peak can
only be declared; nothing is inferred from the panel model.

## 3. Output encoding

The output colour state stays the honest encoding: base-EDID primaries
(patch 0058) and gamma 2.2. Only its luminance changes, to the declared
physical range:

    min = B (0 when undeclared)   max = P   ref = W

Clutter maps luminance relative to the peak, so a physical luminance `L`
encodes as `(L / P)^(1/2.2)`, whatever `B`. At `P = 500`: 500 → 1.0000,
203 → 0.6638, 80 → 0.4347. `B` is published and bounds the target, but it is
not subtracted. This is Mutter's existing SDR behaviour too, and modelling a
black offset would need the measured response this contract does not have.
SDR content at reference white lands on `W`, not on full code.

KMS output keeps the default colorspace and RGB, with no
`HDR_OUTPUT_METADATA` (the connector has none) and no fabricated metadata.
The gamma LUT and CTM keep their SDR roles, so Night Light continues to work
through them.

## 4. Target volume

Patch 0073 selects target luminance only in BT.2100. Relaxing that predicate
alone would leave the encoding at 0.2–80 and publish a 500 cd/m² target over
an 80 cd/m² encoding. The target selector therefore runs on this route too
(user override first, then the generic DisplayID and CTA sources), and the
encoding in §3 is derived from the same selected range. Target and encoding
maxima are then equal by construction, so the existing tone mapping maps
highlights above `P` to `P` and does nothing below it. Target primaries
remain the base-EDID gamut, as in the native SDR mode today.

## 5. What clients are told

| Description | Content |
|---|---|
| Output | Native: base-EDID primaries, gamma 2.2, luminance `B`–`P`, reference `W`, target `B`–`P` |
| Preferred surface | Unchanged transport preference where it already exists; target luminance `B`–`P` and reference `W` from the same record |

The output description must say gamma 2.2, because that is what is on the
wire. A PQ surface remains a client transport into the compositor and is
converted exactly once to the native encoding. Source, target and
reference changes advance the existing description identities.

## 6. Reference-white anchoring

Mutter maps content reference white to `W`. A PQ grade's 203 cd/m² therefore
lands on `W`, and every other level scales by `W / 203` before the target
maps it. At `f = 1` (`W = 203`) a grade is shown at its graded luminance up
to `P`. Below that, a pregraded 500 cd/m² highlight shows at
`500 × W / 203` (about 197 at `W = 80`). That is the existing relative
policy, kept deliberately. A two-anchor policy that preserves HDR peaks under
a lower paper white is a separate, explicitly labelled future change.

## 7. Precision

The panel link is eight bits per channel. Mutter composes in its existing
offscreen formats and quantizes once at scanout. Eight-bit banding is
qualified by synthetic ramps on the actual GPU before installation. Dithering
is separate work, not claimed by this slice.

## 8. Non-goals and open evidence

- No Dolby Vision claim. The OEM `DVB1` payload stays opaque, and HDR10
  shown on this route is not Dolby Vision.
- No calibration claim. `P` and `B` are declarations; there is no meter.
- The Windows runtime trace (ledger §2) may revise `P`. It does not change
  this contract, because `P` is a configuration value.
- Double gamut compression (a generic BT.2020 lease mapped again by Mutter's
  ACES compression) is tested with saturated edges in the synthetic controls,
  not only neutrals.

## 9. Acceptance for this slice

1. Native SDR mode without an override: output colour state, rendering state
   and descriptions identical to before.
2. With `P = 500` and no `B`: encoding 0–500 ref 203 at `f = 1`; ref follows
   `f` and stays inside `B`–`P` at `f` = 0.1 and 2.1; target maxima equal
   encoding maxima; the published output description carries the range.
3. Signal checks against §3 at 500, 203, 80 and 1 cd/m², both into the
   encoding and through the rendering state, and with `B = 50`.
4. An external monitor with a saved override in native SDR is unchanged.
5. On hardware: the reference-white backlight is selected and the sysfs
   backlight held at maximum. Headless tests cannot create a KMS output;
   Mutter recreates backlights on every applied configuration.
6. BT.2100 and forced-HDR behaviour unchanged.
7. Mutter's own native HDR and colour-management test suites pass.
