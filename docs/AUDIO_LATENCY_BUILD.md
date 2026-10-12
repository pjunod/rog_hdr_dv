# Audio latency build — inspect, measure and generate reversible candidates

**Status:** ready to implement; idle baseline captured, physical data absent ·
**Written:** 2026-10-12 · **Executes:** diagnostics/latency lane in
[implementation](AUDIO_IMPLEMENTATION.md).

Read [hardware](AUDIO_HARDWARE.md) and [audio quality](AUDIO_QUALITY.md).
The ROG already has realtime data-loop scheduling. Build diagnostics and
measurement tools first; do not solve a presumed scheduler problem or lower
buffers on the live desktop. Sonos work is last and outside this lane.

## 1. Build a reusable read-only inspector

Proposed interface, following the existing display inspector's privacy model:

```bash
python3 scripts/inspect_audio.py --output PRIVATE_JSON
python3 scripts/inspect_audio.py --from-capture PRIVATE_JSON --public-summary SUMMARY_JSON
```

Native Linux collection uses bounded subprocess calls with an allowlist:
ALSA card/codec metadata, package versions, read-only PipeWire graph/settings,
current profiles/routes, relevant driver/firmware diagnostics, config hashes
and scheduler state. Never record microphone audio, play a probe, install a
package, invoke setters, restart a service or elevate itself. A caller may
supply a privately captured kernel log if permission is unavailable.

Every probe returns `ok`, `unavailable`, `permission-denied`, `timeout` or
`parse-error`; missing data is not a negative hardware finding. Handle no
session bus, absent tools, suspended nodes, hotplug during collection and
multiple cards. Resolve the real session environment; do not hard-code UID
1000, card 1 or PipeWire node 61. The first inspected route is evidence, not
a global constant. macOS invocation should report unsupported collection or
use explicitly scoped native inventory, never execute Linux setters.

Public summaries use an allowlisted schema, not regex-only redaction of full
logs. Omit user/client/app names, node serials, USB serials, hostnames, addresses,
absolute home paths, session cookies and arbitrary configuration content.
Include source-hash provenance and explicit limits. Construct privacy tests
with hostile nested graph properties and diagnostic errors containing secrets.

## 2. Analyse physical latency without relabelling graph timing

Proposed offline interface:

```bash
python3 scripts/analyse_audio_latency.py --input TRIALS_JSON --output RESULT_JSON
python3 scripts/prepare_audio_latency.py --inventory PRIVATE_JSON --quantum 256 --output PRIVATE_CANDIDATE
```

Define and document `TRIALS_JSON` schema before implementation. Each trial
must specify measurement kind (`round-trip`, `event-to-output`, `idle-onset`
or `av-offset`), measured delay and unit, sample rate if sample-based, method,
route, reference/capture clock relationship, uncertainty, power/load state,
DSP state and validity/rejection reason. Preserve raw and corrected values;
never subtract converter or propagation delay without an explicit model and
recorded parameter. Unsynchronised cross-device timestamps are not a valid
latency measurement. Reject NaN, infinity and invalid rates/counts.

Report count, exclusions, median, explicitly defined p95 estimator, min/max
and uncertainty. Keep each route/measurement kind/state separate. Never pool
ASUS speakers, a USB interface, Bluetooth and HDMI into one latency number.
One-way latency cannot be inferred by halving round-trip unconditionally.
Keep PipeWire `quantum_frames / rate_hz` in a separate `graph_period_ms` field.
A fixture-generated result must be labelled synthetic.

Comparison gates in [audio quality](AUDIO_QUALITY.md) are provisional: 100
onset trials per state, zero new xruns/audible gaps in a 60-minute bounded
load run, and a same-path Mac comparison. No physical data exists yet. Build
an import/analysis pipeline and an exact capture procedure; do not fabricate
trials to satisfy the acceptance threshold. The M4 Air is primary and M3 Max
secondary; exact OS/models/interface must be recorded when tested.

## 3. Generate candidates without applying them

`prepare_audio_latency.py` writes a new bundle containing a candidate
configuration, manifest and restoration instructions. It must never change
live metadata or restart services. Keep observed values and proposed changes
side by side, including explicit previous user configuration and unknowns.
Require an unambiguous target route and supported installed config version.
Refuse globally forcing a guessed quantum when endpoint/application-specific
policy can express the experiment. Do not create a watchdog.

Start with 256 and 128 frames at the observed 48 kHz; 64 remains optional.
Retain the working realtime settings and ALSA batch defaults unless a trace
shows why a device-specific change is needed. Account for PulseAudio clients'
additional buffering and any speaker DSP delay. Do not assume a requested
client latency is what the graph actually negotiated. Existing remembered
USB-output preference is not permission to erase it.

The bundle manifest includes inventory/config hashes, proposed values,
version constraints and `activation_state: "not-installed"`. Configuration
syntax must be checked against an isolated PipeWire/WirePlumber environment
matching the installed versions where practical; no host sockets or sound
hardware. If a matching package environment cannot be built, report that
constraint and retain the candidate as unvalidated rather than install it.

## 4. Focused regression and integration checks

Test probe timeouts, partial failures and absent commands without hanging;
privacy allowlists; supported/unsupported inventory schemas; mixed units and
measurement kinds; percentile calculation on hand-computable fixtures;
invalid clocks/nonfinite values; clipping/exclusion flags; deterministic
configuration generation; path/overwrite handling; and no side effects.
The physical analyser is standard-library Python unless a justified algorithm
requires a pinned numerical dependency. Use synthetic data for public tests.

Prepare the bounded recording/playback workflow as an explicit later operator
step. It must identify loopback wiring, shared clock or trigger, test signal,
levels, sample rate, signal detection/correlation method, ambiguity rejection,
error counters and uncertainty. Capture is separately opt-in and cannot be
hidden in `inspect_audio.py` or repository checks.

## 5. Ship actual tooling with a source-bound receipt

Deliver code, synthetic tests, documented schemas, an example generated
candidate and an analysis example clearly labelled synthetic. Run on the
private read-only snapshot if possible, publishing only a sanitised summary.
Record the Linux tool/config validation separately from macOS unit tests.
Prepare rollback and the remaining physical benchmark procedure, then use
independent adversarial review and the affected fast lane in
[implementation](AUDIO_IMPLEMENTATION.md). Do not claim a latency improvement
until a physical before/after receipt exists.
