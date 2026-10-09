# Hardware — the GU605MZ panel and observed colour data

This is the device reference for [operations](OPERATIONS.md) and
[the quality plan](DOLBY_VISION_AND_QUALITY.md). Values below were observed on
October 8, 2026; firmware declarations and factory profile fields are not new
optical measurements.

| Item | Observed value |
|---|---|
| Laptop | ASUS ROG Zephyrus G16 GU605MZ |
| Panel | Samsung SDC41A3, ATNA60DL01-0 |
| Mode | 2560×1600 at 240 Hz with VRR |
| Active internal route | Intel Meteor Lake i915, eDP-2 |
| Other GPU | NVIDIA RTX 4080 Laptop, driver 615.71.09 |
| DisplayID interface | RGB 10 bpc; BT.2020/PQ |
| DisplayID full-screen / 10% luminance | 400 / 616 cd/m² |
| Active Linux profile | Generated EDID profile in colord |
| Night Light | Disabled at inspection |

EDID SHA-256:
`4bd977afbbb5fca2be98f6786ce03b9a1e2170540b6bd6393ca9ee09314296ac`.

## OEM inputs recovered read-only

The original ASUS recovery image contains Intel and NVIDIA GameVisual ICC
profiles for this exact panel identifier, including standard matrix/TRC data.
Their `CMDEF` variants also contain Microsoft `MHC2` and proprietary `DVB1`
tags. The Intel CMDEF file is byte-identical to `PQConfig.dv`.

Both MHC2 tags specify a 616 cd/m² peak and approximately 0.005 cd/m² minimum.
The Intel ICC luminance Y is approximately 294.65 cd/m²; NVIDIA's is 373.12.
These values differ from DisplayID's full-screen declaration. Resolve the
operating mode and measurement conditions before choosing a tuning value.

The factory Dolby Vision Access plugin depends on Windows Media Foundation,
D3D11, COM and WinRT. Its full configuration/processing contract still needs
investigation. See [the detailed findings](DOLBY_VISION_AND_QUALITY.md#3-oem-recovery-provides-concrete-components).

Private OEM files and the inspection manifest remain on the laptop at
`~/.local/state/display-quality/2026-10-08/`. No OEM payload is committed here.
The recovery partition was unmounted after inspection. The BitLocker Windows
installation was not unlocked.

## What is needed for unit-specific calibration

colord reported no supported measurement sensor attached during inspection.
Software work can continue, but physical accuracy needs a suitable sensor
with an appropriate OLED correction. Record brightness, power state, refresh
rate, ambient light, warm-up, patch size and timing. Keep sustained luminance,
small highlights, white point, gamut, near-black response and drift separate.
