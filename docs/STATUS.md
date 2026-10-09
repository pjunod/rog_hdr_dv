# Status — what is working and what remains

**Updated:** 2026-10-08 (America/New_York) · **State:** HDR10 operational by owner report;
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

## Active batch — processor contracts and profile interpretation

The next batch implements a bounded Wine API-resolution diagnostic and a
private ICC/MHC2 inspector, and traces the exact installed Mutter colour
pipeline. It will distinguish API-set loading from a working function,
profile data from applied calibration, and PQ encoding range from physical
target luminance. Review and fast-lane validation happen at the end of the
batch. No live display change is planned for these investigations.

A follow-up read of Mutter's `PowerSaveMode` returned `3` (off), consistent
with the prior disabled-scanout capture. An awake observation is still needed
for physical output acceptance; software inspection continues meanwhile.

| Component | State | Remaining evidence/work |
|---|---|---|
| Native HDR detection | Implemented and installed | Wider hardware/upstream acceptance |
| Kernel and AUX brightness | Test kernel booted with Secure Boot | HDR/SDR transitions, DPMS, suspend/resume, brightness and mode coverage |
| Library | hdr6 amd64/i386 delivered | Revalidate future dependency upgrades against unpublished APIs |
| Mutter | nativehdr2 delivered | Physical colour-path audit; unresolved historical flaky batch failure |
| Full Dolby Vision | First compatibility boundary identified | Resolve the Wine API-set contract, then qualify activation, processing and display management |
| General colour quality | Requirements and initial source audit | Trace transformations and fix gaps across applications and composition |
| Exact-panel tuning | OEM data recovered | Validate profile interpretation, implement calibration path, measure this unit |
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
