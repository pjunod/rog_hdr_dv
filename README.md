# rog_hdr_dv — HDR and Dolby Vision on Linux, done properly

Linux display-stack work for the ASUS ROG Zephyrus G16 (GU605MZ) and its
240 Hz OLED panel. The goal is the picture macOS gives you on the same kind
of screen: HDR that just turns on, Dolby Vision that looks the way the
colourist graded it, and colour that is consistent from one app to the next.
Fixes go into shared Linux components (the kernel, libdisplay-info, GNOME's
Mutter compositor, the playback libraries) rather than into one app, so other
software and other machines benefit too. Plurx is one consumer; this
repository owns the operating-system display work.

> **This is research and patch work, not an installer.** The patches change
> the kernel, the display library and the compositor. Applying them to a
> machine is a deliberate, recoverable operation described in
> [operations](docs/OPERATIONS.md), never something a repository check does.
> Nothing here is upstream yet, and no colour accuracy is claimed without an
> optical measurement of the panel.

## What works today

| Area | State | Where it stands |
|---|---|---|
| HDR detection on the internal panel | **Working** since 2026-10-08 | The panel's DisplayID HDR description is parsed, so HDR is offered and HDR10 plays |
| HDR desktop session | **Installed** | Mutter `nativehdr8` reports the panel's declared range (0.0004–616 cd/m², firmware values) separately from the BT.2020/PQ encoding |
| HLG, highlight mapping, gamut compression | **Installed** | Compositor maps highlights to the panel and compresses out-of-gamut colour toward it |
| Night Light in HDR, per-monitor overrides | **Packaged** (`nativehdr10`) | Built as Ubuntu packages; not yet installed on the laptop |
| Ubuntu packages | **Merged** 2026-10-17 | Source and binary packages with tested install and rollback ([release](docs/MERGED_UBUNTU_PACKAGES.md)) |
| Dolby Vision decode | **Experimental player** | Profile 5 plays through mpv/libplacebo with real RPU reshaping ([player](tools/native_player/README.md)) |
| Dolby Vision display mapping | **In development** | Open mapping passes 13 of 30 new test shots; now being fixed by direct measurement (below) |
| Panel calibration | **Not started** | Needs a colourimeter; the [procedure](docs/PANEL_MEASUREMENT.md) is defined |

[Status](docs/STATUS.md) is the authoritative, dated version of this table.

## How the pieces fit

```text
 Video file / app
   │  decoded pixels + per-frame metadata (Dolby Vision RPU: L1/L2/L8 trims)
   ▼
 Player: FFmpeg decode ─▶ libplacebo reshaping ─▶ open display mapping
   │                                              (Dolby Vision's per-shot
   │                                               tone and colour mapping)
   ▼
 Wayland colour description (what the pixels mean)
   ▼
 Mutter compositor ── HLG, highlight mapping, gamut compression,
   │                  Night Light, per-monitor targets
   ▼
 DRM/KMS output ── kernel: native DisplayID HDR, AUX brightness
   ▼
 Samsung OLED panel (240 Hz, ~616 cd/m² declared peak)
```

[Architecture](docs/ARCHITECTURE.md) assigns each responsibility to a
component and explains why.

## Dolby Vision — where the hard part is

Decoding Dolby Vision is solved in open source. **Display mapping** is not:
the step that fits a film mastered on a 1,000–4,000-nit reference display
into what this panel can show, following the colourist's per-shot trims.
Dolby supplies that code only to licensees, so every open player
substitutes a generic tone mapper.

This repository is building an open mapping from
[Dolby's public patent](https://patents.google.com/patent/US9613407B2/en),
checked pixel by pixel against Dolby's own reference renderer with the
BT.2124 ΔE_ITP colour-difference metric:

- **Development and first held-out frames:** mean ΔE_ITP 0.54–0.73, against
  4.6–9.3 for the stock open-source path
  ([equations and evidence](docs/SQRTSUM_PQ_Y_POST.md)).
- **Broader test, 30 new frame/target pairs:** 13 pass the bar (mean ≤ 1,
  p95 ≤ 3). 12 miss it, and 5 expose an invalid-pixel defect in the native
  renderer that is being fixed at its cause.
- **Next:** [measurement-driven development](docs/MEASUREMENT_DRIVEN_DEVELOPMENT.md).
  Dolby's reference tools are measured directly with synthetic colour grids,
  so each fix is aimed at where the mapping actually differs, and each
  idea is tested in seconds instead of a round of full-frame renders.

The alternative route, running the laptop's own Windows Dolby Vision
processor under Wine, activates but has not yet processed a frame
([activation probe](docs/DOLBY_ACTIVATION_PROBE.md)).

## Working with the repository

The repository holds patch series, source pins and tooling, not full
vendored source trees. It needs Git and Python 3 for its checks; rebuilding a
component needs that component's pinned Linux build environment.

```bash
python3 scripts/check_repository.py                      # patch integrity, series order, doc links
PYTHONPATH=tests python3 -m unittest discover -s tests -v   # Python tooling tests
git status --short                                        # see local work before changing it
```

No check installs packages, changes the display or contacts the laptop.
Some tests need the private reference corpus or the native build
environment and fail without them; that is expected outside those hosts.

**To apply a series**, follow [development](docs/DEVELOPMENT.md) in a
disposable source checkout. **Before any live compositor or kernel change**,
follow [operations](docs/OPERATIONS.md): it covers rollback packages,
Secure Boot signing and recovery access.

**To contribute**, read [AGENTS.md](AGENTS.md). In short: clone from the
primary forge (GitHub is a push mirror of `main` and `codex/*`), work on a
branch, get an adversarial review when ready to merge, run the fast lane
once, then merge. [Development](docs/DEVELOPMENT.md#remotes-branches-and-the-public-mirror)
has the remote and branch rules.

## Documentation

### Start here

| Document | Answers |
|---|---|
| [Status](docs/STATUS.md) · [status page](docs/STATUS.html) | What is proven, what is installed, what remains |
| [Hardware](docs/HARDWARE.md) | Exactly which panel this is and what its firmware declares |
| [Architecture](docs/ARCHITECTURE.md) | Which component owns which part of the colour path |
| [Dolby Vision and display quality](docs/DOLBY_VISION_AND_QUALITY.md) | The overall plan and its staged acceptance criteria |
| [Full HDR programme ledger](docs/FULL_HDR_HANDOFF.md) · [continuation](docs/HANDOFF.md) | Done, current and remaining work across the programme |

### HDR in the compositor and kernel

| Document | Answers |
|---|---|
| [HLG and tone mapping](docs/HDR_MAPPING.md) | How HLG, highlights and out-of-gamut colour are mapped to the panel |
| [Display target sources](docs/DISPLAY_TARGET_SOURCES.md) | Where the target luminance and gamut come from on any HDR output |
| [Night Light and overrides](docs/NIGHT_LIGHT_AND_OVERRIDES.md) | Night Light in HDR and per-monitor target overrides |
| [Native luminance API](docs/NATIVE_LUMINANCE_API.md) | The libdisplay-info API for physical luminance declarations |
| [Native target gamut](docs/NATIVE_TARGET_GAMUT.md) | Keeping the panel's physical primaries intact |
| [Mutter target feedback](docs/MUTTER_TARGET_LUMINANCE.md) | How the compositor reports the physical target to clients |
| [Colour pipeline audit](docs/COLOUR_PIPELINE_AUDIT.md) | Encoding, targets, calibration and KMS metadata, traced in source |
| [Asynchronous lifetime](docs/COLOUR_ASYNC_LIFETIME.md) · [offscreen reuse](docs/OFFSCREEN_REUSE.md) | Two reviewed compositor follow-up fixes |

### Dolby Vision

| Document | Answers |
|---|---|
| [Open display management](docs/OPEN_DV_DISPLAY_MANAGEMENT.md) | The full-fidelity open Dolby Vision target and what it requires |
| [Measurement-driven development](docs/MEASUREMENT_DRIVEN_DEVELOPMENT.md) | How the mapping is derived from reference measurements, and the rules |
| [Current mapping](docs/SQRTSUM_PQ_Y_POST.md) · [ABI368 delivery](docs/MAPPING_ABI368_DELIVERY.md) | The frozen equations, their evidence, and how they are packaged |
| [Headless harness](docs/DOLBY_HARNESS.md) | How references are rendered and scored, and the private boundary |
| [HDR reference corpus](docs/HDR_REFERENCE_CORPUS.md) | Reproducible test images, and what may leave the private area |
| [Authored-master transport](docs/AUTHORED_MASTER_BASELINE.md) · [frame-owned mapping](docs/OPEN_XML205_CANDIDATE.md) · [absolute-PQ](docs/OPEN_ABSOLUTE_PQ_SOP.md) · [public RGB/Y](docs/PUBLIC_RGB_MAPPING.md) | Earlier mapping candidates, kept for their evidence |
| [Native player](tools/native_player/README.md) · [qualification](tools/native_player/QUALIFICATION.md) | The experimental RPU-aware player and its install kit |
| [Activation probe](docs/DOLBY_ACTIVATION_PROBE.md) · [Wine API contract](docs/WINE_API_CONTRACT.md) · [Wine file API](docs/WINE_FILE_FROMAPP.md) · [Wine monitor discovery](docs/WINE_DISPLAY_MONITOR.md) | The Windows-processor-under-Wine route and its prerequisites |

### Packaging, validation and diagnostics

| Document | Answers |
|---|---|
| [Merged Ubuntu packages](docs/MERGED_UBUNTU_PACKAGES.md) | The current source/binary release and its install/rollback test |
| [Ubuntu delivery](docs/NATIVEHDR10_UBUNTU_DELIVERY.md) · [validation receipts](docs/NATIVEHDR10_VALIDATION.md) | The nativehdr10 delivery and its scoped validation |
| [GTK frames compatibility](docs/GTK_FRAMES_COMPATIBILITY.md) | A packaging compatibility correction and its source pins |
| [HDR foundations](docs/QUALIFIED_HDR_FOUNDATIONS.md) | The reviewed main-targeting source batch and its provenance |
| [Display diagnostics](docs/DISPLAY_DIAGNOSTICS.md) | The read-only inspector and Wayland colour probe |
| [ICC characterisation](docs/ICC_CHARACTERISATION.md) | Reading factory profiles without applying them |
| [Panel measurement](docs/PANEL_MEASUREMENT.md) | The optical procedure required before any calibration claim |

### Process and provenance

| Document | Answers |
|---|---|
| [Development](docs/DEVELOPMENT.md) | Reconstructing source, proving changes, remotes and branches |
| [Operations](docs/OPERATIONS.md) | Inspecting the laptop safely and keeping recovery possible |
| [Review](docs/REVIEW.md) | Adversarial review findings and their dispositions |
| [Provenance](docs/PROVENANCE.md) | Where imported work came from and how to read its evidence |
| [Licensing and attribution](LICENSES.md) | Retained upstream terms and the owner's MIT grant |

## Repository layout

- `patches/libdisplay-info/` · `patches/mutter/` — upstream-facing series on
  upstream main, with exact bases in `sources.json`; not yet submitted.
- `patches/ubuntu-libdisplay-info/` · `patches/ubuntu-mutter/` — the Ubuntu
  packaging path: delivered prefixes (now the rollback) plus the candidate.
- `patches/linux/` — native luminance, AUX backlight and parser-test patches.
- `patches/wine/` — Windows API compatibility for the processor route.
- `sources.json` · `SHA256SUMS` — source identities and patch integrity.
- `tools/` · `scripts/` — the native player, harness and validation tools; no
  installation side effects.
- `evidence/` — small validation receipts. Large or private captures, OEM
  binaries, vendor outputs and signing keys never go in Git.
- `docs/` — the documentation indexed above.

Audio (speakers, latency, Dolby Atmos) lives in
[rog_audio](https://github.com/pjunod/rog_audio).

## Progress

- [x] Native HDR detection on the internal panel (HDR10 working 2026-10-08)
- [x] Compositor colour pipeline: physical targets, HLG, highlight mapping,
  gamut compression, Night Light in HDR
- [x] Ubuntu source and binary packages with tested install and rollback
- [~] Open Dolby Vision display mapping — 13/30 on new shots; measurement-driven
  fixes in progress
- [~] Dolby Vision playback — Profile 5 decode and reshaping work; trims,
  Profile 8 and the full mapping remain
- [ ] HDR/SDR, brightness, DPMS and suspend/resume qualification
- [ ] Panel measurement and calibration (needs an instrument)
- [ ] Qualification across apps, including Plurx
- [ ] Upstream submission (the owner's decision)
