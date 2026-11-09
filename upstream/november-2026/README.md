# November upstream review — new work and existing preparation

**Reviewed:** 2026-11-09 · **Public source:** `ac82059` · **Inventory:**
124 entries across 27 upstream destinations, plus local converter observations.

The [canonical ledger](../../docs/UPSTREAM_SUBMISSIONS.md) and
[catalog](../catalog.json) now include 35 additions to the October inventory.
The Linux display effort, also called `rog_hdr_linux`, remains in the
`rog_hdr_dv` repository. This review covers its public source through PR21,
plus the separately pinned Runner and Plurx source. Active work can advance
after this snapshot; the source identities in the notes define what was inspected.

| Review | What it covers | New entries |
|---|---|---:|
| [Display and image changes](DISPLAY.md) | Mutter, Tiling Assistant, GTK/GDK, Glycin, the Rust TIFF crate and the public WebKit baseline | 11 |
| [Media and presentation changes](MEDIA.md) | Mesa, FFmpeg, mpv, libplacebo and GStreamer; imported upstream backports remain attributed | 19 |
| [Other projects](OTHER_PROJECTS.md) | Runner library fixes and Plurx's exported mpv precision and quantizer candidates | 5 |

## Read the states correctly

There are 39 entries with prepared material for human review, 36 held
entries, 25 discussion drafts, 11 superseded/backport groups, 12 exclusions
and one third-party prerequisite. The 39 review entries correspond to
43 patch units prepared in October. Those exact source qualifications are
retained; this audit does not silently advance their bases or rerun native
suites. The 35 new entries comprise 18 held candidates, 15 design discussions
and two groups of fixes already imported from upstream.

A downstream patch that builds or is installed is useful implementation
evidence. It does not establish that an independently extracted patch applies
to current upstream, has the required attribution and explanatory body, or
passes its focused regression there. Several public downstream exports still
contain generated quilt wrappers, distribution changes or temporary metadata.
Keep their upstream preparation holds until those boundaries are resolved.

The [audit receipt](../../evidence/upstream-refresh-20261109.json) accounts
for all 17 public patch-series directories changed since the October merge.
It records the exact base/candidate identities, changed-file hashes,
corresponding inventory IDs and excluded distribution-only material. The
[other-project receipt](../../evidence/upstream-other-projects-20261109.json)
records the separate source-head coverage. Tests described in these receipts
were inspected or inherited; this audit does not claim fresh native passes.

## Corrections to the old inventory

- LNX-3 now has a real i915 patch and a bounded November 2 owner-attended
  VRR round trip. Its remaining hold is upstream extraction/qualification and
  the owner's report, DCO and mail route. Broader optical and mode acceptance
  is a separate question. LNX-2 retains its original two-patch upstream base;
  the later Ubuntu kernel rebase does not replace it.
- MPV-1 already owns the unknown content-light correction. Its newer Ubuntu
  delivery extends the context without creating a duplicate contribution.
  MPV-2's compatibility fallback needs a current-base comparison before
  sending; a newer FFmpeg backport does not prove the whole fallback obsolete.
- ICC float conversion belongs to Glycin even though Loupe carries the
  vendored implementation. Its alpha correction folds into the same unit.
  The byte-tag allocation fix belongs to `image-rs/image-tiff`, not libtiff.
- FFmpeg and libdovi backports retain their upstream authors and are not
  resubmitted as original work. Private display-mapping equations, SDK and
  package coupling, generated checksums and release-install plumbing do not
  become additional generic upstream fixes.
- GStreamer's full normal Profile 7 enhancement reconstruction remains
  unfinished. The subtitle investigation changed no GTK source: its initial
  remux had discarded the Dolby configuration. Neither is counted as a new
  completed fix. WebKit's active private implementation is represented only
  by a public baseline and an explicit design discussion.

## Submission and publication boundary

No third-party fork, PR, issue, comment or email is created by this review.
A November 9 GitHub author search found no third-party PRs by `pjunod` since
October 28. That check does not establish activity on GitLab, email or other
identities; there are no new recorded submissions in this catalog.

The existing [submission commands](../README.md) still prepare only their
qualified units. The newly inventoried candidates have source material and
next steps in these review notes; they do not acquire a live command or an
invented sign-off. Owner review, upstream policy/base checks and the named
preparation steps remain before sending. Account tokens, mail configuration,
private source, captures and recovery bundles stay outside the published tree.
