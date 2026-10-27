#!/usr/bin/env bash
# Upload built .debs to the Forgejo Debian registry.
#
#   FORGEJO_TOKEN=... packaging/ubuntu/publish.sh DIR... [--release 26.10]
#
# Every .deb in each DIR goes to
#   $FORGEJO_URL/api/packages/$FORGEJO_OWNER/debian  <codename> main
# (defaults: http://forge.lan:3000, owner pjunod). The registry refuses a
# second upload of the same package, version and architecture, so a version
# is never replaced: an already published identical file is skipped, a
# different file under a published version is an error.
set -euo pipefail

: "${FORGEJO_TOKEN:?FORGEJO_TOKEN is not set}"
url=${FORGEJO_URL:-http://forge.lan:3000}
owner=${FORGEJO_OWNER:-pjunod}
release=26.10 dirs=()
while [ $# -gt 0 ]; do
  case $1 in
    --release) release=$2; shift 2 ;;
    *) dirs+=("$1"); shift ;;
  esac
done
[ ${#dirs[@]} -gt 0 ] || { echo "usage: publish.sh DIR... [--release R]" >&2; exit 2; }
codename=$(docker run --rm "ubuntu:$release" sh -c '. /etc/os-release; echo "$VERSION_CODENAME"')
pool=$url/api/packages/$owner/debian/pool/$codename/main

for dir in "${dirs[@]}"; do
  for deb in "$dir"/*.deb; do
    [ -e "$deb" ] || continue
    name=$(dpkg-deb -f "$deb" Package) version=$(dpkg-deb -f "$deb" Version)
    arch=$(dpkg-deb -f "$deb" Architecture)
    code=$(curl -s -o /dev/null -w '%{http_code}' -X PUT \
      -H "Authorization: token $FORGEJO_TOKEN" --upload-file "$deb" "$pool/upload")
    case $code in
      201) echo "published $name $version $arch" ;;
      409)
        # Already there: fine only if it is this exact file.
        published=$(curl -sf -H "Authorization: token $FORGEJO_TOKEN" \
          "$pool/${name}_${version}_${arch}.deb" | sha256sum | cut -d' ' -f1)
        if [ "$published" = "$(sha256sum < "$deb" | cut -d' ' -f1)" ]; then
          echo "already published $name $version $arch"
        else
          echo "publish.sh: $name $version $arch is published with different contents" >&2; exit 1
        fi ;;
      *) echo "publish.sh: upload of $deb answered HTTP $code" >&2; exit 1 ;;
    esac
  done
done
