# i915: preserve PSR set-context latency across a VRR transition

**Updated:** 2026-11-09 · **State:** held for current upstream source preparation
and the owner's reviewed report, DCO and mail route. No report or patch has
been sent by this preparation.

## Diagnosis and implemented downstream correction

The October 27 ASUS ROG Zephyrus G16 GU605MZ diagnosis recorded a fullscreen
page flip enabling VRR while `drmModeAtomicCommit` returned `EINVAL` on
`7.3.0-rc5`. Disabling PSR for VRR changed set-context latency from 1 to 0 and
vblank start from 1601 to 1600. That timing change required a full modeset,
which the page flip did not request. The October 28 source check at
`65ba8f34ec886ec72b2c07ddc8cf3d815c32869d` supported that diagnosis; it is not a
fresh check of November's upstream source. Related compositor report:
[Mutter #5079](https://gitlab.gnome.org/GNOME/mutter/-/issues/5079).

The [downstream patch](../../../patches/linux/0005-drm-i915-psr-keep-Wa_14015401596-s-set-context-laten.patch)
now preserves Wa_14015401596's latency when VRR is the reason an otherwise
eligible PSR configuration is disabled. The reviewed correction evaluates the
existing setup-frame timing check before setting `psr_vetoed_by_vrr`; PSR
remains disabled under VRR. The selected release source is Ubuntu
`7.3.0-10.10`, base `0edb54d9220da4f863845a1d1cfdfcf652db51e1`, with the
five-patch candidate tree `b76fb4d9e81f5b44a840810ffbb341929b765c8d`.

## Retained validation and its scope

The [kernel rebase receipt](../../../evidence/kernel-7.3-rebase.json) records
warnings-enabled i915/xe `intel_psr.o` and other affected DRM objects, complete
package construction and the selected source identity. The four parser KUnit
passes belong to the DisplayID work; they do not test the VRR transition.
An earlier upstream-base preparation was superseded before deployment in favor
of Ubuntu's retained security behavior; its tests do not qualify a moved base.

The [November 2 target observation](../../../docs/I915_VRR_FASTSET.md) is a
separate owner-attended silent HDR 24 fps stock-mpv fixture on nativehdr3 and
APT Mutter nativehdr13. Fullscreen/windowed output appeared normal, the active
i915 CRTC's `VRR_ENABLED` changed 0→1→0, and no page-flip errors occurred.
DisplayConfig except serial and `monitors.xml` were unchanged. Broader optical,
long-duration cadence, DPMS/brightness, suspend/resume, other-GPU/mode and
external-monitor acceptance remain open.

## Before sending

Extract the actual correction against the selected current upstream kernel,
review its prerequisites and repeat the affected native check on that exact
source. Attach a scoped sanitized reproduction, the old/new state, GPU/display
version, panel/mode and PSR/VRR flags. Preserve the historical negative and the
bounded downstream pass rather than claiming a new universal hardware result.
Raw logs, private EDIDs, host details and signing material stay private. Do not
invent a released-kernel `Fixes` tag or a personal `Tested-by`.

The October 28 maintainer lookup returned Jani Nikula, Rodrigo Vivi, Joonas
Lahtinen and Tvrtko Ursulin, with intel-gfx and intel-xe lists. Resolve recipients
again with `scripts/get_maintainer.pl` against the final patch/report tree and
verify relevant current threads. The existing helper only exports unit 02's
two luminance follow-ups; it neither exports nor sends this correction.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via
Claude Code). The human submitter reviews the final series and personally adds
any DCO or `Tested-by` attestation before using the configured mail route.
