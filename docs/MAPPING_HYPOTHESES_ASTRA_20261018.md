# Mapping equation continuation — Astra, 2026-10-18

Status: ongoing analysis, not accepted mapping. This continues the committed
[Fable checkpoint](MAPPING_HYPOTHESES_FABLE_20261017.md). Sol owns implementation,
native compilation, and the once-only development GPU/full-raster comparisons.
The untouched frame1200/target48 remains reserved for a frozen development-passing
candidate; none of this analysis accesses it.

## Primary-source check: the actual ST 2094-10 Annex B

Retrieved the public SMPTE ST 2094-10:2021 publication from
https://pub.smpte.org/pub/st2094-10/st2094-10-2021.pdf . SHA256:
`289f2230c949bb9490f15d75e793d9042cc1bdd6a75e0d2769a5565f15d19764`.
The publisher's landing page identifies the document and links this PDF. The
2021 foreword identifies changes to minimum-statistic computation and offset
ranges; it does not describe a new Annex B curve.

- Section 6.1.2 computes statistics on 2x2 component averages throughout the
  image essence associated with a metadata interval. Replacing shot metadata
  with the sparse current-frame lattice is not this calculation.
- Annex B.2 Eq2 includes a contrast exponent n but explicitly fixes n=1 for
  Application #1. It is not a free metadata-controlled contrast parameter.
- The Annex B adaptation point is the nested geometric mean
  `sqrt(input_average * sqrt(target_minimum * target_maximum))`, not the cube
  root of the product of three luminances. The actual example
  is 120, 0.5, 100 nits producing approximately 29 nits; it also discusses an
  upper bound such as 80% of target maximum.
- Consequently the modified PQ knee in libplacebo/MPC is not the standard's
  literal adaptation equation. With the current zero target black, the literal
  geometric midpoint degenerates. Choosing another black floor would require
  an explicit, separate source justification, not a value fitted to references.
- Annex B.3 applies its rational curve independently to linear RGB, followed
  by target-peak-normalized linear SOP and color adjustment. The existing failed
  DoViBaker contract already tests a disclosed nonzero-floor extension of that
  architecture. Do not repeat it or treat it as PQ-Y mapping.

Decision: no n sweep, frame-local L1 substitution, or claim that Annex B supplies
an extra contrast knob. These source questions are resolved without new renders.

## Current evidence and ownership

Sol's corrected ABI367 guard compiles full/noDV/consumer with warnings as errors
(library cd4600f). The missing frame714 lattice now reproduces the chosen chain:
mean 2.418842198716092, p95 5.553420219156015 in the double evaluator; native C
mean 2.4188631814, p95 5.5532675763. Invalid and above-PQ1 counters are zero on
that lattice. The successful frame256 lattice was not repeated. Both shots
still fail unchanged accuracy requirements. These are sampled, not full-raster
results. Lattice scalar/GPU agreement cannot establish that a cap was unexercised
on unsampled full-raster pixels.

## Corrected-anchor intensity/chroma diagnostic — rejected

The older failed IPT/Eq8 composition used the old L1-min knee, whereas the new
mastering-black/zero-low-knee correction materially improves scalar-Y mapping.
The chroma-ray interval failures reject exact equality for that embedding, but
the retained bounded witnesses do not establish failure of the mean/p95 metric.
One complete composition was frozen before execution: full RGB-PQ SOP and actual
CW/SG first, then patent-cited Ebner1998 Eq1 XYZ/LMS, absolute PQ and IPT; apply
the selected mastering-black/zero-low-knee rational to EOTF(I), encode J, scale
P/T by `1+J-I` (US9961237 Eq8/9), inverse colorimetry, then one physical P3 clip.
This is an explicitly hybrid hypothesis, not an identified official pipeline.
No alpha/beta values or matrix sweep were introduced. Below-black inverse LMS
components project to PQ(0), counted explicitly; nonfinite/above-PQ1 rejects.

`tools/dolby_harness/analysis/astra356_ipt.py` executed this new chain exactly
once per retained development lattice, with all 34,560 samples valid per shot:

| Shot | Post-P3 mean | p95 | Signed 720 I/T/P |
| --- | ---: | ---: | --- |
| 256 | 1.7248121682 | 4.6293281770 | -0.827812 / -0.253054 / +0.731762 |
| 714 | 2.7798244959 | 4.8369961758 | -0.839430 / -0.434864 / +0.602183 |

Both mean errors worsen against the selected MB-Y candidate, and both fail.
Frame256 has 12,077 raw-negative pixels and 12,174 physical-P3 excursions;
its raw all-population metric is unavailable (partial raw metrics must not be
promoted). Frame714 has 576 P3 excursions. This diagnostic is rejected, not
promoted into the renderer. Exact source/reference input hashes, metadata,
inverse identity checks, strata and counters are retained in its JSON receipt.
Frame256 retains the adapter's reconstructed-source prospect qualification;
frame714 uses exact stored source triples. No native, render, unit, reference
acquisition, or holdout operation was performed by this analysis.

Current: inspect the remaining metadata/normalization and scalar-curve contract
without fitting free coefficients or repeating rejected chains. Sol's existing
frozen candidate and full-raster comparison ownership remain unchanged.

Remaining: source-grounded passing complete chain, full-raster development and
independent evidence, genuinely independent adversarial review/fixes, one
whole-candidate affected unit batch and repository gate, substantial PR/merge,
and uniquely versioned Ubuntu source/binary packages with isolated install and
rollback evidence. PR16 stays held; no physical device deployment.
