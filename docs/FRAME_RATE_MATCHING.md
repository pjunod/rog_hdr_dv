# Frame-rate matching on the ROG — implementation design (E-9B301F9CFD)

**Status:** design of record, written 2026-11-27 by the coordinating session.
**Applies to:** Ubuntu 26.10, Mutter 51 on Wayland, the ROG's internal panel (Samsung ATNA60DL01-0, 2560×1600, 240 Hz, VRR, driven by i915 on Meteor Lake).

Every statement is marked by where it comes from:

- **[repo]** recorded in `rog_hdr_dv` (file named).
- **[source]** read in upstream source on the main branch (Mutter 51.1, GTK 4.25.2, mpv master, Linux master). The shipped Ubuntu packages may differ, so each one a decision depends on is listed in section 3 to confirm.
- **[hypothesis]** a predicted cause. It is to be tested by measurement, not assumed, and not fixed until measured.
- **[decision]** a design choice made here. Deviate only after telling the coordinating session why.

## 1. What "matched" means here

A source frame is matched when it is on the panel for its own duration, `1/fps`, every time. Two things can break that:

- **Quantisation:** the display only changes at fixed instants, so frame durations round to a multiple of the refresh period.
- **Scheduling:** the player or compositor delivers a frame late, early, or twice.

This panel's fixed mode is already forgiving. At 240 Hz the refresh period is 4.17 ms:

| Source rate | Refreshes per frame at 240 Hz | Result at a fixed 240 Hz |
|---|---|---|
| 24, 30, 60 | 10, 8, 4 exactly | Even |
| 23.976, 29.97, 59.94 | 10.01, 8.008, 4.004 | Even, with one frame held 4.17 ms longer about every 42 s, 33 s and 17 s |
| 25 | 9.6 | Uneven: durations alternate between 9 and 10 refreshes (37.5 and 41.7 ms) |
| 50 | 4.8 | Uneven: 4 and 5 refreshes (16.7 and 20.8 ms) |

So the work is not "make 24p watchable". It is: remove the periodic long frame for the NTSC rates, make 25 and 50 fps even, prove the players are not adding scheduling errors on top, and then solve the case where quantisation is severe, which is an external 60 Hz display (3:2 pulldown for 24 fps).

**[decision]** Acceptance thresholds, used throughout:

| Mode | Pass for a ten-minute run |
|---|---|
| Variable refresh active | Every presented interval within 1.0 ms of `1/fps`; no repeated or dropped source frame |
| Fixed refresh | Every presented interval within one refresh period of `1/fps`; the sequence of durations is the best rounding of the ideal timeline (no error accumulates, no extra long or short frame beyond what the table above predicts); no repeated or dropped source frame |

## 2. What is already known

- **[repo]** `docs/I915_VRR_FASTSET.md`: without `patches/linux/0005`, Mutter's fullscreen `VRR_ENABLED=1` commit fails with `drmModeAtomicCommit: Invalid argument`, because i915 turns PSR off when VRR turns on, which changed the set-context latency and forced a modeset. With the patch the toggle is a fastset.
- **[repo]** The November 2 pass: stock mpv, silent HDR 24 fps fixture, `VRR_ENABLED` went 0 → 1 → 0 around fullscreen with no flip errors. It did not measure cadence. `docs/STATUS.md` says capture timestamps followed the source rate and that this "is not panel-cadence acceptance".
- **[repo]** `patches/ubuntu-mesa-wayland-hdr/0002` keeps Vulkan Wayland FIFO deadlines in the compositor's clock. Before it, a request could be about 4 s late; after it the median was 16.17 ms on a 60 Hz compositor. mpv's Vulkan path depends on this.
- **[repo]** No project patch to Mutter, GTK, gtk4paintablesink, mpv or WebKitGTK changes frame clocks, commit timing or sync defaults. plurx Player's launcher (`clients/linux-player/plurx_player/mpv.py`) sets no `video-sync`, `interpolation` or `display-fps` option, so mpv runs with `video-sync=audio`.
- **[repo]** The internal panel is on i915 only. The NVIDIA GPU does not drive it (`docs/HARDWARE.md`).

## 3. Facts to confirm first (read-only)

Record each in the status page before designing a fix around it.

1. The panel's VRR range: the EDID range-limits descriptor, and i915's view of it in debugfs for the connector. In particular whether the minimum is at or below 24 Hz, between 24 and 48 Hz, or 48 Hz.
2. Whether the owner's session has the variable-refresh mode selected for the panel (`monitors.xml` and `DisplayConfig`), since **[source]** Mutter exposes VRR as a twin "variable" mode of each KMS mode and only enables VRR when that mode is current.
3. The installed Mutter's protocol versions: `wp_presentation` (main advertises 2), `wp_fifo_v1` and `wp_commit_timing_v1` (both present on main). Read them with `wayland-info`.
4. The installed mpv 0.42 package: whether it binds `wp_fifo` and `wp_presentation`, which Vulkan present mode it selects, and whether it has the variable-refresh handling in `vo.c` described in section 5.
5. Which Wayland surface each player commits video on (toplevel, or a subsurface) and whether it asks for presentation feedback on that surface.

## 4. The measurement

Nothing is fixed before this exists. It must work for every player without modifying the player.

### 4.1 Per-frame presentation times

**[decision]** Three sources, used together:

| Layer | What it gives | How |
|---|---|---|
| Client protocol trace | For each video commit, the time the compositor says it reached the screen, and the feedback flags | Run the player with `WAYLAND_DEBUG=1`, parse `wl_surface.commit`, `wp_presentation.feedback` and `wp_presentation_feedback.presented`/`discarded` for the video surface. Works for mpv, GTK and WebKit's UI process. If a player does not request feedback on its video surface (section 3, item 5), say so and use the next two layers for it. |
| Kernel flip trace | When the CRTC actually flipped | Tracepoints `i915:intel_crtc_flip_done`, `i915:intel_pipe_update_start/end` and `drm:drm_vblank_event_delivered`, filtered to the panel's pipe. Needs root, so it runs only in an owner-attended window. It validates that the compositor's reported times are real flips and shows compositor-initiated repeats. |
| Content identity | Which source frame each presentation showed | Fixtures carry the frame index as a strip of large black/white blocks (binary code, plus a parity block) along the top edge. A PipeWire screencast of the monitor, read with the existing `tools/sample-screen-pixel.c` approach, recovers the index per captured frame. This catches a repeated or skipped source frame that timing alone cannot. It is not a timing source. |

Player-internal counters are recorded alongside, never instead: mpv's `frame-drop-count`, `mistimed-frame-count`, `vo-delayed-frame-count`, `vsync-jitter` and `avsync` over IPC; GStreamer QoS messages for Showtime and GtkVideo.

### 4.2 Fixtures

Generated with FFmpeg into an owned directory on the external drive, never committed:

- 23.976, 24, 25, 29.97, 30, 50, 59.94 and 60 fps, 1080p, at least eleven minutes, with the frame-index strip and a moving vertical bar (so the owner can also see judder).
- A silent variant and one with a 1 kHz tick each second for the sync check.
- One HDR10 and one Dolby Vision Profile 8.1 variant at 23.976 fps, built from the project's existing chart, for the picture-unchanged check.
- One file that changes from 23.976 to 59.94 fps mid-stream.

### 4.3 Tooling and output

`tools/cadence/` in `rog_hdr_dv`:

- `make-fixtures.sh`: the FFmpeg recipes.
- `parse-wayland-debug.py`: surface selection and per-commit presented times.
- `flip-trace.bt` (bpftrace) with a wrapper that records start and end and never leaves a tracer running.
- `analyse.py`: interval histogram, maximum deviation, repeats and drops, periodicity (autocorrelation of the interval error), and the pass/fail of section 1. Output is one JSON receipt per run under `evidence/`, with no raw captures.

Unit tests for the parser and the analyser use synthetic traces, including the exact patterns in the section 1 table, and run in the Python fast lane.

### 4.4 Where runs happen

- A private nested or headless Mutter cannot show VRR, so it is used only to develop the tooling.
- Real runs are on the ROG's own session. They play fullscreen video on the owner's display, so they happen in an attended window. They change no setting.

## 5. Predicted causes, to be tested in this order

Each is a hypothesis with the measurement that confirms or kills it and the place a fix would go. Do not write the fix first.

### H1. mpv times frames to a 240 Hz grid even when VRR is active

- **[source]** mpv learns that a display is variable-rate from `wp_presentation` version 3 feedback flags. Mutter advertises version 2, so mpv's refresh kind stays unknown. **[source]** Mutter reports a refresh interval of 0 on a variable mode, and mpv then falls back to the output mode's nominal rate, 240 Hz. With `video-sync=audio` and presentation feedback, mpv aims each frame half a refresh before the nearest refresh of that nominal grid. A fallback in `vo.c` infers "the display follows" only when more than half of frames are shown at once.
- **Prediction:** fullscreen with VRR on, intervals still show the fixed-240 pattern from section 1.
- **Test:** 23.976 and 25 fps fixtures, VRR mode selected, mpv fullscreen; compare the interval histogram with the fixed-mode table.
- **Fix location if confirmed:** Mutter, by advertising `wp_presentation` version 3 and setting the variable-rate flag on feedback while the view's frame clock is in variable mode. This is a small, upstreamable change in `src/wayland/meta-wayland-presentation-time.c`, and it tells every client, not just mpv. Do not fix it with an mpv option in plurx Player's launcher.

### H2. Mutter repeats frames unevenly below 30 fps

- **[source]** In variable mode Mutter's frame clock has a hard-coded minimum of 30 Hz (`MINIMUM_REFRESH_RATE` in `clutter-frame-clock.c`), so it re-presents the same content at most 33.3 ms after the last flip. It has no low-framerate compensation of its own, and none was found in i915.
- **Prediction:** at 24 fps each source frame is shown as a 33.3 ms flip followed by an 8.4 ms flip. The source frame's total duration is right, but the panel's refresh interval alternates. On an OLED that can show as brightness flicker, because panel luminance depends slightly on the refresh interval.
- **Test:** kernel flip trace at 23.976, 24 and 25 fps; look for the 33.3 / 8.4 alternation. Owner observation of a flat mid-grey fixture for flicker.
- **Fix location if confirmed:** Mutter's frame clock. When the fullscreen surface updates more slowly than the maximum interval, schedule the repeats evenly: `n = ceil(content_interval / max_interval)` flips of `content_interval / n` each (two flips of 20.85 ms for 23.976 fps). The content interval comes from the client's `wp_commit_timing_v1` target times when present, otherwise from the measured period of the fullscreen surface's updates over the last several frames. The maximum interval should come from the panel's real VRR minimum (section 3, item 1) instead of the constant, if the kernel exposes it to userspace; if it does not, keep the constant and record that.
- If the panel's VRR minimum is at or below 24 Hz and the kernel accepts a 41.7 ms interval, the simplest correct result is no repeat at all. Establish that before designing the even split.

### H3. Extra flips from the cursor or on-screen display

- **Prediction:** pointer motion or mpv's on-screen controller causes additional flips in variable mode, changing refresh intervals while visible. Source-frame cadence stays right.
- **Test:** flip trace with the pointer still, moving, and with the OSD shown.
- **Fix location:** Mutter (how cursor updates are folded into a variable-mode frame). Record only, unless the owner sees it; the report did not verify Mutter's cursor behaviour.

### H4. The GTK players add main-loop jitter

- **[source]** `gtk4paintablesink` hands each frame to the GTK main context through a bounded channel and invalidates the paintable; the picture is committed on GTK's next frame-clock paint. GTK is driven by `wl_surface` frame callbacks, binds `wp_presentation` at version 1, and uses neither `wp_fifo` nor `wp_commit_timing`. The offload subsurface commits itself.
- **Prediction:** in fixed mode, quantisation as in section 1 plus occasional one-refresh errors when the main loop is busy. In variable mode, jitter equal to main-loop latency.
- **Test:** Showtime and the GtkVideo widget with each fixture; compare with mpv on the same fixture.
- **Fix location if it fails the threshold:** the sink and GTK, by giving each video commit its target time through `wp_commit_timing_v1` so the compositor, not the main loop, decides the instant. That is a larger change; measure before proposing it.

### H5. WebKitGTK video rides the page compositor

- Not verified in any source. **Test first**, same fixtures in the patched WebKitGTK, both for the independent HDR video plane and for the in-page SDR composition (`docs/WEBKIT_NATIVE_HDR.md` describes when each is used).

### H6. Decode or mapping cannot keep up

- A Dolby Vision or 4K title that drops frames is not a cadence problem. Separate it: the frame-index strip shows skipped source frames, and the player counters show drops. Record it and hand it to the owning effort; do not tune sync around it.

## 6. Design rules for any fix

1. **Fix in the owning component.** Compositor facts (variable-rate flag, even repeats) go in Mutter. A player that ignores a correct signal is fixed in that player. No per-player launch options to paper over a compositor gap.
2. **No colour-path changes.** Nothing here may alter targets, descriptions or mapping. Verify with the held-frame comparison (section 8).
3. **Upstreamable shape.** New Mutter patches go in `patches/ubuntu-mutter` and the upstream-facing series, written so they can be submitted; the existing series is current on upstream main and must stay so.
4. **No timers that guess.** A fix uses presentation feedback, commit-timing targets or measured update periods. It does not add a watchdog or a retry.
5. **A Mutter install is a compositor replacement.** It happens only in a coordinated owner-attended window with the rollback packages staged, as the project's operations document requires.

## 7. Windowed playback

**[decision]** Windowed video keeps a fixed refresh. **[source]** Mutter enables VRR only when a fullscreen candidate covers the view exactly, with no effects and unobscured. Driving the whole desktop at one window's rate would make everything else on screen judder.

- Behaviour to document: at 240 Hz the error is bounded by 4.17 ms and follows the table in section 1.
- Requirement: the fixed-mode threshold of section 1 holds windowed for every player. A player that does worse than the best rounding has a scheduling fault to attribute.

## 8. Lifecycle and regression checks

| Case | Check |
|---|---|
| Enter and leave fullscreen | `VRR_ENABLED` 0 → 1 → 0, no page-flip errors in the journal, `monitors.xml` and `DisplayConfig` unchanged afterwards |
| Pause, resume, seek | No stuck repeat cadence after resume; first frame after a seek is not counted against the threshold, the next 100 are |
| Mid-stream rate change | Intervals follow the new rate within one second |
| Player exit and `SIGKILL` | Display returns to its prior state; no VRR left enabled with no fullscreen window |
| Picture unchanged | Paused Dolby Vision and HDR10 frame captured with the pixel sampler, VRR mode on and off: identical |
| Audio sync | mpv `avsync` over a full-length title stays within ±20 ms; for GStreamer players, the tick fixture's audio and flash align within the same bound by the owner's observation. State the measured value. |
| Suspend and resume during playback | Record the result; a failure here belongs with the open suspend/resume acceptance in `docs/STATUS.md` |

## 9. External displays and the NVIDIA route

This is where quantisation is severe: a 60 Hz television shows 24 fps as 3:2 pulldown.

- **First establish the hardware facts** (read-only): which connector each external port is wired to, which GPU drives it, and what modes and VRR capability a connected display reports. If no external display is available, record criterion 7 as waiting on named hardware and stop here.
- **[decision]** Preference order for an external display:
  1. Variable refresh, if the display and the driving GPU support it. Sections 5 and 6 then apply unchanged.
  2. Otherwise a mode whose refresh is an integer multiple of the content rate (120 Hz for 24, 30 and 60 fps; 100 Hz for 25 and 50 fps; 23.976 or 24 Hz as a last resort).
- **Mode switching design, if case 2 is needed.** No Wayland protocol lets a client change the mode, so this needs a small session service using Mutter's `org.gnome.Mutter.DisplayConfig`:
  - It applies a **temporary** configuration (never persisted to `monitors.xml`) when a client that has asked for it goes fullscreen on that output, and restores the previous configuration when the request ends.
  - A request is tied to the requesting client's D-Bus connection. When the name vanishes, including on a crash, the service restores. That is ownership of a resource, not a playback watchdog.
  - The request carries the content rate; the service chooses the mode. Players ask through one small API (mpv through a script hook in the package, GStreamer players through the sink's negotiated frame rate).
  - HDR and the colour target must be re-read after the switch, since a mode change can change both.
  - Write this as its own section of the design and send it to the coordinating session before building it. It is only worth building if an external display is actually in use.

## 10. Order of work

1. Section 3 facts, read-only.
2. Tooling and fixtures (section 4), with unit tests, developed against a private compositor.
3. Attended window 1: baseline every player, fixed mode and variable mode, fullscreen and windowed, with the flip trace. Produce the receipts.
4. Attribute: confirm or kill H1–H6 from the receipts. Report the attribution to the coordinating session before writing fixes.
5. Fixes in the owning components, each with a regression test where the component has a test suite.
6. Attended window 2: install, repeat the failed measurements and the lifecycle table.
7. External display facts and, if hardware exists, section 9.
8. `docs/FRAME_RATE_MATCHING.md` (this design, updated with results), `README.md` and `docs/STATUS.md`.
9. Review by the coordinating session, fast lane once, merge.

## 11. Report back

- The section 3 facts.
- The baseline receipts and the attribution for each hypothesis, before any fix.
- Anything that contradicts a **[source]** statement in the shipped packages.

## 12. Results and contested points (dated)

Sections 1–11 above are the design of record. They are kept as written by the
coordinating session. Results are added here; a point marked *contested* has
been sent to the coordinating session with its evidence and is not yet
decided.

### November 27 — section 3 facts (read-only on the ROG)

| Item | Result | How |
|---|---|---|
| 1. VRR range | **48–240 Hz**. The EDID's only native timings are 2560×1600 at 240.000 Hz and 60.000 Hz (same 1125.28 MHz clock, vtotal 1776 / 7104); there is no 120/144 Hz mode | i915 debugfs `eDP-2/vrr_range`; EDID range descriptor; DisplayID type VII decode |
| 2. Variable mode selected | Yes: `2560x1600@240.000+vrr` is current, refresh-rate-mode `variable` | `DisplayConfig.GetCurrentState`; `monitors.xml` `<ratemode>variable</ratemode>` |
| 3. Mutter globals (51.0-1ubuntu3+nativehdr17) | `wp_presentation` 2, `wp_fifo_manager_v1` 1, `wp_commit_timing_manager_v1` 1, `wp_color_manager_v1` 2 | Raw Wayland registry query on the session socket |
| 4. mpv 0.42.0 | Binds `wp_fifo_manager_v1` and `wp_presentation`, not `wp_commit_timing`. Display fps comes from `wl_output` (240 Hz), and a zero feedback interval falls back to 1/240 s. There is no presentation-v3 refresh-kind or "display follows" handling in 0.42 (that is mpv master) | Binary interface strings; 0.42.0 `video/out/wayland_common.c`, `video/out/vo.c` |
| GTK 4, WebKitGTK, waylandsink | GTK 4 binds `wp_presentation` only; the other two name none of the three protocols | Binary interface strings |
| 5. Surface and feedback per player | Not yet checked; needs running players | — |

### Contested points (sent November 27)

- **Section 1 beat period.** At 240 Hz, 23.976 fps needs 10.01 refreshes
  per frame, so one frame in 100 is held 11 refreshes: every **4.17 s**.
  The same holds for 29.97 (1 in 125) and 59.94 (1 in 250). The table's
  42/33/17 s is the beat a 24 Hz display would have.
- **H2 mechanism.** In the shipped Mutter source, `MINIMUM_REFRESH_RATE` sets
  only the interval of `clutter_frame_clock_schedule_flush_update()`. That
  runs when the KMS thread holds an update the frame clock did not submit,
  such as a cursor move. Nothing re-presents video on a timer in variable
  mode. The panel's own repeat comes first, at 1/48 Hz = 20.83 ms.
- **H2 fix arithmetic.** For 23.976 fps, two flips of 20.85 ms exceed the
  20.83 ms maximum frame time, so the hardware repeat still fires before
  each. Three flips (13.9 ms, 71.9 Hz) clear it, with margin.
- **Measurement deviations proposed.** Content identity from the
  per-refresh i915 pipe CRC rather than a screencast. A Python tracefs flip
  trace rather than bpftrace. MP4 fixtures with an exact track timescale,
  because Matroska's 1 ms timestamps add ±0.5 ms of PTS jitter.

### Timing model (prediction, not measurement)

`tools/presentation_cadence.py model` simulates presentation under fixed
refresh, or under VRR where the hardware repeats at the maximum frame time
and a late flip waits out that repeat's minimum frame time. Its predictions,
pending the baselines:

| Source rate | Fixed 240 Hz | VRR 48–240, no repeats | VRR with 3 even repeats |
|---|---|---|---|
| 23.976 | 4.17 ms long hold every 4.17 s | alternating 37.6 / 45.8 ms | even |
| 24 | even | even only with zero commit jitter; 0.2 ms breaks it | even |
| 25 | 9/10-refresh alternation | even | even |
| 29.97, 59.94 | long hold every 4.17 s | even | — |
| 30, 60 | even | even | — |
| 50 | 4/5-refresh alternation | even | — |

With ±1 ms of uniform commit jitter, every rate fails the 1.0 ms
variable-refresh threshold. Even cadence under VRR therefore also needs
clients to target presentation times.

### Measurement tooling so far

- `tools/presentation_cadence.py`:
  - `capture` (root, attended) records `intel_crtc_flip_done`, `intel_plane_update_arm`, `drm_vblank_event` and `intel_pipe_crc` into a private tracefs instance with the mono clock. It removes the instance on exit or `SIGTERM`. `--crc-crtc N` also holds the pipe CRC open.
  - `analyze` gives per-frame durations, refresh counts and an even/uneven verdict.
  - `model` is the table above.
  - A 3 s run on the ROG with the display off (November 27) created and removed its instance. That shows only the capture lifecycle.
- `scripts/generate_cadence_fixtures.py` writes 11-minute SDR or HDR10 MP4 fixtures at the eight exact rates, with a drawn frame number, a per-second bar and a click. 5 s probes read back exact durations and PQ/BT.2020 tags. The frame-index strip, moving bar, silent variant, DV P8.1 chart variant and rate-change file of section 4.2 are still to add.
- Tests: `tests/test_presentation_cadence.py`, `tests/test_generate_cadence_fixtures.py`.
