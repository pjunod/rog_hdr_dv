# Runtime acceptance corrections — caption mask, first-presentation attribution, seek references

**State: implemented, reviewed and frozen; not run · November 27, 2026.** This page
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
  target round trip. The difference therefore arises after the mapper, in
  GSK, Mutter or the screencast path.
- **A is the seek presentation (source and retained, found in review on
  November 27).** Showtime selects subtitle track 0 at load, so the caption is
  already enabled when the seek frame appears. The early "invalid subtitle
  stream index 0" error comes from that call, which fails before the streams
  exist; the caption is enabled anyway. A carries the seek event's own sink
  frame, context, generation and source epoch. Every later caption
  presentation followed a stream reselection: active-A2 equals restored
  active-A3 exactly, while A differs from both. The first design treated A as
  the first caption toggle; that premise was wrong, and the sequence below
  replaces it.

### Diagnostic sequence

All steps run in the same owned private session, using normal operation only:
player actions, MPRIS, the existing screencast reader, and the existing
`WAYLAND_DEBUG` and GStreamer logs. The paused frame stays the same
throughout, and every compared presentation must carry the same mapper hash.

| Step | Action | Isolates |
|---|---|---|
| D1 | Capture the seek presentation (caption on, as loaded) twice, with no `wl_surface.commit` between the two captures (checked in the protocol log); the first is A | Reader/screencast determinism on the anomalous presentation |
| D2 | Before any target change: caption off (D0) → on (A′) | Seek presentation vs a reselected presentation before the round trip |
| D3 | Target round trip 616 → 308 → 616, then caption on (A2), as in run 007 | Reproduces the failing comparison |
| D4 | Close and relaunch the player in the same private compositor and seek to the same frame. Capture its own seek presentation (A-fresh), then caption off → on (A-fresh′) | Client state vs compositor state |
| D5 | At each phase, a separate passive client records the output's image-description information (`get_output`) | Compositor output-state identity, by protocol; informational |

The run is invalid, not attributed, when:
- the caption is not on at either seek;
- A or A-fresh is not its instance's seek event;
- any compared presentation has a different mapper hash or allocation/UI binding;
- the evaluation runs in a different boot from the capture.

The relaunch reuses the private home and caches (warm, not cold). The
player's normal Quit-to-exit path has not been observed before, because
earlier cleanups ended with the supervisor's TERM. A failed Quit fails the
run closed; no fallback signal is added.

| Outcome | Attribution |
|---|---|
| D1 captures differ | Capture path or compositor repaint (Mutter), not the product |
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

p8loop repeats one static picture, so its seek case proves seek timing and
presentation, not a change of picture content. That was already true at the
old times.

**Still case p7-clip05 → p7-clip20 (owner decision, November 27).** Review of
the change found one more case on the rejected frame: the p7 still picture at
0.5 s. It is moved by the same kind of fixed rule: the smallest half-second t
≥ 1/2 whose p7 reference passes and that no sibling p7 still case uses.
p7-clip15 already uses 3/2, so the rule gives t = 2.

- **What was checked.** No earlier capture of p7 at 2 s exists, so no
  capture informed the choice. The 3/2 and 2 source frames have different
  decoded hashes, so the two still cases compare distinct pictures.
- **Scope change.** The p7 still picture at 0.5 s, shortly after load, is no
  longer covered by this reference method. Nothing records why 0.5 s was
  originally chosen.
- **Unchanged.** p8loop-clip05 still passes its reference and stays as it
  was.

## Implementation and review (November 27)

Implementation agents built all three corrections in private harness copies
outside the product packages; the November 20 harness is unchanged. Every
piece had an independent adversarial review, and review findings were fixed
before freezing. No piece has been launched against a display.

**Caption mask v2 (fourth revision).** The mask is unchanged across
revisions: 1,979 core and 16,660 support pixels. Review added:
- **The sink's alpha round trip, modelled from source.** The sink requests
  straight-alpha pixels, which GStreamer un-premultiplies; GTK keeps the
  straight texture and premultiplies each texel in the shader before the
  bilinear mix. The core test is c′·a ≥ 250·255 on all four footprint texels.
  The sink's own pixel read must equal the model byte for byte. An exhaustive
  8-bit check shows the round trip never changes the core decision.
- **Both GPU renderers.** The test is a sufficient condition for the GL and
  Vulkan GPU renderers, in either sRGB decode order: the decode curve is
  convex and the primaries matrix is non-negative with unit rows. A
  software or Cairo renderer is not covered, and the runner rejects one:
  the window buffers must be dmabuf, with no shared-memory window buffer.
- **The installed GTK.** Within the cited GTK source ranges, the later
  project patches up to the installed revision leave the sampling and upload
  path byte-identical. The installed library equals the packaged payload. A
  byte-level rebuild of that package was not compared.
- **An enforced binding.** The caption acceptance runner checks exact
  package versions and library hashes, the system font configuration and
  resolved font pattern, and the player's environment. It checks before
  launch, and again after the captures against the player's own mapped
  libraries.
- **Evidence limit.** The requested Adwaita Sans is not installed; both the
  offline renderer and the player resolve the same fallback face under the
  same font configuration. The face is witnessed by font matching and file
  hash, not inside the caption element.

**Attribution phase.** It follows the corrected sequence above. It is
invalid on a broken premise, a mapper-hash or UI-binding mismatch, a commit
between the D1 captures, a cleanup failure, or evaluation in another boot.
Parsers reproduce all seven step events of the November 20 run from its own
logs. That check confirms that A was the seek presentation and that the
caption was rendered into it. The D5 output reader is a small passive
protocol client built from installed headers. It has not yet run against
Mutter.

**Browser cases.** The two seek cases start at 1.5 s and seek to 2.5 s. The
p7 still case moved to 2 s. The source-reference list is complete for the
first time: the normal freeze step, run offline, accepts all eleven
references, and they exactly match the set the twelve cases require.

## November 27 runs

No result qualified, and no frozen model was exercised.

**Re-binding before the run.** The frozen runners pinned the November 20
package versions, and reviewed work had since installed newer ones. They were
re-bound in new copies:
- **Paths and versions only:** the copies change only paths, pins and exact
  versions, and a per-file freeze record proves that.
- **Staged package list:** a release manifest and install plan were built
  from the installed state and are staged, not published.

**Showtime.** Attribution and caption/target acceptance both stopped before
playback. The Dolby mapper failed on the first Profile 5 frame with its
generic error. Attribution was invalid and correctly not eligible for the
pre-declared rerun.

**Browser cohort.** Three harness defects were found and fixed in turn:
- **Session folder left behind:** the controller did not archive the GNOME
  session folder before the browser phase.
- **Holder and runner never matched:** the paired session holder created a
  directory its runner never waited for. This dates from the first paired
  copy, so no paired run had ever reached readiness.
- **Proxy socket path too long:** the corrected directory name made WebKit's
  proxy socket paths exceed the 107-byte Unix socket limit, so they were
  silently truncated. The holder now checks the length before it creates
  anything.

The browser then loaded its first case. It played no on-screen frames,
because the painter's first mapper render never completed.

**Diagnosis (read-only).** Three suspects are ruled out:
- the GTK Dolby rogdv11 change, which applies only to Profile 7;
- the PR #76 subtitle change, whose decoder code is byte-identical;
- the browser's VA decoder errors, which occur at teardown and also occurred
  in the passing November 20 run.

The common failure is a fresh mapper's first render, after GPU setup and
before the Dolby provider runs. The mapper gives libplacebo no logger, so the
failing step is unnamed. The next step is a diagnostics-only mapper build
that routes those messages and per-step reasons to its debug log.

## Remaining order

1. **Owner test window:** run the attribution phase, then caption/target
   acceptance with the frozen v2 mask, then the source/seek cohort and the
   loaded-library check.
2. Record the results in [status](STATUS.md) and the recovery record, then
   continue with merge review, the fast lane and publication.
