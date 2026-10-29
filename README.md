# rog_hdr_dv — HDR and Dolby Vision on Linux for the ROG Zephyrus G16

Research and patch work on the Linux display stack for the ASUS ROG
Zephyrus G16 (GU605MZ) and its 2560×1600, 240 Hz Samsung OLED panel. It aims
for the picture macOS gives you on the same kind of screen: HDR that just
turns on, Dolby Vision that follows the colourist's grade, and colour that is
consistent from one app to the next. Fixes go into shared Linux components
(the kernel, libdisplay-info, GNOME's Mutter compositor, the playback
libraries) rather than into one app, so that other software and other
machines can benefit. Plurx, the owner's media server, is one consumer; this
repository owns the operating-system display work.

> **Patches to the display stack, with one installer.** The patches change
> the kernel, the display library and the compositor. The compositor and
> display library install as ordinary Ubuntu packages from an APT repository
> ([APT repository](docs/UBUNTU_APT_REPOSITORY.md)); a kernel is installed
> deliberately, per [operations](docs/OPERATIONS.md), never by a repository
> check. Nothing here is upstream yet, and no colour accuracy is claimed
> without an optical measurement of the panel.

## What works today (2026-10-29)

Installed on the laptop: libdisplay-info `0.3.0-1ubuntu1~hdr9`, Mutter
`51.0-1ubuntu3+nativehdr10` (since 2026-10-13), kernel
`7.3.0-rc6-nativehdr2+`, and plurx Player `0.3.2` for Dolby Vision.
The running kernel lacks CVE-2026-98432's fix. The five display patches
are rebased onto released Linux 7.3, which includes the fix; see the
[kernel rebase](docs/KERNEL_REBASE.md) for build and deployment evidence.

| Area | State | Where it stands |
|---|---|---|
| HDR detection on the internal panel | **Working** since 2026-10-08 | The panel's DisplayID HDR description is parsed, so HDR is offered and HDR10 plays |
| Kernel security rebase | **Source prepared; build pending** (2026-10-29) | Linux 7.3 plus the four HDR patches and the i915 VRR patch; the running `nativehdr2` remains vulnerable until the replacement is signed and booted ([rebase](docs/KERNEL_REBASE.md)) |
| HDR desktop session | **Installed** | Mutter reports the panel's declared range (0.0004–616 cd/m², firmware values) and primaries separately from the BT.2020/PQ encoding |
| HLG, highlight mapping, gamut compression | **Installed** | The compositor maps highlights to the panel and compresses out-of-gamut colour toward it |
| HDR targets on external CTA monitors and native SDR panels | **Installed** (in `nativehdr10`) | Not yet tried on an external monitor |
| Night Light in HDR, per-monitor overrides | **Installed** (in `nativehdr10`) | The owner's visual check is outstanding |
| Ubuntu packages | **APT repository** (2026-10-27) | Rebuilt from Ubuntu's current source whenever Ubuntu updates it; one command sets a machine up ([APT repository](docs/UBUNTU_APT_REPOSITORY.md)) |
| Dolby Vision display mapping | **Done** (closed form) | Closed-form CM v4.0 and CM v2.9 equations; mean ΔE_ITP about 0.005 from Dolby's reference renderer on four titles at 600 nits (below) |
| Dolby Vision playback | **Working** through plurx Player | Profile 5, 8.1 and 7 FEL from the plurx web app, mapped at the panel's 616 nits ([plurx Player](#dolby-vision--the-equations-and-where-they-run)) |
| Panel calibration | **Not started** | Needs a colourimeter; the [procedure](docs/PANEL_MEASUREMENT.md) is defined |

[Status](docs/STATUS.md) is the authoritative, dated version of this table.
The [i915 VRR diagnosis](docs/I915_VRR_FASTSET.md) explains the retained
page-flip fix and the outstanding hardware checks.

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

The player is plurx Player: plurx's closed-form display mapping, with the
per-shot trims, runs inside its libplacebo at the panel's peak, and it
describes the result to Mutter so the compositor does not map it a second
time. [Architecture](docs/ARCHITECTURE.md) assigns each responsibility to a
component and explains why.

## Dolby Vision — the equations and where they run

Open-source decoding and reshaping of Dolby Vision exist (FFmpeg and
libplacebo). **Display mapping** did not: the step that fits a film mastered
on a 1,000–4,000-nit reference display into what this panel can show,
following the colourist's per-shot trims. Dolby supplies that code only to
licensees, and open players substitute a generic tone mapper.

This work derived it in closed form, for both of Dolby's content-mapping
versions, by measuring Dolby's reference renderer as a black box (synthetic
colour grids, then real frames) and scoring every change with the BT.2124
ΔE_ITP colour difference ([measurement-driven
development](docs/MEASUREMENT_DRIVEN_DEVELOPMENT.md)):

- **Result (2026-10-26):** mean ΔE_ITP 0.0036–0.0055 from the reference on
  selected frames of four titles at a 600-nit target, against 0.11–0.31
  before the last CM v2.9 correction. A ΔE_ITP of 1 is about the smallest
  difference a viewer can see. These are differences from the reference
  renderer's output, not measurements of what the panel displays.
- **Where they run:** in plurx, the owner's media server — its processing
  helper and **plurx Player**, an mpv build launched from the plurx web app
  that maps each frame on the laptop's GPU at the panel's own peak, and
  combines Profile 7's full enhancement layer itself.
- **What stays private:** the derivations and Dolby's measured outputs live on
  a private branch, never on `main` or its mirror.

The alternative route, running the laptop's own Windows Dolby Vision
processor under Wine, activates but has not processed a frame
([activation probe](docs/DOLBY_ACTIVATION_PROBE.md)); the closed form made it
unnecessary for playback.

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

**Issues and pull requests on GitHub are welcome.** This GitHub repository
is a push mirror of the maintainer's private forge (`main`, `codex/*`,
`claude/*` and `hermes/*`), so accepted changes are carried through the forge
rather than merged here. Maintainers and agents follow [AGENTS.md](AGENTS.md):
work on a branch, get an adversarial review when ready to merge, then run the
fast lane (the two checks above, also available as a manual GitHub workflow)
once before merging. [Development](docs/DEVELOPMENT.md#remotes-branches-and-the-public-mirror)
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
| [APT repository](docs/UBUNTU_APT_REPOSITORY.md) | Installing the HDR desktop packages on a machine, and how they follow Ubuntu's updates |
| [Merged Ubuntu packages](docs/MERGED_UBUNTU_PACKAGES.md) | The hand-built 2026-10-17 release and its install/rollback test |
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
| [Upstream submissions](docs/UPSTREAM_SUBMISSIONS.md) · [submission kits](upstream/README.md) | Every upstream item's disposition, evidence, submission order and remaining prerequisites |
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
- `packaging/ubuntu/` — build, publish and nightly rebuild of the Ubuntu
  packages, and `setup-apt.sh`, the one installer.
- `tools/` · `scripts/` — the native player, harness and validation tools; no
  installation side effects.
- `evidence/` — small validation receipts. Large or private captures, OEM
  binaries, vendor outputs and signing keys never go in Git.
- `upstream/` — reviewed submission material, descriptions and per-project
  preparation commands; actual submissions and sign-offs belong to the owner.
- `docs/` — the documentation indexed above.

Audio (speakers, latency, Dolby Atmos) lives in
[rog_audio](https://github.com/pjunod/rog_audio).

## Progress

- [x] Native HDR detection on the internal panel (HDR10 working 2026-10-08)
- [x] Compositor colour pipeline: physical targets, HLG, highlight mapping,
  gamut compression
- [~] Night Light in HDR and per-monitor overrides — installed
  (`nativehdr10`); the owner's visual check remains
- [x] Ubuntu packages in an APT repository, rebuilt when Ubuntu updates
- [x] Open Dolby Vision display mapping — closed-form CM v4.0 and CM v2.9
- [x] Dolby Vision playback — plurx Player, Profile 5, 8.1 and 7 FEL
- [ ] HDR/SDR, brightness, DPMS and suspend/resume qualification
- [ ] Panel measurement and calibration (needs an instrument)
- [~] Qualification across apps — plurx Player's acceptance on the laptop is
  next
- [ ] Upstream submission (the owner's decision)
