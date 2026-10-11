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

## Second test machine (`lab6`)

Added on 2026-10-11 to test general availability on hardware unlike the ROG.
Observed read-only with [the inspector](DISPLAY_DIAGNOSTICS.md); nothing was
changed on it. The EDID values are firmware declarations, not measurements.

| Item | Observed value |
|---|---|
| Laptop | Lenovo ThinkPad X1 Extreme, first generation (20MF) |
| Panel | AUO B156ZAN03.2, 3840×2160 at 60 Hz |
| Internal route | Intel Coffee Lake UHD 630 (i915), eDP-1 |
| Other GPU | NVIDIA GTX 1050 Ti Mobile; drives the external HDMI and DisplayPort outputs |
| Software | Ubuntu 26.10, stock `libmutter-51-0` 51.0-1ubuntu3 and `libdisplay-info3` 0.3.0-1 |
| EDID | 128-byte base block, EDID 1.4, 10 bpc DisplayPort, no extensions (no CTA or DisplayID) |
| Base EDID primaries | R 0.6445, 0.3359 · G 0.3105, 0.6064 · B 0.1523, 0.0488 · W 0.3135, 0.3291; gamma 2.2 |
| GNOME colour modes | Default and native SDR (no BT.2100) |

EDID SHA-256:
`88ad8e91f284265fa6bb9b8228d5d6663d0f5a94914a25f31e2b88e766fa3625`.

The panel declares no HDR capability, so its built-in screen cannot use
BT.2100 on any stack. Independently, the i915 driver attaches
`HDR_OUTPUT_METADATA` to a port-A eDP connector only from display version 11
(`intel_dp_has_gamut_metadata_dip()` in `intel_dp.c`). Coffee Lake is
display version 9, so this generation could not drive internal-panel HDR
even with an HDR panel. The machine tests the native SDR target path
([display target sources](DISPLAY_TARGET_SOURCES.md)) on Intel graphics and
a stock 26.10 baseline. External HDR monitors on its NVIDIA outputs would
test the CTA path.
