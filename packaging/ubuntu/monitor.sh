#!/usr/bin/env bash
# Signed Ubuntu source AND project binary publication freshness. Never rebase,
# publish, or rewrite host APT state; the bounded container is disposable.
set -euo pipefail
release=${1:-26.10}
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
export FORGEJO_URL=${FORGEJO_URL:-http://forge.lan:3000}
export FORGEJO_OWNER=${FORGEJO_OWNER:-pjunod}
docker run --rm --cpus=2 --memory=1g --memory-swap=1g --pids-limit=256 \
  -e FORGEJO_URL -e FORGEJO_OWNER -v "$repo:/recipe:ro" "ubuntu:$release" bash -euc '
  sed -i "s/^Types: deb$/Types: deb deb-src/" /etc/apt/sources.list.d/ubuntu.sources
  dpkg --add-architecture i386
  apt-get update -qq -o APT::Update::Error-Mode=any
  apt-get install -y -qq --no-install-recommends python3 ca-certificates curl >/dev/null
  registry=$FORGEJO_URL/api/packages/$FORGEJO_OWNER/debian
  . /etc/os-release
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL "$registry/repository.key" -o /etc/apt/keyrings/rog-hdr-dv.asc
  printf "Types: deb\nURIs: %s\nSuites: %s\nComponents: main\nArchitectures-Add: all\nSigned-By: /etc/apt/keyrings/rog-hdr-dv.asc\n" \
    "$registry" "$VERSION_CODENAME" > /etc/apt/sources.list.d/rog-hdr-dv.sources
  apt-get update -qq -o APT::Update::Error-Mode=any
  python3 /recipe/packaging/ubuntu/managed.py freshness --registry "$registry"
'
