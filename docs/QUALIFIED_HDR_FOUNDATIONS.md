# HDR foundations, public tooling and experimental launcher

Status: final source preparation for [draft PR20](https://github.com/pjunod/rog_hdr_dv/pull/20),
2026-10-15; whole-candidate review completed with three support-helper findings,
now corrected and awaiting focused independent re-review. This is not
full Dolby equivalence, a package release, a new installation, or final review
approval. The integration task is `t_67396754`; independent review is
`t_c00009d9`, followed by final qualification `t_f06aa8f3`.

## Deliberately selected source, not held history

Base main is `9c1fea526c2ea954bd9730e5ffbb4d370cbd13ad`. No merge or
cherry-pick of PR16/17 is used. Donor references are private local inspection
refs only and must not be pushed. Existing main audio separation, attribution,
licences and narrow secret-scan rules are retained. One additional exact-path,
exact-value allowance identifies a recomputed public regression AST digest in
the applicability receipt, not a credential; no detector or general hash class
is disabled. Upstream patch
mail authors, dates and bytes remain unchanged.

| Selected component | Actual qualified repository donor | Contract and retained evidence |
|---|---|---|
| nativehdr10, lifetime/offscreen, Ubuntu port and package recipes | `e8f9e8f6072cfb88a8dd119c33cb17caa407f2f5`, tree `b6d663a70e6b8f5a6f339489842e02860b802ed3` | [Ubuntu delivery](NATIVEHDR10_UBUNTU_DELIVERY.md), [qualification](../evidence/nativehdr10-ubuntu-qualification.json) |
| Public schema1/schema2 headless harness | `2cbbb772c479feb3c754ededbfb250ecbc3a79d1`, tree `1c8c995089f578fd0157df570b86d38b73b25e5b` | [Harness](DOLBY_HARNESS.md), [qualification](../evidence/dolby-postreshape-qualified.json) |
| Experimental2 launcher using stock runtimes | `79f5e0af3bc0cf394ebda2dce2964c993cf92b49`, tree `6f691a2e9d921390c78611ed81e3ab95b0f49e1d` | [Launcher](../tools/native_player/README.md), [qualification](../evidence/experimental-player-qualification.json) |

The player identity was read from the actual FINAL-DELIVERY receipt, not inferred
from an earlier pending-solver kit. No donor-wide global status or held handoff
ordering is imported as current policy. Historical topical checkpoints/receipts
retain their dates and identities; this page and [status](STATUS.md) supersede
old next-task ordering and permissions, not the historical evidence itself.

## Dependency closure and exact component source

The upstream Mutter series remains based on `d82671c3035bfdb10fdc1ffd2c0e31859bb00ff7`.
Main's 0001–0049 are unchanged; append reviewed 0050–0090. The final tree is
`c113c0ca9ac046c43f85992aa81ffb0b57633b36`. Ubuntu's alternative series remains
based on authenticated-source import tree `30242cc54cebe1ec524a6d79473b41be5f07d05b`
(version `51.0-1ubuntu3`): main's 0001–0061 are unchanged; append 0062–0105,
final tree `08740f943fb2ddda60411fa4d72bb4ccc4238e5f`. Do not stack these
alternative series. Existing library source/API is unchanged: upstream tree
`72626245922181526fbcb990de3eb7f575efa56b`, Ubuntu hdr9 tree
`96d65c11ed0f408792c41cd42c2866255b1089d0`. Original archive URLs, hashes,
base/candidate pins and exact order are in [sources.json](../sources.json).

[Integration provenance](../evidence/full-integration-source.json) retains
canonical lifetime0078–0087 and the existing offscreen0088–0089 envelope
renumbering. No new renumbering or patch-body modification is needed here.
SHA256SUMS deliberately appends the donor's exact new entries; old entries and
all patch bytes remain unchanged. Metadata status strings alone are refreshed.

The harness does not link against the custom compositor: it uses the exact
Ubuntu libplacebo packages/headers and CPU Vulkan closure in
[dependencies.json](../tools/dolby_harness/dependencies.json). The launcher is a
Python subprocess/IPC wrapper, not an mpv/libplacebo fork. Its separate stock
mpv/FFmpeg/libplacebo source inventory and package pins are in
[inputs.json](../tools/native_player/inputs.json) and
[interface inventory](../tools/native_player/interface-inventory.json).
The three components do not acquire a new shared render ABI merely by sharing
this patch repository. No WSI bridge, Sparks adapter or partial DM implementation
is selected.

### Explicit inherited prerequisites needing whole-candidate review

The support tools originally published by Claude Agent in held commit `7c78457`
are selected as files, not as history: `build-upstream.sh`, `check-each-commit.sh`,
`codex_apply.py`, `container-setup.sh`, `export_series.py`, `package-ubuntu.sh`,
`reconstruct.py`, `scan_publication.sh`, `test-mutter-colour.sh`,
`upstream_msg.py`, and `wine-runtime-test.sh`, all under `tools/`.
They are in the new independent-review scope. Historical reconstruction/use
receipts are not blanket source approval. The later qualified offline packager
and validation runner also remain visible to that review.

Do not run the container setup, privileged legacy test helper or Wine runtime
helper on an owner's machine. Native execution uses the authorized fixed
wrapper, new owned directories and unprivileged equivalent compiler/test
commands. This PR does not activate anything or include private OEM tools.

## Retained tests, new static checks and compilation

[evidence/qualified-main-applicability.json](../evidence/qualified-main-applicability.json)
binds every selected file to donor bytes and the component receipts to their
unchanged code/dependencies. Retained passes stay at their original executing
heads/trees, not at this integration head. In particular:

- nativehdr10/Ubuntu: the existing 89 scoped invocation requirements and 29
  historical runner methods retain the original per-ID validity/skip/warning
  dispositions. Historical upstream/lifetime/offscreen receipts are preserved,
  not added together as independent new tests.
- Harness: 48 method requirements use the corrected post-reshape receipt,
  including 32 newly executed and 16 retained at their original identities.
  Schema1's 27 methods are not counted again as a separate 27-test addition.
- Launcher: the one 30-method/34-subtest batch and exact payload/solver receipts
  are retained. The genuine stock P5 trial is not a corrected-launcher trial;
  P8 runtime remains unproved and P7 FEL remains excluded.

The initial source preparation executed no units. The correction lane adds
`tests/test_legacy_helpers.py`: actual helper control flow in temporary Git
repositories with stub build/runtime commands, never the privileged Wine outer
installer. Commit builds reject existing paths, check every prerequisite and
Meson source/build association, and remove only their own worktree. Publication
scanning distinguishes no matches from read errors; generated Wine commands
preserve initialization/test/timeout results across owned-process cleanup.
Use `HDR_HELPER_TEST_ROOT` for an explicit durable scratch root; the default is
ignored `work/helper-tests`. Focused independent re-review precedes the single
new helper batch. No unchanged component suite is invalidated by these fixes.

New integrity,
canonical replay, source comparison, syntax/static inspection, compiler and
publication-scan receipts are not unit passes. The reviewer decides the minimum
new/invalidated final batch after all findings are fixed. No full-suite repeat
is justified solely by a new repository commit or reviewer.

The [source-bound compiler receipt](../evidence/qualified-main-compiler.json)
records passing native x86_64 library, headless C and both full Mutter builds,
plus syntax compilation of 28 Python files. All 302 imported compiler inputs
match the final candidate; canonical library10, upstream90 and Ubuntu105 replay
matches the declared trees. The upstream build took 294.22 seconds and Ubuntu
302.04 seconds including setup. Ubuntu's original success was recovered from
the retained execution receipt; a later readback is not another build. A stale
checkpoint prompted one continuation that stopped before compilation on an
existing dependency directory. No passed compiler stage or unit was rerun.
Raw logs and exact executable hashes remain in the private review handoff.

Ubuntu package identity must not be rewritten: the historical qualified kit
contains a corrected common-bin from Ubuntu105 while eight other Mutter
artifacts retain Ubuntu104 construction identity. The separate full fresh
Ubuntu105 build is compiler evidence, not those eight artifacts' provenance.
Same-version provisional common-bin selection requires exact hashes, not a
version-only upgrade. No new binary release or solver state is implied here.

## Publication, durable paths and remaining acceptance

The old publication log's twelve home-workspace paths were historical additions
in donor history. The final selected receipt already uses neutral
`preserved-caller-cancel-t_457bd73c` and `preserved-offscreen-t_38887c3f` identifiers.
No historical path-bearing commits are imported. Historical `/work/...` paths
inside compiler commands are evidence locators, not required build defaults.
All active recipes take explicit paths; use a task-owned durable `HDR_WORK`
root for source/build/scratch and keep the exact private locator mapping on the
board, not in public source. Original receipts and private kits remain immutable.

The deliverable is source-only. Do not attach historical private package kits,
raw host captures, official XML/reference frames, proprietary tools or numerical
comparisons to the PR. Private-only artifact locations and hashes are indexed
in the integration task's durable handoff, never the public archive.

Main-only source applies only to mobile builds intended for installation on
physical devices and those installations; it does not restrict non-mobile HDR
compiler work. This clarification grants no new device/deployment permission.
PR16 stays held; PR17 stays unchanged until the coordinator decides disposition
following safe replacement landing. This preparation does not merge either PR.

Full mapping/trims/reference agreement, exact preferred-target identity and
no-double-mapping, broader KMS scanout and size-accounting warnings, Windows and
optical checks remain programme work. No certification, calibrated accuracy,
clean hardware logs or full Dolby completion is claimed.
