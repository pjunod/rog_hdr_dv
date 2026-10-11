# HLG, tone mapping and gamut compression — compositor contract (nativehdr6–8)

**Status:** implemented as Mutter patches 0028–0038 (`nativehdr6`), 0039–0043
(`nativehdr7`) and the review fixes 0044–0052 (`nativehdr8`); reviewed and
fast-lane qualified (synthetic headless tests); nativehdr8 installed
2026-10-11 (owner accepted the picture) · **Date:** 2026-10-11.

This continues the [colour pipeline audit](COLOUR_PIPELINE_AUDIT.md#follow-up-source-findings--input-contracts-and-mapping-ownership).
`nativehdr5` fixed the input defects. This batch adds the two missing
operations the audit names: HLG input, and mapping highlights to the output's
physical target. Gamut compression follows in
[nativehdr7](#gamut-compression-nativehdr7); output characterization is
[defined and deferred until measured](#output-characterization--defined-deferred-until-measured).

## Ownership

| Operation | Single owner | Inputs |
|---|---|---|
| HLG decode (inverse OETF, black level, OOTF) | Clutter colour pipeline, as the HLG state's EOTF | The HLG state's own luminance range |
| Source target volume (mastering primaries/luminance, MaxCLL, MaxFALL) | Wayland image-description creator → `ClutterColorStateParams` | Client declaration, validated |
| Output target volume | `MetaColorDevice` (already published to Wayland by `nativehdr4`) | Declared target luminance and primaries (DisplayID; since `nativehdr9` also CTA-861 luminance and native SDR base EDID gamut), with provenance |
| Highlight mapping | Clutter colour transform, once per surface, toward the output blending state | Source effective peak, output target peak |
| KMS HDR metadata | Unchanged (zero luminance fields) | — (see [KMS metadata](#kms-hdr-metadata-stays-unknown)) |

Applications that map to the published preferred target themselves, and tag
their output with that target including its published reference luminance,
need no further mapping; the compositor must then leave them unchanged.

## HLG

Follows Rec. ITU-R BT.2100-2. The HLG state's default luminances are those of
the Wayland protocol: minimum 0.005, maximum 1000, reference white 203 cd/m²,
mastering maximum 1000. A client may declare other luminances.

- **Decode:** with `Lw` = the state's maximum and `Lb` = its minimum,
  γ = 1.2 + 0.42 · log10(Lw / 1000) for 400 ≤ Lw ≤ 2000 (BT.2100-2
  Table 5) and the extended form γ = 1.2 · 1.111^log2(Lw / 1000) (BT.2390)
  outside that range (the two meet closely, not exactly, at 400 and 2000),
  and
  β = √(3 · (Lb / Lw)^(1/γ)). Lift black with `max(0, (1 − β)E′ + β)`, apply
  the inverse OETF per channel to scene light `E`, then the OOTF
  `F = Y_s^(γ−1) · E`, where `Y_s` is the luminance of `E` in the **source
  primaries** (the Y row of their RGB→XYZ matrix; 0.2627/0.6780/0.0593 for
  BT.2020). `F` is display light normalized to the state's range.
- **Encode** (HLG as a destination) is the exact inverse: inverse OOTF
  (`Y_s = Y_d^(1/γ)`, `E = F · Y_s^(1−γ)`), OETF, then black removal. Values
  outside the encodable range clip.
- Because the OOTF depends on luminance, decode is not a per-channel curve. It
  runs in the source primaries before the primaries matrix.
- HLG maps from Wayland `transfer_function.hlg` and CICP transfer 18. The
  compositor advertises it.

**Decision:** HLG is decoded for its declared nominal peak (1000 cd/m² unless
the client says otherwise), as the protocol defines, and the common highlight
mapping below then fits it to the panel. Rendering HLG directly for the
panel's peak (a different system gamma) is an alternative left for later
review; it would make HLG a special case of the mapping owner.

## Source target volume

The creator accepts `set_mastering_display_primaries`, `set_mastering_luminance`,
`set_max_cll` and `set_max_fall` and advertises the matching features. Rules:

- Mastering luminance: `0 ≤ min < max`, finite. Mastering primaries are
  validated with the shared matrix definition. They are not required to lie
  within the encoding primaries: `extended_target_volume` is advertised,
  which is truthful: mastering primaries beyond the encoding primaries are
  kept as declared and, since nativehdr7, set the gamut-compression limits
  when compression applies (for extended-range linear content they are the
  only source gamut).
  (Common P3 mastering primaries lie just outside BT.2020.)
- Repeated setters are `already_set` errors. A MaxCLL or MaxFALL of 0 means
  unknown. When both are known, MaxFALL above MaxCLL is the protocol's
  `invalid_luminance` error. For version 1 clients, a known MaxCLL or
  MaxFALL must also lie above the target minimum and at or below the target
  maximum (`invalid_luminance`), as version 1 of the protocol requires.
- With `extended_target_volume` advertised, `set_luminances` accepts a
  reference white above the maximum luminance.
- The values are stored in the colour state's private target volume and take
  part in equality, hashing and image-description identity. The public
  `ClutterLuminance` structure is not changed.
- **Effective source peak** = the smallest of: MaxCLL (if set), mastering
  maximum (if set), and the encoding maximum — but the encoding maximum
  counts only where it describes the content's peak: SDR-type transfer
  functions and HLG (whose nominal maximum is a display-referred peak). For
  PQ (10000 cd/m² is the encoding's capacity) and the extended-range linear
  encoding, only declared values count; without one the peak is unknown and
  nothing is mapped, so plain PQ video keeps its reference white and direct
  scanout and its overshoot is left to the panel. This notion is separate
  from whether an encoding bounds its signal range, which the gamut rule
  uses.
- HLG luminances must satisfy β ≤ 0.5; otherwise the description fails as
  unsupported.

## Highlight mapping

Applies the BT.2390 EETF (Report ITU-R BT.2390, Hermite-spline knee in the PQ
domain) **only** when the effective source peak, after the existing
reference-white scaling, exceeds the output target peak. It never expands.

- **Where:** in the surface → blending-state transform, after the existing
  luminance scaling and before conversion out of linear BT.2020. The output
  blending state carries the output's target peak, so the target is part of
  the transform identity and cache key.
- **Target:** the colour device's target peak luminance. If no target is
  declared, no mapping is applied (today's behaviour) — no constant is
  substituted.
- **Curve:** source range `[Lsrc_min, Lsrc_peak]` → target `[Ltgt_min,
  Ltgt_peak]`, both converted to PQ. Normalize, knee start
  `KS = 1.5 · maxLum − 0.5`, Hermite spline above `KS`, denormalize. There
  is no black adjustment: the mapping never raises black, and the target
  minimum is not used. Signal above the effective source peak is held at
  the target peak.
- **Curve form:** the BT.2390 Hermite knee (KS = 1.5 · maxLum − 0.5) in
  normalized PQ, with the deviations listed in this section; identical on
  the CPU and in the shader.
- **Colour:** applied to max(R, G, B) of linear BT.2020, with all three
  channels scaled by the same ratio, so hue and saturation ratios are kept.
  Negative components are not lifted; max(R, G, B) ≤ 0 is unchanged.
- **Scanout parity:** a surface or cursor whose transform includes mapping
  is composited, not scanned out directly. The decision uses the same
  "mapping required" test as the renderer: the decision is made once per
  (source, target) pair and reused by the renderer, scanout and the cursor,
  and the transform cache compares states exactly. The hardware-cursor plane decision is reviewed but not
  executed by the tests (the test monitors have no KMS CRTC).
- **Units:** both peaks are compared as multiples of reference white. The
  output's reference white (the output encoding's default reference white
  × the brightness factor, 203 cd/m² × the factor for PQ, rounded to
  whole cd/m² as published) is the display reference carried by the blending
  state, so mapping happens once, toward the blending state, and the
  blending → output conversion never maps again. Only the colour device
  creates a display target, through an explicit constructor; a client
  state with mastering metadata never becomes one.
- **Publication:** output and preferred image descriptions are republished
  on the same exact identity the renderer uses, so a client that follows
  the published description after any brightness change is not mapped
  again.
- **Screencasts** of a monitor have no physical target and are not mapped.

### KMS HDR metadata stays unknown

The connector's static metadata keeps zero luminance fields ("unknown").
Declaring the target peak there would claim the composition never exceeds
it, but unmapped content (plain PQ without a declared peak) can. Whether the
panel firmware then applies its own roll-off is a question for the
installed system: compare what is shown with and without a declared peak
before changing this.

## Acceptance

Source-level, at the agreed pre-merge stage:

- HLG: decoding reference HLG signal levels matches values computed
  independently from BT.2100 (at least 0%, 50%, 75% and 100%, plus a
  non-1000 `Lw`), for BT.2020 and BT.709 primaries. Encode round-trips decode
  within tolerance. Wayland and CICP both create HLG states.
- Target volume: invalid mastering values fail as the protocol requires; valid
  ones survive the round trip and change image-description identity.
- Mapping: no change when the source peak is at or below the target, when
  PQ declares no peak, or when no target is declared; the curve matches an independent BT.2390 computation at
  sample points; monotonic; hue ratios kept; scanout rejected exactly when
  mapping applies. The cursor-plane path is covered by review only.

Physical acceptance (what the panel actually emits) needs the
[measurement procedure](PANEL_MEASUREMENT.md) and an instrument; no optical
claim follows from these tests.

## Gamut compression (nativehdr7)

**Status:** implemented as Mutter patches 0039–0043 (`nativehdr7`), with review
fixes in `nativehdr8`; reviewed and fast-lane qualified (synthetic headless tests); installed with
`nativehdr8` on 2026-10-11.

The output signal stays BT.2020/PQ. A colour outside the panel's own gamut
is otherwise left to the panel firmware, whose handling is unknown (it may
clip). This step compresses such colours into the declared target gamut
before encoding, so the gamut decision has one known owner.

- **Owner and place:** the same surface → blending transform and the same
  "mapping required" predicate as highlight mapping. It runs after
  highlight mapping, in linear light. One function decides whether to
  compress and with which limits, for both the predicate and the operation.
- **Target gamut:** the colour device's target primaries, only when a
  display declaration supplies them and their matrices round-trip. Since
  `nativehdr9` that is DisplayID in BT.2100 and the base EDID in native SDR
  ([sources](DISPLAY_TARGET_SOURCES.md)). The encoding fallback is not a
  physical gamut. Without a declaration, nothing is compressed. The blending
  state carries the target primaries next to the target peak. Since
  `nativehdr9` the target is adapted from its encoding's white to D65 before
  containment, limits and matrices are computed, so it is judged in the same
  frame as the source primaries. An output is never outside its own gamut.
- **Source gamut:** where the source primaries actually land in the pixel
  path (the encoding's white-adapted conversion; mastering primaries get the
  same adaptation). Compression applies only when the encoding gamut has a
  primary outside the target and, where mastering primaries are declared,
  so does the mastering gamut. sRGB-encoded content is therefore never
  compressed on a target that contains sRGB (any wide-gamut panel), whatever
  its metadata. ICC sources are not compressed. Limits come from the mastering gamut
  when declared, otherwise from the encoding gamut. For the extended-range
  linear encoding, only declared mastering primaries count; without them
  nothing is compressed.
- **Containment tolerance:** a primary within the target declaration's own
  quantization (one 12-bit step for CIE 1931 declarations; a per-primary
  bound from the u′v′→xy Jacobian for CIE 1976) counts as inside. A P3
  master on a panel that declares P3 is not compressed and is not refused
  scanout on gamut grounds.
- **Algorithm:** the ACES Reference Gamut Compression (ACES 1.3) distance
  compression, in linear RGB of the target primaries (absolute colorimetry;
  no chromatic adaptation in that step). The achromatic value is
  max(R, G, B). For each channel, the distance from it is compressed above
  threshold 0.8 with the published power curve (power 1.2), evaluated in a
  two-branch form that stays finite without clamping or infinities. The limit for each channel is the largest distance any
  point of the source gamut boundary reaches (primaries and the points
  along each edge where two target channels are equal). So no point of the
  source boundary ends beyond the target boundary by more than the
  declaration's tolerance, and each channel's furthest point beyond that
  tolerance lands exactly on it. Non-finite or non-positive achromatic
  values are unchanged.
- **Parameter provenance:** the threshold 0.8 and power 1.2 are ACES 1.3's
  published values, which were tuned for camera colours compressed into AP1.
  Deriving the limits from the source and target gamuts is this project's
  own design. Whether a higher threshold (less compression of honest
  saturated colours near the boundary) suits a real panel better is open
  until it is measured.
- **Parity:** part of transform identity and of the shared predicate, so
  scanout and the cursor decide the same way.

**Acceptance:** source-level, as tested. No change when the source gamut is
inside the target or no target is declared; boundary property; colours
within the threshold unchanged; monotonic; independent reference values;
non-D65 sources; GPU and CPU agree; scanout parity. Whether the panel clips
or maps on its own, and so whether this improves what is shown, needs the
installed system and an instrument.

## Output characterization — defined, deferred until measured

**Status:** contract defined; implementation deliberately deferred until a
measurement exists. Nothing is applied today.

Output characterization corrects for how this panel actually turns the
BT.2020/PQ signal into light. The steps above stop at the signal: they target
the gamut and peak the firmware declares, and leave the conversion from
BT.2020 to the panel's native primaries and to emitted luminance to the
panel firmware.

No available data describes that firmware conversion:

- The DisplayID declarations give the target gamut and peak. They are
  already used, and they say nothing about how accurately the firmware
  reaches them.
- The OEM ICC profiles hold factory SDR characterisation (sampled TRCs and
  luminance) that differs by GPU route; the CMDEF variants' MHC2 transforms
  are identity ([inspection](ICC_CHARACTERISATION.md)). Their operating
  conditions are not established, they are not measurements of this unit's
  response to PQ input, and their TRCs must not be applied to a PQ stage.
- The colour device's EDID-derived profile is model metadata.

Applying a correction built from any of these would guess at the panel's
behaviour and could correct twice (once in the compositor, once in the
firmware). The demonstrated cause of any inaccuracy is not known yet, so
there is nothing to fix at its source.

**Contract for the implementation, once measured:**

- **Input:** a characterization measured in HDR mode with the
  [measurement procedure](PANEL_MEASUREMENT.md): neutral PQ ramps (grey
  balance and EOTF), primaries and white at several luminances (§4), plus
  per-channel PQ ramps added for this purpose, recorded with the
  instrument, mode, brightness factor and date. The record carries
  a new provenance value, `MEASURED`; firmware or profile values never take
  it.
- **Correction:** a 3×3 matrix in linear light plus per-channel 1D curves on
  the PQ-encoded signal, or a 3D LUT in the PQ domain if the measured error
  is not separable. The choice follows the
  measured residuals, not a default.
- **Owner and place:** the colour device holds the record. It is applied
  once, in the blending → output conversion, so every surface, the cursor and
  any direct-scanout decision see the same output. While non-identity, the
  shared scanout predicate refuses direct scanout of every surface and the
  hardware cursor plane.
- **Targets:** measured peak and gamut, when recorded, replace the firmware
  declarations as the mapping targets, with their own provenance.
- **Validation:** held-out patches measured after applying it, against the
  accuracy goals in the measurement procedure. A correction that does not
  improve the held-out patches is not kept.

**Decision:** until an instrument is available, the compositor applies no
output characterization, and gamut and highlight mapping use only the
firmware declarations.
