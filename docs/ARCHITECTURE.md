# Architecture — source colour through to the panel

Companion to [hardware](HARDWARE.md) and [status](STATUS.md). This document
assigns responsibilities; [the quality plan](DOLBY_VISION_AND_QUALITY.md)
contains the unresolved design decisions and acceptance work.

```text
 Application / media player
   source encoding, decoded pixels, frame metadata
                 |
   Shared colour / full DV processing path (DV work pending)
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
4. **Full Dolby Vision remains an explicit missing component.** The OEM
   Windows plugin and profile are investigation inputs, not a working Linux
   implementation. Host-side display management and TV-led HDMI transport
   require different integration proofs.
5. **Applications consume the platform capability.** Plurx negotiation and
   player integration remain in Plurx; the shared display solution belongs
   here and must be exercised by more than one application.

## Scope limits

This repository does not certify Dolby conformance, claim that all Linux apps
already preserve colour metadata, or supply premium-service DRM. It does not
treat an HDR10 conversion as the requested full DV result. The physical panel
cannot display colours or luminance outside its capabilities; correct mapping
and consistent presentation are the goals.
