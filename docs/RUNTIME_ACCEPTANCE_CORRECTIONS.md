# Runtime acceptance corrections — caption mask, first-presentation attribution, seek references

**State: designed, not implemented or run · November 26, 2026.** This page
corrects the three harness defects behind the failed November 20 Showtime
caption/target attempt and the incomplete browser source/seek cohort
([recovery record](UBUNTU_UPDATE_RECOVERY.md#ordinary-video-colour-correction-after-restoration),
[status](STATUS.md)). It changes no acceptance threshold. Each correction comes
from source code or from source-only offline runs. Retained captures are used
only as labelled diagnostics. Acceptance still requires a fresh run on the
lab host, with each model frozen before capture.

Evidence classes used below: **source** (read from the pinned GTK 4.24.1,
GStreamer base, sink or player source), **offline** (a CPU-only run of the
normal component with no display), **retained** (the November 20 run's own
logs and captures) and **diagnostic** (a retained capture scored against a
model it did not produce; never acceptance).

## 1. Caption mask v2

### Cause

The v1 mask re-implemented the caption raster with Pango/Cairo. It defined its
glyph core as projected screen pixels whose four bilinear source texels all
had **alpha** ≥ 250/255. The evaluator then requires all three RGB10 channels
of each core pixel to lie within the white interval.

- **Source/offline.** The host's fontconfig selects subpixel antialiasing for
  the caption font (`rgba` rgb, default LCD filter). Cairo therefore writes
  separate red, green and blue coverage into the ARGB32 raster, and alpha
  holds the maximum. A glyph-edge texel can have alpha 251 with red coverage
  213. An alpha-only core admits such texels, and their dimmest channel lands
  below the white bound after composition.
- **Offline.** The normal `textoverlay` element was run on a black 1920×1080
  frame with the run's font and cue, and its overlay composition was
  extracted. Its colour channels equal the v1 composite raster in every texel
  (0 differing colour bytes). Of the 8,212 texels in v1's alpha core, 1,275
  have a colour channel below 250 (minimum 196).
- **Offline, not attributed.** Alpha differs in 8,023 outline/shadow texels;
  the real raster has 304 nonzero-alpha texels where v1 has zero. v2 removes
  the re-implementation, so this difference no longer matters.
- **Retained, refuted alternative.** A window-scaled caption raster would also
  produce soft edges, but the run's GStreamer log rules it out. It records
  render scale 1, a 795×51 buffer equal to the 795×51 render rectangle at
  (562, 986), and ink rect (0, 8) 262×14. The renderer's allocation query
  returned no overlay-composition meta, so the player's window size never
  reached it.

The November 26 write-up attributed the failure to the bilinear footprint
modelling a 1.5× downscale incorrectly. That attribution is superseded: the
footprint is right, and the per-channel coverage was missing.

### Model

1. **Raster:** the actual composition produced by the installed
   `textoverlay` element, run offline under the player's font environment:
   system fontconfig, and a private HOME and XDG directories with no user font
   configuration. The cue, font description and element properties must match
   the run, and the result is checked against the run's own logged ink rect,
   buffer size, render size and position. A mismatch rejects the mask. If the
   buffer and render sizes differ (a window-scaled state), a new mask is
   generated for that state; the projection is never stretched to fit.
2. **Projection (source, GTK 4.24.1 GSK GPU renderer):** the sink appends a
   texture node with bounds = viewport origin + render rectangle × (720/1080).
   That is (374.667, 697.333, 530, 34) in window pixels, with scale 1.
   - Snapping is off: `GSK_RECT_SNAP_NONE` is the snapshot default, and
     neither the player nor the sink sets one.
   - The texture is not mipmapped: `texture_node_should_mipmap` is false
     because 795 ≤ 2 × 530.
   - Sampling is therefore plain bilinear on the linear sampler. A pixel's
     texel coordinates are u = (x + ½ − Bx)·795/530 − ½, and the same for v.
3. **Core:** screen pixels where each colour channel of all four footprint
   texels is ≥ 250 in the premultiplied raster. A convex combination of those
   texels, composited over any background, stays at or above the evaluator's
   existing per-channel lower bound. The upper bound is also unchanged,
   because alpha ≥ every colour channel.
4. **Support:** footprints containing any texel with nonzero alpha, dilated by
   two pixels (unchanged rule).
5. **Evaluator:** unchanged: the white interval, the 95% core requirement,
   at least 500 core pixels, and exact equality outside the support.

**Diagnostic.** v2 was built from the offline raster without reference to any
capture, then scored against the retained captures:

- 1,979 core pixels and 16,660 support pixels.
- In all four captioned states, 1,979 of 1,979 core pixels are
  directionally white.
- B, A2 and A3 pass. A fails only on its 8,544 outside-support pixels
  (section 2).

These captures shaped the diagnosis, so this score does not grant acceptance.

## 2. First-presentation attribution

### Facts

- **Retained captures.** Active-A differs from active-A2:
  - 8,544 pixels, each by one RGB10 code;
  - balanced in sign (4,373 up, 4,317 down) and spread across all channels;
  - spread over rows 40–752 of the whole viewport, not a damage rectangle.

  Disabled-A equals disabled-A2 exactly.
- **Retained logs.**
  - The mapper's per-redraw rgba64 hash is identical for the frames presented
    at A, A2 and the disabled states: the same pts 30.125 s and the same
    hash, across two epochs.
  - The client protocol shows one unchanged surface image-description object
    in every commit, full-buffer damage and a four-image swapchain rotation.
    Only the preferred target changed (616 → 308 → 616 nits target
    luminance).
- **What distinguishes A.** It is the only capture taken before the first
  target round trip, and it is the first caption presentation. The difference
  therefore arises after the mapper, in GSK, Mutter or the screencast path.

### Diagnostic sequence

All steps run in the same owned private session, using normal operation only:
player actions, MPRIS, the existing screencast reader, and the existing
`WAYLAND_DEBUG` and GStreamer logs. The paused frame stays the same
throughout, and every compared presentation must carry the same mapper hash.

| Step | Action | Isolates |
|---|---|---|
| D1 | Capture one unchanged presentation twice, with no `wl_surface.commit` between the two captures (checked in the protocol log) | Reader/screencast determinism |
| D2 | Before any target change: caption off (D0) → on (A) → off → on (A′) | First presentation vs state before the round trip |
| D3 | Target round trip 616 → 308 → 616, then caption on (A2), as in run 007 | Reproduces the failing comparison |
| D4 | Close and relaunch the player in the same private compositor, seek to the same frame, caption on (A-fresh), and repeat once (A-fresh′) | Client state vs compositor state |
| D5 | At each phase, a separate passive client records the output's image-description information (`get_output`) | Compositor output-state identity, by protocol |

| Outcome | Attribution |
|---|---|
| D1 captures differ | Capture path (Mutter screencast), not the product |
| A = A′ ≠ A2 and A-fresh = A2 | Compositor state that the round trip changed (Mutter) |
| A = A′ ≠ A2 and A-fresh = A | Client state that the round trip changed (GTK) |
| A ≠ A′, A′ = A2, and A-fresh ≠ A-fresh′ | First-frame transient in the client (GTK) |
| A ≠ A′, A′ = A2, and A-fresh = A-fresh′ | First-frame transient in the compositor (Mutter) |
| Anything else | Unattributed; recorded, no acceptance |

The exact outside-support equality stays the acceptance criterion. A
correction follows only after attribution, inside the responsible component.

## 3. Browser source/seek references

The `p7-seek-source` and `p8loop-seek-source` cases started at 1/2 s and
seeked +1 s; both use base@1/2 as their ordinary reference. The unchanged
source builder rejects base@1/2 and p7@1/2 for insufficient region contrast.

**Rule, fixed before any candidate was evaluated:** choose the smallest t on
the half-second grid, starting at 1/2, for which all five references (p7@t,
p7@t+1, p8loop@t, p8loop@t+1 and base@t) freeze at a unique exact timestamp
and pass the unchanged contrast threshold. Both cases move together because
they share base@t.

The **offline** results come from the unchanged builder and fixture manifest
(threshold 4 codes of 10-bit = 0.0039):

| Time | base | p7 | p8loop |
|---|---|---|---|
| 1/2 | fails contrast | fails contrast | 0.368 |
| 1 | fails contrast | fails contrast | 0.368 |
| 3/2 | 0.0525 | 0.353 | 0.368 |
| 2 | 0.0526 | 0.417 | 0.368 |
| 5/2 | 0.0526 | 0.425 | 0.368 |
| 3 and later | 0.0526 | no exact frame | 0.368 |

**Selected: t = 3/2.** Both cases now start at 1.5 s, play 500 ms, and seek to
2.5 s; their base reference is base@3/2. p7@5/2 is the last half-second grid
time with an exact p7 frame. The frozen candidates are private files on the
lab host; the contract change belongs to the reviewed case and contract pins.

## Implementation and order

1. **Implementation agents** build, outside the product packages:
   - caption mask v2: an offline `textoverlay` raster builder plus the
     per-channel core;
   - the D1–D5 controller steps;
   - the case and contract time change.
   Each change gets an independent review before it is frozen.
2. **Owner test window:** run D1–D5 and the caption/target acceptance with
   the frozen v2 mask, then the source/seek cohort and the loaded-library
   check.
3. Record the results in [status](STATUS.md) and the recovery record, then
   continue with merge review, the fast lane and publication.
