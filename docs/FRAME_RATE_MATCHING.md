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
| 23.976, 29.97, 59.94 | 10.01, 8.008, 4.004 | Even, with one frame held 4.17 ms longer every 1001/240 s = 4.17 s (one extra refresh per 100, 125 and 250 frames); *corrected 2026-11-27* |
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

**Read on the ROG, November 27 (read-only):**

| Item | Result | How |
|---|---|---|
| 1. VRR range | **48–240 Hz**. The maximum frame time is 20.83 ms. The EDID's only native timings are 2560×1600 at 240.000 Hz and 60.000 Hz (same 1125.28 MHz clock, vtotal 1776 / 7104) | i915 debugfs `eDP-2/vrr_range`; EDID range descriptor; DisplayID type VII decode |
| 2. Variable mode selected | Yes: `2560x1600@240.000+vrr` is current, refresh-rate-mode `variable` | `DisplayConfig.GetCurrentState`; `monitors.xml` `<ratemode>variable</ratemode>` |
| 3. Mutter 51.0-1ubuntu3+nativehdr17 globals | `wp_presentation` 2, `wp_fifo_manager_v1` 1, `wp_commit_timing_manager_v1` 1, `wp_color_manager_v1` 2 | Raw Wayland registry query on the session socket |
| 4. mpv 0.42.0 | Binds `wp_fifo_manager_v1` and `wp_presentation`, not `wp_commit_timing`. Display fps comes from `wl_output` (240 Hz), and a zero feedback interval falls back to 1/240 s. There is **no** presentation-v3 refresh-kind or "display follows" handling in 0.42; the `vo.c` behaviour in section 5 is mpv master | Binary interface strings; 0.42.0 `video/out/wayland_common.c`, `video/out/vo.c` |
| GTK 4, WebKitGTK, waylandsink | GTK 4 binds `wp_presentation` only; the other two name none of the three protocols | Binary interface strings |
| 5. Surface and feedback per player | Not yet checked; needs running players | — |

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
| Kernel flip trace | When the CRTC actually flipped | Tracepoints `i915:intel_crtc_flip_done`, `i915:intel_plane_update_arm` and `drm:drm_vblank_event`, filtered to the panel's pipe, recorded by a Python tracefs instance (`tools/cadence/presentation_cadence.py capture`) that never leaves a tracer enabled. Needs root, so it runs only in an owner-attended window. It validates that the compositor's reported times are real flips and shows compositor-initiated repeats. *Changed from bpftrace 2026-11-27.* |
| Content identity | Which source frame each refresh showed | The i915 pipe CRC of every refresh, read by holding debugfs `crtc-N/crc/data` open with the default `auto` source. The file is read-only, so Secure Boot lockdown permits it. Fixtures cycle through 16 distinct full-frame patterns, and a calibration pass frame-steps once through the cycle recording each pattern's CRC. The per-refresh stream then decodes to a frame index modulo 16, which exposes skipped as well as repeated source frames. It is not a timing source. *Replaces the screencast strip, 2026-11-27.* |

Conditions on the CRC, set by the coordinating session:

- Before trusting it, show that a paused frame gives a constant CRC with the pointer hidden, and that HDR output does not make it vary (dithering or a compositor overlay would).
- Enabling it while PSR is active forces one full modeset (`intel_crtc_crc_setup_workarounds`), and PSR stays off while it is open. It is opened once per attended window, and the CRC source is switched off again before the window ends.

Player-internal counters are recorded alongside, never instead: mpv's `frame-drop-count`, `mistimed-frame-count`, `vo-delayed-frame-count`, `vsync-jitter` and `avsync` over IPC; GStreamer QoS messages for Showtime and GtkVideo.

### 4.2 Fixtures

Generated with FFmpeg into an owned directory on the external drive, never committed:

- 23.976, 24, 25, 29.97, 30, 50, 59.94 and 60 fps, 1080p, at least eleven minutes. Source frame n shows pattern n mod 16 (a distinct flat level) with a vertical bar that moves with the same period, so the owner can also see judder. The pictures repeat exactly every 16 frames for CRC decoding.
- MP4 with a track timescale that divides the frame period exactly, so source timestamps carry no rounding.
- One Matroska fixture at 23.976 fps as a separate case. Real titles are often Matroska, whose 1 ms timestamps give ±0.5 ms rounding that players must cope with. It is judged against the threshold separately, and the result says so.
- A silent variant and one with a 1 kHz tick each second for the sync check.
- One HDR10 and one Dolby Vision Profile 8.1 variant at 23.976 fps, built from the project's existing chart, for the picture-unchanged check.
- One file that changes from 23.976 to 59.94 fps mid-stream.
- *Changed 2026-11-27:* no screencast frame-index strip.

### 4.3 Tooling and output

`tools/cadence/` in `rog_hdr_dv`:

- `make_fixtures.py`: the FFmpeg recipes (Python, unit-tested).
- `parse_wayland_debug.py`: surface selection and per-commit presented times.
- `presentation_cadence.py`:
  - `capture`: tracefs flip trace and optional CRC hold, never leaving a tracer enabled.
  - `analyze`: interval histogram, maximum deviation, repeats and drops, periodicity, CRC calibration decoding, and the pass/fail of section 1. Output is one JSON receipt per run under `evidence/`, with no raw captures.
  - `model`: the timing predictions of section 12.

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
- **Fix location if confirmed** (*updated 2026-11-27*): both halves are needed.
  - Mutter advertises `wp_presentation` version 3 and sets the variable-rate flag on feedback while the view's frame clock is in variable mode. This is a small, upstreamable change in `src/wayland/meta-wayland-presentation-time.c`, and it tells every client.
  - The project's mpv 0.42 series backports mpv master's variable-refresh handling. 0.42 has none, so without it the Mutter half changes nothing for mpv.
  - Do not fix it with an mpv option in plurx Player's launcher.

### H2. The panel's own repeat collides with film frames in variable mode (*replaced 2026-11-27*)

- **[repo, read]** With a 48–240 Hz range the panel's maximum frame time is 20.83 ms. When no flip arrives by then, the hardware scans the same picture out again. **[source]** Neither Mutter nor i915 adds repeats of its own. Mutter's 30 Hz constant only bounds flush updates the KMS thread raises, such as a cursor move. It does not re-present video.
- **Prediction:** a 23.976 fps frame (41.71 ms) arrives just after the second forced refresh has started (2 × 20.83 = 41.67 ms) and must wait out that refresh's minimum frame time. Durations alternate near 37.6 and 45.8 ms. 24.000 fps sits on the edge and may race either way. 25 fps and faster are unaffected. Variable mode can therefore be *worse* than fixed 240 Hz for film until the compositor compensates.
- **Test:** flip trace and CRC stream at 23.976, 24 and 25 fps, in both fixed and variable mode, compared directly.
- **Fix location if confirmed:** Mutter's frame clock presents each content frame as n even flips. n is the smallest integer with `content_interval / n` at or below the panel's maximum frame time less a safety margin. The margin is derived from the measured spread of flip latency (commit to flip-done) in the baselines and stated with its derivation.
  - That gives n = 3 for 23.976 and 24 (13.9 ms), n = 2 for 25, 29.97 and 30, and n = 1 for 50 and above, for any margin up to 0.8 ms.
  - The content interval comes from `wp_commit_timing_v1` targets when a client supplies them. Otherwise it comes from the measured update period of the fullscreen surface, because mpv 0.42 and GTK do not use commit-timing.
  - The maximum frame time comes from the EDID minimum Mutter already holds (`meta_output_info_get_min_refresh_rate`). The hard-coded constant is not used for this.

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

- **[repo, read 2026-11-27]** The internal panel offers only 240 Hz and 60 Hz timings, so it has no 120 Hz or 100 Hz mode. Mode switching is relevant only to external displays.
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

## 12. Results (dated)

Sections 1–11 above are the design of record, written by the coordinating
session. Corrections it agreed are marked with their date. Results are added here.

### Corrections adopted 2026-11-27

The frame-rate session sent five points back to the coordinating session, which agreed to all of them. They are now part of sections 1–9:

- **A.** The section 1 beat period.
- **B.** The new H2 mechanism.
- **C.** The even-repeat count rule.
- **D.** The VRR minimum comes from the EDID.
- **E.** The two-part H1 fix and the absence of a 120 Hz mode.

The measurement changes (pipe CRC, Python tracefs, Python tooling, MP4 plus one Matroska case) are also adopted. The section 3 facts moved into section 3.

### Timing model (prediction, not measurement)

`tools/cadence/presentation_cadence.py model` simulates presentation under fixed
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

### Measurement tooling (November 27; unit-tested, no player run yet)

- **`tools/cadence/presentation_cadence.py`**
  - `capture` (root, attended) records `intel_crtc_flip_done`, `intel_plane_update_arm`, `drm_vblank_event` and `intel_pipe_crc` into a private tracefs instance with the mono clock. It removes the instance on exit or `SIGTERM`. `--crc-crtc N` holds the pipe CRC open for the run.
  - `calibrate` turns a frame-stepped CRC capture into the 16 pattern CRCs (plus the sync flash). It refuses a cycle that does not repeat, or two patterns with one CRC.
  - `analyze --calibration` decodes every refresh to a pattern index and reports skipped source frames, earlier frames shown again and pictures outside the fixture (for example an OSD), alongside the timing verdict. Without a calibration it reports change-only identity.
  - `model` gives the predictions above.
  - A 3 s run on the ROG with the display off created and removed its instance. That shows only the capture lifecycle.
- **`tools/cadence/parse_wayland_debug.py`** pairs `wp_presentation.feedback` requests with their surface, even when object ids are reused. It records `presented` time, refresh and flags or `discarded`, picks the video surface, and reports the same metrics.
- **`tools/cadence/make_fixtures.py`** builds fixtures:
  - Variants: `standard` (MP4, click and sync flash), `silent`, `matroska` (23.976 only, default 1 ms timestamps) and `rate-change` (23.976 then 59.94, timescale 120000).
  - Source frame n is pattern n mod 16: a flat level and a bar moving with the same period.
  - Encoding is intra-only at constant QP with adaptive quantisation off, because inter prediction made frame n and n+16 decode differently.
  - On the ROG on November 27, `framemd5` of 4 s encodes of each variant read 16 distinct pictures plus the flash, all repeating exactly. Durations read back as 1001/24000, 3600/90000 and 5005/2002 per 120000 for the rate change. Matroska read back 41 ms, as expected.
- **Tests:** `tests/test_presentation_cadence.py`, `tests/test_parse_wayland_debug.py`, `tests/test_generate_cadence_fixtures.py` (43 checks).
