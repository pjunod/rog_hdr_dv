# HLG and target-aware tone mapping — compositor contract (nativehdr6)

**Status:** implemented as Mutter patches 0028–0038 (`nativehdr6`); reviewed and
fast-lane qualified; not packaged or installed · **Date:** 2026-10-10.

This continues the [colour pipeline audit](COLOUR_PIPELINE_AUDIT.md#follow-up-source-findings--input-contracts-and-mapping-ownership).
`nativehdr5` fixed the input defects. This batch adds the two missing
operations the audit names: HLG input, and mapping highlights to the output's
physical target. Gamut compression and output characterization remain later
work with their own contracts.

## Ownership

| Operation | Single owner | Inputs |
|---|---|---|
| HLG decode (inverse OETF, black level, OOTF) | Clutter colour pipeline, as the HLG state's EOTF | The HLG state's own luminance range |
| Source target volume (mastering primaries/luminance, MaxCLL, MaxFALL) | Wayland image-description creator → `ClutterColorStateParams` | Client declaration, validated |
| Output target volume | `MetaColorDevice` (already published to Wayland by `nativehdr4`) | Firmware-declared target luminance and primaries, with provenance |
| Highlight mapping | Clutter colour transform, once per surface, toward the output blending state | Source effective peak, output target peak |
| KMS HDR metadata | Unchanged (zero luminance fields) | — |

Applications that map to the published preferred target themselves (and tag
their output with that target) need no further mapping; the compositor must
then leave them unchanged.

## HLG

Follows Rec. ITU-R BT.2100-2. The HLG state's default luminances are those of
the Wayland protocol: minimum 0.005, maximum 1000, reference white 203 cd/m²,
mastering maximum 1000. A client may declare other luminances.

- **Decode:** with `Lw` = the state's maximum and `Lb` = its minimum,
  γ = 1.2 · 1.111^log2(Lw / 1000) (the extended system-gamma formula), and
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
  which is truthful because target primaries are never used to map gamut.
  (Common P3 mastering primaries lie just outside BT.2020.)
- Repeated setters are `already_set` errors. A MaxCLL or MaxFALL of 0 means
  unknown. When both are known, MaxFALL above MaxCLL is the protocol's
  `invalid_luminance` error.
- The values are stored in the colour state's private target volume and take
  part in equality, hashing and image-description identity. The public
  `ClutterLuminance` structure is not changed.
- **Effective source peak** = the smallest of: MaxCLL (if set), mastering
  maximum (if set), and the encoding maximum. Without any declaration it is
  the encoding maximum (10000 cd/m² for PQ). For the extended-range linear
  encoding, whose nominal maximum does not bound the signal, only the
  declared values count; without one the peak is unknown and nothing is
  mapped.
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
  minimum is not used.
- **Colour:** applied to max(R, G, B) of linear BT.2020, with all three
  channels scaled by the same ratio, so hue and saturation ratios are kept.
  Negative components are not lifted; max(R, G, B) ≤ 0 is unchanged.
- **Scanout parity:** a surface or cursor whose transform includes mapping
  is composited, not scanned out directly. The decision uses the same
  "mapping required" test as the renderer, and the transform cache compares
  states exactly.
- **Units:** both peaks are compared as multiples of reference white. The
  output's reference white (203 cd/m² × the brightness factor, rounded to
  whole cd/m² as published) is the display reference carried by the blending
  state, so mapping happens once, toward the blending state, and the
  blending → output conversion never maps again.
- **Screencasts** of a monitor have no physical target and are not mapped.

## Acceptance

Source-level, at the agreed pre-merge stage:

- HLG: decoding reference HLG signal levels matches values computed
  independently from BT.2100 (at least 0%, 50%, 75% and 100%, plus a
  non-1000 `Lw`), for BT.2020 and BT.709 primaries. Encode round-trips decode
  within tolerance. Wayland and CICP both create HLG states.
- Target volume: invalid mastering values fail as the protocol requires; valid
  ones survive the round trip and change image-description identity.
- Mapping: no change when the source peak is at or below the target or when no
  target is declared; the curve matches an independent BT.2390 computation at
  sample points; monotonic; hue ratios kept; scanout rejected exactly when
  mapping applies.

Physical acceptance (what the panel actually emits) needs the
[measurement procedure](PANEL_MEASUREMENT.md) and an instrument; no optical
claim follows from these tests.
