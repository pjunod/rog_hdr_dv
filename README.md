# rog_hdr_dv — Linux HDR, Dolby Vision and display quality

Linux display-stack work for the ASUS ROG Zephyrus G16 GU605MZ, with reusable
fixes for native DisplayID HDR detection and a programme for accurate colour,
panel calibration and full Dolby Vision. macOS-like consistency and ease of
use are the quality reference. Plurx is one consumer; this repository owns
the operating-system display work independently.

**Current mapping qualification (2026-10-18):** [frozen ABI368 main-based source
and isolated headless package recipes](docs/MAPPING_ABI368_DELIVERY.md).
The unchanged [sqrt-sum PQ-Y/post-SOP candidate](docs/SQRTSUM_PQ_Y_POST.md)
retains full-raster256/27 and714/27 development PASS and once-only independently
reserved1200/48 PASS (mean0.535635/p951.134168,8,847,360pixels,GPUinvalid0).
These observations remain bound to their original executing sources, not new
integration renders. Original numerical/native/provenance bytes and library
tree are preserved; held PR16 history is excluded. Done: scoped transplantation,
exact public-base library replay and package-relative native consumer compile.
Done: Fable's independent final APPROVE of exact `a6b8dcc` after the notice-only
F1 fix, including the owner's scoped [MIT grant](LICENSES.md).
Done: the [single affected batch and reviewed failure-only correction](evidence/abi368-qualification.json)
provide valid passes for all 76 Python methods (zero skips) and five native
checks. The initial CPU Vulkan skip remains uncounted; the corrected CPU-enabled
check proves real texture/render shader execution. No successful checks repeated.
Current: scoped publication/exact-head CI/merge. Remaining: broader 30-new-pair validation, actual
versioned Ubuntu source/binary and isolated install/rollback. The broader batch
is pending; the three retained observations are not general accuracy evidence.
No physical deployment or complete CM/rawRPU/L8/temporal/player/optical claim.

**Previous source batch (2026-10-15):** [HDR foundations, tooling and an
experimental launcher](docs/QUALIFIED_HDR_FOUNDATIONS.md), prepared directly
on `main` without merging held PR16 history. It combines nativehdr10 Night
Light/monitor targets, asynchronous lifetime and offscreen fixes, the Ubuntu
port/package recipes, a public headless reference harness, and a bounded
launcher for the existing stock player. All selected native compiler stages passed;
consumed compiler inputs remain unchanged. Of 302 original transferred files,
299 are byte-identical and three transported-only shell helpers were corrected below.
Independent whole-candidate review and focused re-review closed three helper defects;
the one affected helper batch passed all 29 methods. [Qualification evidence](evidence/qualified-main-final.json)
retains exact reviewed/tested identities and unchanged component passes, not new
component executions. [PR20](https://github.com/pjunod/rog_hdr_dv/pull/20) records final publication/merge disposition. Full Dolby
mapping/trims, reference agreement, optical calibration and broader hardware
acceptance remain unfinished. No new deployment is part of this batch.

**Audio moved:** speaker quality, latency and Dolby Atmos now live in the
independent [rog_audio repository](https://github.com/pjunod/rog_audio),
including its [progress ledger](https://github.com/pjunod/rog_audio/blob/main/docs/STATUS.md).

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
[Night Light and overrides](docs/NIGHT_LIGHT_AND_OVERRIDES.md) defines nativehdr10;
[validation receipts](docs/NATIVEHDR10_VALIDATION.md) describes its scoped runner.
[Asynchronous lifetime](docs/COLOUR_ASYNC_LIFETIME.md) and
[offscreen reuse](docs/OFFSCREEN_REUSE.md) document the reviewed follow-ups.
[Ubuntu delivery](docs/NATIVEHDR10_UBUNTU_DELIVERY.md) and
[merged Ubuntu source-package release](docs/MERGED_UBUNTU_PACKAGES.md) record
historical artifacts separately from the current package construction/qualification;
[GTK frames compatibility](docs/GTK_FRAMES_COMPATIBILITY.md) distinguish source
pins from the actual historical package construction identities.
[The headless harness](docs/DOLBY_HARNESS.md) documents public contracts and the
private reference boundary.
[Measurement-driven development](docs/MEASUREMENT_DRIVEN_DEVELOPMENT.md) is the
standing, model-independent method for deriving each open Dolby Vision stage
from controlled reference measurements, with its rules and acceptance step. [The open display-management contract](docs/OPEN_DV_DISPLAY_MANAGEMENT.md)
describes the unfinished full-fidelity target, not a claim for the launcher.
[Authored-master transport](docs/AUTHORED_MASTER_BASELINE.md),
[OPEN frame-owned mapping](docs/OPEN_XML205_CANDIDATE.md),
[absolute-PQ predecessor](docs/OPEN_ABSOLUTE_PQ_SOP.md) and
[public RGB/Y predecessor](docs/PUBLIC_RGB_MAPPING.md) preserve dated source
dependencies separately from the [current frozen mapping](docs/SQRTSUM_PQ_Y_POST.md)
and [ABI368 source/package boundary](docs/MAPPING_ABI368_DELIVERY.md).
[Launcher source/usage](tools/native_player/README.md) and
[qualification](tools/native_player/QUALIFICATION.md) describe the experimental milestone.
[Continuation](docs/HANDOFF.md) and the [programme ledger](docs/FULL_HDR_HANDOFF.md)
keep the done/current/remaining boundaries visible.
[Integration provenance and applicability](docs/QUALIFIED_HDR_FOUNDATIONS.md)
defines the independently reviewable main-targeting batch.

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
