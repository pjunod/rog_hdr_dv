#!/usr/bin/env bash
# Keep the Forgejo Debian registry in step with Ubuntu.
#
#   FORGEJO_TOKEN=... packaging/ubuntu/rebuild.sh WORK [--release 26.10]
#
# For libdisplay-info and Mutter, asks Ubuntu which source version it
# publishes now, and builds and publishes that version plus this
# repository's series when the registry does not have it complete yet: after
# an Ubuntu update, or after packaging/ubuntu/REVISION was raised for a series
# change. Mutter builds against the registry's libdisplay-info. Once a source's
# new version is complete, its older versions are deleted from the registry,
# so machines move to it even when Ubuntu's new version sorts below the old
# build (0.3.0-1ubuntu0.1 sorts below 0.3.0-1, so 0.3.0-1ubuntu0.1+nativehdrN
# sorts below 0.3.0-1+nativehdrN): the registry holds one version per source.
# WORK holds the build output and is emptied first.
set -euo pipefail

work=${1:?usage: rebuild.sh WORK [--release R]}; shift
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

rm -rf "$work"; mkdir -p "$work"
ldi=$ldi_ubuntu+nativehdr$revision mutter=$mutter_ubuntu+nativehdr$revision
echo "Ubuntu $CODENAME: libdisplay-info $ldi_ubuntu, mutter $mutter_ubuntu; series revision $revision"

# Both architectures: a Multi-Arch: same library must ship byte-identical
# shared files (its changelog, copyright) on each.
if is_published libdisplay-info3 "$ldi" amd64 && is_published libdisplay-info3 "$ldi" i386; then
  echo "libdisplay-info $ldi: published"
else
  for arch in amd64 i386; do
    "$here/build.sh" libdisplay-info "$work/libdisplay-info-$arch" --release "$release" \
      --arch "$arch" --version "$ldi_ubuntu"
  done
  for name in libdisplay-info3 libdisplay-info-dev; do
    "$here/multiarch-same.sh" "$work"/libdisplay-info-amd64/"$name"_*.deb \
      "$work"/libdisplay-info-i386/"$name"_*.deb
  done
  "$here/publish.sh" "$work/libdisplay-info-amd64" "$work/libdisplay-info-i386" --release "$release"
fi
prune libdisplay-info "$ldi" amd64 i386

if is_published mutter "$mutter" amd64; then
  echo "mutter $mutter: published"
else
  # The libdisplay-info Mutter builds against: the registry's.
  mkdir -p "$work/with"
  for name in libdisplay-info3 libdisplay-info-dev; do
    curl -sf -o "$work/with/${name}_${ldi}_amd64.deb" "$pool/${name}_${ldi}_amd64.deb"
  done
  "$here/build.sh" mutter "$work/mutter-amd64" --release "$release" --with "$work/with" \
    --version "$mutter_ubuntu"
  "$here/publish.sh" "$work/mutter-amd64" --release "$release"
fi
prune mutter "$mutter" amd64 all
