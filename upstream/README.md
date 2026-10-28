# Upstream preparation — choose the project, then the unit

**Status:** preparation complete; contributor review and listed holds remain
· **Updated:** 2026-10-28.

Start with the [submission ledger](../docs/UPSTREAM_SUBMISSIONS.md), which
covers the original 85 tracked entries across 20 projects. The
[catalog](catalog.json) connects each entry to its preparation material.
The ledger includes grouped changes, design questions, resolved items and
work that stays local; those counts do not describe ready pull requests.

Each project's README gives the exact source base, unit order, overlap with
existing work, commands and evidence limits. A prepared patch still needs
the contributor's review. A held item needs its stated evidence or design
decision before it can become a submission.

## Inspect the material before submitting

```bash
python3 scripts/check_upstream.py   # Check bytes, metadata, paths and coverage.
python3 scripts/check_repository.py # Also check source series and doc links.
```

`PASS` means the recorded material is internally consistent. It does not
mean a patch compiles, a physical test passed, an account is configured,
the author reviewed the change, or an upstream maintainer accepted it.
The per-project receipts state which of those steps actually happened.

The submission helpers' `--dry-run` path prepares unsigned commits and
does not fork, push, open requests, post comments or email. It may fetch
public source and create an owned local preparation checkout. It is not a
build or test command. An upstream base that has moved requires a new
qualification before the recorded results can support submission.

## Choose a first command

Run these previews from this repository's root. Read the linked project's
README before a live invocation. A preview applies source without sending
anything; it does not rerun the project's build or tests.

| Project | Preview | Submission order or limit |
|---|---|---|
| [libdisplay-info](libdisplay-info/README.md) | `./upstream/libdisplay-info/submit.sh 01 --dry-run` | Six units; 02 overlaps !210 and stays draft |
| [Mutter](mutter/README.md) | `./upstream/mutter/submit.sh 00 --dry-run` | Design issue, then standalone units 01–04; later stacks have release/design prerequisites |
| [bitvec_helpers](bitvec_helpers/README.md) | `./upstream/bitvec_helpers/submit.sh 01 --dry-run` | Reader overflow and endpoint regressions |
| [dovi_tool](dovi_tool/README.md) | `./upstream/dovi_tool/submit.sh 01 --dry-run` | Mixed mapping methods; other bounds fixes were superseded |
| [gemm](gemm/README.md) | `./upstream/gemm/submit.sh 01 --dry-run` | Existing PRs already cover the fix; exact-PR validation reply prepared, no duplicate PR |
| [ksni](ksni/README.md) | `./upstream/ksni/submit.sh 01 --dry-run` | Menu IDs; failing-before regression |
| [hiqlite](hiqlite/README.md) | `./upstream/hiqlite/submit.sh 01 --dry-run` | Draft PRs after explicit local human review; private-reporting and design items stay held |
| [hiqlite-wal](hiqlite-wal/README.md) | `./upstream/hiqlite-wal/submit.sh 01 --dry-run` | Purge boundary; incarnation proposal needs design discussion |
| [mpv](mpv/README.md) | `./upstream/mpv/submit.sh 01 --dry-run` | 01, 02 and 04 have scoped build/test evidence; runtime limits and draft status remain explicit |
| [FFmpeg](ffmpeg/README.md) | `./upstream/ffmpeg/submit.sh 02 --dry-run` | Static Vulkan configure fix; caption proposal still needs runtime evidence; RASL item superseded |
| [jellyfin-ffmpeg](jellyfin-ffmpeg/README.md) | `./upstream/jellyfin-ffmpeg/submit.sh 01 --dry-run` | 01, 02 and 04 prepared; subtitle-filter design held |
| [Linux](linux/README.md) | `./upstream/linux/submit.sh 02 --dry-run` | Exports only our two follow-ups; human `--prepare --thread ID` adds DCO; SMTP/b4 review follows |
| [Proton](proton/README.md) | `./upstream/proton/submit.sh 01 --dry-run` | Three units to Valve's fork; WineHQ receives nothing |
| [EasyEffects](easyeffects/README.md) | `./upstream/easyeffects/submit.sh 01 --dry-run` | Safety first, then gain control; device-route design held |
| [Cavern](cavern/README.md) | `./upstream/cavern/submit.sh 01 --dry-run` | Three independent units with scoped receipts |
| [Expo](expo/README.md) | `./upstream/expo/submit.sh 01 --dry-run` | Splash candidate stays draft pending full package/prebuild checks; optional-camera proposal held |
| [Runner/rqbit](https://github.com/pjunod/runner/pull/257) | In Runner: `contrib/rqbit/upstream/submit.sh --dry-run all` | Nine PR units and three design issue drafts; source remains in Runner |

The [speaker converter](speaker-tuning-to-easyeffects/README.md) questions
resolve to documented normalization behavior and the existing
`--enable level-restore` option. The [Raspberry Pi port](rpi-ffmpeg/README.md)
is third-party work; its residual Makefile hypothesis is not a confirmed bug.
Neither is a new code submission.

## Configure the chosen submission route

GitHub helpers require `gh` logged in as `pjunod`. That login was verified
during preparation. Other live routes need the contributor's own setup:

| Route | Required setup |
|---|---|
| GNOME GitLab | Account and `~/.config/upstream/gitlab.gnome.org.token` |
| freedesktop GitLab | Verified account allowed to fork, and `~/.config/upstream/gitlab.freedesktop.org.token` |
| FFmpeg Forgejo | Account and `~/.config/upstream/code.ffmpeg.org.token` with access to fork, push and open PRs |
| Kernel email | Verified latest original-thread Message-ID, DCO review, and an SMTP or b4 submission route |

The GitLab helpers require `api` and `write_repository` token capabilities.
Keep token files private (`chmod 600`). None of these three token files was
present at the 2026-10-28 check. No Git SMTP server was configured in this
checkout's effective configuration. Account existence and verification were
not inferred from missing local files. Actual submission remains a deliberate
contributor action; no account or transport was tested by sending content.

## Keep authorship and review decisions with the contributor

Exported patches retain their real authors and omit Paul's sign-off.
Only Paul can certify his contribution. Live commands that require a
sign-off add it when he deliberately runs them after review; tests of
those command paths use local fixtures and fake services.

Descriptions disclose AI assistance without claiming human review has
already occurred. Edit the description into your own words, understand
each change, and check the project's current policy before running its
live command. For held issues, first supply the missing evidence in the
draft. Never infer permission to resubmit someone else's patch from a
successful local build.

The kernel has an email preparation path and retains the original
contributor's prerequisite series separately. Expo's splash candidate has
failing-before/passing-after lint and plugin regressions; it stays draft
until full package and prebuild/EAS checks run. Its optional-camera item
remains a discussion draft.
Private display-management work and project-specific policies remain
outside the submission kits.

## Integrity and retained evidence

[SHA256SUMS](SHA256SUMS) covers the submission material, separately from
the repository root's original source-series manifest. Refresh it only
after reviewing intentional changes:

```bash
python3 scripts/check_upstream.py --write-checksums # Record reviewed kit bytes.
```

The [catalog tests](../tests/test_upstream_catalog.py) check missing ledger
coverage, changed bytes, unsafe paths and accidentally exported sign-offs.
Helper tests exercise local transports; a mocked successful API response
does not claim that a real account, fork or upstream request exists.

Large builds and full logs stay in the existing owned build slots. Small
receipts preserve source identities, commands, outcomes and log hashes.
Inherited results are identified as inherited; new focused checks are
recorded separately. No preparation command installs a package, changes
the running display or activates a profile.
