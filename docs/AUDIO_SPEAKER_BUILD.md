# Speaker build — turn exact OEM tuning into an offline Linux candidate

**Status:** ready to implement; exact-match private XML available ·
**Written:** 2026-10-12 · **Executes:** speaker lane in
[implementation](AUDIO_IMPLEMENTATION.md).

Read [hardware](AUDIO_HARDWARE.md), [audio quality](AUDIO_QUALITY.md) and
[development](DEVELOPMENT.md). Build real tools and test artifacts, without
activating the profile. Preserve the working CS35L56 firmware and gain. The
initial deliverable is an auditable candidate, not a calibrated speaker claim.

## 1. Bind the input to the observed hardware

The target is Realtek `10ec0285`, subsystem `10431c63`, two CS35L56 SPI amps,
and speaker ID 0. The exact DAX3 input hash is in the
[inventory receipt](../evidence/audio-inventory-2026-10-12.json). Match both
codec and subsystem, endpoint `internal_speaker`, mode `normal`; require an
explicit profile choice. Start by comparing `music`, `dynamic` and `off`.
Do not silently use a generic ASUS match or a headphone endpoint.

Read the associated INF and private XML; emit only metadata and input hashes
publicly. Recheck the eSupport duplicate or independent WIM extraction because
the first image listing warned about reference counts. Keep disagreement as
a failed input-verification result. Do not copy the entire recovery image.

## 2. Implement an explicit preparation interface

Proposed repository interface:

```bash
python3 scripts/prepare_speaker_profile.py inspect --xml PRIVATE_XML --inf PRIVATE_INF --report PRIVATE_REPORT
python3 scripts/prepare_speaker_profile.py build --xml PRIVATE_XML --inf PRIVATE_INF --codec 10ec0285 --subsystem 10431c63 --endpoint internal_speaker --mode normal --profile music --output PRIVATE_BUNDLE
python3 scripts/prepare_speaker_profile.py verify --bundle PRIVATE_BUNDLE
```

`inspect` parses input without writing configuration or contacting a session.
`build` writes only under the explicit new output directory; refuse overwrite
by default. `verify` checks hashes, schema and internal references. None of
these commands installs, autoloads, launches an audio client or restarts a
service. Exit 0 means the stated offline operation succeeded, 2 means invalid
input/identity, and 3 means an unsupported mapping or missing dependency.
No successful exit may imply physical safety or acoustic accuracy.

The bundle contains `manifest.json`, an EasyEffects JSON preset, impulse
response files if needed, and a machine-readable field-mapping report. A
PipeWire `.conf` candidate is optional after the EasyEffects path is audited.
The manifest records schema version, exact converter commit, dependency
versions, input hashes, hardware IDs, profile/endpoint, sample rate, output
hashes and `activation_state: "not-installed"`.

The mapping report records each interpreted field's source, unit/scale,
output stage, approximation and unsupported status. Reject malformed/nonfinite
parameters and ambiguous profile matches. Limit input size, XML complexity,
output paths and references; never permit profile names or embedded paths to
escape the output directory. Resolve symlinks safely. Unknown relevant fields
must be visible and must prevent a claim of complete equivalence.

## 3. Audit the upstream generator before adapting it

The pinned converter in [implementation](AUDIO_IMPLEMENTATION.md) is MIT
licensed. Its `lib/dax/parse.py` exposes endpoint/profile discovery and XML
parsing; `dolby_to_easyeffects.py` selects and emits profiles. The parser has
fixed-point and per-channel rules that must be retained or deliberately
corrected with tests. The implementation must document omitted speaker-DSP
stages and volume-dependent behaviour, rather than claim one static filter
recreates all Windows processing.

Observed CLI controls at that pin include `--endpoint`, `--mode`, `--profile`,
`--output-dir`, `--irs-dir`, `--no-reload` and `--skip-ee-check`. The wrapper
`dolby_to_pipewire.py` supports `--output-dir` and `--no-activate`. Its default
behaviour writes live configuration and restarts PipeWire. `--dry-run` can
still unpack a driver archive into a cache. Never execute those defaults.
Re-verify call paths at the pinned checkout; prefer direct pure parser/build
functions behind the repository wrapper, or run the external CLI in an
isolated process with only explicit input/output paths and no session access.
Do not repurpose HOME or mount the owner's XDG directories into a container.

Keep OEM FIR/dynamics separate from amplifier firmware calibration. Never
write CS35L56 controls, replace firmware or disable amp protection. No bass
boost, gain restoration or virtual-bass switch is enabled merely to make the
candidate louder. Audit defaults and total headroom. A sample peak limiter
is not a thermal/excursion protection implementation.

## 4. Establish the build loop and focused checks

Use a disposable Linux Python environment with pinned NumPy/SciPy and any
upstream test dependencies. Record architecture and versions. Upstream's
synthetic-only baseline command is:

```bash
pytest -n 0 -m "not live_machine" --ignore=tests/corpus tests/
```

The upstream `live_machine` marker can remove isolation environment values,
so excluding it and the corpus directory is mandatory for this synthetic run.
Keep the container itself isolated from host audio and private data. Run only
relevant upstream synthetic subsets in the fast lane after identifying them;
record their actual names. Keep a private conversion receipt separate.

Required focused checks for the new wrapper:

- Exact match succeeds; wrong codec/subsystem, duplicate endpoint/profile,
  truncated XML and unsupported mode fail without output activation.
- Hostile profile names, symlink output, external references and oversized
  inputs cannot read/write outside the specified paths.
- Synthetic impulse and sweep inputs verify finite output, the expected
  sample rate/channel layout, clipping/headroom reporting and correct units.
- Output is deterministic for a pinned dependency set; manifest hashes catch
  edits, missing impulse files and incorrect references.
- A sentinel fake session and command recorder prove preparation performs
  no `systemctl`, `wpctl` setter, `pactl` setter, autoload, playback or reload.
- Linux plugin/format validation runs against an isolated runtime if needed;
  no public CI job or private conversion opens a physical sound device.

## 5. Deliver a reviewable candidate and a deployment handoff

First produce the wrapper, synthetic fixtures and tests. Then privately
convert the matched OEM input and report mapped/approximated/unsupported
stages, candidate hashes and any failed requirements. If mapping is incomplete,
ship the honest offline tooling and leave the candidate unqualified; continue
fixing supported mappings rather than inventing coefficients.

Update this document with actual CLI names and a source-bound build receipt.
Include later install/remove commands and per-device matching design as
reviewable text, but do not execute them. EasyEffects retains the hardware
sink as default. Speaker selection must be scoped to the actual internal
route, not the ephemeral node ID or every stereo sink. Headphone/HDMI bypass,
service restart behaviour and removal restoring stock are required before
physical testing. Run adversarial review and the affected fast lane per
[implementation](AUDIO_IMPLEMENTATION.md), then submit the completed batch.
