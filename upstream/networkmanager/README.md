# NetworkManager upstream kit

**Project:** [NetworkManager](https://gitlab.freedesktop.org/NetworkManager/NetworkManager) ·
**Base:** `main` at `62c8e8b2caebbb86182c79223c0109048eac154e` (2026-11-16) ·
**Venue:** merge request on gitlab.freedesktop.org, which needs a freedesktop
GitLab account. **Nothing has been sent.**

| # | Catalog | Unit | Files | Status |
|---|---|---|---|---|
| 01 | NM-1 | Keep devices carrying a network filesystem up through suspend | `src/core/nm-manager.c` | held |

## This kit is code only, by NetworkManager's rules

NetworkManager's `CONTRIBUTING.md` (AI coding assistants section) and
`AGENTS.md` at the base above make the author responsible for every line,
require the author to have built and tested the change personally, and require
the author to write the commit message, the merge request description and all
review replies. Agents must not write those, and commits carry no
`Signed-off-by:` and no tool or co-author trailers. AI assistance must be
disclosed in the merge request; the template has a section for it.

So this unit has no commit message and no MR description. It ships
[`01-suspend-netfs/code.diff`](01-suspend-netfs/code.diff) (plain
`git diff HEAD` against the base) and technical notes to help the author
review it line by line: [`01-suspend-netfs/NOTES.md`](01-suspend-netfs/NOTES.md).
This departs from the other kits here, which carry a full exported commit.

## Pre-submit gate (held until done)

1. Get a freedesktop GitLab account.
2. Read the diff and the notes until every line can be explained.
3. On a checkout of `main`, apply the diff, run
   `./contrib/scripts/nm-code-format.sh -i src/core/nm-manager.c`, build
   (`meson setup build`, `ninja -C build`) and run `meson test -C build`.
4. Reproduce the problem and the fix: the
   [VM harness](../../tools/suspend_nfs_repro/nm/) runs NetworkManager with a
   hard NFS reader and `pm_test=freezer`.
5. Write the commit message and the MR description in your own words, disclose
   the AI assistance in the MR, and push.

## What was verified here

On the base above with the diff applied: `meson setup build -Dcrypto=gnutls
-Dppp=false -Dnbft=false` (Ubuntu 26.10 build dependencies plus clang),
`ninja -C build` with no warnings in `nm-manager.c`, and `meson test -C build`
82 OK, 0 fail, 7 skipped (the `checkpoint-rollback` integration tests, which
exit 77 without the privileges they need). `nm-code-format.sh` with
clang-format 22.1.8 was applied; `contrib/scripts/checkpatch.pl` reported
nothing. Behaviour was verified on the Ubuntu 1.58.1 backport, not on `main`:
the VM freezer test (direct NIC and bridge port) and one real suspend on the
ROG ([suspend diagnosis and results](../../docs/SUSPEND_NFS_READER.md)).
[Receipt](../../evidence/upstream-networkmanager-suspend-20261116.json).
