# drm/edid: validate DisplayID luminance limits and test EDID updates

Build on Cristian La Spina's posted DisplayID 2.0 luminance series. Validate payload length/revision, luminance-information semantics, finite nonnegative binary16 values, physical ordering and whole-nit rounding. Keep CTA precedence and do not fabricate HDR metadata. The KUnit regression sends synthetic EDIDs through drm_edid_connector_update() and checks range/reset/CTA behavior.

Current upstream base: 65ba8f34ec886ec72b2c07ddc8cf3d815c32869d (2026-10-28 check). The two prerequisite patches are application inputs only, not part of our outgoing submission.

New checks: W=1 x86_64 compilation of drm_edid.o and intel_dp_aux_backlight.o at the first follow-up commit, then drm_displayid_luminance_test.o at the second. Focused UML KUnit: four tests passed, zero failed. checkpatch: validation patch 0 errors/0 warnings; test patch 0 errors/1 advisory asking whether a new test file needs a MAINTAINERS update. Existing DRM ownership covers the file. The SPDX checker was rerun with task-local ply and GitPython after missing-dependency failures.

Inherited negative control against Cristian-only parser: 1/4 passed, three failed, demonstrating why the validation is needed. Inherited broader DRM suite: 675/675 on drm-misc-next 731ba09867520c047c7de53f92e384808e0b638e. These older runs are distinct from the new four-case current-master run.

The series is not yet merged upstream, so no released-kernel Fixes tag is asserted. Send only the two follow-up patches in this directory, in reply to the verified latest thread. The helper prepares a cover letter and only these two outgoing patches; the owner's explicit --prepare invocation adds DCO, and generated SEND_COMMAND.sh is a separate reviewed email step. No email is sent during preparation.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). The human submitter must review and add any DCO or Tested-by attestation personally.
