#!/bin/bash
# Binary packages for the Ubuntu libdisplay-info (amd64, i386 cross) and
# Mutter (amd64) series, from trees made by tools/reconstruct.py.
# Runs inside a disposable Ubuntu 26.10 container; tests are disabled
# deliberately (the fast lane runs separately).
#
# Usage: package-ubuntu.sh STAGE LIB_TREE MUTTER_TREE ORIG_TARBALL OUT
#   STAGE: setup | lib64 | lib32 | mutter | all
#   ORIG_TARBALL: mutter_51.0.orig.tar.xz (for subprojects/gvdb, which the
#   package's .gitignore keeps out of the recorded import).
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
stage=$1; lib_tree=$(realpath "$2"); mutter_tree=$(realpath "$3"); orig=$(realpath "$4"); out=$(realpath -m "$5")
work=$out/work; logs=$out/logs
mkdir -p "$out" "$work" "$logs"

# The tree is the quilt-applied import; record that for dpkg-source and
# refuse to build unless every series entry really is applied.
mark_applied() {
    local d=$1
    mkdir -p "$d/.pc"
    echo 2 > "$d/.pc/.version"
    echo debian/patches > "$d/.pc/.quilt_patches"
    echo series > "$d/.pc/.quilt_series"
    grep -v -E '^\s*(#|$)' "$d/debian/patches/series" | sed 's/[[:space:]].*//' > "$d/.pc/applied-patches"
    while read -r p; do
        (cd "$d" && patch -R -p1 --dry-run --quiet -f < "debian/patches/$p" > /dev/null) ||
            { echo "series entry $p is not applied in the tree" >&2; exit 1; }
    done < "$d/.pc/applied-patches"
}

copy_tree() {  # $1 source tree, $2 destination (the committed tree only)
    rm -rf "$2"; mkdir -p "$2"
    if command -v git > /dev/null && git -C "$1" rev-parse --git-dir > /dev/null 2>&1; then
        git -C "$1" archive HEAD | tar -x -C "$2"
    else
        tar -C "$1" --exclude=.git --exclude=.pc -cf - . | tar -x -C "$2"
    fi
    mark_applied "$2"
}

if [ "$stage" = all ] || [ "$stage" = setup ]; then
    apt-get update -q
    apt-get install -y -q --no-install-recommends build-essential devscripts equivs dpkg-dev fakeroot ca-certificates
fi

if [ "$stage" = all ] || [ "$stage" = lib64 ]; then
    copy_tree "$lib_tree" "$work/lib64/libdisplay-info-0.3.0"
    cd "$work/lib64/libdisplay-info-0.3.0"
    apt-get build-dep -y -q --no-install-recommends ./
    DEB_BUILD_OPTIONS="nocheck parallel=2" dpkg-buildpackage -b -us -uc > "$logs/lib-amd64.log" 2>&1
    cp ../*.deb ../*.buildinfo ../*.changes "$out/"
fi

if [ "$stage" = all ] || [ "$stage" = lib32 ]; then
    dpkg --add-architecture i386
    apt-get update -q
    apt-get install -y -q --no-install-recommends crossbuild-essential-i386
    copy_tree "$lib_tree" "$work/lib32/libdisplay-info-0.3.0"
    cd "$work/lib32/libdisplay-info-0.3.0"
    apt-get build-dep -y -q --no-install-recommends -a i386 ./
    DEB_BUILD_OPTIONS="nocheck parallel=2" dpkg-buildpackage -a i386 -B -us -uc > "$logs/lib-i386.log" 2>&1
    cp ../*.deb ../*.buildinfo ../*.changes "$out/"
fi

if [ "$stage" = all ] || [ "$stage" = mutter ]; then
    lib_version=$(dpkg-parsechangelog -l "$lib_tree/debian/changelog" -S Version)
    apt-get install -y -q --no-install-recommends \
        "$out/libdisplay-info3_${lib_version}_amd64.deb" "$out/libdisplay-info-dev_${lib_version}_amd64.deb"
    copy_tree "$mutter_tree" "$work/mutter/mutter-51.0"
    echo "5d28f3ae225692428fcafb96500d673f34328b698b86960c9c1460d0b1d983b3  $orig" | sha256sum -c -
    tar -xJf "$orig" -C "$work/mutter/mutter-51.0" --strip-components=1 mutter-51.0/subprojects/gvdb
    cd "$work/mutter/mutter-51.0"
    apt-get build-dep -y -q --no-install-recommends ./
    dpkg -l 'libdisplay-info*' | tail -n +6 > "$logs/mutter-build-libdisplay-info.txt"
    DEB_BUILD_OPTIONS="nocheck parallel=2" dpkg-buildpackage -b -us -uc > "$logs/mutter-amd64.log" 2>&1
    cp ../*.deb ../*.buildinfo ../*.changes "$out/"
fi
(cd "$out" && sha256sum ./*.deb > SHA256SUMS)
echo "stage $stage done: $out"
