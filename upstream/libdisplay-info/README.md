# libdisplay-info submissions

Upstream: <https://gitlab.freedesktop.org/emersion/libdisplay-info> (merge requests into `main`).
Base: `af382cf311ce60983708a9e664728a61843143e7` (`main` on 2026-10-27,
"tool/gen-cta-vic: specify dependencies via PEP 723"). Nothing here has been submitted.

The ten patches in `patches/libdisplay-info/` were reshaped into six units, one commit each, in
the project's commit style (`area: lowercase summary`, with a body). Fixups were squashed:
0006 into 0005, and 0008, 0009 and 0010 into 0007. The resulting tree is identical to the old
series except for one test change in unit 02 (an assertion moved before the allocation it
bounds; the GCC 13 analyzer reported a false positive there, GCC 14 did not). Every commit is
authored by Paul Junod and carries no `Signed-off-by`; `submit.sh` adds it with
`git am --signoff` when Paul runs it, since the DCO is his to certify (the README requires it on
every commit).

## Units, in submission order

| NN | Commit | Depends on | Status | Notes |
|---|---|---|---|---|
| 01 | displayid2: bound section padding scans to the remaining payload | - | ready | Applies alone. ASan out-of-bounds read fix plus test. Best first MR. |
| 02 | displayid2: parse Display Interface Features data block | 01 (test/meson.build context) | ready (opened as a **draft** MR) | Overlaps open MR !210 (Sean Paul), same block. DESCRIPTION.md offers it as review input or an alternative and explains the differences. Decided 2026-10-27 by Claude, for Paul to look over: `submit.sh` opens it as a draft so the code is visible, and Paul links it from a short comment on !210 rather than presenting a competing MR. Units 03-06 build on it. |
| 03 | displayid2: reject unsupported nested CTA headers | 02 (context only) | ready | Builds on merged !202 and !212. |
| 04 | edid: expose structured extension parsing failures | 03 | ready | New public API (`di_edid_has_extension_failures()`); asks for a design nod. |
| 05 | displayid2: expose native luminance from Display Parameters | 04 | ready | Uses the data block plumbing of 02. Asks whether one Display Parameters struct is preferred. |
| 06 | displayid2: expose native chromaticities from Display Parameters | 05 | ready | Same block as 05. |

The units form one chain because each touches `test/meson.build` and 05/06 need 02's data
block plumbing. A stacked MR contains the commits of the units below it; its description says
so. If !210 is preferred over 02, units 03 to 06 need a rebase onto it (05 and 06 only use the
generic data block plumbing).

Mutter depends on 02 to 06 being released (libdisplay-info 0.5): see `../mutter/README.md`.

## Verification (2026-10-27, cloud container)

For each commit, stacked in order on the base, in the four `.gitlab-ci.yml` configurations:

| Configuration | Command | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|---|
| werror | `meson setup build -Dwerror=true; ninja -C build; meson test -C build` | 70/70 | 73/73 | 74/74 | 75/75 | 76/76 | 80/80 |
| build-gcc | `CC=gcc-14 CFLAGS=" -Wnull-dereference -fanalyzer -O1" meson setup b --fatal-meson-warnings -Dwerror=true` + test | 70/70 | 73/73 | 74/74 | 75/75 | 76/76 | 80/80 |
| build-clang | `CC=clang meson setup b --fatal-meson-warnings -Dwerror=true -Db_sanitize=address,undefined -Db_lundef=false`; `UBSAN_OPTIONS=halt_on_error=1 meson test` | 70/70 | 73/73 | 74/74 | 75/75 | 76/76 | 80/80 |
| testing-check | edid-decode from v4l-utils `1316a80455ef` (the CI pin) in PATH; `ninja -C b gen-test-data; git diff --quiet`; every `test/data/*.edid` listed in README | pass | pass | pass | pass | pass | pass |

Toolchain: GCC 13.3 (werror), GCC 14.2 (analyzer, as CI uses a current GCC), Clang 18.1, meson
1.12.1, hwdata `pnp.ids` stub. Not run: the `build-docs` job (gyosu). The same stack also built
and passed 80/80 in an Ubuntu 26.10 container on lab5, where it was installed as the prefix for
the Mutter builds.

## Submitting

One command per unit, from this directory:

    ./submit.sh 01            # or: ./submit.sh all (units in order, up to the first not marked ready)
    ./submit.sh 01 --dry-run  # everything except fork, push and MR

It clones upstream into `~/.cache/upstream-submit/` (override with `UPSTREAM_SUBMIT_DIR`), puts
the unit (and any unit it is stacked on that is not merged yet) on a fresh branch of current
`main` with `git am --signoff`, stops with a clear message if it no longer applies, creates
Paul's fork if it is missing, pushes the branch `ldi-NN-slug` and opens the MR with
`DESCRIPTION.md` (title from its first line). Running it again force-pushes the branch and
updates the existing MR. `--draft` opens it as a draft.

Before the first run:

- gitlab.freedesktop.org only lets **verified** accounts fork. Request "user verification" for
  the `pjunod` account first (the freedesktop GitLab spam-protection process; the fork call
  fails with HTTP 403 until then).
- Put a personal access token with the `api` and `write_repository` scopes in
  `~/.config/upstream/gitlab.freedesktop.org.token` (mode 600).
- Read each DESCRIPTION.md: they are written in Paul's voice and end with the AI-assistance
  statement ("I reviewed the changes and take responsibility for them"), which is his to make.

`submit.sh` was tested with `--dry-run` for every unit and for `all` (the resulting tree equals
the verified stack, and every commit gets exactly one `Signed-off-by: Paul Junod`). The real
fork, push and MR path has not been run.
