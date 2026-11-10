# WebKitGTK packages — replay the reviewed GTK4 source on Ubuntu

**Status:** source recipe; package replay and runtime qualification pending ·
**Updated:** 2026-11-09

This recipe prepares Ubuntu `webkit2gtk 2.52.6-1ubuntu1` plus the reviewed
clear-video/native HDR browser patch as `2.52.6-1ubuntu1+rogdv1`. It keeps
Ubuntu's debhelper generation, symbols, GIR dependency generation and
`dh_shlibdeps`. It selects GTK4 only, with standard `/usr` multiarch paths.
The product patch and [source pin](source-pin.json) identify the separate
browser implementation; this directory contains no decoder, rendering
provider, proprietary SDK, media, binary package or captured reference data.

The [packaging overlay](ubuntu-packaging.diff) is applied only to `debian/`.
The [preparation helper](prepare-source.py) records the product delta in the
ordinary quilt series, including when the exact reviewed source is already
present in an owned warm compiler slot. The retained
[Ubuntu packaging input snapshots](ubuntu-inputs/rules) are public test
fixtures pinned by SHA256; preparation verifies the entire original
`debian/` tree against the distribution import. The [cache verifier](verify-build.py)
checks source contents and modes against Git tree IDs without requiring Git
metadata. Read [the explicit CMake profile](cmake-profile.json) and the complete
[Boolean feature receipt](cmake-features.json) before use.
This is an amd64 clang `Release` derivative with empty C/C++ base flags,
`-O2 -DNDEBUG -g0` release flags and empty linker flags. It does not claim
Ubuntu's default compiler or hardening flags.

## Prepare authenticated distribution source

Use an owned task directory on the configured external storage volume and
Ubuntu's authenticated source metadata. The
[official source descriptor](https://security.ubuntu.com/ubuntu/pool/main/w/webkit2gtk/webkit2gtk_2.52.6-1ubuntu1.dsc)
names the exact archives and hashes recorded in [the pin](source-pin.json).
Verify the descriptor through your authenticated Ubuntu source setup; the
recipe's hash check does not replace archive signature verification. Set the absolute paths below before
running these commands; no helper downloads source or allocates a second
compiler slot.

```bash
# Download the exact published Ubuntu source into your owned source directory.
cd "$source_parent"
apt-get source --download-only webkit2gtk=2.52.6-1ubuntu1
# Unpack with Ubuntu's existing quilt patches applied.
dpkg-source -x webkit2gtk_2.52.6-1ubuntu1.dsc "$task_source"
# Add the exact reviewed public product patch and the packaging overlay.
python3 "$recipe/prepare-source.py" --source "$task_source" \
  --product-patch "$product_patch"
# Produce a normal 3.0 (quilt) source package next to the source tree.
cd "$task_source"
dpkg-buildpackage -S -us -uc -d
```

Preparation refuses a different product patch digest, source tree, executable
mode or Ubuntu `debian/` input. Its full top-level inventory permits only the
six distribution roots plus unexported `.git` and `.pc` metadata. Unknown
files, including private notes at the source root, fail before quilt records
a delta. The recorded patch must touch exactly the 39 pinned regular product
paths, with no binary patch, traversal, deletion or rename. Quilt metadata
cannot contain symlinks or special files. Generated Python caches are excluded
from source diffs explicitly; they never enter the public source package. It prints success only after generated control
contains exactly the six packages below. A failure can leave preparation
partially applied: preserve diagnostics and restart from a fresh extraction;
do not run it again over the same partially prepared source.

Keep the original `.orig.tar.xz` next to the prepared source. The resulting
`.dsc` and its named source archives can be extracted using `dpkg-source -x`
on a fresh Ubuntu builder. The product patch, packaging files, profile and
verifier travel in the Debian source archive. No Git checkout, symlink to an
external source directory, provider payload or private builder path is needed.
Source package generation does not establish binary or runtime acceptance.

## Build a clean extraction with the declared SDKs

The native path needs the public `libgstgtk-dovi-core-dev` package at
`0.1.0+rogdv5` or newer and public GTK development headers at
`4.24.1+ds-1+rogdv5` or newer. The generated control records those minimum
build dependencies. It also records the corresponding native mapping plugin
and GTK runtime minima; coordinated runtime qualification still uses the
exact package set retained privately by the release owner.

```bash
# Install declared build dependencies in the existing isolated Ubuntu builder.
cd "$task_source"
sudo apt-get build-dep .
# Default paths select the public SDK development packages under /usr/include.
# Retain the workflow's existing CPU, memory, disk and process guard.
DEB_BUILD_OPTIONS='parallel=2 nocheck nodoc' dpkg-buildpackage -b -us -uc
```

The default source-owned build directory is `build-gtk4`. A normal clean can
remove it. Bubblewrap and introspection are enabled; API tests,
documentation, WebDriver, gamepad, speech synthesis, AVIF and libbacktrace
are disabled. MiniBrowser is included in the runtime package using the
upstream install manifest. The source distribution does not ship WebKit's
full test harness, so its existing empty `dh_auto_test` override is retained;
`nocheck` is not browser acceptance.

## Reuse the current warm cache without a second full build

Only the owner of an idle, stopped compiler slot should prepare its source.
An active compiler continues to own its source and headers. Add
`--already-patched` to preparation when that source already matches the
reviewed product tree. Preparation records the quilt delta and checks every public source mtime
before and after `dpkg-source --commit`, refusing any change. It does not alter the compiler cache. Keep the exact
Ubuntu original tarball next to that source. A source-only Git archive may
lack quilt's `.pc` directory: in that case also pass
`--quilt-state-from "$ubuntu_clean_source"`, naming a separate authenticated
`dpkg-source -x` extraction of the same Ubuntu version. The helper verifies
that clean baseline and copies only its absent `.pc` metadata, preserving all
active product files. It refuses partial or unexpected quilt state.

```bash
# Run after the active guarded build stops; keep the same source pathname.
python3 "$recipe/prepare-source.py" --source "$task_source" \
  --product-patch "$product_patch" --already-patched
cd "$task_source"
# Explicitly name the existing absolute cache and the public SDK search roots
# that actually produced it. These are build inputs, not installation paths.
export ROG_WEBKIT_BUILD_DIR="$task_build"
export ROG_WEBKIT_DOVI_SDK_ROOT="$task_dovi_sdk_include"
export ROG_WEBKIT_GDK_SDK_ROOT="$task_gtk_sdk_include"
export ROG_WEBKIT_REUSE_RECEIPT="$completed_producer_receipt"
python3 debian/rog-native-hdr/verify-build.py
# Under the same workflow resource guard, retain objects and finish packages.
DEB_BUILD_OPTIONS='parallel=2 nocheck nodoc' dpkg-buildpackage -b -nc -us -uc
```

The gate refuses a changed source, build source pathname, generator, compiler,
flags, feature, output directory or SDK search root. The complete
`ENABLE_*`/`USE_*` Boolean map must match, including key presence; a new or
missing option also fails. The feature receipt has its own canonical SHA256. `GI_GIRDIR` and
`GI_TYPELIBDIR` are SDK search inputs and are deliberately not interpreted as
installation paths. It does not rewrite them. Source/header compile checks
must separately establish that the actual compiler selected the declared
native SDK APIs; matching cache keys alone cannot prove that acceptance.

An external override must be absolute and cannot point at the source, an
ancestor of it or a symlink. Cleanup refuses any external cache override. Use `-nc`, which skips
pre-clean while retaining debhelper's normal build sequence. If the manual
cache has no debhelper configure stamp, the external configure override
verifies the existing source/profile and the retained producer input, then
generates manifests; it does not run CMake. The default configure and clean paths also reject a `build-gtk4`
symlink before calling build tools. Never replace `build-gtk4` with a symlink.
The build and install targets recheck source/profile identity and regenerate
the upstream GTK4 debhelper manifests even when configure was skipped.
Debhelper may build missing GIR/typelib or runtime targets in the existing
graph; it does not start a GTK3 compile. The recipe never wipes the cache.

## Bind external reuse to its completed local producer

`ROG_WEBKIT_REUSE_RECEIPT` names a retained private JSON file outside both
source and build directories. The operator creates it only after the guarded
build completes and the compiler slot is quiescent. This is an explicitly
trusted local operator input, not authenticated CI evidence. The verifier
independently recomputes all referenced current file identities, source tree
IDs, source/build path bindings and the full CMake profile. An arbitrary empty
Ninja file or copied cache cannot stand in for the completed producer.

The receipt uses the following exact fields. Hashes are lowercase SHA256 of
raw file bytes unless a canonical JSON or command stream is specified.

| Field | Required value |
|---|---|
| `schema` | `rog-webkit-local-producer-v1` |
| `trust` | `local-operator` |
| `source_directory`, `build_directory` | Actual resolved absolute paths, matching CMake's source and cache-directory keys |
| `candidate_commit` | Reviewed candidate commit from `source-pin.json` |
| `feature_map_sha256` | Canonical hash retained in `cmake-features.json` |
| `cmake_profile_sha256` | SHA256 of UTF-8 `json.dumps(profile, sort_keys=True, separators=(',', ':'))` for `cmake-profile.json` |
| `completed_guard` | JSON `true`, established after actual guarded completion |
| `files` | Exactly `cache`, `graph`, `rules`, each a `{path, sha256}` record for this build's `CMakeCache.txt`, `build.ninja`, `CMakeFiles/rules.ninja` |
| `ninja_commands_sha256` | SHA256 of raw stdout from `/usr/bin/ninja -C <resolved-build> -t commands` |
| `inputs` | Exactly `guard`, `source_archive`, `sdk_controls`, each a retained absolute regular-file `{path, sha256}` record |
| `sdk_compile_checks` | Exactly `gdk_native_hdr`, `mapper_destination_abi`, `mapper_source_lease_abi`, each JSON `true` after actual compile/preprocessor controls |
| `sdk_headers` | Exactly `mapper`, `gdkwayland`, each a current selected public-header `{path, sha256}` record |

The mapper header is `gst-gtk-dovi-1.0/mapper.h` below the declared mapper SDK
root; the GDK header is `gdk/wayland/gdkwaylandsurface.h` below the declared
GTK SDK root. Retain the actual control receipt used to prove those APIs.
SDK roots are build search inputs and never redefine installation paths.

The gate requires nonempty CMake-generated graph and rules files. It rejects
changed graph, rules, commands, cache, source pathname, feature map, SDK
header or evidence input. If CMake legitimately regenerates a different
identity, stop and establish a new producer receipt from its completed guarded
build before package acceptance. Do not manufacture a receipt merely to
silence a refusal. Private receipts and source archives stay outside Git.

## Package and qualification boundary

| Package | Installed content |
|---|---|
| `libwebkitgtk-6.0-4` | WebKit runtime, injected bundle, processes, MiniBrowser and translations |
| `libjavascriptcoregtk-6.0-1` | JavaScriptCore runtime |
| `libwebkitgtk-6.0-dev` | GTK4 API headers, linker/pkg-config files and WebKit GIR source |
| `libjavascriptcoregtk-6.0-dev` | JavaScriptCore headers, linker/pkg-config files and GIR source |
| `gir1.2-webkit-6.0` | WebKit and web process extension typelibs |
| `gir1.2-javascriptcoregtk-6.0` | JavaScriptCore typelib |

Shared libraries belong in `/usr/lib/x86_64-linux-gnu`; processes,
MiniBrowser and injected bundle belong in
`/usr/lib/x86_64-linux-gnu/webkitgtk-6.0`; translations belong in
`/usr/share/locale`. `DESTDIR` is staging only: it cannot repair a compiled
`/usr/local` helper path. There is no GTK3 runtime, GTK3 JavaScript interpreter,
GTK3-dependent WebDriver, documentation or transitional package in this
source profile. Existing GTK3 packages on the destination are separate.
Debhelper may additionally generate ordinary debug symbol packages.

Before installation, qualify the `.dsc` replay, final package payload and
control dependencies, `dh_shlibdeps`/symbols, GIR import and normal inner
sandbox helper lookup on the exact candidate. Retain the original package
archives and rehearse the actual upgrade and rollback with zero unexpected
removals. Normal sandbox video, HDR/SDR, target changes, protection/source
fallback and CSS/page controls remain the browser implementation's acceptance
work. This recipe does not install packages, merge, publish or grant physical
panel/optical acceptance.

The focused regression is
`python3 -m unittest discover -s tests -p 'test_webkit_ubuntu_packaging.py'`;
it exercises source/mode corruption,
profile/path mismatches and the overlay's GTK4/debhelper contract without
compiling WebKit or contacting a builder.
