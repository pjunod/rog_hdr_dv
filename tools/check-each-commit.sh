#!/bin/sh
# Build every commit of a range with warnings as errors, in a separate
# worktree and build directory, so that each commit of a series stands alone.
#
# Usage: check-each-commit.sh REPO BASE TIP BUILD_DIR LDI_PREFIX
#   LDI_PREFIX: the libdisplay-info install prefix from build-upstream.sh.
# Prints "OK <sha> <subject>" or "FAIL <sha> <subject>" per commit and keeps
# the failing build log in BUILD_DIR.logs. Build and log directories are retained;
# all three paths must be new and exclusively owned by this invocation.
set -eu
die() { printf '%s\n' "$*" >&2; exit 2; }
[ "$#" -eq 5 ] || die 'Usage: check-each-commit.sh REPO BASE TIP BUILD_DIR LDI_PREFIX'
repo=$(realpath "$1") || exit 2
[ ! -e "$4" ] && [ ! -L "$4" ] || die "Refusing existing build path: $4"
build=$(realpath -m "$4") || exit 2
prefix=$(realpath "$5") || exit 2
[ -d "$prefix" ] || die 'Missing library prefix'
base=$(git -C "$repo" rev-parse --verify --end-of-options "$2^{commit}") || exit 2
tip=$(git -C "$repo" rev-parse --verify --end-of-options "$3^{commit}") || exit 2
commits=$(git -C "$repo" rev-list --reverse "$base..$tip") || exit 2
[ -n "$commits" ] || die 'Range contains no commits'
export PKG_CONFIG_PATH=$prefix/lib/x86_64-linux-gnu/pkgconfig
wt=$build-worktree
logs=$build.logs
for path in "$build" "$wt" "$logs"; do
    [ ! -e "$path" ] && [ ! -L "$path" ] || die "Refusing existing path: $path"
done
# mkdir and worktree add are exclusive reservations, not reuse of checked paths.
mkdir "$build" || exit 2
mkdir "$logs" || exit 2
owned_wt=0
cleanup() {
    rc=$?
    trap - EXIT HUP INT TERM
    if [ "$owned_wt" -eq 1 ]; then
        git -C "$repo" worktree remove --force "$wt" || {
            printf 'Owned worktree cleanup failed: %s\n' "$wt" >&2
            [ "$rc" -ne 0 ] || rc=2
        }
    fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
git -C "$repo" worktree add --quiet --detach "$wt" "$tip" || exit 2
owned_wt=1
if [ -d "$repo/subprojects/gvdb/gvdb" ]; then
    cp -r "$repo/subprojects/gvdb" "$wt/subprojects/" || exit 2
fi
status=0
setup=0
for c in $commits; do
    git -C "$wt" checkout --quiet --detach "$c" || exit 2
    actual=$(git -C "$wt" rev-parse HEAD) || exit 2
    [ "$actual" = "$c" ] || die 'Worktree source does not match requested commit'
    if [ "$setup" -eq 0 ]; then
        LDFLAGS="-Wl,-rpath,$prefix/lib/x86_64-linux-gnu" \
            meson setup "$build" "$wt" -Dremote_desktop=true -Dwerror=true > "$logs/setup.log" 2>&1 || exit 2
        setup=1
    fi
    # Meson's own metadata, not the caller's path, establishes build association.
    python3 -c 'import json, pathlib, sys
build, source = map(pathlib.Path, sys.argv[1:])
dirs = json.loads((build / "meson-info/meson-info.json").read_text())["directories"]
if pathlib.Path(dirs["source"]).resolve() != source.resolve() or pathlib.Path(dirs["build"]).resolve() != build.resolve():
    raise SystemExit("Meson source/build association mismatch")' "$build" "$wt" || exit 2
    subject=$(git -C "$wt" log -1 --format=%s "$c") || exit 2
    if nice ninja -C "$build" > "$logs/last.log" 2>&1; then
        echo "OK $c $subject"
    else
        echo "FAIL $c $subject"
        cp "$logs/last.log" "$logs/fail-$c.log" || exit 2
        status=1
    fi
done
exit "$status"
