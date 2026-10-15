# Merged Ubuntu package release

Task `t_b2f97e54` builds the already merged HDR work independently of unfinished
Dolby mapping. The selected source is main `2735b97f7ae6f8b091fcb834df21a8e34b95f3eb`
(tree `7d4f4c269b5291856c64f363ce3ad7b9c9e203e8`). PR16 history remains excluded.

## Done / current / remaining

- Done: current main fetched and isolated packaging ownership established;
  historical Ubuntu104/105, hdr9 multiarch and launcher receipts inventoried.
- Current: convert the launcher to ordinary native source packaging; inspect
  actual multiarch controls and prepare versioned compositor packaging.
  Native namespace creation is denied; acquire task-private public PRoot for
  actual isolated APT/dpkg installation, never call a status MODEL an install.
- Remaining: native source/binary artifacts and complete provenance, independent
  adversarial review/fixes, one minimal affected package batch, actual isolated
  forward/rollback installation, canonical kit and serialized PR landing.

This is not yet a released or newly installed kit. Existing installed binaries,
source merge, compiler success, solver simulation, isolated installation and
live installation are distinct states. No ROG/session/audio/display action is
authorized here. No Apple TV access of any kind.

## Runtime inventory

| Merged runtime | Source and intended Ubuntu delivery | Payload / evidence boundary |
|---|---|---|
| Mutter nativehdr10 Night Light, target overrides, async lifetime, offscreen reuse and GTK frames API correction | Ubuntu Mutter51.0-1ubuntu3, canonical105 tree `08740f943fb2ddda60411fa4d72bb4ccc4238e5f`; unique release packaging under preparation | Normal distribution runtime/GIR/dev/test/common packages; prior104/105 construction identities must not be rewritten |
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
