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
| libdisplay-info | Upstream `62a9346c3dce2bddba1d4dc186949e4320d6f801` | Four additive native parser/API proposals |
| mutter | Upstream `d82671c3035bfdb10fdc1ffd2c0e31859bb00ff7` | Native DisplayID eDP capability recognition |
| ubuntu-libdisplay-info | Authenticated Ubuntu `0.3.0-1` source import | Complete downstream changes through hdr6 |
| ubuntu-mutter | Authenticated Ubuntu `51.0-1ubuntu3` source import | Complete downstream changes through nativehdr2 |
| linux | Ubuntu tag `Ubuntu-7.3.0-8.8`, peeled `d03cf7a92919b0e6ab4e4a756dec41542eb2040f` | Native luminance, Intel selection and KUnit tests |

The upstream and Ubuntu series are alternatives, not patches to stack atop
one another. Ubuntu import/candidate commit IDs are local preparation IDs;
they are not fetchable upstream revisions. Obtain the authenticated Ubuntu
source package version first, then apply the exported series. Do not replace
it with today's latest package and inherit the old results.

For example, from this repository, with network access and Git available:

```bash
repo_root="$PWD"                  # Preserve the patch repository location.
mkdir -p work                    # Ignored, disposable source checkouts.
git clone https://gitlab.freedesktop.org/emersion/libdisplay-info.git work/libdisplay-info
git -C work/libdisplay-info switch --detach 62a9346c3dce2bddba1d4dc186949e4320d6f801
while IFS= read -r patch; do
    git -C work/libdisplay-info am "$repo_root/patches/libdisplay-info/$patch" || break
done < patches/libdisplay-info/series
git -C work/libdisplay-info status  # Stop and resolve an interrupted am.
```

For the exact imported content, verify the resulting tree against
`candidate_tree` in `sources.json`. A fresh `git am` may produce different
commit IDs because committer metadata changes; the source tree must match.

## 3. Establish the compiler loop before editing

Use a Linux environment for the affected component; a macOS repository check
is not a Linux build. Preserve pinned source and actual compiler flags. For
each change run the normal warnings-enabled build and its focused regressions.
Changes to the library additionally need ABI/legacy-consumer checks and both
amd64/i386 packaging evidence if those packages are delivered. Mutter changes
need focused display/parser/KMS cases and compositor tests. Kernel changes
need affected DRM/i915/shared-xe checks and parser KUnit coverage.

A typical upstream library loop, after checking its pinned build options:

```bash
meson setup work/libdisplay-info-build work/libdisplay-info -Dwerror=true
meson compile -C work/libdisplay-info-build
meson test -C work/libdisplay-info-build --print-errorlogs
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

Update patches, source pins, SHA256SUMS, the relevant documentation and
[status](STATUS.md) together. Retain authorship in format-patch exports. Record
source tree, tools, commands, result and limitations in a small evidence
receipt. Keep full logs/packages in ignored storage with hashes.

Before a live test, prepare compatible recovery packages, signing and NVIDIA
module checks, and local recovery access using [operations](OPERATIONS.md).
Do not infer future stock-library compatibility from a larger version number:
the current stack consumes unpublished API additions.
