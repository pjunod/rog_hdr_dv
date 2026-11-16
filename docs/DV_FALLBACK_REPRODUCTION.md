# DV fallback reproduction — distinguish metadata loss from renderer state

Companion to [system playback](SYSTEM_DOLBY_VISION.md) and
[current status](STATUS.md). This records bounded normal-player attempts to
reproduce the inherited claim of DV loss after 6–24 seconds. The original
entry has no confirmed timestamped failure; it is an investigation target,
not an established current defect or a repair claim.

## Observe ordinary playback before changing a variable

The owner starts titles through the normal Plurx Player handoff in an unlocked
GNOME session. A separate read-only IPC client subscribes to native-target and
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
alone. It does not prove what happened in the original unrecorded interval.
The named creative/CM29 gamut strategy is also distinct from HDR10 fallback.

Display configuration (apart from its generation serial), Night Light, boot
identity, mpv binary and kernel tracing policy are unchanged; measurement
services are inactive. The user's Player is left running. No code repair,
forced capability, watchdog or package change is justified by this result.

Raw journals, media identity and runtime state stay private; public evidence
contains software hashes and aggregate observations.
This is not optical calibration, full-film endurance, every-frame metadata
qualification or proof that the inherited event never occurred.
