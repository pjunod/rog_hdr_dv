# ABI368 mapping integration and isolated package preparation

## Current boundary — 2026-10-18

This is a main-based scoped source integration, not a released package or a
new render/accuracy observation. Source starts at public main
`b13ceae3da088bb6326e963b3ba00d4b4b2c748b`, not the held PR16 history. The
frozen algorithm is `us961-sqrtsum-pq-y-post-v1` / `y-pq-post-sqrtsum`, private
ABI368. The [equations, exact scope and retained observations](SQRTSUM_PQ_Y_POST.md)
remain unchanged. No numerical tuning, precision change or broadened support.

Historical observations, each over all 8,847,360 pixels, GPU invalid zero:

| Original frame / target | Mean deltaEITP | nearest-rank p95 |
|---|---:|---:|
| 256 / 27 | 0.5542771866435594 | 1.1767793300544394 |
| 714 / 27 | 0.7337404230568803 | 2.0160825393748225 |
| independently reserved 1200 / 48 | 0.535635380895007 | 1.1341677325267563 |

These are retained source-bound PASS observations, not new-head executions.
The complete frontend froze before the independent acquisition; the holdout is
now consumed for this candidate only. No equation search or repeat render is
justified by main-based transplantation. XML detail -0.75 remains unapplied;
no complete CM/raw-RPU/L8/temporal/player/optical/certification claim follows.

Done: exact-byte scoped harness/source/test/evidence transplantation; public-base
library patch replay to the frozen tree; warm native compiler prerequisite;
separate package-relative consumer compilation and static RUNPATH inspection;
additive genuine parser-input preparation. Current: exact source/recipe/fixture
freeze for independent review. Remaining graph: independent final review
`t_2f09b7c1`, ONE affected whole-candidate batch/repository gate and publication/
merge `t_656472e9`, then actual Ubuntu source/binary construction, closure,
isolated install/rollback `t_c97cbefb`. No unit batch, publication, package
transaction, Apple TV access or physical display deployment in this phase.

Public-distribution prerequisite: owner-original utility/documentation licence
is unselected in [LICENSES.md](../LICENSES.md). Owner-input card `t_886b8dbc`
records the narrow grant question. `LicenseRef-no-public-grant` is a notice of
missing rights, NOT permission or satisfaction of LGPL2.1 section6. Preparatory
recipes/compilation continue; final review/distribution awaits the recorded
decision and corresponding notices. Upstream/vendor terms must not change.

## Source closure and attribution

Donor repository source is `76f465bc882bae5df872f74175aab7ec00ddfaac`; exact
library source is historical head `f3b1d3fceb2dfb8343ef36405e3ff07ea232daab`,
tree `fb4c387992dfd578ffd7694c380e56cc852ea2e5`. All249 library file hashes
remain in `wip/libplacebo-dm/public-rgb/SOURCE.json`; the scalar, metric,
original-target frontend, native consumer/build/provenance are byte-identical.
Earlier ABI variants are required dependencies of this exact tree, not extra
newly accepted mappings. Historical documents below are dated context, not
current delivery status:

- [Authored source/storage/parser baseline](AUTHORED_MASTER_BASELINE.md).
- [Original frame-owned OPEN implementation](OPEN_XML205_CANDIDATE.md).
- [Absolute-PQ predecessor](OPEN_ABSOLUTE_PQ_SOP.md).
- [Public RGB/Y/mastering-black predecessor](PUBLIC_RGB_MAPPING.md).

`python3 scripts/reconstruct_mapping.py NEW-LIBRARY-CLONE` fetches public
upstream `https://github.com/haasn/libplacebo.git` at
`cee9b076f2c63104ccfd497fa79c39a867293ec4`, verifies each original local patch
checksum, applies the three open-xml205 files, absolute-pq mailbox (two mails),
and public-rgb mailbox (eight mails), then verifies the exact tree/all249 hashes.
Git am necessarily creates new commit identities; identical tree/file/mode/
gitlink content, not identical committer timestamps, is the reconstruction
contract. Original authors/mail text/context/licences remain intact. No patch
bytes changed and no SHA256SUMS was regenerated. No Mutter/display/launcher
patch, global sources.json pin or held PR16 history is imported.

For compiler source closure, initialize only the required pinned fast_float
submodule (`97b54ca9e75f5303507699d27c6b4f4efe4641a1`); its original licences
are retained. Demos/OpenGL are disabled in the package; system Jinja/MarkupSafe,
Vulkan, shaderc, LCMS and FFmpeg development inputs are explicit Build-Depends.
Do not silently use a historical `/work` shaderc path in a public artifact.
The native builder's base currently lacks shaderc/FFmpeg/Jinja development
packages; the downstream isolated Ubuntu build root must supply them normally.
That is an environment prerequisite, not permission to weaken source binding.

## Package recipe and supported consumer

New source/binary package: `rog-hdr-dm-experimental`.
Version reserved: `0.1.0~abi368.1-0ubuntu26.10.1`, amd64 Ubuntu26.10.
At preparation, the public Ubuntu primary source-name query returned zero
publications, native dpkg-query found no installed package, and the historical
native task artifact tree contained no same-name deb. Recheck immutable release
storage immediately before downstream publication; never overwrite a collision.

Private layout:

- `/usr/lib/rog-hdr-dm-experimental/libplacebo.so.368` — no global replacement,
  headers, pkg-config provider or ldconfig registration.
- `/usr/libexec/rog-hdr-dm-experimental/open-dm-render` — unchanged native code.
- `/usr/libexec/rog-hdr-dm-experimental/run.py` — package-native wrapper.
- `/usr/share/rog-hdr-dm-experimental/` — research harness, source pins,
  source manifest, distinct package compile/install manifests and documentation.
- Normal debhelper dbgsym/source artifacts retain the debug/source closure.

The actual consumer interface is CONTROL INPUT-F32LE OUTPUT-F32LE. The supported
wrapper deliberately exposes only DVH4 variant7:

    python3 /usr/libexec/rog-hdr-dm-experimental/run.py --inspect --stage NEW-DURABLE-STAGE
    python3 /usr/libexec/rog-hdr-dm-experimental/run.py --stage NEW-DURABLE-OUTPUT CONTROL INPUT-F32LE

The latter writes `output.f32`, actual native stdout/stderr and a distinct
`hdr.abi368.package-native-result.v1` receipt. Caller must supply exact original
physical-source/target volumes, ordered L1, selected original target ID and
actual SOP/CW/SG fields in [DVH4 order](SQRTSUM_PQ_Y_POST.md). Input is tightly
packed P3D65/PQ/full RGB IEEE754-f32le (HALF exactly expanded where applicable);
output is RGB-f32le BT2020/PQ/full. No scaling, registration or pixel transform
is added by the wrapper. Arbitrary caller controls are not authenticated
Dolby metadata and do not inherit the retained three-case accuracy evidence.

The wrapper clears loader/display/driver overrides, uses a new durable own
stage/TMPDIR, requires native x86_64 Linux and the CPU Vulkan ICD, rejects system
preloads and verifies the actual loader selected the exact private ABI368.
All installed payload and runtime/ICD hashes are bound before/after execution;
actual whole-download alpha validity is checked, never fabricated. Its manifests
are integrity records, not signatures or independent package authentication.
Use trusted package distribution. Rejected native results retain diagnostics.

The consumer RUNPATH is `$ORIGIN/../../lib/rog-hdr-dm-experimental`, never `/work`.
Meson's runtime install removes library build RUNPATH; post-strip installed
hashes are generated only after normal debhelper stripping. The actual new
package-relative consumer compilation passed native GCC15/Werror; ELF dynamic
inspection confirmed that RUNPATH. This compile reused read-only frozen library
headers/build and is NOT a completed system-dependency package build, installed
runtime qualification, new render or claim that old artifact hashes changed.
The downstream normal library build/install and loader/debug/source inspections
remain required; do not rebuild the successful historical full/noDV trees.

Python `tools.dolby_harness.open_dm` remains strict RESEARCH SOURCE. To use its
render/compare API, retain all exact original source/compiler dependency/header/
library/runtime roots, native CPU ICD, genuine schema3 input/XML/source/log/
reference assets and immutable frontend binding. Historical experiment receipts
are not portable simply because source files are packaged. Package receipts
cannot pass the historical `hdr.open-dm-compile.v1` validator; that validator is
unchanged. No mpv/launcher/raw-RPU/CM/full-playback support is advertised.

## Downstream source/binary construction (not executed here)

### Once-only invalidated supported-baseline fixture, after review

The legacy schema3 baseline consumer/validator remains supported. Its old
three positive/deep-tamper methods are genuinely invalidated by whole-parser/
frontend binding, not retained current-head passes. Current stale-baseline
rejection and independent-reference storage checks remain, AND separate
`CurrentBaselineResultTests` restores all three positive/deep-tamper equivalents
for that supported branch. OPEN positives alone are not their substitute.
Coordinator adjudication authorizes exactly ONE real current-baseline fixture
AFTER independent review, inside the one affected qualification batch. The
reviewed `scripts/prepare_current_baseline_fixture.py` binds existing original256/
target27 source, unchanged stock baseline native/compiler receipt, actual retained
reference EXR and current frontend before execution. It creates a real new
baseline output and source-bound reference storage envelope, not a relabelled
old execution. No new vendor acquisition, official comparison, curve variant or
mapping accuracy claim; zero fixture executions in integration. Its exact input/
compiler/reference/command and old-to-new method mapping are frozen in private
REVIEW_INPUTS/validation inventory. Failed or truly invalidated steps only may
be retried; successful source/reference/metric observations remain immutable.

### Normal downstream package build

After licence decision, independent review/fixes, single affected batch/gate and
merge, use a fresh source preparation directory and a dependency-complete
isolated native Ubuntu build root. Prepare from the exact reviewed source:

    python3 scripts/prepare_mapping_package.py --library VERIFIED-LIBRARY-CLONE --destination NEW-SOURCE

This copies only verified library files/pinned fast_float, tracked allowlisted
harness/pins/docs/recipes and Debian metadata; no .git, vendor binaries/XML,
images, credentials, private receipts or host paths. `PACKAGE-SOURCE.json` binds
all source bytes. Construct the `.orig.tar.xz` without the top-level `debian/`
directory (retain it for the quilt Debian tar), then run normal unsigned
`dpkg-buildpackage -S -sa -us -uc` and `dpkg-buildpackage -b -us -uc` in that
prepared source. Do not bypass Build-Depends or call the upstream unit suite
again; `override_dh_auto_test` explicitly preserves the separate reviewed unit
receipt. Retain .dsc, orig/debian tars, source/binary .changes and .buildinfo,
.deb, automatic dbgsym, checksums and full build logs. Source reconstruction
must work from those public inputs, not a local Git bundle containing secrets.

Inspect dpkg-shlibdeps closure using the private library search directory;
its private SONAME is resolved internally and excluded as a self-dependency,
not published as a system-wide libplacebo provider. Verify every external runtime
package/ABI and exact build-ID/debug/source correspondence. No unrelated
Mutter/libdisplay-info/old-launcher packages are rebuilt or counted as this
mapping delivery.

## Isolated install and rollback (not executed here)

Never run these recipes on a live desktop/device. Create a NEW task-owned
`/work` PRoot Ubuntu root with dependency-complete baseline and an explicit
`ISOLATED-ABI368-ROOT.json` marker containing exactly:

    {"schema":"hdr.abi368.isolated-root.v1","purpose":"package-qualification-only","package":"rog-hdr-dm-experimental","version":"0.1.0~abi368.1-0ubuntu26.10.1"}

`packaging/rog-hdr-dm-experimental/isolated_transaction.py install --root ROOT
--evidence NEW-INSTALL-EVIDENCE --deb EXACT-DEB` validates artifact identity,
refuses overwriting the unique package, runs only inside PRoot and retains
actual transaction/query/host-state hashes. Then inspect actual package loader
closure in the isolated root with the wrapper's `--inspect`; any permitted
native smoke test is a separately labelled package check, not a new independent
accuracy render or rerun of vendor observations. Preserve input/runtime receipts.
`isolated_transaction.py rollback --root ROOT --evidence NEW-ROLLBACK-EVIDENCE`
purges ONLY this exact private package. Compare the full isolated baseline
package inventory/files and host invariant before/after; the transaction helper
alone checks package disposition and host dpkg status, not every host file.
Remove the task-staged installation deb after verifying its retained hash in
the artifact kit. No boot/compositor/session/profile/physical display is touched.
