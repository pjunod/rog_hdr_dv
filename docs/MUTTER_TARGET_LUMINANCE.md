# Mutter target luminance — independent output feedback

**Status:** accepted design; implementation in progress. **Date:** 2026-10-09.
The coordinator owns design and integration; the implementation agent owns its
independent source clone. [Status](STATUS.md) records current qualification.

## Problem and decision

The [source audit](COLOUR_PIPELINE_AUDIT.md) found that output descriptions use
PQ's theoretical encoding maximum as their target maximum. The
[native library API](NATIVE_LUMINANCE_API.md) now provides the separate physical
firmware declarations needed to correct that boundary.

Keep encoding state and physical target luminance separate. A target-only
change must not alter PQ normalization, reference white, shader identity,
scanout encoding comparisons or KMS content metadata. Wayland output and
preferred descriptions carry an immutable copy of the selected target values.
The renderer continues to consume its existing encoding state.

The [Wayland colour-management protocol](https://github.com/wayland-mirror/wayland-protocols/blob/1.48/staging/color-management/color-management-v1.xml)
requires immutable image descriptions. It also requires target-luminance
information for parametric descriptions, so absent physical evidence needs an
explicit theoretical fallback. Existing description objects retain their old
information after an output changes. Output and preferred feedback must agree
on the identity of the current description; version 2 identities cannot be
recycled. Output description changes must be followed by `wl_output.done`.

## First implementation slice

Read native DisplayID physical data separately from CTA metadata. Do not
combine partial fields from unrelated blocks or silently resolve contradictory
physical declarations. Keep absent fields absent; require finite values,
protocol representability and consistent ordering before target selection.

Select native physical minimum and 10% window peak only on the existing
validated native HDR route while it is configured for BT.2100. This is generic
firmware-driven behaviour, with no panel model or luminance constants embedded
in the compositor. Values are firmware-declared capabilities, not measured
calibration or guarantees about the current optical output.

Where a physical field is unavailable, retain explicit theoretical encoding
fallback provenance and validate the effective minimum/maximum pair. The
initial change preserves existing fallback behaviour for SDR, forced or
ineligible HDR and CTA routes. It does not invent a new CTA target-selection
policy as part of the native fix.

Retain full-frame data for a later explicit policy. Do not emit target MaxCLL
or MaxFALL from it in this slice. Colour primaries, tone mapping, ICC application
and calibration remain separate work. A change only to unexposed evidence must
not generate a new public description identity.

## State, identity and notification ownership

| Owner | Responsibility |
|---|---|
| EDID parser | Retain native declarations and availability independently of CTA/capability decisions. |
| Colour device | Select validated target luminance and provenance independently of encoding state. |
| Colour manager | Forward target changes separately from renderer colour-state changes. |
| Wayland manager | Own protocol identities and immutable records; output and preferred feedback share the current record. |
| Existing image description | Retain its original record until the final reference disappears. |

Replace the cached output record before notifying clients. Recompute preferred
records for surfaces, including surfaces using the primary-monitor fallback,
and suppress unchanged results. Keep record references and identity allocation
safe through output removal, surface destruction and manager teardown.
Client-created image descriptions still describe their submitted pixels; this
output-feedback correction must not change surface-input interpretation.

## Alternatives and consequences

| Approach | Assessment |
|---|---|
| Put the physical peak into Clutter's PQ maximum | Rejected: changes encoding/transform semantics and couples unrelated state. |
| Mutate target data on an existing description | Rejected: existing objects would change meaning without a new identity. |
| Independent target state and immutable protocol records | Selected: preserves rendering contracts but requires explicit lifetime and notification handling. |

This enables applications to choose a rendering target from truthful platform
feedback. It does not itself perform highlight rolloff, gamut mapping, display
calibration or Dolby display management. Those remain explicit acceptance work.

## Qualification and delivery boundary

The pinned Ubuntu Mutter baseline compiled with warnings as errors in an owned
Ubuntu ARM64 container before source edits. The new library will be linked from
a separate source build; stock library version numbers cannot prove availability
of the unpublished API. No host package or live display state is changed.

After implementation, independent adversarial review precedes focused tests.
Regressions must cover valid and absent/conflicting data, route eligibility,
unchanged encoding and reference white, target-only notification, old snapshot
immutability, both identity versions, preferred/output agreement, primary
fallback surfaces and output completion. Rebuilds and test receipts must bind
the final source tree. Package delivery and physical qualification follow as
separate steps with compatible recovery packages ready.
