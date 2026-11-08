# Architecture — source colour through to the panel

Companion to [hardware](HARDWARE.md) and [status](STATUS.md). This document
assigns responsibilities; [the quality plan](DOLBY_VISION_AND_QUALITY.md)
contains the unresolved design decisions and acceptance work.

```text
 Application / media player
   source encoding, decoded pixels, frame metadata
                 |
   Shared renderer: reconstruct picture and apply its RPU to the display target
                 |
   Wayland descriptions and compositor transforms
                 |
   Mutter / DRM KMS output state
                 |
   i915 AUX brightness + eDP transport
                 |
   Samsung OLED with mode-specific characterisation
```

## Existing HDR fixes

**libdisplay-info:** Parse native DisplayID interface capabilities and expose
structured extension failures. The active additive API preserves legacy
native-only high-level getter behaviour; consumers explicitly opt in.

**Mutter:** Recognise a complete native RGB/BT.2020/PQ tuple for eDP with the
required KMS properties. Valid CTA metadata remains authoritative. This does
not fabricate content luminance metadata or a Dolby capability.

**Kernel/i915:** Parse valid physical native DisplayID luminance and permit
the existing recognised Intel AUX brightness path to use it. Preserve the
guard for devices that advertise AUX controls but require PWM. Full-screen
luminance and small-window peak are different quantities.

## Decisions and ownership

1. **Generic capability parsing stays generic.** The fixes use display data,
   not a hard-coded ASUS model whitelist; physical acceptance remains scoped
   to the tested laptop until other devices are measured.
2. **Panel characterisation is data.** Match panel identity and output route;
   do not embed guessed gamut/brightness adjustments in generic parsers.
3. **Each colour transform needs one owner.** Application ICC conversion,
   Dolby display management, composition and display calibration must agree
   on the encoding passed between them to avoid duplicate mapping.
4. **The media renderer owns host-side Dolby grading.** System mpv and FFmpeg use the shared provider. The staged GtkVideo and Showtime packages pass the retained native picture and the target for the view showing it. On a target change the renderer can grade that same paused picture again. The compositor receives pixels tagged with their output encoding. [Client and target contracts](SYSTEM_DOLBY_VISION.md).
5. **Profile coverage belongs to each decoder and renderer pair.** The staged mpv 0.42 path composes the full Profile 7 enhancement layer before display management. The GTK playback controls exercise Profile 5. Recognizing a Profile 7 track in a demuxer establishes its configuration only. [Profile 7 reconstruction](SYSTEM_DOLBY_VISION.md#physical-trim-selection-and-the-staged-dual-layer-player) · [Matroska controls](../evidence/gstreamer-matroska-track-config-20261108.json).

## Characterisation and target mapping are separate contracts

Profile inspection preserves the difference between PCS-adapted ICC
characterisation, standard calibration tags and opaque OEM processor data.
Parsing a matrix or luminance field does not apply it, and applying a file
association does not establish that the compositor consumes its fields.
The [ICC inspector](ICC_CHARACTERISATION.md) records these inputs privately.

The [source audit](COLOUR_PIPELINE_AUDIT.md) distinguishes PQ's encoding
range from a physical display target. A corrective implementation needs
explicit target-volume provenance, a transform owner, and metadata consistent
with the pixels actually emitted. A panel's peak must not be substituted for
an encoding normalization constant. Generic source fixes and panel-specific
calibration data remain separate deliverables. The accepted
[target-luminance design](MUTTER_TARGET_LUMINANCE.md) defines the first compositor
correction, its state ownership and immutable Wayland descriptions.

The [Wine API diagnostic](WINE_API_CONTRACT.md) likewise distinguishes an
API-set name, an exported function, a working function and an activated Dolby
processor. Each is a separate observable boundary. None alone qualifies full
Dolby Vision display management or an accurate image on the panel.

## Scope limits

This repository does not certify Dolby conformance, claim that all Linux apps
already preserve colour metadata, or supply premium-service DRM. It does not
treat an HDR10 conversion as the requested full DV result. The physical panel
cannot display colours or luminance outside its capabilities; correct mapping
and consistent presentation are the goals.

## Audio ownership

Speaker processing, diagnostics, latency and host Atmos are owned by
[rog_audio](https://github.com/pjunod/rog_audio). Audio implementation,
source pins and physical acceptance are maintained there. This repository
continues to own the display stack and panel qualification.
