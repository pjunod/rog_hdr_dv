#!/usr/bin/env bash
# Check that two architectures' builds of a Multi-Arch: same package agree
# on every file they both ship, as dpkg requires to co-install them.
#
#   packaging/ubuntu/multiarch-same.sh A.deb B.deb
set -euo pipefail
a=$(mktemp -d -p "${TMPDIR:-$PWD}") b=$(mktemp -d -p "${TMPDIR:-$PWD}")
trap 'rm -rf "$a" "$b"' EXIT
dpkg-deb -x "$1" "$a"; dpkg-deb -x "$2" "$b"
status=0
while IFS= read -r file; do
  if [ -f "$a/$file" ] && [ -f "$b/$file" ] && ! cmp -s "$a/$file" "$b/$file"; then
    echo "multiarch-same.sh: $file differs between $(basename "$1") and $(basename "$2")" >&2
    status=1
  fi
done < <(cd "$a" && find . -type f)
[ $status = 0 ] && echo "multiarch-same: $(basename "$1") and $(basename "$2") agree"
exit $status
