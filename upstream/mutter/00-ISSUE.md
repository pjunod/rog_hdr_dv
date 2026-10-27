# Using panel-declared HDR targets (DisplayID 2.0, CTA-861, base EDID): series overview and coordination with !5068 and !5177

### Summary

I have a series of Mutter changes, built over the last weeks on two laptops, that make Mutter
use what a panel declares about itself: offer BT.2100 on eDP panels that declare HDR only
through DisplayID 2.0, publish the panel's own luminance and primaries as the Wayland target
volume (separately from the PQ encoding), and render toward that target (BT.2390 highlight
mapping and ACES-style gamut compression in the blending conversion), plus HLG, mastering
metadata on the protocol, and some protocol robustness fixes. It is about +21k lines including
tests, so before opening merge requests I would like to agree on the direction and on how it
should relate to two open MRs that touch the same code: !5068 and !5177.

### Hardware evidence

- **ASUS ROG Zephyrus G16 (GU605MZ)**, Samsung ATNA60DL01-0 OLED eDP panel, Intel Meteor Lake
  (i915). Its EDID has no CTA-861 HDR static metadata block. HDR is declared only in a DisplayID
  2.0 extension: Display Interface Features lists RGB BT.2020 with SMPTE ST 2084, and Display
  Parameters declares 400 cd/m² full-screen and 616 cd/m² 10%-window luminance and native
  primaries. Stock Mutter offers only `default` and `sdr-native`. With these changes (on a
  Mutter 51 build), `gdctl show` reports `bt2100`, and the output's image description publishes
  a target luminance of 0.0004-616 cd/m² and the firmware-declared primaries, while the encoding
  stays BT.2020/PQ. This is the same symptom family as #4847 and #5093.
- **Lenovo ThinkPad X1 Extreme (1st gen)**, AUO B156ZAN03.2 eDP panel, Intel UHD 630. A native
  SDR panel with a 128-byte base EDID only (no CTA, no DisplayID), so no HDR at all. In
  `sdr-native` mode the series publishes the base EDID gamut as both the encoding and the target
  primaries, and content from wider gamuts is compressed into it instead of clipped.

These are firmware declarations, not optical measurements; I have no colourimeter readings yet.
Night Light in HDR and the per-monitor overrides have not had a visual check on the hardware.

### Prerequisite: libdisplay-info

The DisplayID parts need libdisplay-info API that is not released yet: Display Interface
Features (overlapping libdisplay-info!210), a structured "extension failed to parse" query,
and the Display Parameters luminance and chromaticities. Those are being proposed upstream
there first; the Mutter side probes for them in meson.build and cannot pass CI until a release
ships them.

### The series, in proposed order

| Slice | What | Overlap |
|---|---|---|
| frames | `gtk-interface-color-scheme` instead of the deprecated property (GTK 4.20) | none; small standalone MR |
| stage-view | reuse a compatible offscreen buffer across colour state changes | none; standalone |
| backend / seat teardown | destroy the Clutter event source and detach native seat handlers on dispose | none; standalone |
| monitor-manager | clear `restore_config_id` once the restore idle runs | none; standalone |
| native DisplayID PQ | offer BT.2100 on eDP when DisplayID declares RGB BT.2020/ST 2084 | #4847 family |
| native target | publish the declared target luminance and primaries apart from the encoding | !5068 |
| protocol robustness | signed custom primaries, ICC file range/fd 0/short reads, the creator's own `unsupported_feature` code | !4604 (opposite intent on clamping), !5313 |
| HLG | HLG transfer function, protocol support, BT.2100 Table 5 system gamma | none found |
| target volume | mastering primaries/luminance and MaxCLL/MaxFALL on the protocol, carried in colour states | !5068 |
| highlight mapping | BT.2390 EETF toward the declared target peak; scanout and cursor parity | !5068 (tone mapping to display capabilities) |
| gamut compression | compression toward the declared target gamut; scanout and cursor parity | none found |
| target sources | CTA-861 desired content luminance and base EDID SDR primaries as targets | #5001 (related) |
| Night Light in BT.2100 | white adaptation in linear light instead of the CRTC LUT | **!5177**, #3687 |
| per-monitor targets | target overrides in `monitors.xml`, DisplayConfig and gdctl | **!5177** |
| colour device lifecycle | colord/store shutdown and cancellation robustness | **!5177** removes this code |

### Questions

1. **!5068** (Read EDID HDR metadata and complete the protocol): our target-volume, highlight
   mapping and target-source slices cover much of the same ground. Would you rather I review
   and build on !5068, or propose ours as an alternative where they differ? The main
   differences on our side: the declared target is kept separate from the encoding and
   published as the image description's target volume, every target has a recorded provenance
   (firmware, CTA, EDID, user), mapping is decided once per (source, target) pair so the
   renderer, direct scanout and the cursor plane cannot disagree, and plain PQ without a
   declared peak is left unmapped.
2. **!5177** (Rework display colour management): it moves Night Light into linear space and adds
   colour configuration to the display config, and drops the colord/`MetaColor*` machinery.
   I assume our Night Light, per-monitor override and colour lifecycle slices should not be
   proposed against the current code, and would instead be rebased onto !5177 once it lands
   (or offered there as review input). Is that right, and is there a part of !5177 where help
   would be useful?
3. **!4604** clamps custom primaries to [0, 1]; our change accepts signed coordinates (encoding
   gamuts such as ACES AP0 have negative coordinates) within ±16 and rejects unusable
   colorimetry with the protocol's `unsupported` cause. Which behaviour do you want?
4. Is the overall split above reasonable, or would you prefer fewer, larger MRs?

### AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via
Claude Code). I reviewed the changes and take responsibility for them.
