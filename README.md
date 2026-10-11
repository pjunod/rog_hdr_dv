# rog_hdr_dv — Linux HDR, Dolby Vision and display quality

Linux display-stack work for the ASUS ROG Zephyrus G16 GU605MZ, with reusable
fixes for native DisplayID HDR detection and a programme for accurate colour,
panel calibration and full Dolby Vision. macOS-like consistency and ease of
use are the quality reference. Plurx is one consumer; this repository owns
the operating-system display work independently.

**Current status:** the patched kernel (`nativehdr1`), the hdr9 library and the
`nativehdr8` compositor are installed (the compositor and library since
2026-10-11), and Secure Boot is enabled. The owner reported working HDR10 on
the earlier stack; on the new compositor the HDR session runs in BT.2100 mode
and the owner accepted the picture. Full Dolby Vision, measured calibration
and remaining transition/resume acceptance are unfinished. The next batch
(`nativehdr9`) widens the colour targets to ordinary HDR and wide-gamut
hardware; a second laptop (`lab6`, Intel graphics, SDR panel) is the test
machine for that. The earlier mpv
DV-to-PQ sample does not qualify full Dolby Vision.

Start with [status](docs/STATUS.md) for what is proven, then
[hardware](docs/HARDWARE.md) for the exact panel and OEM findings.
[Architecture](docs/ARCHITECTURE.md) explains responsibility boundaries.
[Development](docs/DEVELOPMENT.md) covers source reconstruction and checks;
[operations](docs/OPERATIONS.md) covers inspection and recovery.
[Dolby Vision and image quality](docs/DOLBY_VISION_AND_QUALITY.md) is the
investigation and staged plan. [Provenance](docs/PROVENANCE.md) records where
the imported work came from and how to interpret its evidence.
[Licensing and attribution](LICENSES.md) explains the retained upstream terms.
[The status page](docs/STATUS.html) shows the active workboard;
[review findings](docs/REVIEW.md) records review dispositions and validation.
[Display diagnostics](docs/DISPLAY_DIAGNOSTICS.md) explains the read-only
Linux inspector and bounded Wayland colour probe, including their privacy-filtered reports.
[The Dolby activation probe](docs/DOLBY_ACTIVATION_PROBE.md) documents the
isolated Windows API experiment, compiler receipt and remaining contracts.
[Wine API contract](docs/WINE_API_CONTRACT.md) isolates the missing file API
from Dolby activation. [ICC characterisation](docs/ICC_CHARACTERISATION.md)
explains private inspection of factory profile data.
[The colour pipeline audit](docs/COLOUR_PIPELINE_AUDIT.md) traces encoding,
target-volume reporting, calibration and KMS metadata in pinned source.
[Native luminance API](docs/NATIVE_LUMINANCE_API.md) documents the additive
physical-declaration API and its source-only qualification boundary.
[Mutter target feedback](docs/MUTTER_TARGET_LUMINANCE.md) specifies independent
physical-target state, immutable descriptions and their qualification.
[Wine file API implementation](docs/WINE_FILE_FROMAPP.md) scopes the missing
function correction and its desktop-only compatibility evidence.
[HDR reference corpus](docs/HDR_REFERENCE_CORPUS.md) defines reproducible
synthetic PQ inputs and the separate official-reference workflow.
[Panel measurement](docs/PANEL_MEASUREMENT.md) defines the optical procedure,
initial accuracy targets and evidence required before calibration claims.
[Native target gamut](docs/NATIVE_TARGET_GAMUT.md) specifies lossless physical
chromaticity declarations and independent compositor feedback.
[Wine monitor discovery](docs/WINE_DISPLAY_MONITOR.md) defines the next
activation prerequisite, truthful topology and descriptor handling.
[HLG and tone mapping](docs/HDR_MAPPING.md) defines HLG decoding, mapping
highlights to the panel's declared target and compressing out-of-gamut
colours toward its declared gamut in the compositor, and defines the
deferred output-characterization contract.
[Display target sources](docs/DISPLAY_TARGET_SOURCES.md) extends those targets
beyond the ROG panel: DisplayID or CTA-861 luminance on any HDR output, and
the base EDID gamut in the native SDR mode, for general availability.
[Open RPU-aware display management](docs/OPEN_DV_DISPLAY_MANAGEMENT.md) is the
generally available Dolby Vision track: player-side mapping from the RPU,
validated against Dolby's reference renderer.
[Night Light and target overrides](docs/NIGHT_LIGHT_AND_OVERRIDES.md) specifies
Night Light in linear light for HDR and per-monitor target overrides.

## Work with the repository

This is a source-and-research repository, not a one-command system installer.
It requires Git and Python 3 for repository checks. Rebuilding the components
requires their pinned Linux build environments and dependencies.

```bash
python3 scripts/check_repository.py  # Check patches, manifest and doc links.
git status --short                  # Inspect local work before changing it.
```

No check installs packages, changes the display, or contacts the laptop.
Follow [development](docs/DEVELOPMENT.md) to apply a specific series in a
disposable source checkout. Follow [operations](docs/OPERATIONS.md) before
any live compositor or kernel update.

## Repository layout

- `patches/libdisplay-info/` · `patches/mutter/` — current upstream-facing
  proposals, with exact bases in `sources.json`. The Mutter series carries
  the whole colour programme ported to upstream main; neither series has
  been submitted upstream.
- `patches/ubuntu-libdisplay-info/` · `patches/ubuntu-mutter/` — complete
  local changes from authenticated Ubuntu source imports, including the
  delivered prefixes and explicitly marked unreleased candidates. In
  `sources.json` the `delivered_*` fields pin the earlier delivered prefix
  (now the rollback); the installed release is the candidate. These are alternative packaging paths to the upstream series.
- `patches/linux/` — four native luminance/backlight/parser-test patches.
- `patches/wine/` — bounded Windows API compatibility work for processor investigation.
- `sources.json` · `SHA256SUMS` — source identities and patch integrity.
- `docs/` — maintained technical documentation, indexed above.
- `evidence/` — small reproducible migration/validation receipts. Large or
  private captures, OEM binaries and signing keys do not belong in Git.
- `scripts/` — repository validation, with no installation side effects.

## Progress

- [x] Preserve the current HDR source series independently of Plurx.
- [x] Record the running stack and exact-panel OEM configuration findings.
- [x] Retain patch authorship and identify the historical evidence location.
- [ ] Complete HDR/SDR, brightness, DPMS and suspend/resume qualification.
- [ ] Establish a full Dolby Vision processor path for the internal panel.
- [ ] Implement and measure general colour consistency and panel calibration.
- [ ] Integrate and qualify multiple apps, including Plurx.
- [ ] Package the complete solution and pursue upstream acceptance.
