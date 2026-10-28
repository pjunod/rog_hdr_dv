# i915: VRR page flip loses PSR set-context latency on display 13/14

Draft report; the observation below is inherited from the 2026-10-27 laptop diagnosis and has not been reproduced on today's upstream kernel.

On ASUS ROG Zephyrus G16 GU605MZ, a fullscreen-video page flip enables VRR and drmModeAtomicCommit returns EINVAL. The recorded kernel was 7.3.0-rc5 with DRM debugging. PSR is disabled when VRR is enabled; _intel_psr_min_set_context_latency() returns zero when has_psr is false, before reaching Wa_14015401596. The old state has SCL 1 and vblank start 1601; the new state has SCL 0 and vblank start 1600. That timing change needs a full modeset, which the page flip does not request.

Source check on 65ba8f34ec886ec72b2c07ddc8cf3d815c32869d confirms the early !has_psr return still precedes Wa_14015401596 in intel_psr.c. This supports the diagnosis but does not prove that every current-kernel path still reproduces. Related compositor report: [Mutter #5079](https://gitlab.gnome.org/GNOME/mutter/-/issues/5079).

Before sending, attach sanitized current-kernel DRM logs showing both old/new state, GPU/display version, panel/mode and PSR/VRR flags; record a minimal reproduction and a tested fix or explain why one could not be produced. No raw logs, private EDIDs or host addresses belong in the public report. No Fixes tag, universal hardware claim or patch is invented here.

Maintainer candidates freshly resolved with scripts/get_maintainer.pl --no-git --nogit-fallback: Jani Nikula, Rodrigo Vivi, Joonas Lahtinen and Tvrtko Ursulin; lists intel-gfx and intel-xe. Resolve them again against the final patch/report tree before mailing.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). The human submitter must review and add any DCO or Tested-by attestation personally.
