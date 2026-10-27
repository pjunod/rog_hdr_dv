#!/usr/bin/env bash
# Point this Ubuntu machine's APT at the rog_hdr_dv packages and install them.
#
#   sudo packaging/ubuntu/setup-apt.sh [FORGEJO_URL] [OWNER]
#
# Adds the registry's signing key and source, prefers everything in it over
# Ubuntu's packages (priority 1001: an Ubuntu update never replaces the HDR
# builds with unpatched ones before the registry's rebuild catches up, and a
# rebuild that sorts below the old build still installs), releases any dpkg
# holds on those packages and upgrades whatever of them is installed. The new
# Mutter takes effect at the next login. A release upgrade disables this
# source; run the script again afterwards so it names the new release.
set -euo pipefail

url=${1:-http://forge.lan:3000} owner=${2:-pjunod}
[ "$(id -u)" = 0 ] || { echo "setup-apt.sh: run with sudo" >&2; exit 1; }
codename=$(. /etc/os-release; echo "$VERSION_CODENAME")
host=${url#*://}; host=${host%%[:/]*}
registry=$url/api/packages/$owner/debian

install -d -m 0755 /etc/apt/keyrings
curl -fsSL "$registry/repository.key" -o /etc/apt/keyrings/rog-hdr-dv.asc
cat > /etc/apt/sources.list.d/rog-hdr-dv.sources <<EOF
Types: deb
URIs: $registry
Suites: $codename
Components: main
Signed-By: /etc/apt/keyrings/rog-hdr-dv.asc
EOF
# Every package the registry carries: it carries only these builds.
cat > /etc/apt/preferences.d/rog-hdr-dv <<EOF
# rog_hdr_dv's HDR builds of Ubuntu's Mutter and libdisplay-info.
Package: *
Pin: origin "$host"
Pin-Priority: 1001
EOF

# dpkg-query fails when a pattern matches nothing (no Mutter on a server).
installed=$({ dpkg-query -W -f '${binary:Package} ${db:Status-Abbrev}\n' 'mutter*' 'libmutter-*' \
  'gir1.2-mutter-*' 'libdisplay-info*' 2>/dev/null || true; } | awk '$2 ~ /^.i/ {print $1}')
held=$(apt-mark showhold | grep -E '^(mutter|libmutter-|gir1\.2-mutter-|libdisplay-info)' || true)
[ -z "$held" ] || apt-mark unhold $held
# Naming packages to apt-get marks them manually installed; keep the automatic
# ones automatic, so autoremove still clears them after an ABI change.
auto=$(apt-mark showauto $installed 2>/dev/null || true)
apt-get update
# shellcheck disable=SC2086 # one word per installed package
[ -z "$installed" ] || apt-get install -y $installed
[ -z "$auto" ] || apt-mark auto $auto >/dev/null
apt-cache policy mutter libdisplay-info3 | grep -E '^[a-z]|Installed|Candidate'
