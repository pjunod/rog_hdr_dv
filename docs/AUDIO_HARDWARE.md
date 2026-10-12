# Audio hardware — the inspected ROG and recovered speaker tuning

**Inspected:** 2026-10-12 · **State:** read-only inventory complete; physical
performance unmeasured.

Read [audio quality](AUDIO_QUALITY.md) for goals and
[implementation](AUDIO_IMPLEMENTATION.md) for the build order. This is the
hardware evidence ledger, backed by the
[sanitised receipt](../evidence/audio-inventory-2026-10-12.json).
`lab5` is the neutral repository name for the ROG; it is not an SSH alias.
Connection details stay in private local configuration.

## The codec and both amplifiers are enabled

| Item | Observed state |
|---|---|
| Machine/kernel | GU605MZ; `7.3.0-rc5-nativehdr1` |
| Main audio | Intel PCH HDA, Realtek ALC285, codec `10ec0285`, subsystem `10431c63` |
| Speaker amplifiers | Two Cirrus CS35L56 devices bound over SPI to `cs35l56-hda` |
| Amp firmware | DSP `3.11.16`, system `10431C63-spkid0`, AMP1/AMP2 |
| Amp calibration | Kernel reports calibration applied to both amps |
| Mixer | Speaker and bass-speaker switches on; both amp gains read as 0 dB |
| Active playback | ACP analog stereo, FL/FR; `front:1` at this inspection |
| UCM | Explicit query reports unsupported HDA model; active ACP route exists |
| Other card | NVIDIA HDMI audio; not the internal speaker path |

Kernel messages establish that the model-specific files were loaded. They do
not prove every physical driver is audible, that protection has been exercised,
or that the speaker response is accurate. Unsupported UCM is not by itself a
bug: diagnose actual ACP routing before replacing it. Do not switch to a
SoundWire/SOF recipe just because the processor is Meteor Lake.

Both uncompressed amp tuning files coexist with packaged `.zst` files. Their
bytes equal the decompressed packaged counterparts; hashes are in the receipt.
No different local coefficient override was demonstrated. Preserve these
files and the working firmware rather than replacing them with the older
Windows recovery firmware.

## PipeWire uses an unprocessed stereo route

PipeWire and pipewire-pulse are `1.6.8-1ubuntu4`; WirePlumber is
`0.5.17-1ubuntu1`. ALSA UCM is `1.2.16.1-1ubuntu1`, ALSA utilities
`1.2.15.2-1ubuntu2`, and the firmware metapackage is
`20260915.git1522c78a.1ubuntu`.

No audio filters or playback streams were present in the captured graph.
The graph settings were 48 kHz, default quantum 1024 frames, limits 32–2048,
and no forced rate/quantum. The data-loop threads already had SCHED_RR
priority 20. There is no demonstrated missing realtime scheduling problem.
No `.conf` overrides were found in the inspected user and `/etc` PipeWire or
WirePlumber trees; distro fragments were not exhaustively audited.

A disconnected USB output remains the remembered default; internal speakers
were the actual fallback. Preserve the owner's preference and test hotplug
policy before changing it. The inactive stream snapshot cannot establish
negotiated playback format, actual running quantum, xruns under load or
physical latency. The reported 1024/48000 duration is 21.33 ms per cycle only.

## Recovery contains an exact-match DAX3 speaker profile

The recovery image `Recovery/RecoveryImage/ASUS.swm` was indexed with the
partition mounted `ro,nodev,nosuid,noexec`. Only two selected files were
extracted to private user state; the partition was unmounted after each read.
The BitLocker Windows installation was not unlocked or mounted.

The selected DriverStore package is `dax3_ext_rtk`, driver version
`9.117.611.44`, dated 2024-01-16. Its INF maps both HDAUDIO and INTELAUDIO
`VEN_10EC&DEV_0285&SUBSYS_10431C63` entries and includes:

```text
DEV_0285_SUBSYS_10431C63_PCI_SUBSYS_1C631043.xml
SHA256 d6728635859309e0fecf2bdc32844ac15a32f67261e5aae8ae2e91ab01580149
Size   86807 bytes
```

The XML parses as `device_data`, with endpoint `internal_speaker`, mode
`normal`, and profiles dynamic · movie · music · game · voice ·
voice_onlinecourse · personalize_user1/2/3 · off. Exact matching establishes
which OEM input to investigate; it does not establish a faithful Linux
translation or permission to redistribute the payload.

7-Zip 26.02 exited successfully for the selected extraction but warned
`Some files have incorrect reference count`. The warning is retained, not
silently dismissed. The two hashes identify extracted bytes; whole-image
integrity and signed authenticity were not newly verified. Re-extract through
an independent WIM reader or compare the duplicate eSupport copy before
relying on coefficients for physical acceptance.

Private assets remain under `~/.local/state/audio-quality/2026-10-12/` on the
laptop, including `oem-manifest.json`, index, extraction log and the two OEM
files. Local raw diagnostics and a private copy are outside the public tree.
Future workers receive those locations privately. No tuning coefficient,
OEM payload, raw graph, journal, hostname, address or user identifier belongs
in public evidence. No audio service or setting changed in this inspection.
