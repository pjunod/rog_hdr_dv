# Linux audio quality — speakers, latency and Dolby Atmos

**Status:** hardware inspected and matching OEM tuning recovered; offline
build contracts ready, physical audio qualification pending ·
**Written:** 2026-10-12.

Companion to [hardware](HARDWARE.md), [status](STATUS.md) and
[operations](OPERATIONS.md). The owner prioritises built-in speakers and
everyday media. Use the available M4 Air as the primary macOS reference and
the M3 Max as secondary. The owner also has a Sonos Arc connected by eARC;
the TV model and its passthrough capabilities still need inspection.

Work through the milestones below. Read-only inventory is recorded in [audio hardware](AUDIO_HARDWARE.md); the
detailed [implementation plan](AUDIO_IMPLEMENTATION.md) controls build order.
Sonos Arc work is last, after internal audio and host Atmos. For live changes, coordinate playback, service restarts and profile activation. This
plan does not install anything. Plurx-specific changes stay in Plurx.

## 1. Define macOS-level audio as measured outcomes

The objective is clear, balanced speaker playback; responsive sound; reliable
calls and device switching; correct spatial playback where supported; and
predictable volume without excessive battery cost. Matching a brand name or
buffer setting is not acceptance. Different speaker enclosures impose
different physical limits, so compare both listening quality and measurements.

| Priority | Outcome | Evidence required |
|---|---|---|
| First | Full intended speaker operation and useful tonal balance | Codec/amp/firmware inventory, channel mapping, level-matched listening and acoustic measurements |
| First | Responsive everyday playback | Physical onset latency, idle wake-up delay, A/V sync and no cut-off beginnings |
| First | Stable daily use | Browser/player/calls, AC/battery, load, hotplug, suspend/resume, volume/mute persistence |
| Second | Lower wired latency | Physical round-trip and event-to-output results, with CPU/power and error counts |
| Last | Atmos on Sonos Arc | Known Atmos source reaches Arc intact over the verified TV/eARC chain |
| Research | Atmos on laptop/headphones | Object-aware decoding and appropriate renderer, with source-bound reference comparisons |

**Evidence boundaries:** ASUS specifications describe intended hardware.
Project READMEs describe candidate capabilities. Neither alone proves what this unit runs. The [audio inventory
receipt](../evidence/audio-inventory-2026-10-12.json) now records actual
read-only hardware/configuration findings. No listening, acoustic or Mac
latency results have been obtained.

## 2. Inspect the actual speaker path before choosing DSP

ASUS lists a woofer/tweeter speaker system with Smart Amp technology, Dolby
Atmos and a three-microphone array for the
[GU605 family including GU605MZ](https://rog.asus.com/laptops/rog-zephyrus/rog-zephyrus-g16-2024/spec/).
That does not identify this unit's Linux codec, amplifier driver, firmware,
DSP tuning or exposed PCM channels. Six physical drivers do not imply six
independently addressable surround channels.

Inspection now confirms both amps load matching firmware and the kernel
reports calibration applied; no user-space filters were active. The remaining
hypotheses include missing OEM processing and routing/quality gaps. Do not assume EQ will fix an inactive woofer, wrong
channel map or unloaded amplifier firmware. Establish the ALSA driver path,
UCM profile, firmware/calibration loading and protection ownership first.

Run these read-only commands on `lab5` as the actual desktop user. They are
an inspection recipe, not results obtained on the macOS checkout:

```bash
uname -r                            # Kernel identity.
cat /proc/asound/cards              # ALSA cards and driver names.
aplay -l                            # Hardware playback devices.
arecord -l                          # Hardware capture devices; no recording.
pipewire --version                  # Installed daemon version.
wireplumber --version               # Policy/configuration version.
dpkg-query -W pipewire pipewire-pulse wireplumber alsa-ucm-conf alsa-utils
wpctl status                        # Active devices, streams and defaults.
pactl list cards                    # Profiles, ports and advertised formats.
pw-metadata -n settings             # Read graph settings; supply no setter.
journalctl --user -b -u pipewire -u pipewire-pulse -u wireplumber --no-pager
journalctl -k -b --no-pager          # Inspect audio driver/firmware errors.
```

Use `wpctl inspect NODE_ID` with IDs from that session and `pw-dump` for the
graph; keep full outputs in private local state. Missing commands or restricted
kernel logs are inventory gaps, not permission to install packages or elevate
automatically. Inspect available audio firmware package versions and existing
user overrides after identifying the driver. Save configuration hashes and
stock recovery copies before later edits.

**How to read it:** verify the real output node and selected profile, then
trace the application through every filter to hardware. Investigate missing
firmware, absent endpoints and error messages before decreasing buffers.
During coordinated playback, use `pw-top`: QUANT/RATE describes a scheduling
period; rising ERR counts indicate errors/xruns. It is not an acoustic
latency meter. [PipeWire pw-top reference](https://docs.pipewire.org/page_man_pw-top_1.html).

## 3. Recover speaker tuning, then measure it

The [speaker-tuning-to-easyeffects project](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects)
converts OEM Dolby DAX3 XML tuning into EasyEffects presets or PipeWire
filter chains. It is a promising investigation input, not a qualified GU605MZ
profile. Its README did not explicitly list GU605 at initial research time. An exact
codec/subsystem-matched OEM XML has since been recovered; see
[audio hardware](AUDIO_HARDWARE.md). Its
claims of matching Windows and adding zero latency require independent
verification here. Conversion of EQ/dynamics does not implement Atmos object
decoding or establish amplifier protection.

Inspect the matching ASUS recovery/driver package privately for audio tuning
XML, device IDs and processing endpoints, as was done for display profiles.
Do not reuse another ASUS model's coefficients. Pin and inspect converter
code before execution: its documented workflows can autoload presets or
restart PipeWire. First generate outputs in an isolated directory with no
access to live configuration/services; do not run its default setup on the
desktop. Record unmapped fields and approximation choices.

Prototype with [EasyEffects](https://github.com/wwmm/easyeffects), which exposes
EQ, convolution, dynamics and voice processing. Follow its routing model:
hardware stays the default device. Once a profile is measured and stable,
evaluate a small PipeWire filter chain for maintenance and startup behaviour.
Measure both implementations; neither is presumed faster.

Use conservative gain, headroom and driver-specific protection. An output
limiter does not by itself prove thermal or excursion safety. Asahi's
[speakersafetyd](https://github.com/AsahiLinux/speakersafetyd) illustrates
hardware-specific protection using voltage/current sensing; its supported
Apple hardware is not evidence that it can protect this ASUS. Verify the
existing amp implementation before deciding whether new protection is needed.

Acceptance needs level-matched stock/tuned comparisons, frequency response,
distortion versus level, dialogue intelligibility, stereo balance, and
behaviour at quiet and ordinary listening levels. Log microphone calibration,
position, distance, laptop placement/lid angle, room, volume and power state.
Retain raw recordings privately. A microphone is required for acoustic claims;
listening alone can document preference, not calibration accuracy.

## 4. Reduce measured latency without trading away reliability

```text
Application buffering -> PipeWire graph -> DSP -> ALSA/firmware -> DAC/speakers
        |                    |              |           |
      API route         quantum/rate      filters    device buffers

Bluetooth and HDMI/TV/Sonos add transport and endpoint processing.
```

At 48 kHz, 256, 128 and 64 frames represent 5.33, 2.67 and 1.33 ms per graph
cycle. These are arithmetic scheduling durations, not total output latency.
Application queues, converters, filters and the endpoint remain in the path.

Inventory native PipeWire, PulseAudio compatibility and JACK clients
separately. Inspect realtime scheduling and existing buffers first. In a
coordinated test, step from the working baseline through 256 and 128 frames;
try 64 only if measurements justify it. Keep 48 kHz as an initial test
condition, not a permanent rule for all music. A client can request latency
through `PIPEWIRE_LATENCY`; inspect the actual graph rather than assuming
the request took effect. [PipeWire stream options](https://docs.pipewire.org/page_man_pipewire_1.html).

WirePlumber documents device period size, headroom and batch-device timing.
Tune only the identified endpoint after observing its constraints. Do not
globally disable batch handling or force zero safety margin. Changing reported
internal latency is compensation, not removal of physical delay.
[WirePlumber ALSA configuration](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/alsa.html).

Measure three different things:

1. **Round-trip audio:** use a wired output-to-input loop and `jack_iodelay`
   or equivalent. For a fair OS comparison, use the same USB interface,
   cable, sample rate and comparable application settings on Linux and macOS.
   Interface availability is still unknown. Software loopback alone omits
   converters and cannot establish physical latency.
2. **Everyday response:** measure event-to-sound and first playback after
   idle, using a synchronised trigger and acoustic/electrical capture. Repeat
   in browser and native playback. Record trigger/capture uncertainty and
   acoustic propagation distance. Median and p95 need repeated trials.
3. **Video synchronisation:** measure a known flash/click clip at the actual
   display and speaker, including pause/seek/resume and a long playback run.
   Lip-sync and lowest interactive latency are different acceptance tests.

Provisional engineering gates: seek wired round-trip below 10 ms where the
device allows it; for comparable physical paths, aim for median and p95 within
2 ms of the measured Mac baseline. These are targets, not published macOS
figures or promised hardware limits. Use at least 100 onset trials per state
and a 60-minute representative-load run with zero new xruns or audible gaps.
Record battery/CPU cost before adopting a smaller quantum. Investigate kernel
scheduling only if traces show it is the bottleneck; preserve the working HDR
kernel and establish the [compiler/test loop](DEVELOPMENT.md) before patches.

## 5. Separate the Atmos routes and their acceptance

| Route | Candidate | What it proves if qualified |
|---|---|---|
| Encoded media to Sonos Arc | Player bitstream passthrough over HDMI to TV/eARC | The Arc decodes/renders the preserved Atmos stream |
| Dolby host rendering | Dolby GStreamer plugins plus required proprietary libraries | Supported formats render through an available Dolby implementation |
| Community host rendering | Cavern and its format-specific dependencies | Tested object decoding/rendering for pinned versions and samples |
| Ordinary surround to headphones | PipeWire SOFA/HRTF processing | Binaural spatialisation; not Atmos decoding |
| OEM speaker EQ/dynamics | Recovered tuning plus validated Linux filters | Speaker correction; not Atmos rendering |

### 5.1 Sonos Arc is deferred until internal audio work is complete

The intended route is laptop HDMI -> TV HDMI input -> TV eARC -> Sonos Arc.
Verify the TV's passthrough support and settings. Do not assume a laptop's
ordinary HDMI output can connect directly to an ARC/eARC soundbar port.
Sonos documents DD+ Atmos and TrueHD Atmos support for Arc, with eARC required
for TrueHD. The owner's eARC connection satisfies only one part of the chain.
[Sonos formats](https://support.sonos.com/en-us/article/supported-home-theater-audio-formats?language=en_US)
and [TV/Atmos routing](https://support.sonos.com/en-ca/article/listen-to-dolby-atmos-audio-from-your-tv-on-sonos).

mpv documents `--audio-spdif` for encoded passthrough, including E-AC-3 and
TrueHD; test the installed version, audio backend, driver and advertised
sink capabilities together. Its option name does not mean optical S/PDIF can
carry TrueHD. [mpv stable manual](https://mpv.io/manual/stable/).

Use owned/reference DD+ JOC and TrueHD Atmos samples separately. Record
source hash, actual player/backend route, Arc input format and channel/object
test observations, then check A/V sync and seek/resume. Keep PCM DSP out of
the encoded passthrough route and control listening level at the receiver.
A Sonos Atmos indication plus known test material validates this transport
path; it does not qualify Linux host rendering or laptop spatial playback.
Browser/streaming-service delivery is a separate compatibility test.

### 5.2 Host Atmos rendering has concrete candidates, with gaps

[Dolby's gst-home-audio](https://github.com/DolbyLaboratories/gst-home-audio)
provides Linux build instructions and plugins for DD/DD+ decoding, object
rendering and audio processing. It explicitly requires proprietary libraries;
some renderer configurations also require proprietary tooling. The public
wrapper alone is not a deployable decoder. Establish Linux library access,
permitted use/distribution, supported endpoints and actual behaviour before
selecting it. The Windows OEM Atmos package is not proof those Linux
dependencies are available. Do not infer TrueHD support from the DD+ examples.

[Cavern](https://github.com/VoidXH/Cavern) advertises E-AC-3 JOC decoding and
object rendering. Its README also lists TrueHD Atmos through Cavernize with
Truehdd, a distinct dependency path. Evaluate those separately; pin revisions,
review component licences and build a Linux offline reference test before
designing realtime integration. Its library API does not establish a ready
system-wide PipeWire Atmos service. Moving objects, height placement, timing,
downmix, seeking and reference differences need evidence. Source availability
and functional tests do not establish Dolby certification.

For headphones, PipeWire's optional SOFA spatializer can render directional
audio using HRTFs. It still needs a decoded scene or known channel positions;
spatialising a conventional downmix cannot recover discarded Atmos objects.
[PipeWire filter-chain reference](https://docs.pipewire.org/page_module_filter_chain.html).
Laptop speakers need their own renderer and acoustic/crosstalk treatment;
headphone HRTFs are not a drop-in speaker profile. Gaming object APIs and
Dolby MAT output are separate future integrations from file playback.

## 6. Improve everyday quality alongside the codec work

1. **Consistent routing and volume:** speaker-only DSP must leave automatically
   when headphones or HDMI are selected, return correctly after resume, and
   preserve mute/volume without jumps. Do not stack duplicate spatial effects.
2. **Clear calls:** evaluate microphone channel mapping, echo cancellation,
   noise suppression and gain at realistic fan noise. Choose one processing
   owner per effect; compare against application-native call processing.
3. **Predictable media:** test downmix/dialogue balance, clipping headroom,
   optional loudness normalisation and night mode. Preserve a neutral mode;
   greater loudness alone is not better fidelity.
4. **Power and startup:** measure idle wake-up delay, power draw and crackles.
   Prefer scoped policy changes over globally disabling device suspension.
5. **Wireless as its own endpoint:** measure Bluetooth playback, mic profile
   switching and reconnect behaviour on actual hardware. Do not use wireless
   latency to judge the wired PipeWire result or promise Apple ecosystem
   feature parity without separate support evidence.

## 7. Execute in stages with explicit receipts

| Stage | Work | Acceptance |
|---|---|---|
| A — inventory | Identify driver, amps, firmware, UCM, graph, overrides and OEM assets; record exact Mac models/OS and TV | Sanitised evidence receipt; unresolved hardware fields explicitly marked; no services changed |
| B — baseline | Stock speaker listening/measurements, latency, calls, power and transitions on ASUS/M4 Air | Reproducible setup and raw-data hashes; M3 Max as optional second reference |
| C — speaker tuning | Audit converter, map exact OEM profile, generate offline, activate in test window | Level-matched comparison, measured response/distortion, verified protection path and rollback |
| D — latency/policy | Tune one variable at a time with intended DSP active | Physical timing against §4 gates; zero new xruns in bounded stress run; power trade-off recorded |
| E — host Atmos | Offline candidate decode/render, then a bounded player integration | Source/format/renderer matrix, reference comparisons and measured realtime cost |
| F — daily acceptance | Browser/native media/calls, plug/unplug and 10 suspend/resume cycles on AC/battery | Correct routing, stable volume, no new gaps or missing first sounds; restore stock successfully |
| G — Sonos (last) | Verify TV/eARC then DD+ and TrueHD samples independently | Arc reports correct input; object/channel and sync checks pass for each format |

For each receipt record date, source/configuration hashes, package/firmware
versions, hardware/route, tools, commands, measurement method and uncertainty,
results and failures. Do not import old HDR test passes as audio evidence.
Keep binaries, OEM profiles, generated OEM-derived filters and raw captures in
private storage; commit only reviewed summaries and reproducible tooling.

**Non-goals for the first implementation:** no universal EQ preset, amplifier
gain/protection bypass, unmeasured macOS-parity claim, automatic audio-service
restart, system-wide 64-frame mandate, or relabelling stereo enhancement as
Atmos. Premium-service DRM, commercial licensing and application negotiation
remain separate dependencies. Pin candidates before implementation; links
above are research sources consulted on October 12, 2026, not source pins.
