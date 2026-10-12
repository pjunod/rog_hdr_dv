# Superseded — Night Light in linear light (nativehdr10, part 1)

The three original work-in-progress patches that were kept here are now
patches 0050–0052 of [`patches/mutter`](../../patches/mutter/series). Their
authorship and content are unchanged: only the `[PATCH n/3]` subject
numbering and the abbreviated `index` lines that `git format-patch`
regenerates differ. Applied in order to tree
`3f238d2e9227dacd578f5a673c04ac10de5caac8`, they still reproduce tree
`14ce390cdc57f5b9efac5826e31e625cf3dedb64`. The patch files were removed
from this directory so that there is one copy. The original bytes remain
in Git history (commit `7c78457`, the PR 16 handoff).

Inherited claim, not re-established here: the handoff recorded that the
head built with warnings as errors and that `tools/test-mutter-colour.sh`
passed 24/24 on 2026-10-11. In nativehdr10, each import was rebuilt
individually with warnings as errors. No unit test has been run on the
integrated candidate yet.

Patch 0053 replaces their Bradford white adaptation with bounded diagonal
factors in the output's linear RGB. Patch 0054 adds the transition,
capture and forced-HDR regressions. See
[Night Light and target overrides](../../docs/NIGHT_LIGHT_AND_OVERRIDES.md) and
[status](../../docs/STATUS.md#nativehdr10--source-candidate-awaiting-adversarial-review).
The series is not reviewed, qualified, packaged or installed.
