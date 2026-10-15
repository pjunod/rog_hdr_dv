# Reuse offscreen allocation across colour-state changes

Status: compiled, independently reviewed and affected-test-qualified source follow-up.
This is separate from nativehdr10's frozen delivery and is not a condition on its
already-recorded correctness acceptance. No publication or deployment.

## Cause and correction

`clutter_stage_view_invalidate_offscreen()` discarded both the framebuffer and
output pipeline on every state change. Night Light changes the rendering state
on each temperature step, but the required buffer remains fp16. Reference-white
changes had the same pre-existing behavior; the correction is general, not a
Night Light special case.

Mutter patch0078 preserves the framebuffer until the ensure idle checks it:

- Compute the current allowed format list and transform-adjusted dimensions.
- Reuse the actual allocation only if both dimensions match and its actual
  format is among the candidates. Check all fp16 formats, not just the preferred
  first one, so a supported fallback need not be reallocated repeatedly.
- Otherwise allocate a compatible replacement and invalidate projection and
  viewport as before. An allocation failure remains fatal as before.
- Continue clearing the output pipeline, scheduling a full redraw and rebuilding
  the pipeline for the current source/output states, including uniforms and
  transform. Compatible buffer contents alone do not make the pipeline current.
- When no conversion or transform is required, free the pipeline/buffer, cancel
  any pending ensure idle and invalidate viewport/projection for direct painting.
  Rapid changes before the idle use only the latest state.

No new cache, feature gate, public API or permanent allocation counter is added.
A colour-state change does not alter layout/scale; framebuffer replacement is not
supported by the existing setter. Rotation is construct-only and is still part
of allocation dimension calculation. Real size/rotation changes normally create
new views; this is not cross-view allocation pooling.

## Candidate and compilation

Isolated native branch: `codex/sol-offscreen-t_38887c3f`.

- Base: `de09d575e81799a1a75fe34a44d69f04caf2e727`, tree
  `058bbf9758c65798d4d0010685e32e8e76da9d3d` (frozen nativehdr10).
- Production: `12aa332567274fd3912a11736fe958bf4540ebe0`.
- Regression: `2cc87e0aafc6113184d05586f1a3ea66504ba1dc`, tree
  `ca9aff7ba61bd1d6097d86f0b308dcdc1029255d`.
- Entire separate native x86_64 baseline build with warnings as errors passed
  (162.99s); the production incremental build passed (4.48s); regression
  compilation passed (0.82s). Compiler output is not unit/allocation evidence.
- Full79 exported series replayed on `d82671c` to the same candidate tree.
  Patches0001–0077 are byte-unchanged; SHA256SUMS deliberately appends the two
  new patch hashes only.

The source build has its own worktree and build directory. The frozen source,
its warm build and its receipt ledger were not edited. Frozen unit receipts
retain their original qualification and are not relabeled for this candidate.
[Source receipt](../evidence/offscreen-reuse-source.json).

## Executed regressions and source acceptance

Patch0079 adds a stage-view regression for source/output reference-luminance
changes, compatible allocation identity, uint8→fp16→uint8 transitions, coalesced
incompatible intermediate states, and removal of the conversion with an ensure
idle pending. It extends the existing real PQ Night Light paint/readback case to
26 separately painted steps (6400→3900K in 100K increments) and return to6500K.
Strong framebuffer references rule out a freed object reusing the same address.
Capture pixels must remain unchanged and actual output pixels must warm and
return to their starting values, establishing that reuse does not freeze output
pipeline state.

Read-only adversarial review `t_ef4eb06c` (Astra) approved the exact native
`2cc87e0` / tree `ca9aff7b` and Mac `2b4e5fb` candidate with no blocking findings.
No source changes followed review. Its approved affected batch executed once in
the isolated build on native x86_64 with llvmpipe and no live display/device:

- `mutter:stage-views`
- `mutter:color-state-transform`
- `mutter:wayland-color-management`
- `mutter:wayland-color-management-wayland-night-light-bt2100-scanout`
- `mutter:wayland-color-management-wayland-night-light-bt2100-capture`
- `mutter:wayland-color-management-wayland-mapping-blending-target`
- `mutter:wayland-color-management-wayland-mapping-target-gamut`
- `mutter:wayland-color-management-wayland-published-reference-factor`

All eight invocations passed first time in 15.21s (request
`0591bc75602e47c7b66b60f867f0753d`). The source was clean at the reviewed identity
before and after execution. Passing stdout/TAP, Meson JSON/text/JUnit logs and
the explicit inventory are preserved; all 13 log/inventory hashes verified on
the Mac. No passing suite was rerun. Repository integrity remains a separate
source-bound static gate, retained outside tracked source after the final commit.
[Validation receipt](../evidence/offscreen-reuse-validation.json).

Actual observed messages:

- `Night Light ramp: 26 painted steps, 0 offscreen replacements`
- `Reference-luminance ramp: 10 steps, 0 offscreen replacements`

These counts derive from asserted framebuffer identity after each paint, with
strong references preventing reuse of a freed object's address. They establish
allocation reuse in those fixtures, not an instrumented before/after allocator
benchmark or an all-driver saving. Output endpoint warming/default return and
capture exclusion pass. Night Light intermediate outputs are read and checked
for content, not quantitative accuracy at every temperature. The reference-white
ramp asserts allocation identity, not per-step pixels; color-state-transform
separately exercises source/blend/output conversion. No GPU timing, power, VRAM,
physical picture or optical saving is claimed. Driver-forced fallback formats,
dynamic dimension mismatch and rotated-view reuse are not forced by these fixtures.

The substantial local branch is ready for later coordinated integration/PR
publication. The separate lifecycle follow-up uses overlapping patch0078–0080
numbers on its own branch: integration must serialize, renumber, reconcile
shared status/pin/series files and assess genuinely invalidated checks; do not
blindly concatenate or rerun valid successes. PR16 remains held and this work
must not indirectly land it. No publication, device access, Apple TV activity,
packaging, physical deployment or credentials occurred.
