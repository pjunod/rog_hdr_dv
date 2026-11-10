# ThinkPad X1 Carbon Gen 6 — inspection and native-gamma HDR plan

**Status:** stage 1 read-only inspection closed; implementation and installation
pending · **Inspected:** 2026-11-09 · **Owner:** coordinator for design and
integration; delegated implementation only after the contract is frozen.

Companion to [Status](STATUS.md), which keeps the ROG deployment ledger, and
[display target sources](DISPLAY_TARGET_SOURCES.md), which separates encoding
from physical display targets. This document records the ThinkPad's evidence
and the acceptance needed before a native-gamma HDR implementation can ship.
Follow [measurement-driven development](MEASUREMENT_DRIVEN_DEVELOPMENT.md)
for reference comparisons and [panel measurement](PANEL_MEASUREMENT.md) for
optical claims. No ThinkPad display changes or candidate installations are
claimed here.

## 1. Inspection closed; HDR output remains unimplemented

The inspected machine is a ThinkPad X1 Carbon Gen 6 with an Intel i7-8650U,
16 GB RAM and UHD 620 graphics. Its AU Optronics B140QAN02.0 panel reports
AUO2036. Ubuntu runs the stock generic kernel package `7.3.0-10.10` and
`libmutter` `51.0-1ubuntu3`, the exact Ubuntu source base shared by the
compositor work. No compiler toolchain is installed on this machine yet.
Build preparation remains a separate prerequisite to source implementation.

| Boundary | Read-only observation | What it establishes |
|---|---|---|
| Intel scanout | i915 Gen 9, DDI A, internal eDP, 8 bits per colour | This output needs an eight-bit precision and dithering qualification |
| EDID | Gamma 2.2 and wide-gamut chromaticities; no EDID HDR declaration | Native panel encoding is not established as PQ |
| DRM/KMS | No `HDR_OUTPUT_METADATA` property on this connector | A standard HDR metadata route is not available on this observed output |
| GNOME | Colour modes 0 and 2 available; native wide-gamut SDR mode 2 supported; no HDR mode 1 | Native gamut is usable for SDR; this is not an enabled HDR output |
| Installed software | Stock Ubuntu kernel and compositor | ROG package deployment and its acceptance do not transfer to this machine |

The closed inspection stage identifies the missing contract. It does not close
HDR, Dolby Vision, GPU rendering, visual acceptance or optical calibration.
The owner has no meter, so optical calibration remains open.

## 2. Cached Windows records explain the OEM association, not runtime state

Read-only inspection of the original Windows installation found cached
LEN40AE monitor records. Their model timing and chromaticities match the
panel model. The linked monitor driver sections identify
`TPLCDWQHDF_40AE.Install`, with versions `6.14.21` and `6.14.24`, and associate
`TPLCD_40AE_SDR.icm`. A `DisplayHdrLevel` value is present. No AUO2036 monitor
entry was found in the selected current control set.

These are cached SYSTEM records. Neither record proves which instance a
normal Windows session would bind today. Valid EDID checksums and a matching
timing do not establish an active runtime association. A cached 256-byte
record can contain a zero trailing block while declaring zero extensions;
its length alone is not an HDR extension.

The OEM Dolby Vision ICC contains an opaque private `DVB1` payload. Its
luminance tag value of 80 is not a physical 500 cd/m² peak measurement. Keep
ICC white, physical backlight capacity and Dolby target selection separate.
No private tag schema or Dolby configuration semantics were established by
this inspection. Vendor payloads were not executed or disassembled.

Lenovo's [platform specification](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_X1_Carbon_6th_Gen/ThinkPad_X1_Carbon_6th_Gen_Spec.PDF)
lists the optional Dolby Vision WQHD display at a nominal 500 cd/m² and
1500:1 contrast. Those are OEM specifications, not optical measurements of
this panel at its present brightness. The generation-specific
[monitor INF package](https://support.lenovo.com/us/en/downloads/ds502150)
and [Display Optimizer package](https://support.lenovo.com/us/en/downloads/ds506367)
are relevant provenance. Lenovo describes legacy Dolby Vision's dependency
on the enabled monitor driver, application and certified display in
[its compatibility guidance](https://support.lenovo.com/us/en/solutions/ht510052).
A current download's product-page breadcrumb alone does not establish
compatibility with this generation.

**Next evidence:** trace the original installation through normal Windows
operation, with the owner coordinating boot and recovery. Establish the
runtime monitor binding, active driver/profile, ordinary Dolby playback and
backlight behaviour before choosing Linux output policy. Use supported tools
through normal operation; retain vendor files and detailed captures privately.

## 3. Keep physical peak, SDR white and grade peak independent

The proposed route renders HDR content into the panel's native gamma encoding.
It does not require the panel to accept PQ. Three independent quantities need
explicit provenance:

| Symbol | Meaning | Evidence still required |
|---|---|---|
| `P(b)` | Physical peak capacity at backlight setting `b` | Normal Windows/backlight tracing first; optical measurement for calibrated values |
| `W` | Selected SDR reference white in cd/m² | Correct compositor and client reference anchors at every supported setting |
| `T` | Dolby/HDR destination grade peak in cd/m² | Target policy bounded by available physical capacity, separately from `W` |

An ideal zero-black gamma-2.2 display at `P(b) = 500 cd/m²` would encode a
physical luminance `L` as `(L / 500)^(1 / 2.2)`. This is a **public
mathematical illustration**, using the inspected gamma and OEM nominal peak;
it is not a fitted panel response or an accepted implementation equation.

| Physical luminance | Ideal native signal |
|---|---|
| 500 cd/m² | 1.0000 |
| 203 cd/m² | 0.6638 |
| 80 cd/m² | 0.4347 |

With `W = 203 cd/m²`, SDR white therefore sits below the nominal peak. That
illustration does not make arbitrary `W` work: every normalization and
reference-white anchor must remain consistent when `W`, `T` or `b` changes.
Black offset, actual transfer response, brightness scaling and temporal
behaviour remain unmeasured. A nominal 500 target is an explicitly labelled
OEM assumption until qualified; it must not become a calibration claim.

## 4. Client transport and native scanout have separate contracts

Prefer the existing client PQ transport when it can describe the submitted
pixels truthfully. PQ transport between an application and the compositor
does not imply PQ encoding on the eDP link. The compositor must convert the
submitted picture to the native panel gamut and gamma exactly once.

Client mastering/target gamut, luminance units and reference-white anchors
must describe the actual grade. A display-mapped client picture must not
receive a second tone map or gamut compression because transport metadata
accidentally describes the original master. Conversely, metadata must not
suppress a required conversion. Reuse the existing
[physical target feedback](MUTTER_TARGET_LUMINANCE.md) and
[view target ownership](GDK_DISPLAY_TARGET.md) contracts where applicable,
then qualify their native-gamma boundary explicitly.

A target change during pause needs an immutable target generation and a
retained source-picture lease, so the original picture can be regraded for
the new target. Returning to the original target must recover the original
digital result. Reusing already mapped pixels cannot establish that property.
Eight-bit scanout also requires a demonstrated dithering policy; decoding or
mapping in higher precision alone does not prove precision at the panel.

## 5. Acceptance proceeds from tracing to GPU qualification to installation

| Stage | Required result before advancing | State on 2026-11-09 |
|---|---|---|
| 1. Read-only inspection | Identify Linux output limitations and cached OEM association, with evidence limits stated | Closed |
| 2. Windows and backlight trace | Observe normal runtime binding and Dolby behaviour; separate `P(b)`, `W` and `T` provenance | Pending |
| 3. Source contract and compiler loop | Freeze native-gamma/reference-anchor policy and establish the exact Ubuntu build loop | Pending |
| 4. Synthetic Mutter controls | Verify SDR white, HDR headroom, gamut, target generations, pause/source lifetime and eight-bit dithering, including absent/invalid target controls | Pending |
| 5. Actual ThinkPad GPU qualification | Exercise native output, genuine Dolby grade, truthful transport, paused retargeting and ordinary SDR fallback on this GPU | Pending |
| 6. Package and recovery qualification | Rehearse exact upgrade/rollback and coordinate an owner-attended display test window | Pending |
| 7. Installation and acceptance | Verify installed versions, normal session behaviour and bounded visual acceptance | Pending |
| 8. Optical calibration | Measure peak/black, gamut, transfer response and brightness dependence with a meter | Pending; no meter |

Digital checks can establish consistency with an explicitly declared OEM
nominal target and correct software transformations. They cannot establish
physical peak, calibrated colour accuracy or Dolby certification. Freeze any
measured model before held-out acceptance under the standing reference method.
Historical ROG receipts remain scoped to their original machine and output.

## 6. Guardrails preserve evidence and recovery

Do not force PQ capability flags, invent EDID HDR metadata or transplant the
ROG OLED target. Those actions would bypass the native-gamma contract rather
than demonstrate it. Do not install a compositor, select a kernel, restart a
session or change a display profile as part of an inspection or repository
check. Preserve stock recovery and coordinate any later live display window.

Keep OEM profiles, binaries, hashes, raw captures, private helper output,
unique device identifiers and access details out of this public repository.
This ledger carries sanitized conclusions and primary references only. Source
implementation has not been completed, and no ThinkPad HDR or Dolby Vision
installation is claimed.
