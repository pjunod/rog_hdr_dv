# Unreviewed override transport/API stage — nativehdr10

These six authored Mutter commits complete Sol's configuration, transport,
DisplayConfig and gdctl stage. They are source work in progress, not a
qualified nativehdr10 release. The target-selection policy and Night Light
renderer belong to the dependent Opus integration stage.

- Base tree: `3f238d2e9227dacd578f5a673c04ac10de5caac8` (the unchanged
  49-patch upstream-facing series).
- Native base commit: `5f123bb2c203c44c765d56628b47aad1fcfd9e86`.
- Native branch/head: `codex/sol-overrides` /
  `9b2886d826a577c866c5cd26533a1109c9aba9c7`.
- Result tree: `ebe9aeb880eab66fcfc5cbf34a97d9eaf6cd30f5`.
- All added source and regressions compile natively on x86_64 with warnings
  as errors. gdctl syntax compiles. No unit tests or behavioral probes ran
  in this stage. The original three recovered commits and their build logs
  were preserved; the three new commits have fresh compiler receipts.
- The exported six patches were replayed onto the exact native baseline in
  a fresh worktree and reproduced the result tree. This is source identity
  verification, not behavioral acceptance.
- [Stage receipt](../../evidence/nativehdr10-sol-stage.json) records source,
  hashes, compilation, replay, deferred coverage and evidence limitations.

## What is delivered

1. Shared override type with explicit presence and equality, transported via
   output assignment and `meta_monitor_get_target_override()`.
2. XML persistence and strict validation, including duplicate/nonfinite
   rejection, zero black and omission of unset fields.
3. Configuration deep copies and synthesized layouts preserve each
   monitor's target declarations, colour mode and RGB range.
4. Strict D-Bus apply validation and replacement semantics; effective targets
   and individual provenance come from the applied colour device state.
5. gdctl options with `auto` clearing; read-modify-write preserves configured
   fields and colour context on unrelated layout changes. Effective targets
   and provenance are printed by `show --properties` / `show --verbose`.
6. Bounded NightLightSupported reporting for active BT.2100, refreshed after
   applied-mode changes, while retaining hardware LUT/CTM reporting.

Tests are written and compiled for store round trips/malformed XML,
copy/history/reapply, D-Bus invalid requests and VERIFY nonmutation,
persistent proposal rejection/restore, effective targets and inactive
omission, no-LUT/no-CTM mode transitions, and two-monitor gdctl preservation
and clearing. Golden show fixtures are source-derived expectations, not
execution receipts.

## Opus integration handoff

The warm source/build remain in `$PEER_WORK/src/mutter` and
`$PEER_WORK/build-mutter`. Do not run prepare or rebuild the unchanged
baseline. Preserve these commits and import the original Night Light WIP
with its authorship. Arrange the final series so the Night Light rendering
path precedes the support-reporting consumer, and providers precede selector
consumers. Reordering requires affected incremental compilation, not unit
execution during implementation.

Only the existing provenance converter interface in
`src/backends/meta-color-device.[ch]` was exposed/renamed to
`meta_color_target_provenance_to_string`; the selector is unchanged here.
Add `USER_DECLARED` and its string to that same table in the selector commit.
The D-Bus regression expects a 400 cd/m² override on a no-EDID BT.2100 output
at reference-luminance factor 2.1 (~426 cd/m² white): it intentionally needs
that selector integration before the validation phase.

No `MetaMonitorConfig` equality function or assignment-change short circuit
exists at this pinned upstream base. Native apply always transports output
assignments; no unused equality API was invented. Shared override equality
is used by the copy/history/reapply regressions. Existing hotplug/orientation
and restore cases remain part of the eventual affected batch.

Configured API properties are `target-peak-luminance` (d),
`target-min-luminance` (d), and `hdr-gamut-source` (s: auto/base-edid/none).
Effective properties are `target-luminance` (dd, min/max),
`target-min-luminance-source` and `target-max-luminance-source` (s),
`target-primaries` (dddddddd, RGBW xy), and `target-primaries-source` (s).
They are read from an active device with initialized colour state.

Final integration must export from 0050 without changing patches 0001–0049,
update pins and hashes deliberately, replay the whole integrated series,
obtain both adversarial reviews, fix findings, then execute the affected
unit batch once. `sources.json` and the repository `SHA256SUMS` deliberately
still pin the qualified baseline. PR16 remains held unmerged; no push,
package, deployment, display change or optical/Dolby claim is made here.
