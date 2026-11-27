# Frame-rate matching — even video cadence on the 240 Hz VRR panel

Companion to the [i915 VRR diagnosis](I915_VRR_FASTSET.md) (why fullscreen
VRR could not engage before `patches/linux/0005`) and [status](STATUS.md).
This page holds *what is proven about presentation cadence on the ROG, the
measurement that decides it for every player, and where uneven cadence is
caused*. Source claims, model predictions and measurements are kept apart
and labelled.

**Status (November 27):** source reading, a timing model and the
measurement tool are done. No new player run has been measured. Baselines need an
owner-attended window, because the session must be unlocked, a player must
be visible, and holding the per-refresh CRC open forces one i915 modeset
while PSR is active.

## What is and is not proven

| Claim | Kind | Basis |
|---|---|---|
| Panel VRR range is 48–240 Hz | Read on the laptop (Nov 27) | i915 debugfs `eDP-2/vrr_range` and the EDID range descriptor (48–240 Hz vertical) |
| Fullscreen VRR engages without page-flip errors | Bounded observation (Nov 2) | `VRR_ENABLED` 0 → 1 → 0 with stock mpv, 24 fps HDR, short run ([diagnosis](I915_VRR_FASTSET.md)) |
| Mutter enables VRR only for a fullscreen surface | Source (Mutter 51 `meta-compositor-view-native.c`, `meta_onscreen_native_allow_vrr`) | Windowed playback stays at fixed 240 Hz by design |
| Mutter adds no repeats below the VRR floor | Source (`clutter-frame-clock.c`, variable mode presents on client commit; the only timer is the 30 Hz cursor flush) | Below 48 Hz the panel hardware repeats the picture itself |
| i915 adds no repeats below the VRR floor either | Source (upstream `intel_vrr.c`: vmin/vmax/flipline only) | Hardware scans out again at vmax when no flip arrives |
| Mutter implements `wp_commit_timing_v1` and `wp_fifo_v1` | Source (`meta-wayland-commit-timing.c`, `meta-wayland-fifo.c`) | A client can ask for an exact presentation time |
| Cadence of any player, any rate, any duration | **Not measured** | — |
| NVIDIA route, external display, suspend/resume, DPMS | **Not measured** | — |

Correction to an earlier statement: at a fixed 240 Hz, 24000/1001 material
does not repeat a whole frame every 42 s. Each frame needs 10.01 refreshes,
so one frame in a hundred is held for 11 refreshes. That is a 4.17 ms
over-long hold about every 4.17 s (model below; measurement pending).

## Timing model (prediction, not measurement)

`tools/presentation_cadence.py model` simulates when each source frame first
appears. In the fixed-refresh model, a frame appears at the first refresh at
or after its due time. In the VRR model, a flip latches once the minimum frame
time has passed. With no flip by the maximum frame time, the hardware repeats
the picture, and a later flip waits out that repeat's minimum frame time. The
model ran for 120 s per rate on the 48–240 Hz range, with no commit jitter
unless stated.

| Source rate | Fixed 240 Hz | VRR 48–240, no repeats | VRR, compositor repeats ×k |
|---|---|---|---|
| 24000/1001 | 4.17 ms long hold every 4.17 s | **alternating 37.6 / 45.8 ms** | even (k = 3, 71.9 Hz) |
| 24 | even (10 refreshes) | on the edge: even only with zero jitter; 0.2 ms jitter → uneven | even (k = 3) |
| 25 | **9/10-refresh judder every frame pair** | even | even |
| 30000/1001 | long hold every 4.17 s | even | even |
| 30 | even | even | even |
| 50 | **4/5-refresh judder** | even | even |
| 60000/1001 | long hold every 4.17 s | even | even |
| 60 | even | even | even |

Two conclusions follow, still subject to measurement:

1. **Film needs repeats below the VRR floor.** 41.71 ms is just over twice
   the 20.83 ms maximum frame time, so the hardware repeat lands exactly
   where the next film frame is due. Nobody in the current stack chooses the
   repeat point. Something must present each film frame an even k times,
   k = 3 for 23.976/24/25 on this panel.
2. **Under VRR the panel shows a frame exactly when the client commits.**
   With ±1 ms of uniform commit jitter, every rate is uneven at a 0.75 ms
   tolerance, with or without repeats. Even cadence therefore also needs the
   player to target presentation times through `wp_commit_timing_v1`, or an
   equivalent compositor-side target, rather than commit when a timer fires.

Where the repeats belong (compositor frame clock, kernel driver, or neither)
is decided only after the baselines show the real behaviour. A per-player
repeat would be the kind of workaround the effort excludes.

## Measurement — `tools/presentation_cadence.py`

One instrument for every player and for windowed playback, because it reads
the display engine rather than the player:

- **Flip trace** (read-only for the display). `capture` creates a private
  tracefs instance with the `mono` clock and records `intel_crtc_flip_done`,
  `intel_plane_update_arm` and `drm_vblank_event`. It removes the instance
  on exit, interrupt or `SIGTERM`. Each flip on the chosen pipe is one new
  picture. The hardware frame counter gives the number of refreshes it
  stayed on screen, and cursor-only commits are excluded.
- **Per-refresh content identity** (`--crc-crtc N`). Holding
  `crtc-N/crc/data` open captures the i915 pipe CRC of every refresh with
  the default `auto` source. That file is read-only, so kernel lockdown
  permits it; `control` is not readable under lockdown. Consecutive equal CRCs
  are one picture, a CRC that returns later is a picture shown again, and
  frame-counter gaps mark lost refreshes. The cost: i915 forces a full
  modeset when CRC is enabled while PSR is active
  (`intel_crtc_crc_setup_workarounds`), and PSR stays off during capture.
  Use it only in an attended window, and record the PSR state before and after.
- **Fixtures.** `scripts/generate_cadence_fixtures.py` writes 11-minute
  synthetic SDR or HDR10 files at the eight exact rates (24000/1001, 24, 25,
  30000/1001, 30, 50, 60000/1001, 60). Every frame differs (FFmpeg
  `testsrc2` plus a drawn frame number). A white bar on the first frame of each
  second and a 20 ms click give a later A/V sync check. Output goes
  outside the repository; nothing private is involved.
- **Verdict.** `analyze --rate N/D` skips start-up and reports frames,
  median/min/max/stdev durations, refresh and duration histograms,
  frames off the median by more than 0.75 ms, holds over 1.5 periods, the
  interval between irregularities, and *even* / *uneven* / *incomplete*.
  Exit status is 0 only for *even*.

The analyzer is covered by `tests/test_presentation_cadence.py`, and the
fixture generator by `tests/test_generate_cadence_fixtures.py`. A 3 s capture
on the laptop on November 27, with the display off, created and removed its
instance and recorded no events. That proves the capture lifecycle only.

## Baseline plan (owner-attended)

For each player (mpv, Plurx Player, Showtime, a GtkVideo test window, HTML
`<video>` in the patched WebKitGTK browser), fullscreen and windowed:
capture 10.5 minutes per fixture rate, with flip trace and CRC, on the
Intel route. Record `VRR_ENABLED`, PSR and DisplayConfig before and after,
and page-flip errors from the Shell journal. The NVIDIA route and an
external display follow in the same way, or are recorded as limits.

## Limits

No optical measurement; CRC equality is digital identity at the pipe
output, not light from the panel. No motion interpolation is in scope.
