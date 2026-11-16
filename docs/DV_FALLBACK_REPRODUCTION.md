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

Results are pending. Raw journals, media identity and runtime state stay
private; public evidence contains software hashes and aggregate observations.
This is not optical calibration, full-film endurance, every-frame metadata
qualification or proof that the inherited event never occurred.
