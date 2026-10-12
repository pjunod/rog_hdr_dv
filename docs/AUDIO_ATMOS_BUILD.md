# Host Atmos build — prove decoding and rendering before live integration

**Status:** isolated feasibility build authorised; no host Atmos qualified ·
**Written:** 2026-10-12 · **Executes:** host Atmos lane in
[implementation](AUDIO_IMPLEMENTATION.md).

Read [audio quality](AUDIO_QUALITY.md), [hardware](AUDIO_HARDWARE.md) and
[development](DEVELOPMENT.md). This lane builds host-side file processing
for laptop/headphone use. Sonos Arc passthrough is explicitly last; do not
spend this batch implementing or testing Sonos routing.

## 1. Establish the exact candidate and compiler loop

Fetch Cavern at the revision in [implementation](AUDIO_IMPLEMENTATION.md).
Inspect its solution/project target frameworks, supported Linux entry points,
licence and dependency versions before writing an adapter. Record actual
`dotnet --info`, SDK pin, architecture and Linux container image digest.
Build the relevant libraries first. Do not equate a Windows GUI project build
with a usable Linux library or require a system-wide .NET installation.

The README distinguishes E-AC-3 JOC support from TrueHD Atmos through
Cavernize plus Truehdd. Start with E-AC-3 JOC. Determine whether the TrueHD
path and needed entry points are available and buildable on Linux before
promising support. Pin all added dependencies and preserve attribution.
A missing dependency is an explicit capability result, not a cue to silently
fall back to bed-only PCM while reporting Atmos.

Use Dolby's pinned `gst-home-audio` as a contract reference and alternative
only if the required proprietary Linux libraries are actually available with
appropriate use rights. The public wrapper does not contain those runtimes.
Do not copy Windows DLLs into Linux paths or claim the OEM recovery package
supplies a native Linux renderer. Any proprietary experiment remains private.

## 2. Build an offline harness with an honest result contract

Proposed deliverable location: `probes/atmos/`, including build script,
source manifest, CLI harness and generated synthetic tests. Example intended
interface (adjust executable name to the proved toolchain and document it):

```bash
./probes/atmos/build.sh --output PRIVATE_BUILD
PRIVATE_BUILD/atmos-probe inspect --input PRIVATE_MEDIA --report PRIVATE_REPORT
PRIVATE_BUILD/atmos-probe render --input PRIVATE_MEDIA --layout stereo-binaural --output PRIVATE_WAV --report PRIVATE_REPORT
```

No hardware output, network fetch, default-sink change or desktop registration
occurs. Input must be explicitly supplied; never search personal media.
Write only to explicit new output paths and fail on collision by default.
Constrain untrusted media parsing by resource/time limits in a disposable
process. Keep decoder failures and unsupported formats distinguishable.

The JSON report must include schema/tool/source versions, input hash,
container/codec, detected Atmos signalling, actual decoder, whether object
metadata was consumed, renderer, output layout/rate/channels, sample count,
delay accounting, warnings and evidence class. Unknown metadata fields are
unknown, not false. Report a conventional-channel fallback explicitly; never
label it a successful Atmos render.

Headphone binaural output needs a documented HRTF source/licence, coordinate
convention, channel mapping and gain normalisation. A stereo speaker output
must have a separate label and contract; headphone HRTFs are not laptop
speaker tuning. A reference multichannel render is useful even if binaural
integration remains unfinished. Output WAVs from private media stay private.

## 3. Separate synthetic renderer checks from codec qualification

First build deterministic synthetic moving-object scenes through the library
API. Check channel ordering, position/orientation, finite samples, output
length, silence, gain bounds and repeatability. Test malformed metadata and
resource limits. This proves the exercised renderer API, not Dolby bitstream
decoding, metadata fidelity, perceptual localisation or certification.

Then use a lawfully available local E-AC-3 JOC sample with a recorded hash.
Record object/bed metadata and rendering behaviour against a documented
reference, including height and motion. If no sample is available, finish
the compiler/harness/synthetic work and mark codec qualification pending.
Do not download random copyrighted movie tracks or commit reference payloads.
TrueHD is a separate row with its own decoder dependency and evidence.

Reference comparison records renderer/version/layout, any gain alignment,
resampling, delay alignment and tolerance with its rationale. Samplewise
identity is not assumed across different renderers/HRTFs. An Atmos string
from ffprobe or a successful plain E-AC-3 decode is insufficient.

## 4. Prepare realtime integration only after offline correctness

Measure processing cost and allocations for bounded blocks without writing to
a physical device. Determine whether decoder framing, seeks and rendering
state can support playback. Record algorithmic delay and buffer requirements;
do not force 64-frame processing merely because PipeWire permits it.

A later integration consumes encoded audio and metadata before information
is discarded, renders once, and sends PCM to PipeWire. Generic PipeWire EQ
cannot recover objects from an already downmixed stream. Specify timestamp,
seek/flush, gap, channel layout, volume and EOS contracts. Keep a stereo/bed
fallback visibly labelled. Plurx-specific negotiation remains in Plurx.

Do not build an always-running system-wide service until the offline path and
required app boundary are proven. Document the smallest runnable player-side
prototype and remaining gaps. Measure laptop-speaker spatial treatment
separately from headphone rendering and OEM tonal correction.

## 5. Deliver a build, not another research-only plan

The minimum completed batch is pinned Linux build automation, working offline
CLI, synthetic renderer tests, source-bound receipts and a format capability
matrix. If a candidate genuinely cannot build, diagnose the failure and try a
bounded supported library target or documented alternative; report the exact
external blocker alongside all completed work. Preserve licence limitations.

Submit the implementation for independent adversarial review, fix findings,
then run the affected fast lane once. Record source compilation, synthetic
results, private sample qualification, runtime readiness and physical
acceptance independently. Sonos remains deferred until the coordinator
finishes the internal-audio work and schedules that final route.
