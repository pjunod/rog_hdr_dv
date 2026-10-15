#!/bin/sh
# Build every commit of a range with warnings as errors, in a separate
# worktree and build directory, so that each commit of a series stands alone.
#
# Usage: check-each-commit.sh REPO BASE TIP BUILD_DIR LDI_PREFIX
#   LDI_PREFIX: the libdisplay-info install prefix from build-upstream.sh.
# Prints "OK <sha> <subject>" or "FAIL <sha> <subject>" per commit and keeps
# the failing build log next to BUILD_DIR.
set -u
repo=$(realpath "$1"); base=$2; tip=$3; build=$(realpath -m "$4"); prefix=$(realpath "$5")
export PKG_CONFIG_PATH=$prefix/lib/x86_64-linux-gnu/pkgconfig
wt=$build-worktree
git -C "$repo" worktree add --quiet --detach "$wt" "$tip"
[ -d "$repo/subprojects/gvdb/gvdb" ] && cp -r "$repo/subprojects/gvdb" "$wt/subprojects/"
status=0
for c in $(git -C "$repo" rev-list --reverse "$base..$tip"); do
    git -C "$wt" checkout --quiet --detach "$c"
    if [ ! -d "$build" ]; then
        LDFLAGS="-Wl,-rpath,$prefix/lib/x86_64-linux-gnu" \
            meson setup "$build" "$wt" -Dremote_desktop=true -Dwerror=true > "$build.setup.log" 2>&1
    fi
    subject=$(git -C "$wt" log -1 --format=%s "$c")
    if nice ninja -C "$build" > "$build.last.log" 2>&1; then
        echo "OK $c $subject"
    else
        echo "FAIL $c $subject"; cp "$build.last.log" "$build.fail-$c.log"; status=1
    fi
done
git -C "$repo" worktree remove --force "$wt"
exit $status
