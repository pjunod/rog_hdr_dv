# GNOME image colour — preserve tagged photographs through the desktop

**November 9, 2026.** The reviewed Loupe and Glycin packages are installed. The installed loader preserved 16 Display P3 colours against native macOS CoreGraphics, with maximum absolute linear-channel error 0.0004883 and mean 0.00012436. A private Mutter comparison of staged Loupe against the unclipped float reference matched within one ten-bit PQ code across 49,152 channel samples. The installed Loupe AppArmor profile rejected the private test socket, so this compositor result uses the staged executable. [Method and controls](../evidence/display-p3-macos-software-comparison.json).

The prior six Adobe RGB patches matched an independent BT.2020 reference within one ten-bit code per channel. Embedded profiles survived in small TIFFs. Physical panel accuracy remains unmeasured.

This document covers the image viewer, its Ubuntu source packages and recovery. [Software delivery](SOFTWARE_DELIVERY.md) · [GTK display targets](GDK_DISPLAY_TARGET.md).

## Why the photograph lost colour

Loupe 50 embeds glycin 3.1; the system `glycin-loaders` package supplies separate
sandboxed decoding processes. Correcting only the system library does not change
Loupe's embedded ICC conversion.

The original ICC conversion wrote back into the original integer texture in
sRGB. That discarded colours outside sRGB and quantized the result before GTK
could present it. The correction uses Little CMS to convert source ICC values
into linear BT.2020. Eight-bit sources use RGB(A) float16; higher-precision
sources use RGB(A) float32. Alpha is copied, and associated input colour is
unassociated before the colour transform. Rows retain their source stride while
reading; the replacement texture gets a tightly packed stride only after a
successful conversion. Allocation and layout failures propagate; an invalid
ICC profile retains the original pixels and ordinary sRGB fallback.

CICP metadata keeps its existing precedence over an embedded ICC profile.
Untagged images keep their existing interpretation. The correction relies on
ordinary GTK texture colour states and normal window presentation.

TIFF had a second failure. Its generic tag reader expanded byte metadata into
per-element `Value` objects and charged that representation against a metadata
budget. A valid profile could therefore disappear as the image size changed.
The corrected BYTE/UNDEFINED reader charges the actual byte count against the
caller's metadata limit. It reads incrementally and grows the destination only
after successful reads. Invalid lengths and offsets retain bounded failure and
the existing missing-profile fallback.

## Reconstruct and build the Ubuntu packages

The ordered series are
[`ubuntu-loupe-image-colour`](../patches/ubuntu-loupe-image-colour/series) and
[`ubuntu-glycin-image-colour`](../patches/ubuntu-glycin-image-colour/series).
[`sources.json`](../sources.json) pins the authenticated Ubuntu archive bytes,
base trees and complete candidate trees. Original source hashes came from signed
Ubuntu APT metadata; the original maintainer DSC signatures are not separately
attested. Locally generated candidate DSCs are unsigned.

Use Ubuntu's normal source dependencies and package rules in an owned native
build directory. Set `HDR_WORK` to an empty task directory on the configured
external storage and `PATCH_REPO` to this repository. Obtain the exact original
source artifacts named in `sources.json`, verify their SHA-256 values, and
extract them with `dpkg-source -x`. Preserve the distribution's applied quilt
patches. Import every extracted file except `.pc`, including ignored vendored
files, and require the recorded base tree before applying the exported series.
See [source reconstruction](DEVELOPMENT.md#2-choose-the-correct-source-path).

```bash
# Apply one component's series to its verified source import.
while IFS= read -r patch; do
  git am "$PATCH_REPO/patches/ubuntu-loupe-image-colour/$patch"
done < "$PATCH_REPO/patches/ubuntu-loupe-image-colour/series"

# Synchronize quilt bookkeeping with the already-applied Cargo-only change.
patch -R -p1 < debian/patches/preserve-icc-gamut-in-floating-point.patch
QUILT_PATCHES=debian/patches quilt push
git diff --exit-code

# Check the complete candidate tree and create the DSC before compilation.
git rev-parse HEAD^{tree}
dpkg-source -b .

# Extract that candidate DSC into a separate clean build directory.
dpkg-source -x ../loupe_50.0-0ubuntu2+rogcolor2.dsc "$HDR_WORK/loupe-build"
cd "$HDR_WORK/loupe-build"
DEB_BUILD_OPTIONS='nocheck parallel=1' CARGO_BUILD_JOBS=1 \
  nice -n 10 dpkg-buildpackage -b -us -uc
```

For glycin, use its series and Cargo-only quilt patch
`read-tiff-byte-tags-under-their-metadata-budget.patch`, then extract its candidate
DSC into its own build directory. The reverse/apply step updates only untracked
quilt bookkeeping; the final tracked candidate files must remain unchanged.
`nocheck` defers unit execution until the final
independent review; it does not remove normal application or decoder features.
The exported series keep the Cargo dependency overrides in Cargo-only quilt
patches. Changed vendored source and recalculated Cargo file checksums live
directly in the Debian source archive, so a clean DSC extraction applies them
exactly once. Source-package replay must reproduce the recorded changed files.
Do not build a DSC over an already staged `debian/loupe` binary tree.

Loupe's final binary was built from a fresh candidate DSC extraction. The
normal all-feature glycin build was also replayed from clean DSC source in the
same warm compiler slot. Its Rust source bytes were unchanged; the two packaging
changes were the vendored file checksum and Cargo-only quilt representation.
Content-identical files retained their previous mtimes to reuse the cache.
The resulting loader DEB, its extracted ELF and its control metadata were all
byte-identical to the already qualified package. Original source and package
outputs are retained privately; this is an incremental packaging replay, not a
claim that an empty compiler cache was used.

The intended installation pair is `loupe` `50.0-0ubuntu2+rogcolor2` and
`glycin-loaders` `2.2.1+ds-1ubuntu2+rogcolor1`, both amd64. The loader package is
`Multi-Arch: foreign`. Its libraries and development packages are normal build
outputs but are not part of this two-package upgrade; existing amd64/i386
`libglycin` packages remain at their installed versions.

## Reproduce digital qualification without a colourimeter

[`qualify.py`](../packaging/image-colour/qualify.py) generates its own ICC
profiles and image files. It needs Python, NumPy, Pillow and liblcms2. Its RGB
reference is independently calculated from public primaries, white point and
transfer functions. It uses no OEM profile or proprietary image.

Compile [`image-pixels.rs`](../packaging/image-colour/image-pixels.rs) against
Loupe's built dependency artifacts:

```bash
# Run inside the built Loupe source directory.
d=obj-x86_64-linux-gnu/src/release/deps
rustc --edition 2024 -C opt-level=2 -C lto=fat -C embed-bitcode=yes \
  -L dependency="$d" \
  --extern glycin="$(ls "$d"/libglycin-*.rlib)" \
  --extern glib="$(ls "$d"/libglib-*.rlib)" \
  --extern gio="$(ls "$d"/libgio-*.rlib)" \
  --extern gdk4="$(ls "$d"/libgdk4-*.rlib)" \
  "$PATCH_REPO/packaging/image-colour/image-pixels.rs" \
  -o "$HDR_WORK/image-pixels"

# Use a fresh output path. The loader continues to run in its normal sandbox.
python3 "$PATCH_REPO/packaging/image-colour/qualify.py" \
  --probe "$HDR_WORK/image-pixels" \
  --output "$HDR_WORK/colour-qualification" \
  --loader-data "$HDR_WORK/loader-data"
```

`loader-data/glycin-loaders/2+/conf.d/` contains a copy of the package's ordinary
`glycin-image-rs.conf`, with only its `Exec` path changed to the extracted
candidate loader. `GLYCIN_DATA_DIR` selects this standard deserialized
configuration. No sandbox bypass, loader injection API or host installation is
used. The probe downloads the actual returned GDK texture as linear BT.2020
RGBA float32 and reports its first row. The TIFF fixtures repeat that row; the
separate layout diagnostic below checks multirow stride handling.

The controls cover 256 distinct gray levels, wide/sRGB primaries, RGB/RGBA at
8 and 16 bits, adjacent 16-bit midtones, JPEG, CICP precedence and invalid-profile
fallback. TIFF controls use 21,012-byte synthetic metadata at 80, 320 and 1,024
pixels square with both BYTE and UNDEFINED field types. Invalid metadata-offset
and excessive-count controls must decode safely through the sRGB fallback.

[`icc-layout.rs`](../packaging/image-colour/icc-layout.rs) additionally includes
the actual candidate ICC implementation in a diagnostic executable. It compares
supported associated U8/U16/F32 input against equivalent straight-alpha input,
checks padded two-row input and verifies transactional invalid-profile failure.
Compile it against the same dependencies plus `glycin_common`, `glycin_utils`,
`gufo_common`, `lcms2`, `lcms2_sys` and `half`; set `LOUPE_SOURCE` to the absolute
candidate source directory when invoking rustc. These layout controls supplement
the normal sandboxed image path.

## Ordinary desktop output and remaining acceptance

The exact `+rogcolor2` Loupe package and extracted packaged decoder ran alongside
the stock viewer and reference in one isolated Mutter107 session. Its output
advertised BT.2020/PQ; the ordinary candidate Loupe window and a separately
encoded CICP reference agreed within one 10-bit
PQ code across 18 sampled colour channels. Their maximum difference from the
independent matrix plus 203-nit PQ calculation was 6.20 codes; the stock viewer's
maximum was 134.69. The 203 cd/m² white control was `[594, 594, 594]`.
These are synthetic six-patch, one-row software samples,
using staged GTK `4.24.1+ds-1+rogdv3`, not an optical observation or a full image
quality metric. The capture witness separately verified the packed 10-bit
format; a legacy compositor capture path that advertised XR30 while writing
ARGB8888 is not accepted as evidence.

The final package hashes, exact source replay and retained native receipts belong
in the [machine-readable qualification](../evidence/gnome-image-colour-20261108.json).
No live compositor, viewer default, display profile or GNOME setting is changed
by the preparation or diagnostics. Physical panel measurements, real external
monitor coverage and a coordinated live-desktop installation remain separate
acceptance work.

## Retain exact offline recovery

Keep the two candidate DEBs, their DSC source artifacts and the exact installed
stock `loupe` and `glycin-loaders` DEBs outside the public repository. The stock
versions for this qualification are `50.0-0ubuntu2` and `2.2.1+ds-1ubuntu2`.
The retained final rehearsal accepted exactly two upgrades and two exact stock
restores, with zero removals and unchanged live dpkg status bytes. Before any
later installation, rehearse the local candidate pair and its exact stock
rollback against the then-current destination dpkg state with networking disabled. Require
that APT changes only those two packages and does not remove or upgrade the
parallel i386 libraries. Use the existing solver helper, which also verifies that
the live dpkg status bytes remain unchanged:

```bash
python3 "$PATCH_REPO/tools/qualify-ubuntu-bundle.py" \
  "$HDR_WORK/bundle/candidate" "$HDR_WORK/bundle/rollback" \
  "$HDR_WORK/offline-rehearsal"
```

Preserve the accepted plans and package SHA-256 values. A simulated rollback is recovery evidence; it does not claim an actual rollback
was executed on the owner's desktop.
