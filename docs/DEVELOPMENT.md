# Development — reconstruct source and prove each change

Read [architecture](ARCHITECTURE.md) for ownership and [provenance](PROVENANCE.md)
for imported source identities. The repository stores patch series, not full
vendored Linux/Mutter trees or installable binaries.

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
| libdisplay-info | Upstream `62a9346c3dce2bddba1d4dc186949e4320d6f801` | Six native parser/API and regression patches |
| mutter | Upstream `d82671c3035bfdb10fdc1ffd2c0e31859bb00ff7` | Native DisplayID eDP capability recognition |
| ubuntu-libdisplay-info | Authenticated Ubuntu `0.3.0-1` source import | Delivered hdr6 prefix plus source-only hdr7 candidate |
| ubuntu-mutter | Authenticated Ubuntu `51.0-1ubuntu3` source import | Complete downstream changes through nativehdr2 |
| wine | Wine `wine-11.0`, peeled `db11d0fe6a169c457e23d007e20404643d067aa8` | Source-only desktop CreateFileFromAppW compatibility |
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
and stage source with `git add -f -- . ':(exclude).pc'`; `.pc/` is generated
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
  --arch x86_64 --jobs 2 --build_dir /tmp/rog-hdr-kunit \
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
after its required fast lane passes. Use local Git identity `Codex <codex@invalid>`
for agent work; preserve upstream patch authorship. The repository is public:
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
