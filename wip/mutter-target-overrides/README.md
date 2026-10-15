# Superseded — per-monitor target override configuration/API stage

Sol's six authored commits that were kept here are now patches 0055–0060
of [`patches/mutter`](../../patches/mutter/series). They were rebased
unchanged after the Night Light patches, so the renderer precedes
NightLightSupported reporting. Only subject-line wrapping and the
abbreviated `index` lines differ from the stage export. The patch files,
series and stage checksum list were removed from this directory so that
there is one copy; they remain in Git history at commit `5bfde55`. The
stage receipt is still
[`evidence/nativehdr10-sol-stage.json`](../../evidence/nativehdr10-sol-stage.json).
Each of the six commits was rebuilt at its rebased position with warnings as
errors.

Patch 0061 adds the target selector these commits were waiting for:
`user-declared` provenance, the user luminance override ahead of DisplayID
and CTA (no EDID needed), and the BT.2100 gamut-source decision table.
Configuration and API semantics are in
[Night Light and target overrides](../../docs/NIGHT_LIGHT_AND_OVERRIDES.md#configuration-and-api-semantics).
Review and validation state is in
[status](../../docs/STATUS.md#nativehdr10--source-candidate-awaiting-adversarial-review).

Known limits carried from the stage, unchanged: there is no
`MetaMonitorConfig` equality or assignment-change short circuit at this
upstream base. Golden gdctl show fixtures are source-derived expectations,
not execution receipts. Clients that do not know the new properties,
including today's Settings, drop overrides when they replace a layout.
