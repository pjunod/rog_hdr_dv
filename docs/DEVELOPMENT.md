# Development — reconstruct source and prove each change

Read [architecture](ARCHITECTURE.md) for ownership and [provenance](PROVENANCE.md)
for imported source identities. The repository stores patch series, not full
vendored Linux/Mutter trees or installable binaries.

## Current source batch and durable workspace policy

The [main-targeting HDR foundations candidate](QUALIFIED_HDR_FOUNDATIONS.md)
selects qualified component bytes and preserves their actual historical receipts.
Its inherited support tools are explicit independent-review scope, not implicit
approval of every helper. No unit execution occurs during preparation; review
and corrections precede the minimum affected final batch. Retain valid passing
receipts instead of repeating suites on every repository commit.

All source/build/input/scratch directories must be task-owned and durable, for
example an explicit `HDR_WORK` under the agent's collaboration workspace or
`/work/<owned-task>` in the native builder. Set HOME/XDG/TMPDIR to that owned
root before compiler/testing work. Do not use system temporary directories,
owner repositories, another worker's tree or a frozen qualification build.
Native commands use the existing fixed native x86_64 wrapper, unprivileged;
never emulation, private-key access, host installs or warm-tree reconstruction.
The legacy root-oriented test helper is not the wrapper's execution recipe.

Owner clarification: only mobile app builds intended for physical-device
installation, and those installations, require source already merged into main.
Non-mobile HDR pre-merge builds remain authorized under the existing workflow.
No additional device/deployment permission or review/test waiver follows.

## 1. Verify the repository

```bash
python3 scripts/check_repository.py  # Integrity, series ordering, doc links.
```

A passing result means the recorded patch bytes and repository links agree.
It does not mean the source compiles or the panel renders correctly.

## 2. Choose the correct source path

`sources.json` records the exact base and candidate identities. Each directory
under `patches/` has a `series` file. Apply files in that order.

| Series | Base | Purpose |
|---|---|---|
| libdisplay-info | Upstream `62a9346c3dce2bddba1d4dc186949e4320d6f801` | Native parser/API and regression patches; ordered inventory in sources.json. Upstream follow-up: one Display Parameters structure with per-field presence and diagnostics for reserved values (see [review](REVIEW.md#ninth-batch--independent-review-and-fixes)) |
| mutter | Upstream `d82671c3035bfdb10fdc1ffd2c0e31859bb00ff7` | Native DisplayID eDP capability recognition |
| ubuntu-libdisplay-info | Authenticated Ubuntu `0.3.0-1` source import | Delivered hdr6 prefix, hdr7 luminance and hdr8 chromaticity API, hdr9 packaging (installed 2026-10-11) |
| ubuntu-mutter | Authenticated Ubuntu `51.0-1ubuntu3` source import | Delivered nativehdr2 prefix, then target feedback, colour input, HLG, highlight mapping, gamut compression and review fixes through nativehdr8 (installed 2026-10-11) |
| wine | Wine `wine-11.0`, peeled `db11d0fe6a169c457e23d007e20404643d067aa8` | Desktop CreateFileFromAppW compatibility and the DisplayMonitor runtime class (source; test fixtures only) |
| linux | Ubuntu tag `Ubuntu-7.3.0-8.8`, peeled `d03cf7a92919b0e6ab4e4a756dec41542eb2040f` | Native luminance, Intel selection and KUnit tests |

The upstream and Ubuntu series are alternatives, not patches to stack atop
one another. Ubuntu import/candidate commit IDs are local preparation IDs;
they are not fetchable upstream revisions. Obtain the authenticated Ubuntu
source package version first, then apply the exported series. Do not replace
it with today's latest package and inherit the old results.

Each downstream `source_origin.artifacts` entry now records a public archive
URL and SHA-256, alongside the expected `base_tree`. Archive files can age out;
if retrieval fails, use the version's linked Launchpad source page or an Ubuntu
snapshot and require the same hashes. Never substitute another version.

On a Linux build host with `dpkg-dev`, fetch the three recorded artifacts into
one empty directory, verify every hash, and run `dpkg-source -x` on the `.dsc`.
Keep its normally applied quilt patches. Initialise Git in the extracted tree
and stage source with `git add -- . ':(exclude).pc'`, preserving the source's
ignore rules (including vendored gvdb/build products); `.pc/` is generated
quilt bookkeeping, not part of the recorded imported tree. Check `git write-tree`
against the component's `base_tree` before creating a baseline commit or
applying any exported patch. Stop on a mismatch and report the differing
paths. After applying the ordered series, require `candidate_tree` equality.

The previous retrieval used authenticated Ubuntu APT archive metadata. The
maintainer's inline `.dsc` signature is not independently attested here; the
library extraction explicitly reported a missing acceptable maintainer key.
Pinned hashes establish equality with the imported bytes, not a fresh
signature-verification claim. Do not suppress or relabel authentication errors.

The Linux `upstream` URL follows Ubuntu's official per-series Git layout.
Fetch the recorded tag and require its peeled commit to equal `base_commit`.
There is no full kernel `candidate_tree` claim: the saved candidate identity
belongs to a source-subset repository. Reapply and compile against full source
before a new kernel change, rather than treating the partial import receipt
as a complete reconstruction test.

For example, from this repository, with network access and Git available:

```bash
set -e                           # A failed clone, checkout or patch stops here.
repo_root="$PWD"                  # Preserve the patch repository location.
mkdir -p work                    # Ignored, disposable source checkouts.
git clone https://gitlab.freedesktop.org/emersion/libdisplay-info.git work/libdisplay-info
git -C work/libdisplay-info switch --detach 62a9346c3dce2bddba1d4dc186949e4320d6f801
while IFS= read -r patch; do
    git -C work/libdisplay-info am "$repo_root/patches/libdisplay-info/$patch"
done < patches/libdisplay-info/series
git -C work/libdisplay-info status  # Stop and resolve an interrupted am.
```

For the exact imported content, verify the resulting tree against
`candidate_tree` in `sources.json`. A fresh `git am` may produce different
commit IDs because committer metadata changes; the source tree must match.

## 3. Establish the compiler loop before editing

Use a Linux environment for the affected component; a macOS repository check
is not a Linux build. Preserve pinned source and actual compiler flags. For
each change establish the normal warnings-enabled compiler loop. Batch related
commits into one PR. When the candidate is ready to merge, request an independent
adversarial agent review and fix its findings, then run the affected fast lane.
Run each required check successfully once on the merged candidate's code;
rerun failed checks and checks invalidated by later edits only. A failure is
not a reason to repeat unrelated passing suites. Full unit-suite follow-up is
a separate batch process; record unresolved failures explicitly.
Changes to the library additionally need ABI/legacy-consumer checks and both
amd64/i386 packaging evidence if those packages are delivered. Mutter changes
need focused display/parser/KMS cases and compositor tests. Kernel changes
need affected DRM/i915/shared-xe checks and parser KUnit coverage.

A typical upstream library loop, after checking its pinned build options and
providing `hwdata` (`pnp.ids`), Meson, Ninja, pkg-config and a C compiler:

```bash
meson setup work/libdisplay-info-build work/libdisplay-info -Dwerror=true
meson compile -C work/libdisplay-info-build
meson test -C work/libdisplay-info-build --print-errorlogs  # Pre-merge fast lane.
```

The kernel parser suite is selected by `drm_displayid_luminance`:

```bash
python3 tools/testing/kunit/kunit.py run \
  --arch x86_64 --jobs 2 --build_dir "$HDR_WORK/rog-hdr-kunit" \
  --kunitconfig drivers/gpu/drm/tests --timeout 120 \
  drm_displayid_luminance  # Run inside the reconstructed kernel source.
```

Do not reuse stale affected objects after source archive replacement. Earlier
warm KUnit objects and ineffective Meson CFLAGS reconfiguration produced
invalid evidence; record actual compile commands and invalidate stale builds.

Full packaging requires the matching Ubuntu build dependencies and the
source's own packaging rules. The previous exact command logs remain in the
historical workspace identified in [provenance](PROVENANCE.md). Transcribe and
requalify those into maintained build automation as components change; this
initial repository does not claim a newly tested all-component build script.

## 4. Record and ship only the result actually tested

Use a separate agent clone, not the owner's working checkout. Keep related
implementation commits on a `codex/` branch and merge the reviewed PR only
after its required fast lane passes. Use a neutral agent Git identity, such as
`Codex <codex@invalid>` or `Claude Agent <claude-agent@invalid>`, and keep the
authorship of recovered or imported work; preserve upstream patch authorship. The repository is public:
inspect staged changes and Git metadata before pushing and never paste tokens,
raw host captures, OEM files or signing material into commits or CI output.

The Python-only fast lane for the diagnostic and repository tooling is:

```bash
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -v
```

For a failed test, use its reported module/class/method directly, for example
`PYTHONPATH=tests python3 -m unittest -v test_module.TestClass.test_method`.
Do not rerun the whole discovery suite to retry that case. The manual GitHub
workflow accepts the same test target and a separate repository-check choice;
it deliberately does not run on every push. For the initial workflow addition,
record these local checks because GitHub dispatch needs the workflow on the
default branch first. Display experiments have their own receipts and never
run automatically on the owner's laptop from public CI.

Update patches, source pins, SHA256SUMS, the relevant documentation and
[status](STATUS.md) together. Retain authorship in format-patch exports. Record
source tree, tools, commands, result and limitations in a small evidence
receipt. Keep full logs/packages in ignored storage with hashes.

Before a live test, prepare compatible recovery packages, signing and NVIDIA
module checks, and local recovery access using [operations](OPERATIONS.md).
Do not infer future stock-library compatibility from a larger version number:
the current stack consumes unpublished API additions.

## 5. Audio builds have a separate repository

Use [rog_audio development](https://github.com/pjunod/rog_audio/blob/main/docs/DEVELOPMENT.md)
for the audio build environments, review and validation workflow. Do not add
audio tools or their dependency manifests to the display patch series.

## Build, test and packaging harness tools

`tools/reconstruct.py COMPONENT WORKDIR` binds the public pinned base, ordered
series and exact final tree. Use only a fresh owned directory; do not reconstruct
over work. For offline native replay use public cached base objects in a new
task-owned repository and require the same tree equality. Do not substitute a
newer Ubuntu import or imply signature authentication beyond recorded evidence.

`tools/build-upstream.sh LIB_SOURCE MUTTER_SOURCE BUILD_ROOT ORIG_ARCHIVE`
stages the library into its own prefix and compiles with warnings as errors.
`tools/package-ubuntu-offline.py` constructs an unprivileged, source-tree-bound
Ubuntu package set using the exact supplied library packages, with no APT or
host installation and no units. [Ubuntu delivery](NATIVEHDR10_UBUNTU_DELIVERY.md)
records actual historical construction versions, API dependency, GTK floor and
both library architectures; never relabel all packages as rebuilt on Ubuntu105.

`tools/export_series.py` preserves upstream authorship when exporting ordered
mail patches; regenerate SHA256SUMS deliberately only when patch bytes change.
`scripts/nativehdr10_validation.py` retains per-invocation logs and validity.
`tools/dolby_harness/build.py` binds the headless consumer, exact headers and
CPU Vulkan closure; [the harness contract](DOLBY_HARNESS.md) scopes its evidence.
`tools/native_player/build.py` packages the [experimental launcher](../tools/native_player/README.md)
without rebuilding stock mpv/FFmpeg/libplacebo, installing or playing media.
None of these commands should be inferred as permission for a device action.
