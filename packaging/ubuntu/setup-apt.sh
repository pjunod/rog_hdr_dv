#!/usr/bin/env bash
# Point this Ubuntu machine's APT at the rog_hdr_dv packages and install them.
#
#   sudo packaging/ubuntu/setup-apt.sh [FORGEJO_URL] [OWNER]
#
# Adds the registry's signing key and source, prefers its Mutter and
# libdisplay-info over Ubuntu's (priority 1001, so an Ubuntu update never
# replaces them with unpatched builds before the registry's rebuild catches
# up), releases any dpkg holds on those packages and upgrades them. The new
# Mutter takes effect at the next login.
set -euo pipefail

url=${1:-http://forge.lan:3000} owner=${2:-pjunod}
[ "$(id -u)" = 0 ] || { echo "setup-apt.sh: run with sudo" >&2; exit 1; }
codename=$(. /etc/os-release; echo "$VERSION_CODENAME")
host=${url#*://}; host=${host%%[:/]*}
registry=$url/api/packages/$owner/debian
packages="mutter mutter-common mutter-common-bin libmutter-* gir1.2-mutter-* libdisplay-info*"

install -d -m 0755 /etc/apt/keyrings
curl -fsSL "$registry/repository.key" -o /etc/apt/keyrings/rog-hdr-dv.asc
cat > /etc/apt/sources.list.d/rog-hdr-dv.sources <<EOF
Types: deb
URIs: $registry
Suites: $codename
Components: main
Signed-By: /etc/apt/keyrings/rog-hdr-dv.asc
EOF
cat > /etc/apt/preferences.d/rog-hdr-dv <<EOF
# rog_hdr_dv's HDR builds of Ubuntu's Mutter and libdisplay-info.
Package: $packages
Pin: origin "$host"
Pin-Priority: 1001
EOF

installed=$(dpkg-query -W -f '${binary:Package} ${db:Status-Abbrev}\n' 'mutter*' 'libmutter-*' \
  'gir1.2-mutter-*' 'libdisplay-info*' 2>/dev/null | awk '$2 ~ /^.i/ {print $1}')
held=$(apt-mark showhold | grep -E '^(mutter|libmutter-|gir1\.2-mutter-|libdisplay-info)' || true)
[ -z "$held" ] || apt-mark unhold $held
apt-get update
# shellcheck disable=SC2086 # one word per installed package
apt-get install -y $installed
apt-cache policy mutter libdisplay-info3 | grep -E '^[a-z]|Installed|Candidate'
