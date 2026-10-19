# Contributor workflow

Read README.md, docs/STATUS.md and the relevant topical document first.
This repository owns Linux HDR, Dolby Vision, colour management and panel
tuning. Audio belongs in pjunod/rog_audio; Plurx application changes belong
in its separate repository.

Keep source claims, inherited test receipts and new physical measurements
distinct. A successful HDR decode or PQ surface is not full Dolby Vision.
Do not claim calibrated accuracy without an optical measurement receipt.

Preserve imported patch authorship, attribution and existing licence terms.
Do not invent signoffs, reviews, certification or upstream acceptance. Keep
superseded series distinguishable from the active source pins.

Use your own clone of the primary forge remote, never the owner's checkout.
Public work goes on a mirrored prefix (codex/, claude/ or hermes/); work not
cleared for publication goes on private/. Push only to the forge, never to
GitHub directly: docs/DEVELOPMENT.md explains the mirror and its fast lane.
If the forge remote or its token is not configured for you, stop and ask the
owner; never fall back to GitHub. Establish the relevant compiler loop
before changing C, kernel code or build metadata. Make normal related commits and batch them
into a larger PR. Only when ready to merge, obtain an adversarial agent review,
fix findings, then run the required fast lane once. Rerun only failed checks
and checks invalidated by subsequent edits. Merge after those checks pass;
full unit-suite follow-up belongs to a separate batch process. Run
python3 scripts/check_repository.py in that pre-merge fast lane. Regenerate
SHA256SUMS deliberately when patch bytes change and record why.

Document each new topic in README.md. Update docs/STATUS.md when the work or
acceptance state changes. Use neutral host names such as lab5 and operator;
keep host addresses, OEM binaries/profiles, raw device captures, signed
packages, signing keys and private recovery bundles out of version control.

Derive and correct Dolby Vision stage equations by the method in
docs/MEASUREMENT_DRIVEN_DEVELOPMENT.md. Its rules bind every model and agent:
measure the reference tools only through their normal operation, never
inspect their binaries, keep vendor outputs out of Git, tag every equation
term public or measured, and grant claims only through held-out acceptance.

Read-only laptop inspection is distinct from display changes. Maintain
recoverable stock packages and kernels. Do not replace a live compositor,
alter boot selection or restart a session without a coordinated test window.
No repository check may silently install or activate a display profile.

The repository is public. Scan the staged tree and reachable Git history for
secrets before pushing; diagnostics and experimental output remain private
until explicitly sanitized. Use a neutral agent Git identity. Keep the status
page updated and record autonomous decisions and unresolved evidence limits.
Delegate specified implementation work to implementation agents; the
coordinating agent owns design, review and integration. Fix demonstrated causes within the
architecture, not symptoms with watchdogs, forced capabilities or ad hoc gates.
