# DV fallback reproduction — distinguish metadata loss from renderer state

Companion to [system playback](SYSTEM_DOLBY_VISION.md) and
[current status](STATUS.md). This records bounded normal-player attempts to
reproduce the inherited claim of DV loss after 6–24 seconds. Exact original
map/reset log timing has now been recovered; no timestamped persistent
fallback is established. The claim remains an investigation target, not an
established current defect or a repair claim.

## Original timing recovered — persistent fallback remains unproved

[The historical journal timeline](../evidence/dv-historical-journal-timeline-20261117.json)
was retrieved read-only on November 17 UTC (November 16 Eastern). This is new
analysis of retained software logs, not fresh playback or a physical
measurement. The two original cases occurred on November 13 UTC, equivalent
to November 12 Eastern. Intervals use same-boot journal monotonic timestamps;
each starts at that renderer's first successful-map diagnostic.

| Case | First map (UTC, November 13) | First reset after map | Outside-range recreation log after reset | Subsequent stale-fence 409 responses |
|---|---|---|---|---|
| A | 02:50:51.616889 | 23.864949 s | 1.577518 s | 9, then session ended/superseded |
| B | 02:52:23.096283 | 6.470154 s | 0.811647 s | 10, then session ended/superseded |

The original 6–24 seconds therefore describes first-map-to-reset intervals,
not observed fallback durations. Initial maps reported enhancement composition.
The reset diagnostic preceded the outside-range session-recreation log in both
cases. Message ordering does not locate the initiating seek/control action or
establish an inter-process cause. Launch and seek initiators, owner attendance
and owner visual observations are unverified.

No recovered record proves a server route change, spontaneous metadata loss
or persistent HDR10 base output. Successful-map return traces and displayed
frames were not recorded after reset; successful mapping can be silent. The
November 16 seek-spanning trace below independently demonstrates why the reset
message alone cannot establish persistent fallback.

The historical Player `0.5.0-1` identity comes from the inherited handoff, not
a new binary attestation. The separate run-wide control-sequence defect was
repaired in Player `0.5.1-1`, merged as Plurx PR 1577, landing `a4c316d0baac`:
sequence state binds to session/generation/epoch. The 105 affected tests and
required main lane recorded in [status](STATUS.md) are inherited source/test
qualification, not newly rerun checks. Actual outside-range OSC seeking and
session-replacement runtime acceptance remain unqualified. That boundary needs
control identity and mapper returns on one timeline. Read-only inspection of
the installed source (hashes in the receipt) shows that both seek handlers
bypass recreation for VOD; the OSC sends its film-seek message only outside
the held live-film range. A normal live-session route is therefore needed to
exercise replacement. Indexed direct-mpv VOD seeks do not qualify it, and no
forced DV capability is part of this diagnostic.

## Observe ordinary playback before changing a variable

Two title starts through the normal Plurx Player handoff were recorded in an
unlocked GNOME session. The launch initiator and physical attendance were not
verified; the earlier attribution to the owner is withdrawn. There is no
verified owner visual observation. A separate IPC client subscribes to native-target and
video-parameter changes, captures mpv diagnostics, and samples progress,
selected tracks, cache and drop counters at a requested 4 Hz. It does not
change capabilities, options, source, pause or seek during each three-minute
initial run. Application/provider journals are retained privately.

The bounded cases use delivered Profile 8 and Profile 7 streams. Input-profile
metadata, decoded Dolby colour representation, target eligibility and a
matching-generation successful map are recorded separately. The
`native-dovi-target-state.active` flag alone means physical-target eligibility,
not successful mapping of every frame. Quiet repeated-success logs and sampled
properties cannot prove every-frame RPU continuity.

Idle-window `active=false` before the first mapped picture is startup state. A
provider reset alone does not demonstrate sustained fallback. A spontaneous
loss would require time-correlated evidence during advancing playback, with
source/seek/target changes and owner observations kept distinct.

## Qualification remains bounded

[The November 16 receipt](../evidence/dv-fallback-reproduction-20261116.json)
records 180-second normal startup runs of delivered Profile 8 and Profile 7. After
the first matching successful map, 669/679 snapshots respectively retained
active generation 1 and decoded Dolby colour representation, covering
167.28/169.60 seconds. Both 6–24-second windows after that map contain 72
active snapshots. Reported renderer/decoder/delayed-frame drop counters stayed
at zero. Profile 7 initially logged enhancement composition; Profile 8 did not.

Two separate +60-second indexed seek controls reproduced the reset diagnostic.
The first appeared 0.383 seconds after the seek control was launched, without
a native-target generation or decoder-colour change. A later 20-second ABI
probe observed 483 completed mapped returns, but was too late to measure
immediate recovery. The final 45-second trace spanned the second seek: one
reset call in second 3, 1,077 positive-RPU-length/EL-composed entries and 1,075
completed mapped returns. There were no observed unsupported/error returns,
and every probe-elapsed full-second bucket 4–43, all after the seek, contained
mapped returns.
Counters are unpaired at probe boundaries; their difference is not a drop count.

The [project mapper ABI](../packaging/system-dv/include/dv_provider387.h) defines
return 1 as mapped, 0 as unsupported and −1 as error. This control is a
counterexample to inferring sustained HDR10 fallback from the reset message
alone. It does not establish mapping continuity in the original interval,
which has journal diagnostics but no mapper-return trace.
The named creative/CM29 gamut strategy is also distinct from HDR10 fallback.

Display configuration (apart from its generation serial), Night Light, boot
identity, mpv binary and kernel tracing policy are unchanged; measurement
services are inactive. The observed Player process was left running. No code repair,
forced capability, watchdog or package change is justified by this result.

Raw journals, media identity and runtime state stay private; public evidence
contains software hashes and aggregate observations.
This is not optical calibration, full-film endurance, every-frame metadata
qualification or proof that the inherited event never occurred.
