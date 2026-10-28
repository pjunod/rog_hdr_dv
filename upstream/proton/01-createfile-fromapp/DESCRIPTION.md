# kernelbase: Implement CreateFileFromAppW().

Prepared for ValveSoftware/wine proton_11.0 at e60892cc2398b0a83c332a2078c7b85e47bdb42b. The port preserves Proton's Gamescope-supplied/generated EDID path. These are recovered source candidates, not a WineHQ submission.

Expose the existing desktop file-opening path through CreateFileFromAppW and test API-set resolution, creation dispositions, access/sharing and Unicode names.

**Verification:** inherited full --enable-win64 build succeeds, with no warnings in touched files. New isolated-prefix runtime: 123 checks, zero failures, zero skips. A fresh candidate-specific Wine prefix, explicit C.UTF-8 locale and a valid Windows TEMP directory resolved the earlier fixture failures. The implementation and tests were unchanged.

The owner selected ValveSoftware/wine as the destination. No explicit Valve AI prohibition was found in the inspected repository. WineHQ is not a destination. Tool use remains disclosed; silence about a policy is not a claim of upstream acceptance. No AppContainer, real Windows reference, or physical display qualification is claimed.

Prepared with AI coding assistants (OpenAI Codex and Anthropic Claude via Claude Code). Human review and responsibility remain with the submitter before publication.
