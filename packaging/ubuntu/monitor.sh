#!/usr/bin/env bash
# Refresh signed Ubuntu source metadata in isolation, then compare every public
# managed distribution source against its reviewed pin. Never auto-rebase.
set -euo pipefail
release=${1:-26.10}
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
docker run --rm -v "$repo:/recipe:ro" "ubuntu:$release" bash -euc '
  sed -i "s/^Types: deb$/Types: deb deb-src/" /etc/apt/sources.list.d/ubuntu.sources
  apt-get update -qq -o APT::Update::Error-Mode=any
  apt-get install -y -qq --no-install-recommends python3 >/dev/null
  python3 /recipe/packaging/ubuntu/managed.py freshness
'
