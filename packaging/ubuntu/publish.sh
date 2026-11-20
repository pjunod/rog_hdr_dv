#!/usr/bin/env bash
# Publish complete public derivative families. Versions and bytes are immutable;
# an interrupted upload may resume only with the same retained package payloads.
set -euo pipefail
release=26.10 dirs=()
while [ $# -gt 0 ]; do
  case $1 in
    --release) release=$2; shift 2 ;;
    *) dirs+=("$1"); shift ;;
  esac
done
[ ${#dirs[@]} -gt 0 ] || { echo 'usage: publish.sh DIR... [--release R]' >&2; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
FORGEJO_URL=${FORGEJO_URL:-http://forge.lan:3000} FORGEJO_OWNER=${FORGEJO_OWNER:-pjunod}
CODENAME=$(docker run --rm "ubuntu:$release" sh -c '. /etc/os-release; echo "$VERSION_CODENAME"')
. "$here/registry.sh"
: "${TMPDIR:?set TMPDIR to private external task storage}"
work=$(mktemp -d "$TMPDIR/managed-publish.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT
# Validate the entire transaction before the first registry mutation.
python3 "$here/managed.py" bundle "${dirs[@]}" > "$work/bundle.json"
python3 - "$work/bundle.json" > "$work/upload-list" <<'PY'
import json, sys
for row in json.load(open(sys.argv[1])):
    print('\t'.join(row[k] for k in ('Package', 'Version', 'Architecture', 'SHA256', 'Path')))
PY
while IFS=$'\t' read -r name version arch digest deb; do
  code=$(authed_curl -s -o /dev/null -w '%{http_code}' -X PUT --upload-file "$deb" "$pool/upload")
  case $code in
    201) echo "published $name $version $arch" ;;
    409)
      published=$(curl -fsS "$pool/${name}_${version}_${arch}.deb" | sha256sum | cut -d' ' -f1)
      [ "$published" = "$digest" ] || {
        echo "publish.sh: immutable version conflict: $name $version $arch; use a new revision" >&2; exit 1;
      }
      echo "already published $name $version $arch" ;;
    *) echo "publish.sh: upload answered HTTP $code for $name $version $arch" >&2; exit 1 ;;
  esac
done < "$work/upload-list"
# Forgejo keeps Architecture: all packages in a separate signed binary-all index.
indices=()
while read -r arch; do
  packages_index "$arch" > "$work/$arch.Packages"
  indices+=("$work/$arch.Packages")
done < <(python3 - "$work/bundle.json" <<'PY'
import json, sys
print('\n'.join(sorted({r['Architecture'] for r in json.load(open(sys.argv[1]))})))
PY
)
python3 "$here/managed.py" verify-index "$work/bundle.json" "${indices[@]}"
echo 'Published complete family inventory and SHA256 identities verified.'
