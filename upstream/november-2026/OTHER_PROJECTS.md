# Other project additions — November 2026

**Status:** source-backed inventory additions; upstream ports remain ·
**Updated:** 2026-11-09.

These five candidates extend the [submission ledger](../../docs/UPSTREAM_SUBMISSIONS.md).
They come from Runner dependency changes and Plurx player exports after the
October 28 inventory.
The [audit receipt](../../evidence/upstream-other-projects-20261109.json)
records exact source identities, reviewed paths and test-presence limits.
The [submission guide](../README.md) explains how preparation states differ
from contributor review and upstream acceptance.

| Unit | Project | Disposition | Next action |
|---|---|---|---|
| R14 | rqbit | Discussion draft | Agree the read-only verification API, then prepare an upstream port with tests. |
| R15 | rqbit | Held | Split the file-lookup optimization and qualify its boundaries independently. |
| HQ-27 | hiqlite | Held | Export the generic terminal-stream fix against current upstream, separate from Runner shutdown changes. |
| MPV-8 | mpv | Held | Extract and qualify the generic software-upload precision and cleanup change. |
| LP-3 | libplacebo | Discussion draft | Agree reusable quantizer placement; the existing call site is a custom mapped cache. |

## Source boundary

The inspected Runner source is
[`6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e`](https://github.com/pjunod/runner/commit/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e).
The rqbit additions entered Runner in
[`0af6210fd0cbaa6f2cdd08421e02eb70f7364e1a`](https://github.com/pjunod/runner/commit/0af6210fd0cbaa6f2cdd08421e02eb70f7364e1a)
on November 1. The hiqlite fix entered in
[`14f283c6acd719cabcf5c99fda85675fca8b160d`](https://github.com/pjunod/runner/commit/14f283c6acd719cabcf5c99fda85675fca8b160d)
on November 3.

These are maintained downstream source changes. This inventory review did
not build, run tests, requalify the nine existing rqbit submission units or
check the current third-party upstream heads. A named test means its
assertions were inspected in source; it is not a new passing receipt.
No submission was sent during this review.

## R14 — selected-piece verification over read-only storage

**What changes:** the new `verify_selected_piece_ranges` API reuses
rqbit's piece verifier against caller-owned storage callbacks. It merges
selected piece ranges, reads neighboring boundary bytes where a piece
crosses files and accepts a cancellation checkpoint. It does not create a
session or writable storage.

**Source:** [maintained patch 0022](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/contrib/rqbit/0022-read-only-piece-verifier.patch)
and the [exported function](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/contrib/rqbit/vendor/crates/librqbit/src/file_ops.rs#L364).
The maintained dependency starts from rqbit v8.1.1,
`00b97485160ff5b5aa2b379ea0815d568ec665f0`, plus the ordered series in
[Runner's derivation contract](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/contrib/rqbit/README.md).

**Existing test:**
[`selected_piece_verification_checks_neighbor_boundary_and_changed_payload`](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/crates/nzbd-torrent/src/lib.rs#L2568)
checks a selected file whose last piece includes bytes from its neighbor,
rejection after a boundary payload changes and an interrupted callback.
It lives in Runner's adapter suite, rather than rqbit's upstream suite.

**Before a submission:** discuss the callback and cancellation API, check
today's upstream interfaces and move the behavioral tests into the proposed
upstream change. This is a separate proposal from R1–R13's restore,
discovery, tracker and connection-budget changes.

## R15 — locate the first intersecting file for piece reads

**What changes:** the same maintained patch changes existing
[`FileOps` piece lookup](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/contrib/rqbit/vendor/crates/librqbit/src/file_ops.rs#L192)
to use `partition_point` and begin at the first intersecting file. It avoids
iterating over every earlier torrent file for each piece. This change can
be exported independently of R14's new public API.

**Evidence limit:** R14's source test exercises a cross-file boundary, but
it does not independently establish zero-length-file behavior, lookup
complexity or a measured performance improvement. No new timing claim is
made here.

**Before a submission:** compare the current upstream implementation, split
the change from the API addition and add focused boundary and empty-file
cases. Qualify the performance claim with a many-file regression or a
bounded benchmark before presenting it as a performance fix.

## HQ-27 — close upgraded API streams after Raft termination

**What changes:** an established API WebSocket can outlive its HTTP listener
and keep returning stopped-leader errors to surviving voters. The
[server stream fix](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/vendor/hiqlite/src/network/api.rs)
observes the matching Raft group's metrics and closes the existing writer
loop on shutdown, a fatal running state or closure of the metrics channel.

**Source provenance:** [Runner's vendor record](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/vendor/README.md)
identifies the inherited maintained hiqlite source as plurx commit
`8663d6c0e7d4a8242cd1b6c6d385cecd72c7d176` and names the additional local
transport correction. That provenance is not an unmodified upstream base.

**Existing test:**
[`api_stream_stop_watch_ignores_live_updates_and_observes_terminal_states`](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/vendor/hiqlite/src/network/api.rs#L288)
checks that live metric changes preserve the connection and that shutdown,
fatal stop and a closed channel end the wait. Runner's
[focused check target](https://github.com/pjunod/runner/blob/6a6ff9d3a12f2def82e7ebbc33280ce47cf3c48e/Makefile#L201)
names this test; this audit did not execute it.

**Before a submission:** split the generic library change from Runner's
minority-shutdown adapter work, reconcile it with current upstream socket
ownership and qualify the exported port. HQ-10 concerns joining socket
tasks and HQ-11 concerns dropped-RPC manager notification; this candidate
addresses a different lifetime boundary, the terminal Raft group of an
already established server API connection.

## MPV-8 — software upload precision and partial enhancement cleanup

**Source:** [Plurx patch 0007](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/packaging/patches/mpv/0007-vo_gpu_next-preserve-DV-software-sampling-precision.patch)
at the remote source head recorded below. Owned high-aligned UNORM16
staging preserves filtering precision for low-aligned planar 10-bit software
Dolby inputs and limited BT.2020/PQ, including ordinary HDR10. Hardware
imports, P010 and integer-format fallback retain their paths. Required
unusable enhancement input is refused with partial-frame ownership cleanup.

The
[source control](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/tests/test_dv_render_precision.py)
extracts actual production upload/helper code into a CPU boundary harness.
It covers code values, padded/negative strides, eligibility, ownership and
failure cleanup. This audit did not execute it. The generalized export's
native build, GPU playback performance and current-upstream extraction
remain requirements. Preserve the generic upload/cleanup scope and omit
private renderer integration; this is distinct from MPV-6's raw-RPU ownership.

## LP-3 — discuss exact binary32-to-UNORM16 quantization

**Source:** [Plurx patch 0008](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/packaging/patches/mpv/0008-vo_gpu_next-round-the-final-DV-UNORM16-cache-exactly.patch)
contains a public integer GLSL helper for rounding the exact binary32 input
times 65535 with ties to even. Its actual call site is the custom Vulkan
mapped UNORM16 cache. That call site is not a generic stock libplacebo fix;
the proposal is a reusable quantizer interface or placement discussion.

The
[source test](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/tests/test_dv_unorm16.py)
compiles the extracted shader as a CPU control with an independent rational
oracle. Its expected exhaustive totals are assertions, not new execution
results. Discuss upstream applicability, produce a standalone current-source
change and establish native GPU behavior before a code submission. Private
mapping equations and implementation remain excluded.

Patch 0006's normalization and renderer-error checks repair the custom
reconstruction pass. They supply context for LP-1/LP-2 and MPV-3's boundary;
they do not add another independent baseline mpv defect to this inventory.

## Remote-head coverage beyond the local snapshots

The initial local source heads lagged the published branches. The audit
therefore also inspected these immutable remote deltas on November 9:

| Project | Published head checked | Complete changed-file delta | Result |
|---|---|---:|---|
| plurx | `8ab61a77989c8200af8db6f060328192e47ee16f` | 318 | Three new mpv patch exports, listed below. |
| Runner | `30f4a1a8e68317cad4ca9cd71773557ef812f0e4` | 170 | No vendor/contrib/patch changes; the R14/R15/HQ-27 source hashes above remain valid. |
| Curator | `ae26882cae67edfedd2b7395c53158448261f9b4` | 272 | No plugin implementation change; mobile dependency patch-version alignment adds no demonstrated upstream fix. |

GitHub's plurx comparison hit its 300-file limit. Comparing both complete,
non-truncated recursive Git trees supplied all 318 changed blob paths.
Runner and Curator remained below that limit. Relevant mobile manifests
were read at both ends: Runner changed its own version, and Curator aligned
Expo SDK 57 patch versions. Those dependency bumps do not establish whether
the older Expo submission candidate is still needed.

The newly inspected plurx exports are
[reconstruction metadata normalization](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/packaging/patches/mpv/0006-vo_gpu_next-normalize-DV-reconstruction-metadata.patch),
[software sampling precision](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/packaging/patches/mpv/0007-vo_gpu_next-preserve-DV-software-sampling-precision.patch)
and [exact final UNORM16 quantization](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/packaging/patches/mpv/0008-vo_gpu_next-round-the-final-DV-UNORM16-cache-exactly.patch).
Their public source and controls require upstream-scope review alongside the
[media inventory](MEDIA.md). The custom reconstruction/cache call sites do
not establish a stock mpv or libplacebo defect or authorize private renderer
implementation for publication.

The
[upload and cleanup control](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/tests/test_dv_render_precision.py)
extracts the actual production functions into a CPU boundary harness. The
[quantizer control](https://github.com/pjunod/plurx/blob/8ab61a77989c8200af8db6f060328192e47ee16f/clients/linux-player/tests/test_dv_unorm16.py)
checks a pinned shader against a rational reference. Both were inspected in
source and were not executed by this audit. Their assertions do not supply
new native or GPU results.

The inspected rog_audio delta through
`ee47f81460169ec3dd3ddb7126110ca635cd81cf` contains its own speaker service
ordering and bounded diagnostic tools, with no changed Cavern or EasyEffects
source. Those service and diagnostic changes therefore add no upstream-library
candidate here. These bounded findings do not classify uninspected active
work or assert that no upstream communication occurred elsewhere.
