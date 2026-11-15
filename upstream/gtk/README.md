# GTK submissions

Upstream: <https://gitlab.gnome.org/GNOME/gtk> (merge requests into `main`).
Base: `2c32595f20d987869e9122e9be901aaf2191f844` (`main` on 2026-11-14, "Merge branch
'imquartz-filter-once' into 'main'"). `gdk/wayland/gdkwaylandcolor.c` was last changed upstream
by `cf6b6de955b1`. Nothing here has been submitted, pushed or posted.

The patch is authored by Paul Junod, has a body and a `Link:` line, and has no `Signed-off-by`
(added by `submit.sh` when Paul runs it). `Link: TBD-MR` becomes the unit's own MR URL.

## Units, in submission order

| NN | Slice | Unit | Commits | Stacked on | Status | Overlap / notes |
|---|---|---|---|---|---|---|
| 01 | GTK-6 | gdk/wayland: NULL-tolerant color-state description destructor | 1 | - | ready | No upstream test; no MR or issue found for it |

The product-side form of this fix is `patches/ubuntu-gtk4-display-target/0021-*`, written for
GTK 4.24.1. The upstream patch is the same change adapted to current `main` (whose table has
`id_to_cs`, not `identities_by_wire`). The other GTK ledger items (GTK-1 to GTK-5) are design
discussions or held; none is prepared here.

## Evidence limits

The patch applies to the recorded base (`git apply --check` in a minimal repository holding only
that file). It has not been compiled against a full GTK build, and no GTK test, CI job or
compositor run covers it. The crash was reproduced on GTK 4.24.1 with gdb, not on `main`; `main`
was inspected and has the same table construction and the same NULL insertions.

## Submitting

From this directory:

    ./submit.sh 01 --dry-run   # unsigned application preview; no remote changes
    ./submit.sh 01             # fork if missing, push hdr-01-slug, open the MR

Before the first run: GNOME GitLab account, and a personal access token with `api` and
`write_repository` in `~/.config/upstream/gitlab.gnome.org.token` (mode 600). GTK has no written
AI rule that was found at preparation time; GNOME-wide policy is being debated. The description
discloses AI assistance without claiming human review. Edit it into your own words and check the
current policy first. A real submission also requires upstream `main` to still equal the base
above, or a rebuild and retest on the newer tree.

The shared helper tests (`../../tests/test_upstream_gitlab_submit.py`) use local Git and a fake
GitLab; `submit.sh` for this kit has not been run against a real GitLab.
