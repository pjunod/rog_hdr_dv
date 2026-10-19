# Measurement-driven development — derive the mapping from the reference tools

**Status:** standing method since 2026-10-18 · **Applies to:** every open
re-implementation of a Dolby Vision stage in this repository · **Executable
by:** any agent or person, whatever the model or tooling

Companion to [the headless harness](DOLBY_HARNESS.md) (how references are
rendered and scored) and [the HDR reference corpus](HDR_REFERENCE_CORPUS.md)
(what may leave the private boundary). This document is *how* we turn the
reference tools into measurements that fix our equations, and the rules
every step must keep. The current equations live in
[the sqrt-sum mapping](SQRTSUM_PQ_Y_POST.md).

It is written so that a model with no history of this project can execute
it: every step names its inputs, its output, and a check that proves it was
done. If a step seems to require breaking one of the rules in §2, stop and
record the conflict instead of working around it.

## 1. Why we measure instead of guess

Until 2026-10-18, each idea for the mapping was coded into the renderer,
run on whole 4K frames and scored against the reference. That costs a full
render and score per frame and returns **one number per frame**, mixing the
tone curve, the colour handling, the trims and the final clip. A failing
number says *that* we are wrong, not *where*.

A single reference render of a synthetic colour grid returns hundreds of
thousands of exact input → output pairs for one shot and one target, covering
the whole colour volume. With those stored:

| | Whole-frame loop | Grid measurement |
|---|---|---|
| Evidence per reference render | 1 error figure per frame | ~275,000 colour pairs + ramps |
| Cost to test one hypothesis | a render + full-frame score per frame | evaluate a formula against stored data, seconds on a CPU |
| Tells you where the error is | no | yes: blacks, mids, highlights, hue, saturation |
| Generalisation across shots | inferred from pass/fail | read directly from how outputs vary with metadata |

The whole-frame score stays, but as the **final acceptance** step only (§6).

## 2. Rules — what every step must keep

1. **Synthetic inputs through the reference kit are allowed.** CM Analyze,
   Metafier and CM Offline (5.6.4 at the time of writing) may be run on
   synthetic images and sequences built for measurement. The owner reviewed
   this use against the tools' licences on 2026-10-18. Run them only through
   their normal command-line operation on the existing reference route.
   Inputs are synthetic grids, ramps and patterns, never edited real frames,
   so every measurement is reproducible from its manifest alone.
2. **Never modify, patch, disassemble, decompile or inspect the vendor
   binaries, and never bypass their normal operation.** Measuring outputs is
   the method; reading the implementation is not, and it would contaminate
   everything derived afterwards.
3. **Use each shot's original metadata unchanged.** Do not hand-edit or
   fabricate XML/RPU metadata to probe a behaviour. Vary the *image*, and
   choose *targets* from those the tools offer. An edited input measures a
   configuration no real stream contains. Display-mapping grids are rendered
   with the source shot's original XML. When CM Analyze itself is the stage
   being measured, the metadata it generates is that measurement's output; it
   is never fed into a display-mapping render.
4. **Vendor outputs never enter Git.** Rendered images, grid outputs, and
   any per-colour or per-sample table or curve taken from them stay in the
   private retained area named in [the reference corpus](HDR_REFERENCE_CORPUS.md).
   Git may hold scripts, manifests, hashes, fitted scalar parameters and
   equations (tagged `measured`), aggregate residual statistics and written
   findings. Never commit a plot or table dense enough to reconstruct the
   reference output, such as a full neutral curve. The repository is public,
   and reconstructable data is the vendor's output under another name.
5. **Label the origin of every equation term.** Each constant or functional
   form is tagged `public` (with its citation, e.g. US9613407B2
   ¶0048–0062) or `measured` (with the measurement manifest hash). Without
   the tag, nobody can later say which parts come from public sources, and
   the published write-ups depend on that distinction.
6. **Development is not acceptance.** Grid analysis, fits and
   development-frame scoring need no review before they run, because they
   grant no claim. Anything fitted from
   measurements must be **frozen first** and then scored **once** on held-out
   genuine content (§6). A fit that has only been checked on the data it was
   fitted to proves nothing about other shots.
7. **Keep concurrent native work apart.** The native builder runs up to three
   requests at once (since 2026-10-18). Two separate mechanisms keep them from
   corrupting each other's receipts, and every task relies on both:
   - The transport gives each request a fresh read-only source snapshot
     (`$PEER_SOURCE`) and its own empty `$PEER_WORK/export`. Files placed there
     are returned with that request only, and nothing else in
     `$PEER_WORK/export` survives it.
   - `$PEER_WORK`, the persistent Linux working directory, is shared by every
     task. Keep all persistent state under `$PEER_WORK/<work-item-id>/`, where
     the id is your unique board card or work-item id. Never write in another
     task's subtree, and treat retained references and corpora as read-only.

   If all three slots are busy, `run.py` reports a pending request; wait a few
   seconds and resubmit. Run your own steps one after another only when a step
   reads another step's output.
8. **Fix causes, not symptoms.** A residual that a clamp, mask or special
   case would hide is a finding to explain. It is not a number to make
   disappear.

## 3. The measurement grid — what to render

One grid image per (shot, target). Build it in **exactly the input encoding
the reference route already feeds the tool for that shot**: PQ, BT.2020, the
same bit depth `b`, container and frame size. A different encoding measures
a different pipeline. Code values below are integers in `0 … 2^b − 1`.

| Region | Content | What it isolates |
|---|---|---|
| Lattice A | 65 × 65 × 65 RGB lattice, level `i` = round(`i` · (2^b − 1) / 64) per channel (274,625 colours), raster order | the full colour-volume response |
| Lattice B | the same 274,625 colours, shuffled with a recorded seed | spatial independence (see below) |
| Neutral ramp | R = G = B, min(4096, 2^b) evenly spaced code values from 0 to 2^b − 1 | the tone curve alone |
| Hue ramps | 6 hues (BT.2020 R, Y, G, C, B, M) × 8 luminance levels (PQ 0.1, 0.2 … 0.8) × 64 steps from neutral to the BT.2020 boundary at that luminance | saturation and hue behaviour |
| Padding | a fixed mid-grey | keeps the frame valid; never analysed |

About 556,000 pixels in all, which fits any UHD frame. Write a **manifest**
next to every grid: pixel coordinates of each region, the shuffle seed, the
encoding, the frame size, and SHA-256 of the grid file. The analysis reads
positions only from the manifest, never from assumptions.

**Spatial-independence check.** Every colour appears once in lattice A and
once in lattice B, with different neighbours. If the tool's two outputs for
the same colour differ by more than one output code value, the tool is doing
spatial processing (for example the detail trim) at that point. Then a
per-colour model cannot describe it, and that behaviour needs its own
measurement (step edges, textures). Report the max and p99 difference per
shot, with the shot's detail-trim value.

**Targets.** Render each shot at its acceptance target. To learn how the
mapping depends on the display, also render it at two or more further peaks
(for example 300- and 1000-nit P3). Record every target's black, peak and
primaries in the manifest.

## 4. The loop — one pass, step by step

```
 build grid + manifest ──▶ render once per (shot, target) ──▶ store privately
                                                                   │
        ┌──────────────────────────────────────────────────────────┘
        ▼
 analyse residual vs our model ──▶ hypothesis (source-grounded) ──▶ test on
        ▲                                                   stored grids
        │                                                         │
        └──────────── not explained ◀─────────────────────────────┤
                                                                  │ explained
                                                                  ▼
                                   freeze ──▶ held-out full-frame score once (§6)
```

### 4.1 Measure

**Input:** a list of shots (source frame, original XML, target) chosen
before any result is seen. **Do:** build each grid and manifest (§3) and
render each (shot, target) **once**. A render that fails or produces an
invalid file may be retried once, with the reason recorded. **Output:**
private grid outputs plus a committed manifest of hashes. **Check:** every
(shot, target) has exactly one accepted output whose hash is recorded.

Every shot measured here becomes a **development** shot. It can never again
serve as held-out acceptance content (§6).

### 4.2 Analyse

Evaluate the current open model on the same grid inputs and compare with
the reference output. Always produce these four views, per shot and target:

- **Tone curve:** neutral-ramp input PQ → output PQ, reference vs ours. Read
  off the output where the shot's L1 Crush, Mid and Clip land, and the slope
  at Mid. Compare with the model's anchors and slope.
- **Colour:** for each hue ramp at matched input luminance, output chroma
  and hue angle vs input. This separates the luminance-ratio RGB scaling, the
  L2 chroma-weight and saturation-gain trims, and the final clip.
- **Trims:** where in the signal and in which domain the L2 slope, offset and
  power act, compared with where the model applies them.
- **Structure:** fit the patent's structure, a 1-D tone curve on luminance
  followed by a colour step, and report the residual it leaves.

Then tabulate every divergence against the shot's metadata: mastering black
and peak, target black and peak, L1 Crush/Mid/Clip, L2 values, detail trim
and CM version. **The parameter that predicts the error is the lead.**

**How to read it:** a divergence that is the same in every shot is a wrong
constant or functional form. A divergence that grows with one metadata
value is a wrong dependence on that value. A divergence confined to one hue
is in the colour step, not the tone curve. Spatial-check failures are
excluded from the per-colour fit and listed separately.

**Check:** the four views exist for every (shot, target), and the
divergence table has one row per (shot, target) with every metadata column
filled.

### 4.3 Hypothesise

Write each hypothesis as an equation change with its origin tag (§2,
rule 5) and a **predicted** improvement on the failing shots, before testing
it. Prefer changes grounded in a public source. Measured corrections are
allowed but must be labelled `measured`. **Check:** the hypothesis and its
prediction are committed before the §4.4 run, so the prediction cannot be
written to fit the result.

### 4.4 Test on stored data

Evaluate the changed model against the stored grid outputs for **every
measured shot**, not only the ones that motivated it. Use leave-one-shot-out
for anything fitted: fit on all shots but one, score the one left out, and
repeat. A change that makes any measured shot's mean or p95 residual worse
is rejected unless the commit explains that shot. **Check:** a residual table
per shot, before and after, committed with the script that produced it.

### 4.5 Freeze

Commit the source, parameters and build. Record the commit and tree hash.
Nothing after this point may change the model; a change starts a new pass.
**Check:** `git status` is clean, and the commit and tree hash are written
in the acceptance brief.

## 5. Handing a step to another agent

Each step above can be handed to any agent as a self-contained brief. A
brief that relies on conversation history fails when the model or session
changes. Every brief states:

- **Goal** in one sentence, and which step of §4 it executes.
- **Inputs** by path or hash: shots, manifests, stored outputs, the commit of
  the model under test.
- **Rules** it must keep: link this document's §2 and add any narrower limits.
- **Output** files and where they go: committed vs private.
- **Done when:** the check from the step, as a runnable command or an
  observable fact.
- **Stop and report** if a rule would have to be broken.

## 6. Acceptance — the only step that grants a claim

Acceptance uses [the harness](DOLBY_HARNESS.md) on **genuine** source frames
that were reserved before the frozen candidate existed:

- Held-out frames come from shots that were never measured as grids, never
  used in a fit and never used for a development score. Commit the hash of
  the reserved list before the freeze, so nobody can choose it afterwards.

- BT.2124 ΔE_ITP over every pixel of the full frame, with no pixels excluded.
  Pass = **mean ≤ 1 and nearest-rank p95 ≤ 3**. The thresholds never change,
  and no subset or trimmed statistic counts.
- Score once. A failure is recorded as a failure; the next attempt is a new
  frozen candidate scored on newly reserved frames.
- An adversarial review of the frozen candidate happens before held-out
  scoring and again before merge, never before development experiments.

## 7. Non-goals

- **Not a way to ship the vendor's output.** Measurements inform the open
  equations; vendor outputs and data taken directly from them stay private
  and are never distributed (§2, rule 4).
- **Not a licence to tune to the test set.** Held-out acceptance exists
  because a fit can match every measured shot and still be wrong elsewhere.
- **Not reverse engineering of the binaries.** Rule 2 of §2 holds absolutely.
- **Not a replacement for optical measurement.** Agreement with the
  reference renderer says nothing about what the physical panel emits; see
  [panel measurement](PANEL_MEASUREMENT.md).
