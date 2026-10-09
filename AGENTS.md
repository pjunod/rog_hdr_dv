# Contributor workflow

Read README.md, docs/STATUS.md and the relevant topical document first.
This repository owns Linux HDR, Dolby Vision, colour management and panel
tuning. Plurx application changes belong in its separate repository.

Keep source claims, inherited test receipts and new physical measurements
distinct. A successful HDR decode or PQ surface is not full Dolby Vision.
Do not claim calibrated accuracy without an optical measurement receipt.

Preserve imported patch authorship, attribution and existing licence terms.
Do not invent signoffs, reviews, certification or upstream acceptance. Keep
superseded series distinguishable from the active source pins.

Use codex/ branches for implementation. Establish the relevant compiler/test
loop before changing C, kernel code or build metadata. Check source application
and focused regressions before committing a modified patch series. Run
python3 scripts/check_repository.py for repository changes. Regenerate
SHA256SUMS deliberately when patch bytes change and record why.

Document each new topic in README.md. Update docs/STATUS.md when the work or
acceptance state changes. Use neutral host names such as lab5 and operator;
keep host addresses, OEM binaries/profiles, raw device captures, signed
packages, signing keys and private recovery bundles out of version control.

Read-only laptop inspection is distinct from display changes. Maintain
recoverable stock packages and kernels. Do not replace a live compositor,
alter boot selection or restart a session without a coordinated test window.
No repository check may silently install or activate a display profile.
