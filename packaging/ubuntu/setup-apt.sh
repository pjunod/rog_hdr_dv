#!/usr/bin/env bash
# Configure exact public release families. Every failure restores the previous
# key/source/preferences (including mode, ownership, symlink and absence), holds
# and automatic marks. Successful no-op intentionally configures protection.
set -euo pipefail
url=${1:-http://forge.lan:3000} owner=${2:-pjunod}
[ "$(id -u)" = 0 ] || { echo 'setup-apt.sh: run with sudo' >&2; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
codename=$(. /etc/os-release; echo "$VERSION_CODENAME")
host=${url#*://}; host=${host%%[:/]*}
registry=$url/api/packages/$owner/debian
: "${TMPDIR:?set TMPDIR to private external task storage}"
umask 077
work=$(mktemp -d "$TMPDIR/managed-setup.XXXXXXXX")
configs=(/etc/apt/keyrings/rog-hdr-dv.asc /etc/apt/sources.list.d/rog-hdr-dv.sources /etc/apt/preferences.d/rog-hdr-dv)
auto=() held=() marks_changed=0 config_changed=0
mkdir "$work/config-backup"
for i in "${!configs[@]}"; do
  if [ -e "${configs[$i]}" ] || [ -L "${configs[$i]}" ]; then
    cp -a --no-dereference "${configs[$i]}" "$work/config-backup/$i"
  fi
done
restore_state() {
  local status=$? restore_failed=0 i
  trap - EXIT
  set +e
  if [ "$marks_changed" = 1 ]; then
    [ ${#auto[@]} -eq 0 ] || apt-mark auto "${auto[@]}" >/dev/null || restore_failed=1
    if [ "$status" -ne 0 ] && [ ${#held[@]} -gt 0 ]; then
      apt-mark hold "${held[@]}" >/dev/null || restore_failed=1
    fi
  fi
  if [ "$status" -ne 0 ] && [ "$config_changed" = 1 ]; then
    for i in "${!configs[@]}"; do
      rm -f -- "${configs[$i]}" || restore_failed=1
      if [ -e "$work/config-backup/$i" ] || [ -L "$work/config-backup/$i" ]; then
        cp -a --no-dereference "$work/config-backup/$i" "${configs[$i]}" || restore_failed=1
      fi
    done
  fi
  if [ "$restore_failed" = 0 ]; then
    rm -rf -- "$work"
  else
    echo "setup-apt.sh: state restoration incomplete; retained private recovery records: $work" >&2
    status=1
  fi
  exit "$status"
}
trap restore_state EXIT
python3 "$here/managed.py" names > "$work/names"
mapfile -t names < "$work/names"
{ dpkg-query -W -f '${Package} ${Architecture} ${Version} ${db:Status-Abbrev}\n' "${names[@]}" 2>/dev/null || true; } |
  awk '$4 ~ /^.i/ {print $1, $2, $3}' > "$work/installed"
awk '{print $1 ":" $2}' "$work/installed" > "$work/installed-names"
mapfile -t installed < "$work/installed-names"
apt-mark showhold > "$work/holds"
if [ ${#installed[@]} -gt 0 ]; then
  auto_output=$(apt-mark showauto "${installed[@]}")
  if [ -n "$auto_output" ]; then mapfile -t auto <<< "$auto_output"; fi
fi
while read -r name; do
  for package in "${installed[@]}"; do
    if [ "$name" = "$package" ] || [ "$name" = "${package%:*}" ]; then held+=("$name"); break; fi
  done
done < "$work/holds"
# Generate all replacements in private external storage first. Replace symlinks
# rather than writing through them; backups retain the original link itself.
curl -fsSL "$registry/repository.key" -o "$work/key"
cat > "$work/source" <<EOF
Types: deb
URIs: $registry
Suites: $codename
Components: main
Architectures-Add: all
Signed-By: /etc/apt/keyrings/rog-hdr-dv.asc
EOF
python3 "$here/managed.py" preferences "$host" > "$work/preferences"
install -d -m 0755 /etc/apt/keyrings /etc/apt/sources.list.d /etc/apt/preferences.d
config_changed=1
for i in "${!configs[@]}"; do rm -f -- "${configs[$i]}"; done
install -m 0644 "$work/key" "${configs[0]}"
install -m 0644 "$work/source" "${configs[1]}"
install -m 0644 "$work/preferences" "${configs[2]}"
# APT verifies Release signatures and index hashes. Failed updates/preflight
# restore the old live policy rather than leaving a failed candidate active.
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
[ ${#targets[@]} -gt 0 ] || { echo 'No managed packages installed; project source and protection configured intentionally.'; exit 0; }
apt-get -s --no-remove --allow-change-held-packages install "${targets[@]}" > "$work/simulation"
cat "$work/simulation"
python3 "$here/managed.py" simulation "$work/Packages" < "$work/simulation"
marks_changed=1
[ ${#held[@]} -eq 0 ] || apt-mark unhold "${held[@]}"
apt-get install -y --no-remove "${targets[@]}"
echo 'Installed intended public families; automatic marks preserved.'
