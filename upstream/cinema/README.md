# Submission transport — human-run source proposals

The project `submit.sh` wrappers use [submit.py](submit.py). It prepares
GitHub proposals and FFmpeg's code.ffmpeg.org proposals from each project's
manifest. No upstream publication has been performed during preparation.

```bash
upstream/mpv/submit.sh 01 --dry-run  # Fetch, check the pinned base and apply unsigned.
upstream/mpv/submit.sh 01            # Human-reviewed live submission with sign-off.
```

An unsigned preview prints the retained owned checkout and each unit's state.
It can inspect held source units. A live command accepts only units marked
`ready-for-human-review`, checks the `pjunod` account and the fork's canonical
parent, then adds Paul's sign-off. The human must review the code, description,
project policy and recorded validation before invoking it. `all` previews all
units; live `all` requires every selected unit to be eligible.

The current target must equal the manifest's qualified base. Refresh source
and evidence when it moves. Existing fork commits must exactly match the
prepared commit before reuse; different observed content or metadata causes a
clear refusal. Closed and merged proposals are reported without resubmission.
Held design questions, private reports and existing-PR replies use their
prepared descriptions and retain their explicit route decisions.

GitHub publication uses `gh`. FFmpeg publication uses
[forgejo.py](forgejo.py) and
`~/.config/upstream/code.ffmpeg.org.token`. That transport refuses API and Git
redirects, clears unrelated Git credential helpers and supplies the token only
through an askpass environment. A preview uses neither transport's credentials.

The focused transport regressions are
[the shared-helper tests](../../tests/test_upstream_cinema_submit.py) and
[the Forgejo tests](../../tests/test_upstream_forgejo_submit.py). They cover
holds, stale bases, missing material, private-fork credentials, redirects,
existing proposal states and preserved bracketed commit subjects. The fixtures
exercise local Git and local HTTP; they do not claim live publication testing.
