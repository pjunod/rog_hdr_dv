#!/usr/bin/env bash
# Configure package-scoped project preferences; preflight complete indexed
# families before changing holds or installing the exact reviewed transaction.
set -euo pipefail
url=${1:-http://forge.lan:3000} owner=${2:-pjunod}
[ "$(id -u)" = 0 ] || { echo 'setup-apt.sh: run with sudo' >&2; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
codename=$(. /etc/os-release; echo "$VERSION_CODENAME")
host=${url#*://}; host=${host%%[:/]*}
registry=$url/api/packages/$owner/debian
: "${TMPDIR:?set TMPDIR to private external task storage}"
work=$(mktemp -d "$TMPDIR/managed-setup.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT
python3 "$here/managed.py" names > "$work/names"
# Capture state before changing configuration or holds. dpkg patterns are exact
# manifest names; include actual architectures and omit residual-config rows.
mapfile -t names < "$work/names"
{ dpkg-query -W -f '${Package} ${Architecture} ${Version} ${db:Status-Abbrev}\n' "${names[@]}" 2>/dev/null || true; } |
  awk '$4 ~ /^.i/ {print $1, $2, $3}' > "$work/installed"
awk '{print $1 ":" $2}' "$work/installed" > "$work/installed-names"
mapfile -t installed < "$work/installed-names"
apt-mark showhold > "$work/holds"
auto=()
if [ ${#installed[@]} -gt 0 ]; then
  mapfile -t auto < <(apt-mark showauto "${installed[@]}")
fi
install -d -m 0755 /etc/apt/keyrings
curl -fsSL "$registry/repository.key" -o /etc/apt/keyrings/rog-hdr-dv.asc
cat > /etc/apt/sources.list.d/rog-hdr-dv.sources <<EOF
Types: deb
URIs: $registry
Suites: $codename
Components: main
Signed-By: /etc/apt/keyrings/rog-hdr-dv.asc
EOF
python3 "$here/managed.py" preferences "$host" > /etc/apt/preferences.d/rog-hdr-dv
# APT verifies the Release signatures and index hashes. Read only project
# Packages indexes from that authenticated cache, not unauthenticated curl.
apt-get update -o APT::Update::Error-Mode=any
apt-get indextargets --format '$(IDENTIFIER) $(URI) $(FILENAME)' > "$work/targets"
: > "$work/Packages"
while read -r identifier uri filename; do
  if [ "$identifier" = Packages ] && [[ "$uri" = "$registry/"* ]]; then
    /usr/lib/apt/apt-helper cat-file "$filename" >> "$work/Packages"
    printf '\n' >> "$work/Packages"
  fi
done < "$work/targets"
python3 "$here/managed.py" preflight "$work/installed" "$work/Packages" > "$work/targets-exact"
mapfile -t targets < "$work/targets-exact"
[ ${#targets[@]} -gt 0 ] || { echo 'No managed packages installed.'; exit 0; }
# Simulation still runs while original holds and marks are intact.
apt-get -s --allow-change-held-packages install "${targets[@]}" > "$work/simulation"
cat "$work/simulation"
python3 "$here/managed.py" simulation < "$work/simulation"
held=()
while read -r name; do
  for package in "${installed[@]}"; do
    if [ "$name" = "$package" ] || [ "$name" = "${package%:*}" ]; then
      held+=("$name"); break
    fi
  done
done < "$work/holds"
restore_marks() {
  local status=$?
  [ ${#auto[@]} -eq 0 ] || apt-mark auto "${auto[@]}" >/dev/null
  if [ "$status" -ne 0 ] && [ ${#held[@]} -gt 0 ]; then
    apt-mark hold "${held[@]}" >/dev/null
  fi
  rm -rf -- "$work"
  exit "$status"
}
trap restore_marks EXIT
[ ${#held[@]} -eq 0 ] || apt-mark unhold "${held[@]}"
apt-get install -y "${targets[@]}"
echo 'Installed managed public families; automatic package marks preserved.'
