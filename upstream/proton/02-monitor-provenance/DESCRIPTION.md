# win32u: Report monitor connector technology.

Prepared for ValveSoftware/wine proton_11.0 at e60892cc2398b0a83c332a2078c7b85e47bdb42b. The port preserves Proton's Gamescope-supplied/generated EDID path. These are recovered source candidates, not a WineHQ submission.

Carry monitor provenance and connector technology through win32u and the X11/Wayland backends; reject partial EDID provenance.

**Verification:** inherited full --enable-win64 build succeeds, with no warnings in touched files. Inherited displayconfig runtime at the first provenance commit: 13 tests, zero failures. The separate EDID completeness follow-up is included in this unit. New exact-tip full build succeeds and the isolated-prefix displayconfig runtime passes13checks with zero failures/skips.

The owner selected ValveSoftware/wine as the destination. No explicit Valve AI prohibition was found in the inspected repository. WineHQ is not a destination. Tool use remains disclosed; silence about a policy is not a claim of upstream acceptance. No AppContainer, real Windows reference, or physical display qualification is claimed.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). Human review and responsibility remain with the submitter before publication.
