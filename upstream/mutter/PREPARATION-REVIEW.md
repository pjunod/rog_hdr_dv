# Mutter preparation review

The saved series contains 80 commits across 15 submission units. The production
changes in all units were reviewed on 2026-10-28. One numerical conversion defect
was reproduced and corrected in units 06 and 09. A teardown fix that previously
appeared later in unit 06 was also folded into the first commit that needs it. No upstream submission, fork,
public issue or merge request was made by this review.

## Correction and regression

The protocol permits a positive luminance maximum up to `UINT32_MAX`. Storing
that value in a `float` rounds it to `2^32`; casting it back to `uint32_t` has
undefined behavior. A standalone Clang undefined-behavior sanitizer reproducer
confirmed the invalid cast before the correction.

`meta_color_luminance_to_uint32()` now checks before casting: nonpositive and
NaN values become zero; positive overflow, including positive infinity,
saturates at `G_MAXUINT32`; ordinary finite values retain truncation. The same
conversion is used for scaled minima, output information and the unit 09
refactored record lookup. Existing target validation still requires a positive
maximum and rejects inverted ranges.

The native regression `/native-hdr/luminance-protocol-boundaries` checks zero,
negative, NaN, fractional finite values, the exact integer maximum, its rounded
single-precision representation, `2^32` and infinity. Unit 09 additionally sends
raw integer maxima near and at `UINT32_MAX` through both encoding and mastering
luminance requests. Those cases prove successful description creation and
exercise record lookup; they do not assert a numeric maximum returned by a
`get_information` wire round trip.

An independent agent reviewed the checked conversion, callers and added tests,
including the rounded-float boundary. The helper was placed at the end of its
existing backend source/header so later units retain their original application
contexts. Exports preserve the original author and contain no sign-off.

The first unit 06 commit initially compiled and passed `native-hdr`, but its
existing Wayland color-management test exited with SIGSEGV during teardown
after reporting its TAP case passed. The unit's later disposal commit explains
the cause: the manager's object-data finalizer ran after its display, outputs
and backend were gone. That production fix now lives in the first commit;
its test sync-point adjustments were folded into commit 3, where topology
phases are introduced. All final unit trees remain identical after this fold.
The failing early-commit result and corrected rerun are retained in the receipt.

## Review scope

The review covered production diffs and relevant tests, with special attention
to these boundaries:

- DisplayID remaining lengths, section padding, nested headers, explicit
  incomplete-parser status, binary16 luminance and chromaticity decoding in all
  six libdisplay-info units.
- KMS capability gates; target source fallback and conflicts; signed primaries,
  finite/invertible matrices and shared validation/rendering definitions.
- Protocol request validation, ICC descriptor zero, offsets, short reads,
  descriptor ownership, immutable description records and manager disposal.
- HLG parameters; highlight and gamut CPU/GLSL paths; cache identity; composition,
  direct scanout, capture and cursor interactions; CTA/native SDR selectors.
- Linear-light Night Light, override XML and D-Bus/gdctl paths, cancellation,
  callback ownership, device/store teardown and test seams.

No further demonstrated defect was found in that scope. This was a semantic
review of production changes, not an assertion that every repetitive test line
or external standards clause was independently verified. Hardware behavior,
GNOME design acceptance and coordination with overlapping work remain separate
requirements. Units already held or blocked keep those dispositions.

## Fresh qualification

[saved preparation receipt](../../evidence/upstream-saved-review.json) records exact Git trees,
source archive hashes, container identity, commands, results and hashes of the
retained full build/test logs. Only source archives were transferred to the
isolated compiler slot. The image's dependencies were installed inside Docker;
no host compositor or system packages were changed.

The fresh checks use an Ubuntu 26.10 container, GCC 15.3, `-Dwerror=true`, a
private libdisplay-info prefix and software Mesa. The final unchanged six-unit
libdisplay-info stack passes 80/80 tests. Mutter checks cover the first changed
unit 06 commit, the revised unit 06 and 09 tips, the deep unit 14 stack and the
separate lifecycle unit 15 stack. The named native and protocol regressions are
executed in the focused test selections.

Unsigned submit-helper previews apply units 06, 09, 14 and 15, with their full
minimal dependency graphs, on the recorded upstream base. No three-way fallback
is required. Metadata-only export normalization does not change the archived
source trees.

The earlier per-commit, release and wider-suite table in README.md remains
inherited evidence for the pre-correction branches; it has not been rerun for
every revised descendant. The fresh checks do not cover the complete Fedora CI
matrix, native KMS/KVM, X11/Xwayland or these exact branches on real hardware.
