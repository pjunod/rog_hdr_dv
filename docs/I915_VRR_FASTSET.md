# i915 VRR fastset — why full-screen video never got variable refresh

Companion to [status](STATUS.md) (what is installed and open) and
[operations](OPERATIONS.md) (installing a kernel deliberately) — this is *the
diagnosis of the `Page flip failed: drmModeAtomicCommit: Invalid argument`
messages, the kernel fix, and the report for the i915 maintainers*.

**Status:** fix in `patches/linux/0005`, built as `7.3.0-rc6-nativehdr2` on
Ubuntu `7.3.0-9.9`; upstream report drafted below, not yet sent (it goes out
under the owner's name).

## The symptom

GNOME Shell logs `Page flip failed: drmModeAtomicCommit: Invalid argument`
whenever a video goes full screen on the laptop's panel (36 times in one
boot on 2026-10-27, each at the start or end of a playback). Playback goes
on, but the panel stays at a fixed 240 Hz: 23.976 fps material repeats a
frame about every 42 s, and VRR never engages.

## The cause

Captured with `drm.debug=0x14` (atomic + KMS) on `7.3.0-rc5-nativehdr1`
while `mpv --fs` played a clip; the same code is in Linux master as of
2026-10-26:

```
 Mutter: fullscreen client drives the frame clock ─▶ commit VRR_ENABLED=1
        │                                             (page flip, no ALLOW_MODESET)
        ▼
 intel_psr.c _psr_compute_config: vrr.enable ─▶ PSR off
        │   ("PSR doesn't work reliably with VRR enabled")
        ▼
 _intel_psr_min_set_context_latency: !has_psr ─▶ 0
        │   (Wa_14015401596 gives 1 line only while PSR is on,
        │    display version 13/14, VRR possible)
        ▼
 crtc_vblank_start 1601 ─▶ 1600, set_context_latency 1 ─▶ 0
        │   neither is fast-settable
        ▼
 "fastset requirement not met, forcing full modeset" ─▶ -EINVAL
```

The kernel log shows the new state with `vrr: yes` and `psr: disabled`, and
`fastset requirement not met in set_context_latency (expected 1, found 0)`.
The debugfs PSR status reports the sink as capable and reliable, so PSR is
off only because of the VRR veto.

## The fix — `patches/linux/0005`

Keep the workaround's line while PSR is off only because VRR is enabled: a
new `psr_vetoed_by_vrr` in the CRTC state, set where `_psr_compute_config`
refuses PSR for VRR, keeps `_intel_psr_min_set_context_latency` at 1. One
line of set context latency without PSR costs nothing, and the VRR toggle is
fast-settable again. Verify on the laptop with the same capture: no
`Page flip failed`, and `drm_info` shows `VRR_ENABLED` 1 during full-screen
playback.

## Upstream report (draft, for the owner to send)

To `intel-gfx@lists.freedesktop.org`, with the patch from
`patches/linux/0005` (`git send-email`, after adding the sender's
`Signed-off-by`), or as an issue at
<https://gitlab.freedesktop.org/drm/i915/kernel/-/issues>:

> **drm/i915/psr: VRR cannot be enabled by a page flip on a PSR-capable
> eDP (display 14)**
>
> Hardware: ASUS ROG Zephyrus G16 (GU605MZ), Meteor Lake (display version
> 14), Samsung ATNA60DL01 eDP OLED 2560×1600 240 Hz with VRR and PSR1.
> Kernel: Ubuntu 7.3.0 (v7.3-rc5/rc6); the code is unchanged in master.
> Compositor: GNOME Shell / Mutter 51 with variable refresh enabled.
>
> When a full-screen client makes Mutter enable VRR, the atomic commit fails
> with -EINVAL. With drm.debug=0x14:
>
> ```
> fastset requirement not met in hw.adjusted_mode.crtc_vblank_start (expected 1601, found 1600)
> fastset requirement not met in set_context_latency (expected 1, found 0)
> fastset requirement not met, forcing full modeset
> ```
>
> Enabling VRR disables PSR (`_psr_compute_config`), which drops
> Wa_14015401596's set context latency from 1 to 0, moving the vblank start.
> A page flip cannot request the resulting modeset, so VRR never engages.
> The attached patch keeps the line while PSR is off only because of VRR.

## Non-goals

- **Not a PSR-with-VRR change.** PSR stays off while VRR is on, exactly as
  upstream decided; only the set context latency stops moving.
- **No compositor workaround.** Mutter allowing a modeset for the VRR toggle
  would blank the panel at every full-screen transition.
