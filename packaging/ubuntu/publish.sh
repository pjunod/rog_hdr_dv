#!/usr/bin/env bash
# Publish exact reviewed public families. Check EVERY existing target identity
# and payload before any upload; --preflight-only is used before registry prune.
set -euo pipefail
release=26.10 preflight_only=0 dirs=()
while [ $# -gt 0 ]; do
  case $1 in
    --release) release=$2; shift 2 ;;
    --preflight-only) preflight_only=1; shift ;;
    *) dirs+=("$1"); shift ;;
  esac
done
[ ${#dirs[@]} -gt 0 ] || { echo 'usage: publish.sh [--preflight-only] DIR... [--release R]' >&2; exit 2; }
# Verify prerequisites before the caller is allowed to prune anything.
for command in python3 docker curl sha256sum dpkg-deb mktemp; do command -v "$command" >/dev/null; done
: "${FORGEJO_TOKEN:?publication requires FORGEJO_TOKEN before any registry mutation}"
: "${TMPDIR:?set TMPDIR to private external task storage before publication/pruning}"
[ -d "$TMPDIR" ] && [ -w "$TMPDIR" ] || { echo 'publish.sh: TMPDIR is not writable' >&2; exit 1; }
umask 077
here=$(cd "$(dirname "$0")" && pwd)
FORGEJO_URL=${FORGEJO_URL:-http://forge.lan:3000} FORGEJO_OWNER=${FORGEJO_OWNER:-pjunod}
CODENAME=$(docker run --rm "ubuntu:$release" sh -c '. /etc/os-release; echo "$VERSION_CODENAME"')
. "$here/registry.sh"
work=$(mktemp -d "$TMPDIR/managed-publish.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT
python3 "$here/managed.py" bundle "${dirs[@]}" > "$work/bundle.json"
indices=()
while read -r arch; do
  packages_index "$arch" > "$work/$arch.Packages"
  indices+=("$work/$arch.Packages")
done < <(python3 - "$work/bundle.json" <<'PY'
import json, sys
print('\n'.join(sorted({r['Architecture'] for r in json.load(open(sys.argv[1]))})))
PY
)
python3 "$here/managed.py" preflight-existing "$work/bundle.json" "${indices[@]}"
python3 - "$work/bundle.json" "${indices[@]}" > "$work/upload-list" <<'PY'
import json, sys
from pathlib import Path
rows = json.load(open(sys.argv[1]))
# Every package is also fetched from the pool below, including unindexed pool
# payloads left by an interrupted publication. Index presence distinguishes an
# absent target from a corrupt index pointing to a missing payload.
indices = '\n\n'.join(Path(p).read_text() for p in sys.argv[2:])
for row in rows:
    present = any(all(f'{key}: {row[key]}' in block.splitlines() for key in ('Package', 'Version', 'Architecture'))
                  for block in indices.strip().split('\n\n'))
    print('\t'.join([*(row[k] for k in ('Package', 'Version', 'Architecture', 'SHA256', 'Path')), str(int(present))]))
PY
number=0
while IFS=$'\t' read -r name version arch digest deb indexed; do
  number=$((number + 1))
  code=$(curl -sS -o "$work/existing-$number.deb" -w '%{http_code}' "$pool/${name}_${version}_${arch}.deb")
  case $code in
    200)
      published=$(sha256sum < "$work/existing-$number.deb" | cut -d' ' -f1)
      [ "$published" = "$digest" ] || {
        echo "publish.sh: immutable version conflict before mutation: $name $version $arch; retain old bytes and use a new reviewed revision" >&2; exit 1;
      } ;;
    404) [ "$indexed" = 0 ] || { echo "publish.sh: registry index references a missing $name $version $arch payload" >&2; exit 1; } ;;
    *) echo "publish.sh: cannot inspect existing target: HTTP $code for $name $version $arch" >&2; exit 1 ;;
  esac
done < "$work/upload-list"
[ "$preflight_only" = 0 ] || { echo 'Publication prerequisites, complete intended family and existing target identities verified.'; exit 0; }
while IFS=$'\t' read -r name version arch digest deb indexed; do
  code=$(authed_curl -s -o /dev/null -w '%{http_code}' -X PUT --upload-file "$deb" "$pool/upload")
  case $code in
    201) echo "published $name $version $arch" ;;
    409)
      published=$(curl -fsS "$pool/${name}_${version}_${arch}.deb" | sha256sum | cut -d' ' -f1)
      [ "$published" = "$digest" ] || { echo "publish.sh: immutable concurrent version conflict: $name $version $arch" >&2; exit 1; }
      echo "already published $name $version $arch" ;;
    *) echo "publish.sh: upload answered HTTP $code for $name $version $arch" >&2; exit 1 ;;
  esac
done < "$work/upload-list"
# Forgejo keeps Architecture: all in its separate index; verify every payload.
for index in "${indices[@]}"; do
  arch=${index##*/}; arch=${arch%.Packages}
  packages_index "$arch" > "$index"
done
python3 "$here/managed.py" verify-index "$work/bundle.json" "${indices[@]}"
echo 'Published complete intended family inventory and SHA256 identities verified.'
