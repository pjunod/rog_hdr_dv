# Linux display quality — full Dolby Vision and a calibrated laptop pipeline

**Status:** open; hardware/OEM investigation recorded, implementation and
physical acceptance outstanding · **Written:** 2026-10-08.

This is the investigation ledger and staged plan for general Linux display
quality, the ASUS GU605MZ internal OLED, and Plurx playback on that machine.
The user wants actual Dolby Vision and macOS-like colour consistency and
ease of use. Both are requirements. The existing
Plurx DV-to-HDR10 processing project has a separate
HDR10 output contract; it does not satisfy this project's Dolby Vision goal.
Plurx remains an independent consumer of this stack.

## 1. The outcome to build

Make supported applications render correctly through a shared Linux colour
pipeline, with a display-specific calibration layer and full Dolby Vision
processing. Plurx must use that capability and preserve the source metadata.
An application should not require guessed saturation, gamma or peak settings
to look correct. macOS is the usability and consistency reference, not a
claim that two different panels can reproduce the same physical colour volume.

| Area | Required behaviour |
|---|---|
| SDR and wide gamut | Tagged sRGB, Display P3, Adobe RGB and Rec.2020 content is interpreted correctly, then mapped into the display's measured capabilities. Untagged content has an explicit, consistent default. |
| HDR | Correct PQ and HLG interpretation, reference white, highlight roll-off, black level and mixed SDR/HDR composition. Each transform has one owner. |
| Dolby Vision | Preserve and process the applicable source metadata, including creative trims; perform the display management required for the supported profile and content-mapping version. Validate against a known Dolby reference. |
| Panel tuning | Match the actual panel and active GPU route; use OEM data as a starting point, then measure this unit. Keep SDR and HDR calibration distinct. |
| Image quality | Correct range, chroma siting/reconstruction, scaling, gradients, dithering and near-black detail; no accidental sharpening, oversaturation or double tone mapping. |
| Everyday use | Consistent browser/photos/video, fullscreen/windowed transitions, brightness changes, AC/battery, suspend/resume, and supported refresh/VRR combinations. |
| Plurx | Negotiate actual decoder/render/output capability, retain DV metadata through delivery, and report source and displayed treatment accurately. |

**Scope boundaries:** An HDR10 conversion, a codec badge, a successful decode
or an HDR-enabled desktop is not full Dolby Vision acceptance. HDMI output to
a television is a useful separate path, but cannot qualify the internal eDP
panel. Premium-service DRM is a separate integration from local Plurx media.
Factory binaries stay on the laptop; this ledger contains findings and hashes.

## 2. Verified laptop and Linux baseline

Live inspection on October 8 used the existing laptop connection (`lab5`).
The morning HDR work remains the foundation:

| Component | Observed state |
|---|---|
| Laptop | ASUS ROG Zephyrus G16 GU605MZ |
| Panel | Samsung SDC41A3 / ATNA60DL01-0; 2560×1600, 240 Hz, VRR |
| Internal display route | Intel Meteor Lake i915, connected eDP-2; NVIDIA RTX 4080 Laptop also present |
| OS and kernel | Ubuntu 26.10 development; `7.3.0-rc5-nativehdr1` |
| Display libraries | libdisplay-info `0.3.0-1ubuntu1~hdr6`; Mutter `51.0-1ubuntu3+nativehdr2` |
| DisplayID | Native RGB 10 bpc and BT.2020/PQ support; 400 cd/m² full coverage, 616 cd/m² at 10% coverage |
| Colour profile | colord assigns a generated EDID profile, not the recovered ASUS profile |
| Comfort adjustment | Night Light disabled at inspection |
| Measurement device | colord reports no supported sensor attached; this does not establish whether the owner has one elsewhere |
| Playback libraries | mpv 0.41.0, libplacebo 7.360.1, FFmpeg 8.1.2 |

DisplayID values are advertised capabilities, not measurements of this unit.
The EDID SHA-256 is
`4bd977afbbb5fca2be98f6786ce03b9a1e2170540b6bd6393ca9ee09314296ac`.

The earlier Profile 5 sample test exercised DV reshaping and a 10-bit PQ
Vulkan surface. It did not establish full Dolby display management, creative
trim fidelity, or Profile 7 FEL support. Preserve that distinction.

### 2.1 The current compositor needs a deeper calibration audit

The inspected morning-work Mutter checkout is clean at candidate commit
`ab7633fd411d159ca588ba52f01e07ecd940d390`, based on
`d82671c3035bfdb10fdc1ffd2c0e31859bb00ff7`. Its
`src/backends/meta-color-device.c:get_color_metadata_from_monitor()` selects
sRGB/gamma 2.2, BT.2020/PQ or EDID-native colourimetry by monitor mode.
`update_color_state()` starts with EOTF default luminance and scales reference
white. `clutter/clutter/clutter-color-utils.c` defines the PQ default maximum
as 10000 cd/m² and reference white as 203 cd/m².

That explains why a player can see a 10000-nit working range. It is not a
measurement of this 616-nit panel and, by itself, is not proof of a bug. Trace
the remaining compositor, KMS and panel mapping before changing it.

`meta-color-profile.c:meta_color_calibration_new()` extracts VCGT calibration
and an optional supplied adaptation matrix. No `MHC2` or `DVB1` handling was
found in the inspected Mutter `src`/`clutter` tree. The recovered ASUS files
contain no VCGT tag. Importing them into colord alone therefore does not prove
that their characterisation, HDR metadata or Dolby block reaches the output.
Application ICC use and compositor calibration must be tested separately.

## 3. OEM recovery provides concrete components

The ASUS recovery partition was mounted read-only, selected factory files
were extracted, and the mount was removed. The encrypted Windows installation
was not unlocked. No display settings or packages were changed.

Evidence is retained on the laptop under
`~/.local/state/display-quality/2026-10-08/`: `oem/`,
`oem-inspection.json`, `selected-paths.txt`, and `linux-baseline.json`.
The original source is `Recovery/RecoveryImage/ASUS.swm`. These are shipped
factory files, not a capture of the currently installed Windows configuration.

### 3.1 Dolby's Windows processor is present

Package `DolbyLaboratories.DolbyVisionAccess_2.20301.388.0_x64` contains
`x64/DolbyVisionPlugin.dll` (2,372,704 bytes). Its SHA-256 is
`ecb3d9024e53defcdfaa0ae6bd3fdc87165f2a845efc71d83456d59add4d9936`.

Static inspection found D3D11, Media Foundation, COM and WinRT dependencies;
the exports include `DllGetActivationFactory` and `DllGetClassObject`.
The app manifest registers `windows.videoRendererEffect` for `dvhe.04`,
`dvhe.05`, `dvhe.08` and `dvav.09`. Registration is not runtime proof for all
those profiles; Profile 7 is not listed.

[Chromium's Windows integration](https://chromium.googlesource.com/chromium/src/media/+/88ab84191d96172c750cb05f75417bcce4dcd7d9%5E%21/)
also locates and preloads `DolbyVisionPlugin.dll`. This supports investigating
the OEM processor contract; it does not establish that this older factory
version works with the newer Chromium path or under Wine.

### 3.2 The exact-panel profiles carry ordinary and proprietary data

`ProgramData/ASUS/GameVisual/` contains Intel (`8086`) and NVIDIA (`10DE`)
variants for panel identifier `834C41A3`. Standard profiles have matrix/TRC
characterisation. The 9,124-byte `CMDEF` variants additionally have a 132-byte
`MHC2` tag and a 6,460-byte `DVB1` block containing ASUS/model identifiers.
The latter's complete binary meaning has not been established.

`Windows/System32/spool/drivers/color/PQConfig.dv` is byte-identical to
`GU605MZ_8086_834C41A3_CMDEF.icm`, with SHA-256
`f5f693598cf35f3b540046bbcc1d605f1e9a72c052816749b6471122da933908`.
This is strong evidence tying the factory Dolby configuration to this panel's
Intel profile. Actual runtime consumption remains to be traced.

| Profile metadata | Intel CMDEF | NVIDIA CMDEF |
|---|---:|---:|
| MHC2 peak luminance | 616 cd/m² | 616 cd/m² |
| MHC2 minimum luminance | approximately 0.005 cd/m² | approximately 0.005 cd/m² |
| ICC luminance Y | approximately 294.65 cd/m² | approximately 373.12 cd/m² |

[Microsoft's MHC2 specification](https://learn.microsoft.com/en-us/windows/win32/wcs/display-calibration-mhc)
defines the HDR luminance fields and how Windows combines calibration and
display metadata. The profiles' full-frame values differ from DisplayID and
from each other. Preserve all three sources until operating conditions and
measurements explain the differences; do not replace them with one guessed
peak. The files identify a model/panel combination, not proven per-unit
optical calibration for this particular screen.

## 4. Full Dolby Vision has an unresolved processing boundary

For the built-in panel, determine where the factory path performs Dolby
display management and whether any panel-specific control accompanies its
pixels. Do not assume that an eDP panel consumes the same tunnel as an HDMI
television, or that the absence of HDMI signalling means Dolby processing
cannot happen on the host.

```text
DV bitstream + frame-matched metadata
                 |
         Decode / reconstruct
                 |
   Full Dolby display management <--- validated panel configuration
                 |
      Colour-managed composition
                 |
       i915 / eDP / internal OLED
```

The diagram is the required responsibility chain, not a claim that the
missing engine exists on Linux. The eventual design must specify whether
display management runs in the player, a reusable media component, or an
output stage, and prevent the compositor from mapping it a second time.

| Candidate | Concrete next proof | Current limit |
|---|---|---|
| Native Dolby/OEM component | Establish availability and supported Linux/GPU/display interface for a full display-management implementation. | No compatible native package identified in this investigation. Do not assume a Windows licence or binary supplies one. |
| Compatibility host for the recovered processor | Build an isolated COM/WinRT/MF/D3D11 probe; establish activation, formats, metadata transport, profile loading and output semantics before player integration. | Feasibility unproven. Wine installation alone is not evidence. Record the first missing API/driver contract; do not assume it is a trivial DLL wrapper. |
| Open implementation | Audit metadata/reconstruction/display-management coverage and compare output with controlled Dolby reference cases, including trims and target changes. | Parsing metadata and matching a pleasant-looking sample do not demonstrate a complete Dolby display manager. |

An additional source lead is
[CroqueMr's experimental Linux DV project](https://github.com/CroqueMr/libreelec-x86-DV).
Its [processing contract](https://github.com/CroqueMr/libreelec-x86-DV/blob/main/docs/cb1/PROCESSING.md)
describes TV-led HDMI output and explicitly says player-led/LLDV output is
not implemented. This may provide reusable transport/reconstruction work;
it has not been built or tested here, and does not qualify this laptop's
internal panel. Its HDR10 conversion modes are outside this project's DV
acceptance contract.

## 5. Work in stages with observable acceptance

### 5.1 Capture the colour path and validate OEM data

Record active output, application buffer encoding, Wayland description,
compositor transform, KMS precision/range and panel mode together. Inspect
the ordinary ICC characterisation separately from the proprietary tags.
Capture current brightness/reference-white controls and retain a reversible
baseline before changing them. Audit both Intel and NVIDIA display routes
without assuming their OEM profiles are interchangeable.

**Acceptance:** For SDR and PQ test images, identify every conversion and its
owner. Resolve where physical peak and gamut are applied. A saved ICC profile
or a 10-bit framebuffer alone cannot close this stage.

### 5.2 Establish a full Dolby processor path

Use the exact OEM binaries and profile inventory to specify a bounded
compatibility probe while researching a native integration. Pin any open
implementation being evaluated. Start with P5 and P8 test cases supported by
the OEM registration; track content-mapping versions and creative trim
coverage independently. P7 MEL/FEL requires its own reconstruction and
metadata qualification; neither an OEM registration nor P5 success implies it.

**Acceptance:** Demonstrate correct response to controlled metadata changes,
target-display changes and reference frames. Identify the actual output
encoding and final display-management owner. Publish exact supported profiles
and known limitations. If a route fails, record its failing contract and
continue another candidate; do not rename an HDR10 fallback Dolby Vision.

### 5.3 Implement general colour management and panel tuning

Give shared Linux components the generic correctness fixes and place device
characterisation in a versioned panel profile. Evaluate SDR white/gamma,
wide-gamut mapping, HDR reference white, peak handling and OLED near-black
response separately. Use a neutral accuracy baseline; comfort adjustments and
optional sharpening/debanding are explicit user choices.

**Acceptance:** A controlled colour patch/ramp suite agrees across supported
apps and survives fullscreen/windowed, brightness, suspend and display-mode
changes. Measure this unit with a suitable colourimeter/spectrophotometer and
OLED correction before claiming calibrated accuracy. Record patch size,
duration, ambient conditions, brightness, power state and refresh rate;
ABL and drift make a lone peak reading insufficient. Set numerical error
limits with that measurement protocol, before evaluating candidate tuning.

### 5.4 Make the capability available to apps and Plurx

The reusable media path must carry decoded surfaces plus frame-associated DV
metadata and display configuration. Define its concrete API after stage 5.2
establishes the processor's requirements. At least two independent consumers
must exercise it to demonstrate general availability beyond a Plurx-only path.

Current Plurx negotiation is
`buildPlayCaps()` in Plurx’s `crates/plurxd/src/web/player/decode-tiers.js`, which
probes `dvh1`/`dvhe` through browser video/MSE support and sends `dv` and
`dvprofile`. A native renderer must report its own proven capabilities.
[Chromium's media build options](https://chromium.googlesource.com/chromium/src/+/main/media/media_options.gni)
also constrain DV support by platform. Linux system-library changes do not
automatically give its HTML video element the OEM Windows processor.

Choose browser integration or a native Linux playback surface from that
evidence. Preserve original RPUs and applicable enhancement layers through
Plurx delivery; test subtitles, seek, quality switches, fullscreen and overlays.
Apply the Plurx web layout contract if web scripts change.

**Acceptance:** Plurx plays the reference corpus through the established full
DV path, with source/processing/output diagnostics that match observed
behaviour. No hard-coded capability override or badge closes this stage.

### 5.5 Qualify and package the complete result

Cover sRGB/Rec.709, Display P3, Adobe RGB, Rec.2020/PQ, HLG and qualified DV
profiles. Include correct limited/full range, gradients, saturated colours,
skin tones, near-black detail, 24/25/30/50/60 fps cadence, scaling and
supported high-refresh/VRR operation. Check screenshot/screen-share colour
descriptions independently of physical panel output.

**Acceptance:** Reproducible packages and profile selection; successful
install/reboot/upgrade/rollback; consistent app results; instrumented colour
receipts and known Dolby reference comparisons. Software correctness can be
built before instruments are attached, but physical colour accuracy remains
unqualified until measured. Follow [development and validation](DEVELOPMENT.md) when implementation
begins; qualify Plurx-side changes in the separate Plurx repository.

## 6. Current completion boundary

Hardware, running profile, OEM component dependencies and profile inventory
are investigated. OEM evidence is retained locally and the recovery partition
is unmounted. Full Dolby processing, shared Linux integration, panel tuning
and Plurx integration remain unimplemented or unqualified. No new calibration
has been activated and no full Dolby Vision success is claimed.
