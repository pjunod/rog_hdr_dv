# nativehdr10 integration series: checkpoint, incomplete

This is the integrated native branch `codex/opus-nightlight` at the point
where Opus's run 2 stopped. It is unfinished work in progress, not a
candidate for review.

- Base: native `5f123bb` (tree `3f238d2e…`, the unchanged 49-patch series).
- Head: `bd6b2ea042fb61ee534e8ee0304227c3c6b91feb`, tree
  `5d90ca1a3e70ad8e488a4ad9c5356a15f3478274`. A git bundle of the same
  history is kept in the ignored `.peer-linux/deliverables/opus-nightlight.bundle`.
- Order: 0001–0003 are the original Night Light imports. Authorship and
  content are unchanged; only the `[PATCH n/11]` subject numbering differs
  from `wip/mutter-nightlight`, and they reproduce tree `14ce390…`.
  0004 replaces the Bradford white adaptation with clamped, normalised
  diagonal factors in the output's linear RGB. 0005 adds the mode-transition,
  capture-exclusion and forced-HDR assertions. 0006–0011 are Sol's six override
  commits, rebased unchanged, so the renderer now precedes support reporting.
- Compilation: each import commit was built individually, and so were
  0004, 0005 and the rebased head. All builds were native x86_64 with
  `-Werror` and produced 0 diagnostics. 0006–0010 at their rebased
  positions were not built individually. No unit tests or probes have run.

## Still missing before review

1. The target selector in `meta-color-device.[ch]`: `USER_DECLARED` in
   the shared provenance table, the user luminance source ahead of
   DisplayID, and `hdr-gamut-source` auto/base-edid/none in BT.2100 per the
   agreed decision table. The override must also be honoured with no
   EDID; native SDR stays unaffected. Add native-hdr/wayland regressions.
   Sol's D-Bus test (0009) expects `user-declared` at 400 cd/m² with
   reference factor 2.1.
2. Topical doc update: name the diagonal method, the 1000 K projection
   and the capture inventory.
3. Export from 0050 into `patches/mutter`, pins, hashes, full replay,
   status pages, receipt, then both adversarial reviews and one unit batch.
