#!/usr/bin/env bash
# Keep the Forgejo Debian registry in step with Ubuntu.
#
#   FORGEJO_TOKEN=... packaging/ubuntu/rebuild.sh WORK [--release 26.10]
#
# For libdisplay-info and Mutter, asks Ubuntu which source version it
# publishes now, and builds and publishes that version plus this
# repository's series when the registry does not have it yet: after an
# Ubuntu update, or after packaging/ubuntu/REVISION was raised for a series
# change. Mutter builds against the registry's libdisplay-info. WORK holds
# the build output and is emptied first.
set -euo pipefail

work=${1:?usage: rebuild.sh WORK [--release R]}; shift
release=26.10
[ "${1:-}" = --release ] && release=$2
here=$(cd "$(dirname "$0")" && pwd)
url=${FORGEJO_URL:-http://forge.lan:3000}
owner=${FORGEJO_OWNER:-pjunod}
revision=$(tr -d '[:space:]' < "$here/REVISION")

read -r codename ldi_ubuntu mutter_ubuntu < <(docker run --rm "ubuntu:$release" bash -c '
  sed -i "s/^Types: deb$/Types: deb deb-src/" /etc/apt/sources.list.d/ubuntu.sources
  apt-get update -qq >/dev/null
  newest() { apt-cache showsrc "$1" | sed -n "s/^Version: //p" | sort -V | tail -1; }
  . /etc/os-release; echo "$VERSION_CODENAME $(newest libdisplay-info) $(newest mutter)"')
registry=$url/api/packages/$owner/debian
packages() { curl -sf "$registry/dists/$codename/main/binary-$1/Packages" || true; }
published() {  # published PACKAGE VERSION ARCH
  packages "$3" | awk -v p="$1" -v v="$2" '
    $1 == "Package:" {name = $2} $1 == "Version:" && name == p && $2 == v {found = 1}
    END {exit !found}'
}

rm -rf "$work"; mkdir -p "$work"
ldi=$ldi_ubuntu+nativehdr$revision mutter=$mutter_ubuntu+nativehdr$revision
echo "Ubuntu $codename: libdisplay-info $ldi_ubuntu, mutter $mutter_ubuntu; series revision $revision"

for arch in amd64 i386; do
  if published libdisplay-info3 "$ldi" "$arch"; then
    echo "libdisplay-info $ldi $arch: published"
  else
    "$here/build.sh" libdisplay-info "$work/libdisplay-info-$arch" --release "$release" --arch "$arch"
    "$here/publish.sh" "$work/libdisplay-info-$arch" --release "$release"
  fi
done

if published mutter "$mutter" amd64; then
  echo "mutter $mutter: published"
else
  # The libdisplay-info Mutter builds against: the registry's, which this run
  # just published if it was missing.
  mkdir -p "$work/with"
  for name in libdisplay-info3 libdisplay-info-dev; do
    curl -sf -o "$work/with/${name}_${ldi}_amd64.deb" \
      "$registry/pool/$codename/main/${name}_${ldi}_amd64.deb"
  done
  "$here/build.sh" mutter "$work/mutter-amd64" --release "$release" --with "$work/with"
  "$here/publish.sh" "$work/mutter-amd64" --release "$release"
fi
