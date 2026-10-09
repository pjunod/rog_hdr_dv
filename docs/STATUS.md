# Status — what is working and what remains

**Updated:** 2026-10-09 (America/New_York) · **State:** HDR10 operational by owner
report; full Dolby Vision and measured image-quality acceptance remain open.

The [visual status page](STATUS.html) shows the workboard. [Provenance](PROVENANCE.md)
distinguishes inherited evidence from new work, [development](DEVELOPMENT.md)
defines validation, and [review](REVIEW.md) records findings and their resolution.
Source qualification is separate from package delivery and physical measurement.

## Active fifth batch — display contracts and delivery

The qualified Wine candidate now loads the exact recovered Dolby DLL. Its
factory request stops when the component asks for the missing Windows
`DisplayMonitor` runtime class. The manifest, hashes and loader trace agree;
[activation evidence](DOLBY_ACTIVATION_PROBE.md#wine-11-follow-up--the-dll-loads-displaymonitor-activation-is-missing)
records the exact scope. Object activation and frame processing remain open.

Work continues on a generic monitor contract backed by actual display data,
native physical-target gamut reporting, and matching amd64/i386 library plus
amd64 compositor packages. Packaging uses isolated source-only builds; no host
installation or live display change is implied. The [optical measurement procedure](PANEL_MEASUREMENT.md) defines conditions,
initial accuracy goals and held-out validation; this unit has not been measured.

## Fourth batch — native target feedback and processor prerequisites

[PR 4](https://github.com/pjunod/rog_hdr_dv/pull/4) adds three components:

| Component | Qualified evidence | Remaining delivery or acceptance |
|---|---|---|
| [Mutter physical-target feedback](MUTTER_TARGET_LUMINANCE.md) | Compiled with warnings as errors; independent review corrections addressed; all eleven selected checks passed across initial runs and focused retries | Package and verify active physical output |
| [Wine file API](WINE_FILE_FROMAPP.md) | Reviewed, compiled; 123 focused assertions passed with no failures or skips; loaded module identity verified | Continue processor activation investigation |
| [Synthetic HDR corpus](HDR_REFERENCE_CORPUS.md) | Eleven new tests passed; private official-reference experiment completed | Creative-trim and consumer-profile comparisons |

Mutter now keeps firmware-declared physical target luminance separate from PQ
encoding and renderer state. Immutable Wayland descriptions preserve old
snapshots and notify clients of target changes. The first test pass exposed a
shutdown lifetime defect; explicit manager cleanup before output destruction
fixes its demonstrated cause. Synthetic forced-HDR tests preserve
their manually selected output mode while testing target policy. This fixed-route
fixture does not qualify real monitor reconfiguration.

Wine is used to investigate the Windows Dolby processor recovered from the
factory image. The missing file function now passes its desktop API contract.
DLL loading now passes; actual processor activation remains open; Wine is a candidate compatibility
route, not a confirmed requirement of the final Linux solution. The HDR and
colour-management changes are native Linux code.

The owner supplied and accepted official Dolby Professional Tools v5.6.4.
Private offline reference processing has completed. Proprietary tools,
documentation, generated metadata, rendered outputs and numerical comparisons
remain private. This establishes a reference workflow, not general playback,
creative-trim fidelity or calibrated panel accuracy. Its processing container
and owned runtime image were removed after retaining private evidence.

No host package, live display setting, boot selection or calibration changed
in this batch. Mutter remains ARM64 source qualification; delivery needs amd64
Mutter and matching amd64/i386 library packaging.

## Overall remaining work

| Area | State | Remaining work or acceptance |
|---|---|---|
| Native HDR detection | Implemented and installed | Wider hardware and upstream acceptance |
| Kernel and AUX brightness | Test kernel booted with Secure Boot | HDR/SDR transitions, DPMS, suspend/resume, brightness and display-mode coverage |
| Physical luminance library | hdr6 delivered; additive hdr7 source qualified | Matching packages and compositor consumer delivery |
| Compositor feedback | nativehdr2 delivered; nativehdr3 source qualified | Package and verify active output |
| Full Dolby Vision | Processor route unresolved; reference workflow available | Activate/evaluate full processor, preserve frame metadata, validate supported profiles and trims, integrate playback |
| General colour quality | Delivered-source audit complete | Tone and gamut mapping, correct profile application, SDR/HDR consistency and cross-application checks |
| Exact-panel tuning | Four factory profiles inspected privately | Implement characterisation/calibration path, obtain measurement equipment and measure this unit |
| Applications | Shared platform path first | Qualify independent consumers; Plurx integration belongs in its separate repository |

The owner has no colourimeter or spectrophotometer yet and is open to obtaining
one. Software work continues independently. Define the measurement procedure
and OLED correction before choosing equipment. Firmware and factory-profile
values are not measurements of this particular unit.

## Completed source batches

1. **Repository, diagnostics and activation probe:** ordered patch provenance,
   public source reconstruction inputs, read-only diagnostics and an isolated
   activation probe. Review findings resolved; 45 Python tests and repository
   integrity passed. Live capture reported BT.2100 at 2560×1600/240 Hz, but the
   display was powered off, so active scanout remains unqualified. The original
   Wine 9 probe initialized COM/WinRT/Media Foundation and stopped at DLL loading.
2. **Profile interpretation and colour audit:** four factory ICC variants were
   parsed privately. MHC2 transforms are identity; standard characterisation
   differs by GPU route. All 16 new ICC tests passed across the initial run and
   one corrected-fixture retry. Stock Wine 11 isolated the missing file export.
3. **[Native physical-luminance API](NATIVE_LUMINANCE_API.md):** merged in
   [PR 3](https://github.com/pjunod/rog_hdr_dv/pull/3). Additive API preserves
   fractional physical luminance and field presence separately from CTA metadata.
   ARM64 and emulated amd64 builds passed with warnings as errors; 12 selected
   checks passed with only the corrected synthetic fixture retried. Previous
   consumer binaries passed against the new libraries; both series reconstructed.

## Installed baseline and inherited evidence

- Kernel `7.3.0-rc5-nativehdr1`, from Ubuntu `7.3.0-8.8` plus four patches.
- libdisplay-info `0.3.0-1ubuntu1~hdr6`, amd64 and i386.
- Mutter `51.0-1ubuntu3+nativehdr2`.
- NVIDIA `615.71.09`; Secure Boot remains enabled.
- mpv `0.41.0`, libplacebo `7.360.1`, FFmpeg `8.1.2` at inspection.

Historical receipts record upstream library GCC/Clang suites at 75/75, Ubuntu
library suites at 40/40 per architecture, ABI/export checks and actual package
install/offline rollback. Mutter's six focused regressions passed; its ordinary
package batch had 190 passes and five expected failures. A marked-flaky batch
had one unresolved `map-after-headless` failure; isolated passes did not establish
that it was unrelated.

Kernel receipts record affected DRM/i915/xe compilation, sparse, four KUnit
groups, full package builds, signature checks and delivered-header NVIDIA
builds. Initial physical boot and working HDR10 were subsequently reported.
These are scoped historical results, not freshly repeated tests.

## Next work

Continue the bounded processor activation experiment and native/full-DV
route evaluation alongside
colour-pipeline implementation. Package and install source-qualified components
in a coordinated recovery-ready window; qualify actual output before optical
calibration. The staged acceptance criteria remain in
[Dolby Vision and display quality](DOLBY_VISION_AND_QUALITY.md#5-work-in-stages-with-observable-acceptance).
