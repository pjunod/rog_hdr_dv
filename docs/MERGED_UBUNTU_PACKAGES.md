# Merged Ubuntu package release

Task `t_b2f97e54` builds the already merged HDR work independently of unfinished
Dolby mapping. The selected source is main `2735b97f7ae6f8b091fcb834df21a8e34b95f3eb`
(tree `7d4f4c269b5291856c64f363ce3ad7b9c9e203e8`). PR16 history remains excluded.

## Done / current / remaining

- Done: current main fetched and isolated packaging ownership established;
  historical Ubuntu104/105, hdr9 multiarch and launcher receipts inventoried.
- Done: ordinary launcher `1.0~experimental3` source/binary construction from
  committed `6d6ab5e`, and coherent Mutter `51.0-1ubuntu3+nativehdr10.1`
  source/binary construction using committed recipe `32f05a4`. The full Mutter
  command passed once in 533.52 seconds. Both use nocheck; no upstream units ran.
  Normal `.dsc`, source archives, `.changes`, `.buildinfo`, actual binaries and
  matched Mutter debug symbols exist privately, not a recipe-only milestone.
- Current: unchanged hdr9 multiarch applicability/source closure, private kit,
  and actual isolated-install environment. Native namespace creation is denied;
  task-private public PRoot plus libtalloc starts with `PROOT_NO_SECCOMP=1`.
  This proves compatibility only, not installation. Never call a status MODEL
  or copied baseline an install.
- Remaining: complete provenance and isolated environment, independent
  adversarial review/fixes, one minimal affected package batch, actual isolated
  forward/rollback installation, canonical kit and serialized PR landing.

This is not yet a released or newly installed kit. Existing installed binaries,
source merge, compiler success, solver simulation, isolated installation and
live installation are distinct states. No ROG/session/audio/display action is
authorized here. No Apple TV access of any kind.

## Runtime inventory

| Merged runtime | Source and intended Ubuntu delivery | Payload / evidence boundary |
|---|---|---|
| Mutter nativehdr10 Night Light, target overrides, async lifetime, offscreen reuse and GTK frames API correction | Ubuntu Mutter51.0-1ubuntu3, canonical105 tree `08740f943fb2ddda60411fa4d72bb4ccc4238e5f`; constructed `51.0-1ubuntu3+nativehdr10.1` | Nine normal distribution runtime/GIR/dev/test/common packages and matching debug symbols; prior104/105 construction identities remain historical |
| libdisplay-info native luminance/chromaticity API | hdr9 canonical tree `96d65c11ed0f408792c41cd42c2866255b1089d0` | SONAME3 runtime/dev/decoder, amd64 and i386; unchanged source tests retained at original identities; inspect actual Multi-Arch applicability before reuse |
| Experimental player launcher | `hermes-hdr-experimental-player` `1.0~experimental3`, `tools/native_player/debian` | `/usr/bin/hermes-hdr-player`, desktop entry and documentation; unchanged qualified player algorithm and stock runtime dependencies |
| Stock mpv/FFmpeg/libplacebo/Python | Ubuntu packages declared by launcher Depends | No fork/new runtime algorithm in this release; retain original source inventory in `tools/native_player/inputs.json` |

The public headless harness and review/build tools are development utilities,
not additional system runtime packages. Kernel/Wine series are separate existing
research topics, not newly installed components of the merged nativehdr10 kit.
Unmerged Dolby/Sparks/WSI/preferred-target/tiling work is excluded. Full Dolby
operator coverage, agreement with official output, Windows comparison and optical
acceptance remain incomplete; experimental reshaping is not certification.

## Source package construction

Launcher packaging uses debhelper14, `3.0 (native)`, a versioned changelog and
normal `dpkg-buildpackage -F -us -uc`. It has no maintainer scripts or services.
The `build.py` driver accepts a hash-bound `git archive COMMIT:tools/native_player`
prepared before transfer and records the full repository commit. It never copies
Git storage or credentials into the native builder. Use a fresh owned output:

    python3 build.py --source-archive launcher.tar --sha256 SHA256 --commit COMMIT --output /work/OWNED/launcher

The default build deliberately does not run unit suites: complete independent
review and execute only affected package/launcher checks once afterward. Normal
source archives, `.dsc`, `.changes`, `.buildinfo` and `.deb` are mandatory outputs.
The native archive format has one source `.tar.xz`, not an invented orig archive.
Historical experimental2 artifacts and their original 30-method evidence remain
immutable. Only the metadata-path method and new packaging behavior are invalidated.

Mutter/library source closure uses `tools/merged-ubuntu-release.py`, the exact
committed canonical source tree, original hash-pinned Ubuntu archive and actual
preserved distribution quilt bookkeeping. It copies into a new owned directory,
records the aggregate merged runtime changes as a normal quilt patch, constructs
the `.dsc`, extracts that `.dsc` again, and requires every non-packaging runtime
file hash to match. The extracted source package is the actual Mutter binary
input. The only intentional Mutter packaging deltas are the unique changelog
version and ordinary hdr9 `shlibs.local` metadata. All distro recipes, installed
paths, SONAMEs, API Provides and strict runtime/dev/GIR/test dependencies remain.
The original source patch series and SHA256SUMS need no rewriting.

The coordinator approved one coherent nine-binary source release, not a bespoke
component-only dh target: canonical105 fixes frames/API requirements while the
historical kit contained eight104 artifacts and a same-version105 common-bin.
`nativehdr10.1` supersedes that ambiguity with a monotonic unique identity and
normal full distribution package closure. hdr9 source/runtime inputs are unchanged;
its actual amd64/i386 binaries retain their original hashes and identities, not
a fictitious new i386 build. No successful source unit suite is invalidated by
the packaging/changelog/quilt representation alone.

## Isolated installation and validation boundary

`tools/isolated-ubuntu-apt.py` prepares an independently writable copy of the
compiler's `/usr` and actual dpkg database below a durable owned root. It copies
only explicitly allowed public/configuration files, not `/etc` wholesale or
credentials. It binds no host home, `/run`, display or service sockets. A private
`policy-rc.d` returns101. PRoot is a trusted-package compatibility tool, not a
security sandbox. Only normal trusted Ubuntu packages are used.

Preparation is a copied baseline, not an install. The reviewed validation must
record APT solver plans separately from the actual private-root unpack/configure
and rollback transactions, verify installed package/file hashes and `dpkg --audit`,
and compare real host package-state hashes before/after. No service or physical
display is exercised, and no successful old source suite is repeated. The scoped
new package tests are `tests/test_merged_ubuntu_packages.py`; actual artifact
fixtures are mandatory and missing fixtures fail rather than skip. The one
existing launcher metadata-path method is the only changed old method.
