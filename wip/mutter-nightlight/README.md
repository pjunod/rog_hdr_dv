# Unreviewed work in progress — Night Light in linear light (nativehdr10, part 1)

These three patches are an implementation agent's partial start on part 1 of
[Night Light and target overrides](../../docs/NIGHT_LIGHT_AND_OVERRIDES.md).
The batch was interrupted before review, so they are kept here rather than
in `patches/`. They are not pinned in `sources.json`, not reviewed, not
packaged and not installed anywhere. Part 2 (per-monitor overrides) has not
been started.

- **Base:** the upstream-facing Mutter series in `patches/mutter` (candidate
  tree `3f238d2e9227dacd578f5a673c04ac10de5caac8`); reconstruct it with
  `tools/reconstruct.py mutter`, then `git am` these in order.
- **Result tree:** `14ce390cdc57f5b9efac5826e31e625cf3dedb64`.
- **Checked on 2026-10-11:** the head builds with warnings as errors
  against the upstream libdisplay-info series, and
  `tools/test-mutter-colour.sh` passes 24/24 (the 23 existing invocations
  plus one new one). Individual commits were not built separately; there is
  no adversarial review and no check against the contract's acceptance list.

Before this becomes part of a series: review it against the contract,
complete part 2, build each commit, run the fast lane once after the review
fixes, port to the Ubuntu series, and record the receipt.
