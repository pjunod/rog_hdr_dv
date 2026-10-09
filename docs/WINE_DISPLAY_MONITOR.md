# Wine DisplayMonitor — truthful monitor discovery for processor activation

**Status:** implementation and compiler qualification in progress; runtime
qualification has not started. **Date:** 2026-10-09.

The [activation experiment](DOLBY_ACTIVATION_PROBE.md#wine-11-follow-up--the-dll-loads-displaymonitor-activation-is-missing)
loaded the exact OEM Dolby component, then stopped when it requested the
Windows `DisplayMonitor` runtime class. This is a demonstrated prerequisite,
not proof that implementing this class will complete Dolby activation.

## Contract and responsibility

Implement the ordinary Windows API in Wine, backed by real monitor topology
and descriptors. Keep the OEM component outside the implementation and its
tests. Do not fabricate monitor IDs, a Dolby capability, package identity or
licensing state to make a particular caller proceed.

The observed interface is `IDisplayMonitorStatics`, IID
`6eae698f-a228-4c05-821d-b695d667de8e`. Its
[pinned SDK declaration](https://github.com/microsoft/win32metadata/blob/b07213e28bcc48221c155024f9c5e0e1a92c6497/generation/WinSDK/RecompiledIdlHeaders/winrt/windows.devices.display.idl)
and [Microsoft class documentation](https://learn.microsoft.com/en-us/uwp/api/windows.devices.display.displaymonitor)
define the three statics: device selector, asynchronous creation by device ID,
and asynchronous creation by device-interface ID. The two identifiers are
different forms; neither is an arbitrary display name or a new identity scheme.

| Owner | Required source of truth |
|---|---|
| Display backend | Facts it can actually obtain, with provenance and validity independent of field values. |
| win32u monitor inventory | Existing monitor nodes, adapter LUID, output ID and interface links; consistent DisplayConfig reporting. |
| SetupAPI / device enumeration | Existing monitor interface discovery and identifier resolution. |
| WinRT component | Standard registration, COM lifetime, async completion and immutable returned descriptor data. |

## Shared topology and connector facts

Before this change, `QueryDisplayConfig` hard-codes external DisplayPort while
`DisplayConfigGetDeviceInfo(GET_TARGET_NAME)` hard-codes internal display for
the same monitor. A new consumer cannot safely interpret either answer as
hardware evidence. Both must read one shared, validated value.

An internal typed payload records provider origin, connector technology and
an explicit connector-valid bit. Zero initialization means unknown: numeric
zero is also the Windows value for HD15, so the value alone cannot establish
validity. Missing or malformed optional registry payloads remain unknown.
Legacy providers must continue functioning without a manufactured connector.

Known Wine-generated fallback monitors may be marked virtual. An ordinary
Wayland output without EDID is not thereby virtual, internal or Dolby-capable.
Display-server provenance identifies where information came from; it does not
prove that a monitor is physical. XRandR's typed `ConnectorType` property may
supply a recognized technology; output-name prefixes do not establish one.

Changing `gdi_monitor` changes the internal driver ABI. The candidate bumps
that ABI and must be deployed with matching source-built win32u and applicable
driver PE/Unix components. A runtime assembled with stale packaged drivers is
not valid evidence for this change.

## WinRT object and descriptor handling

Use the normal `windows.devices.display` component and registration. Implement
all three statics with standard agile COM identity and reference ownership.
The selector identifies monitor interfaces; creation resolves through the
same SetupAPI inventory instead of synthesizing an unrelated list. Handle
device removal between discovery and asynchronous completion explicitly.

Provide only descriptor-backed physical properties. Keep current desktop
mode, logical dimensions and scale separate from native pixel resolution and
physical size. Descriptor retrieval returns an owned bounded copy of the
actual descriptor. Validate type, length and extension completeness; never
substitute a hand-written EDID for missing data. XRandR retrieval must not
silently accept a truncated extension list.

Nullable physical size may represent absence directly. Some scalar getter
behaviour for missing descriptors is not fully specified in the public API
documentation; retain this as a native-Windows qualification gap. Provisional
unsupported/error handling must be explicit and testable, without guessed
sizes, primaries or luminance values.

Do not expose `IDisplayMonitor2` merely because HDR works.
[Microsoft describes its Dolby property](https://learn.microsoft.com/en-us/uwp/api/windows.devices.display.displaymonitor.isdolbyvisionsupportedinhdrmode)
as monitor metadata indicating a particular Dolby treatment of HDR. Generic
PQ support, an installed DLL and an OEM profile's presence do not establish
that property or its backend provenance.

## Qualification sequence

The compiler baseline is the qualified Wine 11 file-API source
`68c5cce867c8c5dc7e318eefc4c13f832d0471fa`. Before edits, native amd64 builds
passed with warnings as errors and both X11 and Wayland positively enabled.
Affected targets include win32u, user32, SetupAPI, cfgmgr32, device enumeration
and both display drivers. A missing build dependency was corrected inside the
owned compiler environment before this baseline was accepted.

Compile each coherent implementation slice, including its test binaries.
When the complete candidate is ready, obtain adversarial review, address
findings, then execute the affected fast lane once:

- COM identity, factory interfaces, agility, ownership and async lifetimes.
- Selector discovery against independent SetupAPI enumeration, both identifier
  forms, invalid identifiers and removal races.
- DisplayConfig agreement, explicit unknowns and genuine synthetic-origin
  handling; no absent-EDID inference about physicality.
- Valid, malformed and truncated descriptors; unavailable physical properties
  and copies that remain valid after object destruction.
- Previous file-API regression where dependency changes invalidate its earlier
  runtime receipt; preserve unaffected passing evidence otherwise.

Pin source trees, compiled modules and loaded paths/hashes. Keep raw monitor
enumeration and loader logs private; public receipts contain sanitized facts.
Run no OEM component as part of the ordinary regression suite. A later bounded
activation experiment is a separate operation with its own exact inputs and
isolation checks.

## Remaining processor boundary

A working monitor API may only reveal the next missing dependency. Dolby
object creation, supported formats, frame/metadata transport, panel-profile
consumption and display management each need separate evidence. Wayland's
available monitor information also remains narrower than raw physical DRM
descriptors; no connector association may be guessed to fill that gap.
The native decoder route remains open in the
[full Dolby Vision plan](DOLBY_VISION_AND_QUALITY.md#42-native-decoder-integration-has-a-public-interface-example).
