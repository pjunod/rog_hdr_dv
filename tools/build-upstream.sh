#!/bin/sh
# Build the upstream-facing libdisplay-info and Mutter series with warnings as
# errors, Mutter against that libdisplay-info. Incremental on reruns.
#
# Usage: build-upstream.sh LIBDISPLAY_INFO_SRC MUTTER_SRC BUILD_ROOT [ORIG_TARBALL]
#   The sources are trees from tools/reconstruct.py (or work branches on them).
#   ORIG_TARBALL: Ubuntu's mutter_51.0.orig.tar.xz, used to supply
#   subprojects/gvdb when gitlab.gnome.org cannot be reached; its SHA-256 is
#   checked against the pin in sources.json.
set -eu
lib_src=$(realpath "$1"); mutter_src=$(realpath "$2"); out=$(realpath -m "$3"); orig=${4:-}
prefix=$out/ldi-prefix
export PKG_CONFIG_PATH=$prefix/lib/x86_64-linux-gnu/pkgconfig
mkdir -p "$out"

if [ ! -f "$PKG_CONFIG_PATH/libdisplay-info.pc" ]; then
    meson setup "$out/ldi" "$lib_src" -Dwerror=true --prefix="$prefix" --libdir=lib/x86_64-linux-gnu > "$out/ldi-setup.log" 2>&1
fi
ninja -C "$out/ldi" install > "$out/ldi-build.log" 2>&1

if [ ! -d "$mutter_src/subprojects/gvdb/gvdb" ] && [ -n "$orig" ]; then
    want=5d28f3ae225692428fcafb96500d673f34328b698b86960c9c1460d0b1d983b3
    echo "$want  $orig" | sha256sum -c -
    tar -xJf "$orig" -C "$mutter_src" --strip-components=1 mutter-51.0/subprojects/gvdb
fi
if [ ! -d "$out/mutter" ]; then
    LDFLAGS="-Wl,-rpath,$prefix/lib/x86_64-linux-gnu" \
        meson setup "$out/mutter" "$mutter_src" -Dremote_desktop=true -Dwerror=true > "$out/mutter-setup.log" 2>&1
fi
nice ninja -C "$out/mutter" > "$out/mutter-build.log" 2>&1
echo "build OK: $out/mutter"
