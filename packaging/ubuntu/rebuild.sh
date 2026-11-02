#!/usr/bin/env bash
# Keep the Forgejo Debian registry in step with Ubuntu.
#
#   FORGEJO_TOKEN=... packaging/ubuntu/rebuild.sh WORK [--release 26.10]
#
# For libdisplay-info and Mutter, asks Ubuntu which source version it
# publishes now, and builds and publishes that version plus this
# repository's series when the registry does not have it complete yet: after
# an Ubuntu update, or after packaging/ubuntu/REVISION was raised for a series
# change. Mutter builds against the registry's libdisplay-info. Once a new
# version has built, the source's older versions are deleted from the registry
# and the new one is uploaded, so machines move to it even when Ubuntu's new
# version sorts below the old build (0.3.0-1ubuntu0.1 sorts below 0.3.0-1, so
# 0.3.0-1ubuntu0.1+nativehdrN sorts below 0.3.0-1+nativehdrN): the registry
# holds one version per source. The deletions come before the uploads because
# Forgejo (v16) does not rebuild the index when it deletes a version's last
# file; each upload rebuilds its architecture's index.
# WORK is a private durable retention root, never emptied. A run-* child is
# reserved exclusively when a build is needed; an already-published no-op
# leaves WORK untouched. Keep failed/partial runs as well as successful ones.
set -euo pipefail

root=${1:?usage: rebuild.sh WORK [--release R]}; shift
work=
umask 077
release=26.10
[ "${1:-}" = --release ] && release=$2
here=$(cd "$(dirname "$0")" && pwd)
FORGEJO_URL=${FORGEJO_URL:-http://forge.lan:3000} FORGEJO_OWNER=${FORGEJO_OWNER:-pjunod}
export FORGEJO_URL FORGEJO_OWNER
revision=$(tr -d '[:space:]' < "$here/REVISION")
# A series change without a REVISION bump would look published and never ship.
python3 "$here/../../scripts/check_repository.py" >/dev/null

read -r CODENAME ldi_ubuntu mutter_ubuntu < <(docker run --rm "ubuntu:$release" bash -c '
  sed -i "s/^Types: deb$/Types: deb deb-src/" /etc/apt/sources.list.d/ubuntu.sources
  apt-get update -qq >/dev/null
  newest() { apt-cache showsrc "$1" | sed -n "s/^Version: //p" | sort -V | tail -1; }
  . /etc/os-release; echo "$VERSION_CODENAME $(newest libdisplay-info) $(newest mutter)"')
[ -n "$mutter_ubuntu" ] || { echo "rebuild.sh: could not read Ubuntu's source versions" >&2; exit 1; }
# shellcheck source=registry.sh
. "$here/registry.sh"
# Stop here, not after an hour of building, when the registry cannot be read.
packages_index amd64 >/dev/null

# Delete every version but KEEP of a source's binaries, on the given archs.
prune() {  # prune SOURCE KEEP ARCH...
  local src=$1 keep=$2 arch name version; shift 2
  for arch in "$@"; do
    binaries_of "$src" "$arch" | while read -r name version; do
      [ "$version" = "$keep" ] && continue
      delete_package "$name" "$version" "$arch"
      echo "removed superseded $name $version $arch"
    done
  done
}

ensure_work() {
  [ -z "$work" ] || return 0
  work=$(python3 "$here/outputs.py" reserve "$root")
  echo "retained build outputs: $work"
}

# Capture raw build diagnostics privately rather than upload them as CI logs.
# The producer writes directly into this run; no archive copy can go stale.
build_retained() {  # build_retained SOURCE ARCH UBUNTU-VERSION VERSION [BUILD-ARGS...]
  local src=$1 arch=$2 ubuntu=$3 version=$4 out; shift 4
  ensure_work
  out=$work/$src-$arch
  mkdir "$out"
  if ! "$here/build.sh" "$src" "$out" --release "$release" --arch "$arch" \
      --version "$ubuntu" "$@" >"$out/invocation.log" 2>&1; then
    echo "rebuild.sh: $src $arch build failed; private diagnostics retained in $out" >&2
    return 1
  fi
  python3 "$here/outputs.py" seal "$out" "$out.manifest.json" \
    "$src" "$ubuntu" "$version" "$arch"
}

ldi=$ldi_ubuntu+nativehdr$revision mutter=$mutter_ubuntu+nativehdr$revision
echo "Ubuntu $CODENAME: libdisplay-info $ldi_ubuntu, mutter $mutter_ubuntu; series revision $revision"

# Both architectures: a Multi-Arch: same library must ship byte-identical
# shared files (its changelog, copyright) on each.
if is_published libdisplay-info3 "$ldi" amd64 && is_published libdisplay-info3 "$ldi" i386; then
  echo "libdisplay-info $ldi: published"
else
  for arch in amd64 i386; do
    build_retained libdisplay-info "$arch" "$ldi_ubuntu" "$ldi"
  done
  for name in libdisplay-info3 libdisplay-info-dev; do
    "$here/multiarch-same.sh" "$work"/libdisplay-info-amd64/"$name"_*.deb \
      "$work"/libdisplay-info-i386/"$name"_*.deb
  done
  prune libdisplay-info "$ldi" amd64 i386
  "$here/publish.sh" "$work/libdisplay-info-amd64" "$work/libdisplay-info-i386" --release "$release"
fi

if is_published mutter "$mutter" amd64; then
  echo "mutter $mutter: published"
else
  # The libdisplay-info Mutter builds against: the registry's.
  ensure_work
  mkdir -p "$work/with"
  for name in libdisplay-info3 libdisplay-info-dev; do
    curl -sf -o "$work/with/${name}_${ldi}_amd64.deb" "$pool/${name}_${ldi}_amd64.deb"
  done
  build_retained mutter amd64 "$mutter_ubuntu" "$mutter" --with "$work/with"
  prune mutter "$mutter" amd64 all
  "$here/publish.sh" "$work/mutter-amd64" --release "$release"
fi
