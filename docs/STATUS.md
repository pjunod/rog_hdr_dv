# Status — what is working and what remains

**Updated:** 2026-10-09 (America/New_York) · **State:** HDR10 operational by owner report;
full DV and measured image-quality acceptance open.

This is the current ledger. [Provenance](PROVENANCE.md) identifies inherited
evidence; [development](DEVELOPMENT.md) defines new checks. Importing patches
into this repository is not a fresh build or hardware qualification.

See [the visual status page](STATUS.html) for the current workboard and
[the review ledger](REVIEW.md) for findings. The first implementation batch
adds reproducible read-only diagnostics and an isolated OEM activation probe.
Adversarial findings are resolved; all 45 Python tests and the repository
integrity check passed. Live collection and bounded activation were executed.

The [display inspector](DISPLAY_DIAGNOSTICS.md) captured the configured
2560×1600/240 Hz BT.2100 output and one colord display association. Scanout was
disabled at capture time, so active-output colour qualification remains open.
The [Dolby activation probe](DOLBY_ACTIVATION_PROBE.md) initialized COM, WinRT
and Media Foundation but stopped at DLL loading: Wine 9.0 lacks the imported
`api-ms-win-core-file-fromapp-l1-1-0.dll`. Processor activation was not reached.
The reviewed experiment changed no live display settings; raw results are
private. Full Dolby Vision remains unimplemented/unqualified.

## Active source correction — physical luminance without fabricated metadata

An additive libdisplay-info low-level API is in implementation for the native
DisplayID 2 display-parameters luminance fields. It preserves fractional
physical minimum/full-frame/small-window data and distinguishes absent fields
from zero. It leaves legacy CTA desired-content metadata unchanged, so a
future compositor target policy can use physical declarations explicitly.

The work uses independent source clones and a disposable compiler environment.
It is source work only: no package installation or display change on the host.
Review, focused regression and publication receipts remain pending. The
compositor target-volume correction follows this data-source boundary.

## Second batch — reviewed tools and concrete remaining contracts

The [ICC inspector](ICC_CHARACTERISATION.md) parsed all four factory profile
variants privately. Both CMDEF files contain identity MHC2 matrix/LUTs and
616 cd/m² peak metadata; their standard ICC characterisation is nontrivial
and differs by GPU route. These are data findings, not activated calibration.

The [Wine API diagnostic](WINE_API_CONTRACT.md) ran on stock Wine 11.0:
API-set loading succeeds, but `CreateFileFromAppW` lookup fails with Win32
127. The required function contract remains unimplemented in that runtime.
The disposable container was removed after saving private receipts.

The [compositor audit](COLOUR_PIPELINE_AUDIT.md) identifies separate output
target-volume reporting, display characterisation and mapping gaps in the
exact Ubuntu source candidate. The first correction should carry physical
target data separately from PQ encoding normalization. KMS content metadata
must not be populated with a guessed panel peak.

Adversarial review found no actionable defects. The repository check passed;
all 16 new ICC tests passed across the initial run and a focused retry after
correcting one malformed fixture. Unchanged suites were not rerun. The
[review ledger](REVIEW.md) records the exact CI receipts.

Mutter's `PowerSaveMode` returned `3` (off), consistent with the prior disabled
scanout capture. Awake-output and optical acceptance remain open. Availability
of a measurement instrument and official reference-tool package is unanswered;
software source corrections can proceed independently.

| Component | State | Remaining evidence/work |
|---|---|---|
| Native HDR detection | Implemented and installed | Wider hardware/upstream acceptance |
| Kernel and AUX brightness | Test kernel booted with Secure Boot | HDR/SDR transitions, DPMS, suspend/resume, brightness and mode coverage |
| Library | hdr6 amd64/i386 delivered | Revalidate future dependency upgrades against unpublished APIs |
| Mutter | nativehdr2 delivered | Physical colour-path audit; unresolved historical flaky batch failure |
| Full Dolby Vision | Missing function confirmed on stock Wine 11.0 | Implement the required file API semantics; continue native reference and processor routes |
| General colour quality | Delivered-source audit complete | Separate physical target feedback from encoding, then implement and qualify mapping/calibration |
| Exact-panel tuning | Factory ICC/MHC2 structures inspected | Implement the correct characterisation/calibration path and measure this unit |
| Plurx | Independent downstream integration | Browser/native rendering route, metadata preservation and physical playback |

## Installed baseline

- Kernel `7.3.0-rc5-nativehdr1`, from Ubuntu `7.3.0-8.8` plus four patches.
- libdisplay-info `0.3.0-1ubuntu1~hdr6`, amd64 and i386.
- Mutter `51.0-1ubuntu3+nativehdr2`.
- NVIDIA `615.71.09`; Secure Boot remains enabled.
- mpv `0.41.0`, libplacebo `7.360.1`, FFmpeg `8.1.2` at inspection.

## Inherited qualification receipts

The preceding workspace records upstream library GCC/Clang suites at 75/75,
Ubuntu library suites at 40/40 per architecture, ABI/export checks, and actual
package install/offline rollback. Mutter's six focused regressions passed;
its ordinary package batch had 190 passes and five expected failures. A
marked-flaky batch had one unresolved `map-after-headless` failure; isolated
passes did not prove it unrelated.

Kernel receipts record affected DRM/i915/xe compilation, sparse, four KUnit
groups, full package builds, signature checks and delivered-header NVIDIA
builds. Initial physical boot and working HDR10 were subsequently reported.
These are scoped historical results, not newly rerun here.

## Next work

1. Trace actual SDR/PQ encoding, reference white, physical peak and calibration
   ownership through the current compositor and panel.
2. Probe the OEM processor contract and evaluate a native/open full-DV route.
3. Implement generic colour corrections and panel characterisation separately.
4. Qualify multiple applications, including Plurx, then measure and package.

The staged acceptance criteria live in
[Dolby Vision and display quality](DOLBY_VISION_AND_QUALITY.md#5-work-in-stages-with-observable-acceptance).
