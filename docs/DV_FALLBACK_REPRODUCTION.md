# DV fallback reproduction — distinguish metadata loss from renderer state

Companion to [system playback](SYSTEM_DOLBY_VISION.md) and
[current status](STATUS.md). This records bounded normal-player attempts to
reproduce the inherited claim of DV loss after 6–24 seconds. Exact original
map/reset log timing has now been recovered; no timestamped persistent
fallback is established. The claim remains an investigation target, not an
established current defect or a repair claim.

## Profile 7 MEL — an identity enhancement layer declined by the mapper

[The November 26 UTC receipt](../evidence/mel-identity-el-20261125.json) records
an owner report on a newly downloaded Profile 7 title: no FEL pill and
"display mapper unavailable" in plurx Player 0.5.5 with mpv `+rogdv5.7`. An
attended probe found every mapper call made with the enhancement layer not
composed, and every call declined with "unsupported residual".

The file, the server route and mpv were each ruled out. The title has the same
dual-layer single-track layout as a working FEL title. A working FEL title was
served through the identical temporary live-HLS copy remux, and the remux and
the live segments kept every enhancement-layer and RPU unit. mpv's Profile 7
splitter paired every picture. The same decline occurred in an ordinary mpv
window from the original file and from the captured live bytes.

The title is **MEL**: its RPUs keep `disable_residual_flag=0` but carry an
identity linear dead-zone NLQ (zero offset, slope and threshold, `vdr_in_max`
of 1.0). libplacebo marks such a frame `nlq_active=false`, drops the bound
enhancement layer and reports it as not composed. The provider reads the raw
RPU, sees a residual that is not disabled, and requires a reconstructed
master. The identity residual is exactly zero for every enhancement-layer
code, so the base reshape already is that reconstruction; MEL carries its
Dolby Vision grade entirely in the RPU.

[Patch 0003](../patches/libplacebo-fel-system-dv/0003-report-an-identity-enhancement-layer-as-reconstructed.patch)
of `libplacebo-fel-system-dv` decides this from the frame's raw RPU, the bytes
the provider reads. When no enhancement layer was composed, it parses the RPU
with libdovi and reports the master as reconstructed only for an enabled
residual that is exactly zero: linear dead-zone NLQ with zero slope and
threshold in every component, and no reference to a previous RPU. Disabled
residuals, single-layer profiles and parse failures are unchanged, the
decision does not depend on whether the caller attached the layer, and a
build without libdovi warns once and keeps the previous behaviour. A first
version inferred the zero residual from `nlq_active`; independent review
showed that is unsafe for callers that fill the metadata themselves, so it
was replaced. With the installed mpv selecting each library, two independent
MEL titles changed from declined to mapped with the enhancement layer
composed, and a MEL frame with mpv's enhancement layer suppressed was
pixel-identical to the frame with it. A FEL title, the same FEL title with
its layer suppressed (still declined), an HDR10 title and a Profile 8 title
(still not composed) gave pixel-identical window screenshots to the stock
rebuild, which itself matched the installed library.

Because mpv, the provider, the GTK Dolby plugin, its GStreamer sinks and
Showtime pin exact versions, the release carries libplacebo-rog387 `-3` and
six metadata-only `+depfix1` repacks with byte-identical contents. It was
installed on the ROG with the release tooling (seven changes, no removals;
audit and verify clean). In the owner's attended check the MEL title showed
the mapper active and the FEL pill on, with a mapped, enhancement-layer-
composed frame in the player log.

Limits: digital decisions and paused single-frame pixels, not continuous
playback or light. The server still labels an MEL title FEL.

### The GTK Dolby plugin (Showtime, browser)

Up to `0.1.0+rogdv10` the GTK Dolby mapper declined every Profile 7 picture
whose NLQ was inactive before libplacebo saw it ("matched enhancement planes
or NLQ unavailable"), so an MEL title lost the mapping in Showtime and the
browser even with libplacebo `-3`. `0.1.0+rogdv11` stops deciding this
itself: it uploads the enhancement layer only for an active NLQ, the only
case the renderer samples one, and passes the picture and raw RPU on. The
renderer reports whether the master is reconstructed (patch 0003), and the
mapper's provider callback still maps a Profile 7 picture only when it does,
now naming that decline ("renderer did not reconstruct the Profile 7
master"). FEL pictures (active NLQ) and single-layer Profile 5 and 8
pictures take the unchanged path.

[The GTK receipt](../evidence/gtk-dovi-mel-20261125.json) records the
build (warnings as errors; negotiation probe 169 checks, 0 failures) and
Showtime runs selecting the built library without installing it. Two MEL
titles changed from declined to mapped with the master reconstructed. A FEL
title mapped as before, and an HDR10 title never reached the provider in
either build. The core, plugin, GTK sink, Showtime, libplacebo, the
provider and mpv pin each other exactly, so the release is one
seven-package transaction. It carries the rebuilt core and plugin, which now
depend on libplacebo-rog387 `-3` or later, and metadata-only repacks with
unchanged files. The sink and Showtime repacks (`+depfix2`) carry the new
pins. libplacebo `-4`, provider `+depfix2` and mpv `+depfix2` restore the
`shlibs` files that the `-3`/`+depfix1` repacks left empty.

Limits: mapper decisions, not pixels or light; the browser was not run.
Both full MEL files fail to start in Showtime with either build, for a
separate reason. Each selects a PGS subtitle track by default (cause and fix
in the next section). The runs therefore used video-only copies, with a
first build made against `-3` through a container-only `shlibs` override.
The final build against `-4` differs only in packaging metadata. After
the owner-attended install of the seven-package release, the same runs on
the installed packages, with no library path override, gave the same
decisions: both MEL titles mapped (652 and 654 frames), the FEL title
mapped (657) and the HDR10 title never reached the provider. MEL title B and the FEL title each
showed the same one-time startup decline before mapping, in both runs.

### Subtitles with NVDEC-decoded Dolby video in Showtime

When a Dolby title's default subtitle track is PGS, playsink inserts its
subtitle overlay with `dvdspu`. The NVDEC decoder has already chosen CUDA
memory: bad series patch 0015 asks downstream with the stream's Dolby-marked
caps, and the GTK Dolby mapper accepts marked native input. Up to plugins-bad
`+rogdv10`, `dvdspu` then decided whether downstream takes its overlay
metadata by intersecting an unfiltered peer caps answer with its own caps.
The mapper's accepted input depends on stream fields that only a filter
carries, so its unfiltered answer held identity memory only. `dvdspu` found no
CUDA memory with the overlay meta ("caps have dvdspu meta 0"), refused the
caps and renegotiated forever. Playback never started and no error was
posted.

[Patch 0019](../patches/ubuntu-gst-plugins-bad-rpu/0019-subtitle-renderers-ask-downstream-with-the-overlay-caps-as-filter.patch)
makes `dvdspu`, `assrender` and `dvbsuboverlay` pass their overlay caps as the
filter and test the answer for emptiness, as `textoverlay` (plugins-base)
already does. For a peer that follows the caps-query rules the decision is
the same by construction; only the PGS path was run. The mapper then answers through its marked-filter path and offers
CUDA memory with the overlay meta. Changing the mapper's unfiltered answer
instead was tried and dropped. Unmarked native memory there would mislead
unmarked producers. Marked memory needs the stream configuration, which
Showtime's playback does not carry on its stream-start event.

[The subtitle receipt](../evidence/showtime-pgs-subtitles-20261126.json)
records Showtime runs on full files with the patched plugins loaded from the
built package and the installed mapper. Both MEL titles changed from never
starting to mapped. A FEL title without a default subtitle track and an
HDR10 title with one played as before. The release, installed on the ROG
in an owner-attended window, holds the five installed plugins-bad binaries at `+rogdv11` and a metadata-only Showtime
repack (`+depfix3`) carrying their exact pins. The installed `rogdv10` holds a
paused-subtitle change that this repository's series does not, so `rogdv11`
was built from that installed source plus patch 0019.

Limits: negotiation and mapper decisions, not pixels. No run measured a
drawn subtitle; the owner reported seeing subtitles over the second MEL
title after the install (a visual report). ASS and DVB
subtitles, the browser and plurx Player were not run.

## Owner-attended session re-creation — the EL pill, not the mapping

[The November 25 UTC receipt](../evidence/dv-owner-recreation-el-pill-20261125.json)
records an owner-attended Dolby Vision play in plurx Player 0.5.3-1 with the
installed mpv `+rogdv5.5`. The owner reported "all enhancements (FEL, RPU, DYN
pills)" for a few minutes, then, after seeking forward 30 seconds, "FEL no longer
shows as active, only RPU and DYN". The seek was outside the live session, and
the player re-created it. A read-only IPC recorder sampled
`native-dovi-target-state` as active generation 1 before and after the
re-creation's `start-file`. Decoded colour stayed Dolby Vision/PQ, and every
drop counter stayed zero. The provider logged its reset diagnostic 2.85 seconds
after the re-creation and no later mapped-frame diagnostic. Because the
generation stayed 1 on every sample, that reset line most likely came from the
reset branch at the stream change rather than a sustained absence of RPU.

The first-map diagnostic reported `EL composed=1`, so a dual-layer stream
reached mpv: the server's native route, on which the server's route code never
marks FEL active. On that route the overlay can draw only its local EL pill, so the
owner's "FEL" is most likely that pill. The recorder did not capture the
overlay's input, so FEL versus EL is inferred from the code path, not
observed. The EL pill needs the player's renderer facts, while RPU and DYN need
only Dolby decoding. The player clears those facts
at `start-file` and restores them from the VO's physical-target success record
whose generation matches the property. This follows the property's rule that a
source change requires a fresh record. [Patch 0002](../patches/mpv-fel-system-dv/0002-target-the-physical-display-and-retain-cached-PQ-signals.patch)
logged that record once per render generation, and a re-created session keeps
generation 1, so no fresh record followed.

No mapper probe ran in this window, so mapping continuity here is not
measured. The separately measured November 17 replacement trial below recorded
187 enhancement-layer-composed mapped returns after an actual replacement on
the same route. [Patch 0010](../patches/mpv-fel-system-dv/0010-log-a-fresh-Dolby-success-record-after-each-reset.patch)
logs the record again after each frame-queue reset (seek, new file or refill), on the first successful
private map. A reset after which mapping stays inactive still logs nothing.

Limits: the recorder captured neither the overlay's input property, the
selected track's Dolby profile nor the mpv log stream. No mapper probe ran
during this window, and the host carried heavy concurrent build load. The
owner's report covers the pills, not a measured picture. Patch 0010 is
installed in mpv `+rogdv5.6` ([install receipt](../evidence/mpv-rogdv56-install-20261125.json)). In
the owner's attended re-check, a session re-created by a seek kept the EL pill. The earlier unexplained loss reports below also
followed outside-range re-creation. This mechanism may account for them, but
that is not established. The success record attests a successful private
map, not enhancement-layer composition, and it is edge-triggered: an
enhancement-layer-only loss with mapping still succeeding would not clear the
EL pill. Patch 0011 adds a level-triggered composition field to
`native-dovi-target-state`, installed in mpv `+rogdv5.7`
([install receipt](../evidence/mpv-rogdv57-install-20261125.json)), and
plurx Player's EL pill reads it.

**Direct check, November 25 UTC.** [A second owner-attended run](../evidence/dv-owner-recreation-probe-20261125.json)
repeated one outside-session seek on the installed `+rogdv5.5` with the
PID-scoped mapper probe, and also recorded the overlay's input. Every mapper
return before the seek and after re-creation was "mapped" with the enhancement
layer composed and RPU present: 24 per full second, including every full second
67–80 s of probe time after re-creation. Apart from the probe's own startup,
there was one provider reset, after the seek, and no unsupported or error
returns. The
overlay's renderer record was present before the seek and stayed `null` after
re-creation, and the generation stayed 1. The owner again saw no enhancement-layer
pill. Mapping and composition therefore continued, and only the player's
renderer record, and with it the EL pill, was lost. That is the mechanism patch
0010 addresses. Limits: about 15 seconds after the seek, on the unfixed build,
without an optical measurement. The owner also noted about 14 seconds from the
seek to the first new frame; that latency is separate and not investigated here.

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
qualification, not newly rerun checks. The November 17 normal live trial below
adds one bounded actual OSC replacement observation with direct control
receipts and time-aligned mapper returns. Read-only inspection of
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

## Normal quality round trip — live boundary unexercised

[The November 17 UTC receipt](../evidence/dv-normal-route-boundary-20261117.json)
(November 16 Eastern) records a fresh, bounded normal-route check. After the
operator explicitly confirmed unlock, the agent activated the existing Chrome
Resume accessibility action. This launch is agent-attributed; no owner visual
attendance or acceptance is asserted. A preceding unlock-wait timeout is
retained separately and is not counted as a playback attempt.

The 180-second Profile 7 startup produced 715 samples. The initial mapping
journal reports target 616 and enhancement composition. After that first map,
635 emitted samples had Dolby decoder representation; 634 had active target
generation 1. One transition snapshot reported an inactive generation
0 target beside Dolby decoder data: property reads are sequential, so this is
not an atomic state observation or proof of sustained fallback. From the first
active sample onward all 634 snapshots retained active generation 1. The
6–24-second window after first map contains 72 active samples. All 635 valid
post-map renderer/decoder/delayed-frame drop-counter samples were zero. First
and last numeric positions were 375.417 and 533.950 seconds. Initial null and
inactive startup values remain separate from sustained playback observations.

The agent then used the normal `cinema-quality` controls over IPC, not pointer
clicks. The initial Auto remux/HLS route had no live film metadata; its null
presentation session field alone does not establish live mode. Selecting 1080
settled as transcode/HLS/VOD with BT.709 decoder representation and inactive
target generation 2. Returning to Auto settled as remux/HLS/VOD, Dolby decoder
representation and active generation 3. No numeric live-film origin/duration
was advertised in either observer run. The helper therefore issued no
`osc-film-seek`: that VOD trial did not qualify live outside-range replacement.
Intentional transcoding is not evidence of spontaneous DV loss.

A concurrent PID-scoped mapper probe with a configured 150-second lifetime
recorded 50 positive-RPU/EL1 entries and 50 completed mapped returns, with no
observed unsupported/error returns, plus 71 resets. Mapped returns occurred in probe buckets 0/1 and 22/23;
resets in buckets 18–22 overlapped intentional transcode, restoration and
cleanup. Counts are unpaired callback observations, not displayed-frame or
frame-drop counts. The BPF origin numerically aligns with recorded boottime,
not Python monotonic time; quality selection was 0.253 seconds after that
origin. Buckets start at BPF BEGIN and cannot be read as seconds after a control.
The owned Player quit about 23.374 seconds after probe BEGIN; remaining trace
walltime after process exit supplies no playback coverage.

The helper's legacy SQLite database poll is excluded from all conclusions: it
read an unused old store after production migrated to Hiqlite. Neither empty
results nor recorded bindings supply authoritative session, epoch or sequence
evidence. A separate bounded query of current Hiqlite telemetry recorded three
session starts, three session ends, three start attempts and one native-mapper
event. Those counts contain no control generation/epoch/sequence acceptance
receipt. There is no new runtime qualification of the previously repaired
control-sequence defect.

Auto restoration was observed settled before cleanup. The ordinary indexed
cleanup seek to 375.417 seconds was accepted, then immediately followed by the
agent's quit request; exact restored position and persisted watch position were
not independently verified. Postflight confirms byte-identical preferences,
no remaining Player/ffmpeg processes and inactive measurement units. Remote
staging was removed after archive verification; the idle inhibitor was released.
The second observer ended after 23.107 seconds with
91 samples and `ipc_closed`/exit 1 because the owned Player quit; this is neither
a test pass nor a failed live-mapping result. No production fix is justified.

## Actual live OSC replacement — one bounded control acceptance

[The November 17 live-replacement receipt](../evidence/dv-live-session-replacement-20261117.json)
records a fresh normal-route trial at 15:34–15:36 UTC (also November 17 Eastern).
The agent opened an ordinary catalog window and activated its standard Play
button. Fresh server records report three `vod_index_pending` fallback events
across initial play, main replacement and cleanup. Authoritative Hiqlite route
rows report `vod=false`; the Player advertises live film origin 0 and duration
11707.744 seconds, with advancing Dolby decoder state. No quality/settings
change, forced capability, index deletion or synthetic handoff selected the
route. The earlier index census is separate from this fresh route evidence.

The agent moved mpv's mouse to the actual Cinema timeline, waited 0.3 seconds,
then issued an ordinary left-button single click. This executes the installed
Lua hit test and its normal outside-range handler; the main gesture was not a
direct `osc-film-seek` injection. The expected midpoint was 5853.872 seconds;
the new session's actual film origin was 5853.639 seconds.

A passive capture retained whitelisted control fields without writing raw
packets, HTTP headers or bodies. Symbolic bindings below replace all private
session and client identifiers. All 18 requests paired with HTTP 200 responses;
every accepted sequence equals its request, with matching protocol, control
generation and epoch. One client identity persisted across all three bindings.

| Binding | Normal operation | Accepted sequences | Control epoch |
|---|---|---|---|
| A | Initial live playback | 1–4 | 1 |
| B | Actual OSC outside-range replacement | 1–7 | 1 |
| C | Cleanup seek replacement | 1–7 | 1 |

The session and control generation changed at replacement; epoch 1 did not
need to change. Each binding's first normal response directly accepted
sequence 1. The helper observed B's first acceptance at 15:34:55 UTC, then
sequences 2–6 during its 30.0579-second control window, with no captured 409.
The completed capture also contains B7: its packet UTC precedes the helper's
cutoff, but processing emitted that record about 0.530 seconds after the
cutoff. Packet time and processing time are distinct. No observer-generated
HTTP control POSTs were sent. Tcpdump reports 17,530 captured packets, 35,138
received by the filter and zero kernel drops; those tool counters are not used
to infer a packet-loss ratio here. No known
incomplete control messages were reported.

Playback recovery was slow despite prompt control acceptance. Initial Play to
first mapping took 18.951 seconds. For the main replacement, sequence 1 was
accepted on the wire about 4.190 seconds after the click, but the earliest
mapped-return bucket bounds resumption to 26.194–27.194 seconds after that
click. The first new-origin active-Dolby snapshot arrived after 27.083 seconds:
22.893 seconds after the response packet's UTC, or 22.464 seconds after the
helper observed that acceptance on its monotonic clock. Packet capture,
processing and helper-observation clocks are kept distinct in the receipt.
This characterizes recovery latency; it does not establish its cause or accept
it as low-latency playback UX.

Retained diagnostics narrow most of the observed delay to stream opening:
`curl Opening` appears at +1.161 seconds, first MIME type at +26.711,
demux/stream-info work at +26.712–26.743, decoder setup at +26.745–26.892,
first shown frame at +26.993 and completed restart at +26.996. These are
observer receipt timestamps and log ordering, which may be buffered. They are
not wire time-to-first-byte or proof of unavailable server bytes; the underlying
cause is not isolated, and the long interval is not demonstrated to be spent
in client probing, decoding or mapping.

This control window is not 30 seconds of continuous DV progression. Fifteen
later snapshots span 7.594 seconds, with active physical target generation 1,
Dolby decoder representation and film position 5854.598→5862.064 seconds
(+7.466 seconds). Physical-target generation and control-generation identity
are separate facts. The project-provider ABI probe recorded 215 positive-RPU/
EL1 entries and 215 mapped returns: 26 in early buckets 17–18, 187 after main
replacement in buckets 45–53, and two after cleanup seeking in bucket 59.
Four resets accompanied startup/replacement/cleanup; no unsupported/error
return was observed. These are unpaired callback counts, not frame counts or
proof of displayed output. Buckets start at BPF BEGIN and numerically align
with recorded boottime, not Python monotonic time. The configured 180-second
probe lifetime is not playback coverage; the owned Player and probe stopped
with the bounded helper.

The primary helper did **not** satisfy its paused/stable/watch-near-zero cleanup
criterion within 35 seconds. That result is retained. Follow-up normal UI
`Mark watched` then `Mark unwatched` verified zero position and unwatched state
and closed only the task-owned page. This is a semantic UI reset: the initially
absent watch row was not restored to absence, and a new zero-position row
exists. Preferences remained byte-identical; postflight found no Player or
ffmpeg processes, the runner was inactive and the idle inhibitor was released.
The observer ended with `ipc_closed` when the owned Player quit; capture ended
on deliberate interruption. Those exit statuses are not new test results.

This adds one bounded runtime acceptance for Player 0.5.1's already-merged
sequence repair. Its inherited source tests were not rerun. The original
spontaneous 6–24-second DV-loss claim remains unreproduced, and no new production
fix follows. No owner physical attendance, visual acceptance, full-film
continuity, every-frame mapping or optical accuracy is claimed. A separate
failed unlock wait is retained without counting it as a playback trial.

Raw journals, media identity and runtime state stay private; public evidence
contains software hashes and aggregate observations.
This is not optical calibration, full-film endurance, every-frame metadata
qualification or proof that the inherited event never occurred.
