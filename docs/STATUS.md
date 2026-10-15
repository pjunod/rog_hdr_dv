# Status — what is working and what remains

**Updated:** 2026-10-15 (America/New_York) · **State:** main-targeting HDR
foundations/tooling/experimental-launcher source independently reviewed and qualified;
three support-helper defects corrected and re-reviewed, all 29 affected methods passed.
Previously qualified component source and exact historical receipts are selected
without importing held PR16/17 history. [PR20](https://github.com/pjunod/rog_hdr_dv/pull/20)
records final publication/merge disposition. Full Dolby Vision and measured image-quality
acceptance remain open; source qualification authorizes no deployment.

The [visual status page](STATUS.html) shows the workboard. [Provenance](PROVENANCE.md)
distinguishes inherited evidence from new work, [development](DEVELOPMENT.md)
defines validation, and [review](REVIEW.md) records findings and their resolution.
Source qualification is separate from package delivery and physical measurement.

## HDR foundations — main-targeting candidate

Merged-package lane `t_b2f97e54` now owns [normal Ubuntu source/binary packaging](MERGED_UBUNTU_PACKAGES.md)
in a new isolated clone from actual main2735b97f. Done: source/receipt inventory;
done: launcher experimental3 and coherent nine-package Mutter nativehdr10.1 normal
source/binary construction, including .dsc/archive/.changes/.buildinfo and matched
debug symbols, with nocheck/no repeated upstream units. Current: retained hdr9
multiarch source/applicability, private kit and actual isolated-install environment.
Remaining: independent review/fixes, one affected package batch, actual isolated
install/rollback evidence, canonical kit and PR landing.
Not yet a fresh release or live installation. Unqualified Dolby work is excluded.

Done: selected nativehdr10 upstream90/Ubuntu105 source, unchanged library pins,
the qualified public schema1/schema2 headless harness and experimental2 launcher.
Imported source/test bytes and retained evidence are compared against qualified
donors, not described as new executions. Component receipts retain their actual
heads/trees; no unit suite runs in this preparation phase.
See [scope/provenance/applicability](QUALIFIED_HDR_FOUNDATIONS.md).

Done: canonical library10/upstream90/Ubuntu105 replay and all selected native
compiler stages, including both full Mutter builds. The [compiler receipt](../evidence/qualified-main-compiler.json)
binds the original 302-file source transfer, zero unit execution and recovered
original Ubuntu success. Final static binding finds 299 identical transferred
files plus three corrected shell helpers not invoked by the direct replay/compiler
drivers; actual consumed compiler inputs remain unchanged. Whole-candidate review of [PR20](https://github.com/pjunod/rog_hdr_dv/pull/20)
completed with changes required: unsafe commit-build prerequisites/ownership,
fail-open publication scanning, and masked Wine initialization/test exits.
All three findings closed in independent focused re-review at `2bf1912`;
the one hermetic helper batch passed 29/29, with no failures/errors/skips.
The [qualification receipt](../evidence/qualified-main-final.json) binds the actual
review, source hashes, executed IDs and logs. Component suites were not repeated.
Inherited support-tool prerequisites are explicit new review scope, not
implicitly qualified by use on an older branch. Main's audio ownership and security policy are preserved.
PR16 remains closed/unmerged and held; PR17 is superseded source history, not the qualified delivery.

Qualification lane `t_f06aa8f3` retains final source-integrity/publication and
actual merge readbacks. Whole-candidate review `t_c00009d9` required changes;
focused re-review `t_d1b8661c` approved their correction. Evidence/status-only
closeout does not change executable/test/patch/dependency/build/scanner/CI inputs.
Do not repeat successful component units without actual invalidation. The broader programme
still owns KMS scanout/size-warning causes, transitions/resume, exact target
handoff/no-double-mapping, Dolby minimum/creative trims/reference agreement,
Windows comparison, optical measurement and upstream disposition. A bounded
historical laptop trial is not clean-log or full hardware acceptance.

Owner clarification: main-only builds/installs apply only to mobile builds
intended for installation on physical devices, and those installations.
Non-mobile HDR pre-merge compiler work follows the existing authorized workflow;
all device restrictions, independent-review gates and PR16 hold remain.

The installation sections below are dated historical evidence, not a fresh
inventory or permission to install their artifacts.

## Audio — moved to rog_audio on 2026-10-12

At the owner's request, all active speaker, latency and Atmos implementation
moved to [rog_audio](https://github.com/pjunod/rog_audio). Its
[status ledger](https://github.com/pjunod/rog_audio/blob/main/docs/STATUS.md)
tracks the GPT-6.1 Sol builds, review, validation and remaining measurements.
The read-only hardware inventory and detailed build contracts moved with it.
The original documentation review remains below in the review history.
No live audio settings changed during the repository split.

## Installation — hdr9 and nativehdr8 (2026-10-11)

In a coordinated window with the owner logged out, the six packages were
installed (6 upgraded, 0 added, 0 removed), held, and the display manager
restarted. The new login screen runs on the installed compositor with no
colour or EDID warnings; it is in SDR mode and publishes a coherent
description ([receipt](../evidence/install-2026-10-11.json)). The kernel,
boot selection, Secure Boot, profiles and display settings are unchanged.
The previous hdr6/nativehdr2 packages remain the hash-verified rollback.
The owner's HDR desktop session then started on the new compositor in
BT.2100 mode. It now reports the panel's firmware-declared target to clients
(primaries and 0.0004–616 cd/m², not a measurement) separately from the
BT.2020/PQ encoding, with no colour warnings in the session journal. The owner then
checked the picture and accepted it ("the picture looks awesome"); that is
a subjective check, not an optical measurement. At the owner's request, the old agent build
containers from earlier batches were removed.

## Tenth batch — general availability: targets and upstream port

Until now only an internal panel whose DisplayID declares native RGB
BT.2020 PQ (the ROG route) had a declared colour target; every other output
used the encoding fallback, so nothing was tone-mapped or gamut-compressed.
[Display target sources](DISPLAY_TARGET_SOURCES.md) widens target selection
in the colour device. In BT.2100, the peak and black come from DisplayID
physical luminance (10% window peak required), else from CTA-861 HDR static
metadata. A peak at or below the encoding's nominal reference white is not
a target. The BT.2100 gamut still comes only from DisplayID. In the native
SDR mode, the base EDID gamut (the encoding's own) is the target, so wider
content is compressed rather than clipped. Gamut containment is now judged
after adapting the target to D65, in the frame the pixels use. Otherwise a
native SDR output whose white is not D65 judged its own encoding out of
gamut.

The whole colour programme was also ported to upstream Mutter main
(`d82671c`) as the upstream-facing series (`patches/mutter/`, 49 patches):
43 ported commits, debian excluded, with messages in upstream form, plus
the six target commits. Every commit builds with warnings as errors against
the upstream-facing libdisplay-info series. That series needed no rebase:
upstream libdisplay-info is still at its base. Neither series has been
submitted upstream. The Ubuntu series gained the same six commits as
`nativehdr9` (Mutter patches 0053–0061).

An adversarial Fable review found the white-point containment defect (by
executing a probe), the low-peak risk and the base-EDID-gamut-in-HDR risk,
plus smaller items. All were fixed or decided, and a Fable re-review found
no remaining code defects ([findings](REVIEW.md#tenth-batch--general-targets-and-upstream-port)).
The colour test set (23 invocations including two new compositor cases) passed on
the upstream-facing head ([receipt](../evidence/general-targets-fast-lane.json)).

A second test machine, `lab6` (ThinkPad X1 Extreme, Intel UHD 630, an SDR
panel with base EDID only), was inspected read-only
([hardware](HARDWARE.md#second-test-machine-lab6)). It cannot use BT.2100 on
its built-in screen. It tests the native SDR target path on Intel graphics.

`nativehdr9` was installed on `lab6` in a coordinated window: 5 upgrades, 0
added, 0 removed, held, with a stock rollback set. The login screen and the
owner's session run on it with no colour messages. In the default mode, the
session publishes sRGB with the fallback target. In native SDR mode
(selected with `gdctl`), the encoding and target primaries are the panel's
base EDID gamut ([receipt](../evidence/install-lab6-2026-10-11.json)). The
owner's visual check is pending.

An independent Fable review of the whole plan followed (strategy, design,
upstreaming, measurement, process). Its recommendations and the decisions it
puts to the owner are in [review](REVIEW.md#independent-plan-review-2026-10-11).

## Ninth batch — independent review and fixes

At the owner's request, independent Fable 5.1 reviews covered the whole
compositor stack, the library, Wine and Dolby activation work, and the
evidence, packaging and install kit ([findings](REVIEW.md#ninth-batch--independent-review-and-fixes)).
The most important finding: plain PQ video without a declared peak was being
tone-mapped from the 10000 cd/m² encoding capacity, which would have dimmed
ordinary HDR. `nativehdr8` (Mutter patches 0044–0052) now leaves such content
unmapped, publishes descriptions on the renderer's exact identity, and
applies the other fixes. The Wine DisplayMonitor took three fixes (lock, EDID copy, output
technologies; patches 0010–0017). A Fable re-review found no blockers and
approved the fixes (recorded in [review](REVIEW.md#ninth-batch--independent-review-and-fixes)),
and the affected fast lanes passed (synthetic headless tests;
[receipt](../evidence/review-fixes-fast-lane.json)).

The delivery set was the hdr9 library (hdr8 code; it provides the native
HDR API as a virtual package the compositor depends on) with `nativehdr8`
([receipt](../evidence/hdr9-nativehdr8-packages.json)). The install kit holds
the six packages, checks the rollback packages first and snapshots the
package state. The `nativehdr6` comparison set was dropped: it lacks the
review fixes. The hdr9 + `nativehdr8` set was installed on 2026-10-11 (see
above).

## Eighth batch — gamut compression and delivery (merged, PR 8)

`nativehdr7` (Mutter patches 0039–0043) compresses colours outside the
panel's declared gamut into it, using the ACES reference gamut compression
with limits derived from the source and target gamuts
([contract](HDR_MAPPING.md#gamut-compression-nativehdr7)). It applies only
when the content can exceed the declared gamut, so sRGB content on a
panel whose declared gamut contains sRGB, and P3 masters on a P3 panel, are
untouched. It was reviewed adversarially and
passed its affected fast lane on the first run (synthetic headless tests,
software rendering; [receipt](../evidence/mutter-gamut-compression.json)).
Whether the panel itself clips out-of-gamut input, and so how much this
changes on screen, needs the installed system and an instrument.

## Seventh batch — HLG and tone mapping (merged, PR 7)

`nativehdr6` (Mutter patches 0028–0038) implements the
[HLG and tone-mapping contract](HDR_MAPPING.md): HLG decoding with its OOTF,
validated source mastering metadata, and BT.2390 highlight mapping to the
panel's declared target luminance. Mapping is applied once per surface and
only when content exceeds that target. It was reviewed adversarially and
passed its affected fast lane (synthetic headless tests, software rendering;
[receipt](../evidence/mutter-hdr-mapping.json)).

## Sixth batch — colour input and processor activation (merged, PR 6)

With DisplayMonitor merged, the recovered OEM processor now **activates**
under Wine in the isolated fixture. It returns an `IMFTransform` that reports
one input and one output stream. It offers P010/NV12 input and 10-bit RGB,
half-float or 8-bit RGB output.
[The activation section](DOLBY_ACTIVATION_PROBE.md#displaymonitor-follow-up--the-processor-activates)
records what that does and does not prove. No media type has been set and no
frame has been processed. The next stage negotiates the offered types and
traces the metadata the transform requests. It has not started and awaits the
owner's scope confirmation.

The compositor's colour-input defects from the
[audit](COLOUR_PIPELINE_AUDIT.md#implementation-status) are fixed in
`nativehdr5`, which was reviewed and passed its affected fast lane
([receipt](../evidence/mutter-colour-input.json)).

## Fifth batch — display contracts and delivery (merged, PR 5)

Before this batch, the qualified Wine candidate loaded the exact recovered
Dolby DLL but its factory request stopped at the missing Windows
`DisplayMonitor` runtime class
([evidence](DOLBY_ACTIVATION_PROBE.md#wine-11-follow-up--the-dll-loads-displaymonitor-activation-is-missing)).
The batch delivered a [generic monitor contract](WINE_DISPLAY_MONITOR.md)
backed by actual display data, and native
[physical-target gamut reporting](NATIVE_TARGET_GAMUT.md) in the library
(hdr8 and upstream series) and the compositor (`nativehdr4`). It also added
the bounded read-only Wayland colour inspector
([guide](DISPLAY_DIAGNOSTICS.md#inspect-the-compositors-actual-colour-descriptions)).
The [optical measurement procedure](PANEL_MEASUREMENT.md) defines conditions,
initial accuracy goals and held-out validation; this unit has not been
measured.

Baseline packaging preceded the batch. The exact qualified hdr7 library
source produced amd64 and i386 packages, and nativehdr3 compositor packaging
completed in the isolated native builder. The
[package receipt](../evidence/baseline-native-packages.json) records source
identities and the six runtime artifacts. Read-only APT simulations found a
coherent six-package upgrade and modeled six-package rollback, with no
additions or removals. Recovery artifacts are hashed and retained privately;
the live installation is unchanged. Delivery now targets the newer reviewed
candidates instead of installing this baseline.

The adversarial review found two blockers and a set of should-fix defects;
all are addressed ([review](REVIEW.md#fifth-batch--display-contracts-pr-5)).
The pre-merge fast lane then passed: library groups and legacy consumers,
Mutter `native-hdr` and all Wayland target-volume invocations, 23 probe
cases, and the Wine `displaymonitor` and `displayconfig` tests
([receipt](../evidence/batch5-fast-lane.json)). Nothing was installed at that point.

On 2026-10-10 the previous agents' macOS temporary clones were gone and two
local commits had never been pushed. Every unfinished change was recovered:
the probe test selectors are byte-identical to their recorded hash, the
library, nativehdr3 and Wine baselines reproduce their recorded trees, the
Mutter edit was replayed from the implementing agent's log, and the Wine
component was copied from the retained offline compiler container. Recovered
work keeps its original authorship; corrections are separate commits.

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
| Physical luminance library | hdr9 (hdr8 luminance and gamut API) installed for amd64 and i386 | Wider hardware and upstream acceptance |
| Compositor feedback | nativehdr8 (target luminance and gamut, colour input, HLG, highlight mapping, gamut compression, review fixes) installed; nativehdr9 (targets on CTA HDR outputs and native SDR panels) packaged | Install and check nativehdr9 on lab5 and lab6; optical verification needs an instrument |
| Upstream | Upstream-facing Mutter series (49) and libdisplay-info series (10) current on upstream main | Owner decides submission (merge requests under the owner's identity) |
| Full Dolby Vision | OEM processor activates and describes its transform under Wine (proven with Wine patches 0001–0009; the review-fix modules 0010–0017 passed the DisplayMonitor tests but have not been re-run against the processor); reference workflow available; the OEM plugin does not register Profile 7, so P7 FEL is outside this route | Negotiate types, establish the device and metadata contract, process frames, validate profiles and trims, integrate playback |
| General colour quality | Audit complete; input defects fixed (nativehdr5); HLG and BT.2390 highlight mapping (nativehdr6); gamut compression (nativehdr7); all reviewed with fast lanes passed | Output characterization (contract defined; needs a measurement, see [HDR mapping](HDR_MAPPING.md#output-characterization--defined-deferred-until-measured)), SDR/HDR consistency and cross-application checks; optical verification (the owner's visual check passed) |
| Exact-panel tuning | Four factory profiles inspected privately | Obtain measurement equipment and measure this unit, then implement the [output-characterization contract](HDR_MAPPING.md#output-characterization--defined-deferred-until-measured) |
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

- libdisplay-info `0.3.0-1ubuntu1~hdr9` (amd64, i386) and Mutter
  `51.0-1ubuntu3+nativehdr8`, installed and held on 2026-10-11.
- Kernel `7.3.0-rc5-nativehdr1`, from Ubuntu `7.3.0-8.8` plus four patches. The
  installed stock fallback kernel is now `7.3.0-9-generic` (the `7.3.0-8`
  image named in the older recovery notes has been removed).
- Replaced on 2026-10-11 and kept as the hash-verified rollback:
  libdisplay-info `0.3.0-1ubuntu1~hdr6` (amd64, i386) and Mutter
  `51.0-1ubuntu3+nativehdr2`.
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

`nativehdr9` is ready to install, in a coordinated window, on `lab6` (stock
26.10, native SDR path) and then `lab5`. An external HDR monitor on `lab6`
would test the CTA path. Submitting the upstream-facing series is the
owner's decision. Two further steps wait on the owner, and one comparison
is optional. The KMS
metadata question can be settled by an on-screen comparison if the owner
wants it; the owner's subjective check of the current picture passed. The Dolby processor's next
stage waits for the owner's scope confirmation and, before it can say
anything about this panel, a monitor descriptor source in Wine
([prerequisites](DOLBY_ACTIVATION_PROBE.md#displaymonitor-follow-up--the-processor-activates)).
Output characterization waits for a measurement instrument (owner to
obtain).
The staged acceptance criteria remain in
[Dolby Vision and display quality](DOLBY_VISION_AND_QUALITY.md#5-work-in-stages-with-observable-acceptance).

## Decisions taken without the owner

Recorded for review; each can be revisited.

- Audio implementation moved to rog_audio on 2026-10-12 and uses GPT-6.1 Sol chats in
  isolated clones. The coordinator owns design, review and integration; this
  does not change the existing display team or its held work.
- Since the fifth batch, display agent commits use `Claude Agent <claude-agent@invalid>`
  with a co-author trailer, and implementation and review agents are Claude
  agents. Earlier agent commits used `Codex <codex@invalid>`; recovered work
  keeps its original authorship.
- Compositor and library builds, compositor tests, the Wine fast lane and the
  packages run in disposable agent containers off the laptop (native amd64;
  the i386 library is cross-built; Wine tests use WineHQ 11.0 with the
  candidate modules overlaid). The Wine compiler and the Dolby activation
  probe run in agent-owned containers on the laptop (`lab5`) with no network,
  mounts or GPU. Package simulations and staging happened on the laptop
  before the coordinated installation of 2026-10-11; agent build containers
  from earlier batches were removed at the owner's request that day.
- The Wine DisplayMonitor uses base EDID 1.4 facts where DisplayID declares
  none.
- HLG is decoded for its declared nominal peak and then fitted by the common
  tone mapper, rather than rendered for the panel's peak.
- The BT.2390 tone mapper applies only when the content's effective peak
  exceeds the panel's declared peak. It never expands or raises black, and
  monitor screencasts are not mapped.
- `extended_target_volume` is advertised; declared mastering primaries set
  gamut-compression limits when compression applies.
- Gamut compression uses ACES reference gamut compression with limits derived
  from the source and target gamuts, tolerating the declaration's own
  quantization.
- Output characterization is not applied until a measurement exists.
- The delivery set is hdr9 with `nativehdr8`; the earlier `nativehdr6`
  comparison set was dropped because it lacks the review fixes.
- PQ content without a declared peak is not tone-mapped; its overshoot is
  left to the panel.
- KMS static metadata keeps zero ("unknown") luminance fields; whether to
  declare the target is decided by an on-screen comparison on the
  owner's HDR desktop session.
- Display targets use CTA-861 desired content luminance as the BT.2100 peak
  where DisplayID declares none. Its own provenance is `cta-declared`. It
  is a content preference, not a measurement, but most HDR displays declare
  no other peak.
- A target peak at or below the encoding's nominal reference white
  (203 cd/m² for PQ) is no target, so a bogus low peak cannot dim SDR. The
  rule uses the nominal value, not the brightness-scaled one, so a target
  does not appear and disappear with the brightness setting.
- Base EDID primaries are not a BT.2100 gamut target. Many HDR displays
  declare their SDR gamut there, so compressing toward it risks visible
  desaturation without a measurement. They are the native SDR target only.
- The upstream-facing Mutter series is a port of the reviewed Ubuntu series
  to upstream main, with commit messages rewritten to upstream rules
  (authorship, trailers and inherited validation claims preserved). A
  separate test machine, `lab6`, was added for general-availability
  checks; it stays a stock Ubuntu 26.10 baseline and is not used for builds.
