# Open RPU-aware display management — the generally available Dolby Vision track

**Status:** contract; owner decision 2026-10-11 to make this the main Dolby
Vision track · **Date:** 2026-10-11.

Dolby Vision on a PC panel has no display-side engine. On Windows, Dolby's
display management runs on the host with a panel configuration, and the panel
receives an ordinary HDR signal ([investigation](DOLBY_VISION_AND_QUALITY.md)).
What makes Dolby Vision content look different from its HDR10 base layer is
that host-side step. It uses the RPU: the reshaping that rebuilds the
picture (Profile 5 and 8), the per-shot level 1 analysis (minimum, average
and maximum in PQ), and the colourist's trims for given target displays
(level 2, and level 8 in content mapping v4.0). An independent review
(2026-10-11, [findings](REVIEW.md#independent-plan-review-2026-10-11))
recommended making an open implementation of that step the generally
available track. The OEM processor under Wine stays a time-boxed experiment
that only this laptop can run. The owner accepted.

## What this delivers, and what it must not be called

An open display manager that uses the RPU's reshaping, level 1 and level 2/8
trims to map each shot to the display's published target. It is validated
against Dolby's own reference renderer (CM Offline, which the owner holds
privately) within a stated colour-difference tolerance. Its output is
handed to the compositor already mapped, so the compositor passes it
through unchanged.

It is not Dolby's algorithm and not a certified Dolby Vision implementation.
Public names and documentation say "RPU-aware display management, validated
against Dolby's reference renderer to within the stated tolerance". They
never say "Dolby Vision playback" or "certified". Dolby tools, generated
metadata, reference renders and numerical comparisons with them stay
private, as the [reference workflow](HDR_REFERENCE_CORPUS.md#official-reference-workflow)
already requires. Only the open code, synthetic inputs and sanitized summary
statistics are public.

## Where today's open stack stands

| Stage | Today (Ubuntu 26.10: FFmpeg 8.1, libplacebo 7.360, mpv 0.41) | Gap |
|---|---|---|
| Decode and RPU parse | FFmpeg decodes Profile 5/8 and exports the RPU, including display-management levels 1, 2, 8 and others (`AVDOVIMetadata`, `AVDOVIDmData`) | — |
| Reshaping | libplacebo reconstructs Profile 5 (IPT-PQ-c2) and 8 (`pl_map_avdovi_metadata`) | Profile 7 FEL is not reconstructed (out of scope; the OEM plugin does not register Profile 7 either) |
| Per-shot mapping | libplacebo takes level 1 maximum and average as dynamic HDR metadata for its own tone mapper (`max_pq_y`, `avg_pq_y`) | Level 1 drives libplacebo's curve, not a Dolby-like one. Level 1 minimum is unused |
| Trims | None | Level 2 and level 8 trims (slope, offset, power, chroma weight, saturation gain and the v4.0 equivalents) are parsed by FFmpeg and ignored |
| Target | mpv can follow the compositor's published target | Target selection for trims (choose or interpolate the trim for the published target peak) does not exist |
| Hand-off | mpv tags its output | The output must carry exactly the compositor's preferred description, so Mutter maps nothing. That rule already exists in Mutter (`nativehdr8`, publication on exact identity) |

## Design

1. **Home.** Implement in libplacebo, as a display-management stage used
   when the frame carries Dolby Vision metadata, so mpv and any libplacebo
   player get it. Plurx would need a native Linux player to use it. Its
   browser player cannot carry an RPU.
2. **Inputs.** The reshaped linear signal; the level 1 values per shot;
   the trims; the source range and mastering display (from the RPU header and level 6);
   the target from the compositor's preferred description (target peak,
   minimum and primaries, which `nativehdr8+` publishes from the panel's
   declarations).
3. **Mapping.** A tone curve anchored on level 1, as SMPTE ST 2094-10
   (Dolby's published dynamic-metadata application) defines the metadata's
   meaning. Then the trims for the target, chosen or interpolated by target
   peak as the metadata intends, applied in the colour space the metadata
   defines. Where the standard leaves the curve open, choose
   by measured agreement with the reference renderer, not by appearance.
4. **Output.** PQ BT.2020 within the target volume, tagged with the preferred
   description. The compositor then neither tone-maps nor compresses gamut.
   It shows the frame as delivered. A stream without Dolby Vision metadata
   keeps libplacebo's existing behaviour.
5. **No fabricated metadata.** Test metadata comes only from Dolby's own
   tools (analysis and trims made through them) or from real Dolby Vision
   content the owner owns. Trims are never invented by hand or by script.

## Validation

- **Corpus.** The [synthetic PQ inputs](HDR_REFERENCE_CORPUS.md) plus
  owner-held masters. The private workflow generates metadata for them and
  renders reference frames for a custom target equal to the panel's
  published target (616 cd/m², 0.0004 black, the panel primaries) and at
  least two other targets, for example 1000 and 300 cd/m².
- **Candidate.** The same masters and metadata, rendered through the open
  path headlessly (libplacebo on the CPU Vulkan driver), with identical source
  interpretation and frame alignment.
- **Metric.** ΔE_ITP (ITU-R BT.2124) per pixel on patches and full frames,
  reported as mean, 95th percentile and maximum per target. The first
  acceptance bar is mean ≤ 1 and 95th percentile ≤ 3 on the synthetic
  corpus at every target. It is revisited with the first results and
  recorded with its reasoning before it is relied on.
- **Ablations.** Level 1 only, level 1 plus trims, and libplacebo's current
  behaviour. This shows each stage's contribution and guards against a
  result that only agrees by coincidence.
- **On the laptop.** mpv with the open path on `lab5`. Mutter's debug output
  must show no mapping applied to the video surface. Optical checks follow
  once the instrument exists.

## Stages

1. Harness: drive the open path headlessly from a frame and its metadata, and
   compute ΔE_ITP against a reference image. Public code, synthetic test
   vectors.
2. Baseline: measure libplacebo's current behaviour against the private
   references (the ablation's first row).
3. Level 1 curve: implement and measure.
4. Trims: level 2 then level 8, implement and measure.
5. Target hand-off: the compositor's preferred description as the target,
   exact tagging, and a pass-through check on `lab5`.
6. Upstream proposal to libplacebo, under the owner's identity.

The OEM processor experiment continues only to a go/no-go: one frame
processed on the GPU with this panel's configuration engaged, compared with
the same reference. A trace of the OEM pipeline on the laptop's Windows
installation, run with the owner, informs both tracks.

## Stage-1 implementation checkpoint (2026-10-13)

The [headless harness](DOLBY_HARNESS.md) now has a compiled native x86_64
libplacebo 7.360.1 consumer, exact source/range/bit-depth/frame/target and
parsed-real-metadata contracts, and a BT.2124 Annex-1 metric. Compiler/header/ELF
identities are in the [receipt](../evidence/dolby-harness-compile.json).
The original Astra review required R1–R3 corrections; the
[correction receipt](../evidence/dolby-harness-corrections.json) records explicit
requested/effective semantics (PQ ignores all minima, Dolby RPU owns range,
zero L1 falls back), per-invocation source/ELF/runtime and comparison identities,
and stronger public coverage. The passing native ELF is retained because C/build
inputs are unchanged. Astra independently approved corrected `2ab8332` / tree
`69c59f2`; qualification ran all **27 actual regression methods once**: **26 passed,
1 failed, no skips**, with 25 passing subtests. All native renderer cases passed;
the informative Annex-4 metric-vector expectation requires independent arithmetic
reconciliation, correction review and failed-only retry before stage-1 qualification
is complete. See the [source-bound receipt](../evidence/dolby-harness-qualification-attempt1.json).
No real metadata
or private reference comparison has run, no trims/new mapping are implemented,
and no full Dolby, compositor pass-through or optical acceptance is claimed.
Private reference absence does not block this stage-1 implementation handoff.
