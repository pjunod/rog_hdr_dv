# Status — what is working and what remains

**Updated:** 2026-10-12 (America/New_York) · **State:** hdr9 library and
`nativehdr8` compositor installed on 2026-10-11; the owner's HDR session runs
on it and the owner accepted the picture. The tenth batch (`nativehdr9`,
general display targets, and the upstream-facing Mutter port) is reviewed
and packaged. It is installed on the second test machine `lab6`, where
native SDR mode publishes the panel's EDID gamut as its target. Full Dolby
Vision and measured image-quality acceptance remain open.

The [visual status page](STATUS.html) shows the workboard. [Provenance](PROVENANCE.md)
distinguishes inherited evidence from new work, [development](DEVELOPMENT.md)
defines validation, and [review](REVIEW.md) records findings and their resolution.
Source qualification is separate from package delivery and physical measurement.

## nativehdr10 — reviewed source batch and validation

The owned collaboration clone starts at the exact final handoff
`7c78457581906a43377f8dbb0d8dc95b438f30d3`; PR 16 remains unmerged.
Astra and Fable approved the design; Sol and Opus implemented the two source
parts. The pinned upstream Mutter tree
`3f238d2e9227dacd578f5a673c04ac10de5caac8` and library tree
`72626245922181526fbcb990de3eb7f575efa56b` were reconstructed and compiled
natively on x86_64 with warnings as errors in this task (164.61 seconds).

**Initial source checkpoint (compiled):** both parts became Mutter patches 0050–0061
in `patches/mutter`, originally pinned as candidate
`fa7eb2cf55dd39464ef04042e3f085a5d6c18e5f`, tree
`18ba4b5a752f4ee383541757b20116060f18daf9`. Patches 0001–0049 are unchanged.

- 0050–0052: the original Night Light work in progress, imported with
  authorship and content unchanged (tree `14ce390c…` reproduced).
- 0053: bounded diagonal factors in the output's linear RGB replace Bradford.
  Negative factors are clamped at construction, so 1000 K is projected.
- 0054: warm LUT/CTM SDR→BT.2100→SDR transitions, capture exclusion and
  forced-HDR regressions. The capture inventory found no capture path that
  applies the adaptation, so no fix was needed.
- 0055–0060: Sol's configuration, persistence, copy/history, DisplayConfig,
  gdctl and NightLightSupported commits, rebased unchanged after the
  renderer.
- 0061: target selection with `user-declared` provenance. The luminance
  override comes before DisplayID and CTA, needs no EDID and is validated
  against nominal white. The BT.2100 gamut source is auto, base-edid or none;
  native SDR is unaffected.

Every commit was built individually with warnings as errors, with 0
diagnostics. The exported series replays onto the base to the same tree.
`check_repository.py` passes. See the
[candidate receipt](../evidence/nativehdr10-source-candidate.json), the
[earlier stage receipt](../evidence/nativehdr10-sol-stage.json) and the
[contract and implementation notes](NIGHT_LIGHT_AND_OVERRIDES.md).

**Done (validation tooling, compiled):** Sol's runner, 24 regression
methods and [instructions](NATIVEHDR10_VALIDATION.md) are integrated with
authorship kept (Sol's commit `e0742e8`, cherry-picked as `b9837a4`). The
runner executes a reviewed manifest of affected checks, one argument vector
per check, with an explicit environment. It keeps receipts tied to the
source tree and its own bytes. Later runs skip receipts that still match and
retry failures. Changed inputs stop the whole batch until the affected checks
are invalidated with a reason. Its files were only syntax-compiled; the
regressions had not run at integration. The later 29-method Linux batch passed
every method (see below). The Mutter source and native build tree were
unchanged by tooling integration, so no rebuild was needed for it.

**Done (review):** Astra and Fable delivered independent reviews of
`73918f3` / native `fa7eb2cf`. Changes are required: continuous default-anchored
Night Light factors, a bounded observable-state restore wait, isolated
user-override registration, real headless capture/readback coverage and
SIGTERM child cleanup. Review completion is not candidate acceptance.

**First batch (historical result):** the single affected batch executed 71 checks on native
`9570f9bb` / tree `ac02a18f`: **69 passed, 2 failed** in 134.99 seconds.
All 29 individual Linux runner methods passed; 40 of 42 native checks passed,
including the real capture case, isolated override case, gdctl, remaining
monitor/backend and cursor cases. The failures are `mutter:color-hdr`
(near-zero channel-bound assertion) and `mutter:monitor-dbus-tests`
(restored-peak wait timeout). That first candidate was **not accepted**.
The [first batch receipt](../evidence/nativehdr10-validation-attempt1.json)
records every original attempt, command, source identity and log hash.
All 71 original logs were retrieved and hash-verified and remain preserved.

Review corrections 0062–0068 are integrated and pinned at native
`9570f9bb` / tree `ac02a18f`, with unchanged 0001–0061 prefix, individual
warnings-as-errors builds and replay equality. See the
[correction receipt](../evidence/nativehdr10-review-corrections.json).
Focused Astra review approves the default-anchored production design;
Opus completed the requested successful/nonempty capture readback sanity
in 0068 and released native source/build ownership to Sol. Fable confirmed
runner `cc82113`; Sol folded the scoped mask/replay hygiene into `e4f981d`
before freezing it. Documentation precision is fixed in `4846eda`.
Fable's
recorded decision anchors the diagonal factors at the default temperature's
Planckian white, preserving exact off-state identity and continuous onset;
absolute Planckian-white accuracy is no longer the acceptance claim.

**First retry candidate:** reviewed corrections 0069–0071 are integrated and pinned at native
`a8847717` / tree `9111578e`, with individual -Werror builds and replay equality.
0069 corrects the float32 near-zero test allowance; 0071 holds the test shell's
synchronous confirmation so rejection actually runs. 0070 fixes the pre-existing
upstream restore-idle lifecycle bookkeeping, separately from the HDR feature;
it has no upstream-acceptance claim. Prefix 0001–0068 is unchanged; hashes were
deliberately appended. See the [correction receipt](../evidence/nativehdr10-failure-corrections.json).

The approved two-check retry passed `mutter:color-hdr`; `monitor-dbus-tests`
passed the new target-overrides case, then failed on a fatal existing-colord-device
lookup in `/backends/monitor/has-external-monitor` after disabling the external
monitor. Latest required receipts: **70 passed, 1 failed** (29 runner methods,
41 native invocations passed). The candidate is **not accepted**.
All 73 execution logs were hash-verified and all 69 non-retried histories remain
unchanged; see the [retry receipt](../evidence/nativehdr10-validation-attempt2.json).
Fable `t_bedcc81f` attests retention of the 40 original native passes: exact binary
identity for 0069/0071, source unreachability for 0070's changed idle callback.
Those passes stay at their actual executing tree `ac02a18f`, never rewritten
as passes on `9111578e`. This is reviewer interpretation, not automatic runner
reuse across whole-tree changes. Sol's transport postcheck assumed history length
2 instead of original + invalidation + retry (3); its export assertion failed
after both checks ran. A retrieval-only request preserved the actual ledger/logs,
without reexecution or runner edits.

**Colord correction checkpoint:** Opus delivered and Fable `t_6b592492` approved 0072–0074
at native `980bb21` / tree `41605eb0`, individually built with -Werror and replayed.
0072 binds colord unregister to the manager's removal rather than the last reference;
0073 removes old devices before creating replacements on connector moves. These
are distinct fixes to pre-existing upstream lifecycle defects, not HDR features or
upstream acceptance. 0074 adds unplug-with-reference and connector-move regressions.
Sol owned integration/native validation during this retry. The approved retry
is exactly 17 checks whose mocked-colord traffic changes; 25 native and 29 runner
histories retain their actual executing trees under Fable's two-tier decision.
**Actual required gate:** on `41605eb0`, `monitor-dbus-tests` failed in 2.59 seconds
with exit 245 after reconnect/HasExternalMonitor TRUE; the target-overrides case
passed, and no earlier fatal-colord warning was printed. The signal/root cause
is not established by this log. `color-management` passed all 20 cases, including
the new unplug-with-reference and connector-move regressions. The remaining 15
TEST-context checks did **not** run after the required gate failed. Raw ledger:
70 recorded passes, one failure; current-candidate validity: **55 passes, one
failure, 15 pending invalidated checks**, not acceptance. All 75 execution logs
are hash-verified; 69 histories are unchanged. See the
[gated retry evidence](../evidence/nativehdr10-validation-attempt3.json) and
[colord correction receipt](../evidence/nativehdr10-colord-corrections.json).
Opus `t_ef832f3b` delivered compiled corrections 0075–0077 at native
`de09d575` / tree `058bbf97`; Fable `t_c88207c7` approved them. Source analysis
identifies base async callbacks casting borrowed user data before cancellation
checks, made reachable by 0072; no core frame was observed. The corrections
check cancellation first and add an unplug-during-setup regression. Sol now
owns released native source/build/retry-ledger and Mac integration/evidence/status.
The same exact 17 checks required retry; color-management's `41605eb0` pass was
genuinely invalidated. Retain 25 native and 29 runner histories at their actual
executing trees under Fable's recorded source/equivalence decision. Canonical
full 77-patch replay gives tree equality; prefix 0001–0074 is unchanged and
three SHA256SUMS entries were deliberately appended for the reviewed corrections.

**Done (unit validation): all17 approved retries passed** on `058bbf97`, required
pair then dependent fifteen, same persistent ledger/frozen runner. Monitor-dbus
passed as a complete invocation; color-management passed21/21 cases including
unplug-during-setup. Every one of the **71 required unit checks** has a valid
pass:42 native invocations plus29 runner methods. All92 execution logs are
hash-verified;54 retained histories remain unchanged. See the
[final scoped retry evidence](../evidence/nativehdr10-validation-attempt4.json)
and [cancellation correction receipt](../evidence/nativehdr10-cancellation-corrections.json).
The wrapper returned1 only from an erroneous postcheck after both phases rc0 and
export; schema-aware independent verification confirmed all histories/hashes,
without test reexecution or frozen-runner edits. The final source bundle and
full evidence archive are preserved under owned `.peer-linux/deliverables`.

**Current handoff:** final repository integrity binds the final evidence/docs
commit in an external receipt at `.peer-linux/deliverables/final-integrity`,
avoiding receipt-in-tree circularity. Final-delivery `t_2b0d5704` verifies those
receipts and prepares the substantial PR without repeating successful units.
**Remaining:** no second candidate-wide batch. Separate optimization
`t_38887c3f` and base async lifetime assessment `t_3502f623` wait for delivery
and must not edit the frozen source/build. Publication and all later
qualification stages remain separate.
One substantial PR must declare its
dependency on the held PR 16. Ubuntu port (0062+) and packaging, physical
deployment, optical accuracy and Dolby Vision remain
separate qualification stages. No laptop or display configuration change is
authorized in this source batch.

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
owner then looked at it and reported that the image looks great; that is a
subjective check, not a measurement.

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

## Owner decisions (2026-10-11)

- The generally available Dolby Vision track is open, player-side
  RPU-aware display management validated against Dolby's reference renderer
  ([contract](OPEN_DV_DISPLAY_MANAGEMENT.md)). The OEM processor under Wine
  is a time-boxed experiment with a one-frame go/no-go.
- The owner will boot the laptop's Windows installation for a coordinated
  trace of the OEM Dolby pipeline (private results).
- KMS HDR metadata: run the on-screen comparison on `lab5`, then bound the
  composition and declare the display's own values if the comparison
  supports it.
- Upstream submission: yes, under the owner's identity, in slices, design
  discussions first.
- Measurement: a Calibrite ColorChecker Display Plus / X-Rite i1Display Pro
  Plus class colourimeter (supported by ArgyllCMS; not an "HL" model), plus
  one spectrophotometer session for a panel-specific correction, is the
  recommendation; purchase pending.
- A measured colour profile takes priority over EDID declarations.

## Decisions taken without the owner

Recorded for review; each can be revisited.

- Since the fifth batch, agent commits use `Claude Agent <claude-agent@invalid>`
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
