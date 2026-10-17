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
- Done: independent adversarial packaging review (REVIEW316, `t_c3e311e9`)
  returned CHANGES NEEDED with four corrections, all implemented on this branch:
  typed source manifests bound to the final `.dsc` (R1), real artifact
  closure/ABI/debug/source inspections plus two negative regressions (R2),
  current launcher instructions and the reserved `1.0~experimental4` (R3), and
  the hash-bound provenance/errata companion below (R4). No unit, build or
  install ran for those corrections.
- Current: focused independent closure of the corrections against this exact
  diff; then the launcher `1.0~experimental4` source/binary construction from
  the closed commit, the supplemental `--audit-existing` receipts for the
  existing Mutter and library source packages, and the provenance companion.
- Remaining: ONE affected batch (the eleven existing scoped package methods,
  the two new negative regressions and the one changed launcher method), actual
  isolated forward/rollback installation, canonical kit and serialized PR
  landing. Mutter `nativehdr10.1` and the hdr9 binaries are not rebuilt.

This is not yet a released or newly installed kit. Existing installed binaries,
source merge, compiler success, solver simulation, isolated installation and
live installation are distinct states. No ROG/session/audio/display action is
authorized here. No Apple TV access of any kind.

## Runtime inventory

| Merged runtime | Source and intended Ubuntu delivery | Payload / evidence boundary |
|---|---|---|
| Mutter nativehdr10 Night Light, target overrides, async lifetime, offscreen reuse and GTK frames API correction | Ubuntu Mutter51.0-1ubuntu3, canonical105 tree `08740f943fb2ddda60411fa4d72bb4ccc4238e5f`; constructed `51.0-1ubuntu3+nativehdr10.1` | Nine normal distribution runtime/GIR/dev/test/common packages and matching debug symbols; prior104/105 construction identities remain historical |
| libdisplay-info native luminance/chromaticity API | hdr9 canonical tree `96d65c11ed0f408792c41cd42c2866255b1089d0` | SONAME3 runtime/dev/decoder, amd64 and i386; unchanged source tests retained at original identities; inspect actual Multi-Arch applicability before reuse |
| Experimental player launcher | `hermes-hdr-experimental-player` `1.0~experimental4`, `tools/native_player/debian` (committed; construction follows closure). `1.0~experimental3`, the first normal source construction, is superseded and immutable | `/usr/bin/hermes-hdr-player`, desktop entry, uncompressed `USAGE.txt`, `inputs.json`, copyright and changelog; unchanged qualified player algorithm and stock runtime dependencies |
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
Construction is normal source packaging from pinned committed inputs; no
bit-for-bit reproducibility is claimed for any package in this release.

Mutter/library source closure uses `tools/merged-ubuntu-release.py`, the exact
committed canonical source tree, original hash-pinned Ubuntu archive and actual
preserved distribution quilt bookkeeping. It copies into a new owned directory,
records the aggregate merged runtime changes as a normal quilt patch, constructs
the `.dsc`, extracts that `.dsc` again, and requires the typed runtime manifest
to match: regular files by SHA256 and execute bit, symlinks by literal target
(never followed), other entry types rejected, directories implied by members.
`.pc` and `debian/` stay excluded from that runtime manifest; `debian/` is
inventoried separately and may differ from the canonical git archive only by
the explained allowlist (Mutter: the unique changelog entry, `shlibs.local`,
the appended `series` line and the aggregate patch; library: the latter two).
A binary build regenerates the `.dsc` and debian archive, so the FINAL
delivered source package is extracted and compared again and both hash bindings
are recorded. The extracted source package is the actual Mutter binary input.
All distro recipes, installed paths, SONAMEs, API Provides and strict
runtime/dev/GIR/test dependencies remain. The original source patch series and
SHA256SUMS need no rewriting.

The already constructed `nativehdr10.1` and hdr9 source packages predate the
typed manifest. They are not rebuilt for that metadata: the recipe's
`--audit-existing` path extracts an existing `.dsc` (or inspects an extracted
tree) next to the canonical archive, records the typed comparison, packaging
deltas and actual applied quilt state in `source-audit.json`, and exits 2 on
any recorded difference so it is assessed before any artifact is replaced.
Those audit receipts are mandatory fixtures of the package regressions.

The coordinator approved one coherent nine-binary source release, not a bespoke
component-only dh target: canonical105 fixes frames/API requirements while the
historical kit contained eight104 artifacts and a same-version105 common-bin.
`nativehdr10.1` supersedes that ambiguity with a monotonic unique identity and
normal full distribution package closure. hdr9 source/runtime inputs are unchanged;
its actual amd64/i386 binaries retain their original hashes and identities, not
a fictitious new i386 build. No successful source unit suite is invalidated by
the packaging/changelog/quilt representation alone.

## Source provenance and errata

`tools/merged-ubuntu-provenance.py` writes `SOURCE-PROVENANCE.json` and
`SOURCE-PROVENANCE.txt` into the canonical kit from the kit's actual bytes. It
verifies the pinned identities below by size and SHA256, hashes the aggregate
`debian/patches/merged-hdr-runtime.patch` inside each delivered debian archive,
checks that its header names no reviewer, and binds the public patch series
that built each canonical tree. It regenerates, relabels or replaces nothing.

| Source package | Canonical commit / tree | Delivered `.dsc` SHA256 (size) | Delivered debian archive SHA256 (size) |
|---|---|---|---|
| `mutter_51.0-1ubuntu3+nativehdr10.1.dsc` (binary build input) | `63a74de8177c7ace14995cc4ca300cf85f94da8d` / `08740f943fb2ddda60411fa4d72bb4ccc4238e5f` | `3624030bf9560e43ea6367b519a132586adfea1338ed535d6aeb5b95324e64ce` (4121) | `927b324d1a16db86583ade0d5f7876f15c65e23d6d739918ca6e7e774548e33b` (251288) |
| `libdisplay-info_0.3.0-1ubuntu1~hdr9.dsc` (source-only reconstruction) | `79ffc865a9d1b1eb9c965ae32f481afa516ddba5` / `96d65c11ed0f408792c41cd42c2866255b1089d0` | `e68b1c25a33cd2e8f096b6a249c0d609c1d3e1b6606221b3817207dca970657f` (1425) | `e012d3a834d356d03454089d8d7544d0e011a35775308b9e7bba6f75730de9a8` (38764) |

Both were constructed by recipe commit `32f05a40` from the pinned Ubuntu
originals (`mutter_51.0.orig.tar.xz`
`5d28f3ae225692428fcafb96500d673f34328b698b86960c9c1460d0b1d983b3`,
`libdisplay-info_0.3.0.orig.tar.bz2`
`915cc6713b7b2e173a90f9db248fb8994f9668171fecc1e9fded5e36bb34d890`). The
aggregate patch hashes are bound in the kit companion from the archive bytes.

Errata, stated rather than corrected by regeneration:

- The aggregate patch is a mechanical source representation of the committed
  canonical tree generated by `dpkg-source --commit`. Its header is the dpkg
  template (placeholder Subject, TODO paragraph, Origin/Bug/Forwarded/
  Reviewed-By placeholders, generation-time Date). It is not a finished DEP3
  description, and the Reviewed-By template is **not** an approval by anyone.
  Original per-change authorship, attribution and licences are preserved in
  the public `patches/ubuntu-mutter` and `patches/ubuntu-libdisplay-info`
  series that built those trees, not re-stated inside the aggregate.
- The hdr9 `.dsc` is reconstructed source-only from the qualified canonical
  tree. It is not the `.dsc` used for the historical amd64/i386 binary
  construction; the six retained binaries keep their original identities and
  were not rebuilt.
- Source generation is normal source packaging with pinned inputs. No
  bit-for-bit reproducibility experiment was performed and none is claimed.
- The independent packaging review of this kit is REVIEW316 plus its focused
  closure; no other review, signoff, certification or upstream acceptance
  exists. This is a bounded private-kit disposition, not distro-upload metadata.
- The recipe now writes a factual deterministic DEP3 header (origin commit,
  canonical tree, canonical commit date, no review or signoff) for future
  source releases. That correction is not applied to this kit: the existing
  `.dsc`/debian archives and the unchanged Mutter and library binaries keep
  their exact identities with this erratum. A future corrected source would
  take a distinct source revision and would not be the build source of the
  retained binaries; same-name artifacts are never overwritten.

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

The affected batch is exactly fourteen selected methods in one native Python
process: the eleven `test_merged_ubuntu_packages` methods already named in the
review, the two negative regressions
`ReleaseRecipeTests.test_source_manifest_detects_mode_and_symlink_drift` and
`ReleaseRecipeTests.test_source_closure_rejects_missing_or_wrong_hash`, and
`test_native_player.PlayerTests.test_desktop_control_and_no_global_configuration_payload`.
`HDR_MERGED_ARTIFACT_ROOT` must hold the hash-verified kit view: `mutter/`
(binaries, debug symbols, source, both `.changes`/`.buildinfo` pairs,
`source-receipt.json`, `construction.log`, `source-audit.json`), `launcher/`
(the experimental4 set with `committed-source.tar`, `build.log`,
`build-receipt.json`, `SHA256SUMS`), `library/` (six retained binaries,
`RETAINED.json`, the historical amd64/i386 `.changes`/`.buildinfo`) and
`library-source/` (the reconstructed hdr9 source set with its receipts and
`source-audit.json`). Historical library references to debug or source files
not in the kit are a labelled partial closure, never a silent pass.
