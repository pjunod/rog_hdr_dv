# Audio implementation — build order, ownership and integration

**Status:** ready for isolated builds; deployment and physical tests pending ·
**Written:** 2026-10-12 · **Executes:** [audio quality](AUDIO_QUALITY.md).

Read [hardware evidence](AUDIO_HARDWARE.md), [status](STATUS.md), and
[development](DEVELOPMENT.md) first. Implement in separate agent clones on
`codex/` branches. The coordinating agent owns review and integration; the
owner requested GPT-6.1 Sol implementation chats. Preserve concurrent display
and Dolby Vision work. This plan extends the platform repository, not Plurx.

## 1. Order the work around internal speakers

1. Build the offline speaker-profile pipeline and read-only diagnostics.
2. Build latency analysis and reversible candidate configuration generation.
3. Build and evaluate host-side Atmos decoding/rendering offline, then prepare
   a bounded laptop/headphone integration. Separate speaker and headphone DSP.
4. Qualify speaker quality, calls, routing, latency and resume in a coordinated
   physical test window, using the M4 Air and optionally the M3 Max.
5. Do Sonos Arc/eARC Atmos last. No Sonos worker is dispatched in this batch.

Independent offline builds can run concurrently; that does not authorise
concurrent laptop playback or simultaneous audio-configuration writers.
If a physical gate needs the owner or equipment, finish all offline work and
report the exact remaining test. Do not invent a pass or stop at a plan.

## 2. Assign concrete deliverables

| Lane | Build contract | Initial deliverable |
|---|---|---|
| Speaker | [Speaker build](AUDIO_SPEAKER_BUILD.md) | Exact-match private OEM importer, offline preset bundle, mapping report and deterministic synthetic checks |
| Diagnostics/latency | [Latency build](AUDIO_LATENCY_BUILD.md) | Read-only inspector, physical-measurement analyser and non-activating candidate configs |
| Host Atmos | [Atmos build](AUDIO_ATMOS_BUILD.md) | Pinned Linux compiler receipt, offline decode/render harness and honest capability matrix |
| Integration | This document | Reviewed PRs, merged docs/status, evidence and explicit deployment procedure |

All proposed commands in the lane documents are interfaces to implement,
not claims that those executables already exist. Re-verify upstream interfaces
at the pinned revisions before implementing adapters. Workers own their new
files and tests; shared README/status changes are reconciled at integration.

## 3. Keep source and results reproducible

| Candidate | Repository | Inspected/resolved revision | Purpose |
|---|---|---|---|
| Speaker converter | [speaker-tuning-to-easyeffects](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects) | `430e3a501e21bf8fdb615b133d2e8130b17973c1` | DAX3 parser and filter-generation reference; source inspected |
| Cavern | [VoidXH/Cavern](https://github.com/VoidXH/Cavern) | `7d85d1880666ca5ea323848cff47ce7f50b29f7d` | Object rendering candidate; remote HEAD resolved, not built |
| Dolby integration | [gst-home-audio](https://github.com/DolbyLaboratories/gst-home-audio) | `e37c7a61b82cd91e4584ce1fe579c326991334e4` | Public wrapper/contract reference; proprietary runtime required |

A worker may select a better-supported revision after documenting the reason
and updating the pin; never silently float a dependency. Preserve licences
and imported attribution. Store audio-specific pins in an audio manifest;
do not misrepresent a new tool as an existing display patch series in
`sources.json`. `SHA256SUMS` changes only if patch bytes actually change.

The compiler loop is a disposable Linux environment, with architecture,
image digest, compiler/runtime version and exact command in the receipt.
Dependencies may be installed inside that build environment. Do not install
packages on the live laptop, restart services, alter ALSA controls, change
PipeWire metadata or render to hardware during this batch. An isolated
PipeWire instance must have no host runtime socket or `/dev/snd` access.

## 4. Share evidence, not private payloads

Receipts distinguish `source-review`, `synthetic-test`, `private-offline`,
`live-read-only`, `physical-measurement` and `owner-listening` evidence. A
successful private conversion is not acoustic validation. A graph cycle is
not round-trip delay. A format badge is not object-rendering evidence.

Public JSON uses a schema version, tool/source pins, commands with neutral
paths, result/limitations and hashes. Raw data, device serials, host addresses,
usernames, OEM paths containing private identities, generated OEM-derived
filters and recordings remain private. Test fixtures must be generated or
redistributable. Never make CI discover local OEM files automatically.

## 5. Review and merge each complete batch

Implement and compile first. Before merging, obtain independent adversarial
review of the actual diff, fix findings, then run one affected fast lane:
repository integrity, focused new tests, compiler/synthetic checks appropriate
to the lane, and the staged-tree/reachable-history privacy scan. Retry only
failed or invalidated checks. Record test skips and unavailable dependencies.

Open a PR against current main, resolve shared-document conflicts against the
latest ledger, and merge only the qualified scope. Existing held display PRs
are unrelated; do not merge or rewrite them. Keep source, build readiness,
installation and physical acceptance as separate status fields. Update the
HTML workboard alongside the Markdown ledger. This batch authorises builds
and document integration, not an uncoordinated live audio deployment.

## 6. Prepare the later activation window

The later operator procedure must snapshot exact configs, routing, relevant
mixer state, profile hashes and recovery commands. Activate only the internal
speaker candidate, at a conservative listening level, with the stock amp
firmware/protection preserved. Bypass/removal must restore the prior route;
headphones and HDMI must never inherit speaker correction. Coordinate every
service restart and audible test with the owner.

Record baseline and candidate acoustic response, level-matched preference,
onset/round-trip latency, A/V sync, CPU/power, calls, hotplug and ten resume
cycles. Compare to the M4 Air using the methods in
[audio quality](AUDIO_QUALITY.md). Optical display tests remain independent.
After internal audio and host Atmos results are recorded, schedule the final
Sonos format/passthrough tests with the actual TV model and eARC chain.
