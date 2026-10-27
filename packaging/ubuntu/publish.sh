#!/usr/bin/env bash
# Upload built .debs to the Forgejo Debian registry.
#
#   FORGEJO_TOKEN=... packaging/ubuntu/publish.sh DIR... [--release 26.10]
#
# Every .deb in each DIR goes to $FORGEJO_URL/api/packages/$FORGEJO_OWNER/debian
# (defaults: http://forge.lan:3000, owner pjunod), suite <codename>, component
# main. The token needs the write:package scope.
#
# The source's sentinel package (the one named like the source: mutter,
# libdisplay-info3) is uploaded last, on its last architecture, so a version
# whose sentinel is in the registry is complete. A version without its
# sentinel is a partial upload from an earlier failed run: its files are
# replaced. A complete version is never replaced, and a different file under
# it is an error.
set -euo pipefail

release=26.10 dirs=()
while [ $# -gt 0 ]; do
  case $1 in
    --release) release=$2; shift 2 ;;
    *) dirs+=("$1"); shift ;;
  esac
done
[ ${#dirs[@]} -gt 0 ] || { echo "usage: publish.sh DIR... [--release R]" >&2; exit 2; }
FORGEJO_URL=${FORGEJO_URL:-http://forge.lan:3000} FORGEJO_OWNER=${FORGEJO_OWNER:-pjunod}
CODENAME=$(docker run --rm "ubuntu:$release" sh -c '. /etc/os-release; echo "$VERSION_CODENAME"')
# shellcheck source=registry.sh
. "$(dirname "$0")/registry.sh"

field() { dpkg-deb -f "$1" "$2"; }
source_of() { local s; s=$(field "$1" Source 2>/dev/null || true); s=${s%% *}; echo "${s:-$(field "$1" Package)}"; }

# Upload order: everything but sentinels, then the sentinels.
debs=() sentinels=()
for dir in "${dirs[@]}"; do
  for deb in "$dir"/*.deb; do
    [ -e "$deb" ] || continue
    name=$(field "$deb" Package)
    case $name in mutter|libdisplay-info3) sentinels+=("$deb") ;; *) debs+=("$deb") ;; esac
  done
done
[ ${#debs[@]} -gt 0 ] || [ ${#sentinels[@]} -gt 0 ] || { echo "publish.sh: no .deb in ${dirs[*]}" >&2; exit 1; }

complete() {  # complete SOURCE ARCHS VERSION: is every architecture's sentinel published?
  local sentinel=$1 arch rc
  [ "$1" = libdisplay-info ] && sentinel=libdisplay-info3
  for arch in $2; do
    if is_published "$sentinel" "$3" "$arch"; then continue; else rc=$?; fi
    [ "$rc" = 1 ] || exit 1   # the registry could not be read
    return 1
  done
}

for deb in "${debs[@]}" "${sentinels[@]}"; do
  name=$(field "$deb" Package) version=$(field "$deb" Version) arch=$(field "$deb" Architecture)
  code=$(authed_curl -s -o /dev/null -w '%{http_code}' -X PUT --upload-file "$deb" "$pool/upload")
  case $code in
    201) echo "published $name $version $arch"; continue ;;
    409) ;;
    *) echo "publish.sh: upload of $deb answered HTTP $code" >&2; exit 1 ;;
  esac
  published=$(curl -sf "$pool/${name}_${version}_${arch}.deb" | sha256sum | cut -d' ' -f1) \
    || { echo "publish.sh: cannot download the published $name $version $arch" >&2; exit 1; }
  if [ "$published" = "$(sha256sum < "$deb" | cut -d' ' -f1)" ]; then
    echo "already published $name $version $arch"
    continue
  fi
  src=$(source_of "$deb")
  archs=amd64; [ "$src" = libdisplay-info ] && archs="amd64 i386"
  if complete "$src" "$archs" "$version"; then
    echo "publish.sh: $name $version $arch is published with different contents" >&2; exit 1
  fi
  echo "replacing $name $version $arch from an incomplete earlier upload"
  delete_package "$name" "$version" "$arch"
  code=$(authed_curl -s -o /dev/null -w '%{http_code}' -X PUT --upload-file "$deb" "$pool/upload")
  [ "$code" = 201 ] || { echo "publish.sh: re-upload of $deb answered HTTP $code" >&2; exit 1; }
  echo "published $name $version $arch"
done
