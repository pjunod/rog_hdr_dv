# Status — what is working and what remains

**Updated:** 2026-10-08 · **State:** HDR10 operational by owner report;
full DV and measured image-quality acceptance open.

This is the current ledger. [Provenance](PROVENANCE.md) identifies inherited
evidence; [development](DEVELOPMENT.md) defines new checks. Importing patches
into this repository is not a fresh build or hardware qualification.

See [the visual status page](STATUS.html) for the current workboard and
[the review ledger](REVIEW.md) for findings. The first implementation batch
adds reproducible read-only diagnostics and an isolated OEM activation probe;
final review, fast-lane checks and live diagnostic receipts are pending.

The [display inspector](DISPLAY_DIAGNOSTICS.md) is implemented with fixture
regressions awaiting the agreed pre-merge fast lane. It deliberately produces
observations, not a universal HDR/DV support verdict.
The [Dolby activation probe](DOLBY_ACTIVATION_PROBE.md) cross-compiles with
warnings as errors in an isolated container. Runtime activation remains
pending; no proprietary code or live display change is part of public CI.

| Component | State | Remaining evidence/work |
|---|---|---|
| Native HDR detection | Implemented and installed | Wider hardware/upstream acceptance |
| Kernel and AUX brightness | Test kernel booted with Secure Boot | HDR/SDR transitions, DPMS, suspend/resume, brightness and mode coverage |
| Library | hdr6 amd64/i386 delivered | Revalidate future dependency upgrades against unpublished APIs |
| Mutter | nativehdr2 delivered | Physical colour-path audit; unresolved historical flaky batch failure |
| Full Dolby Vision | Investigation | Qualify a complete processor/display-management route and supported profiles |
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
