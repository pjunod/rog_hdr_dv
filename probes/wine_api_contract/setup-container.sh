#!/bin/sh
# Prepare only this new disposable compiler/runtime; no Wine execution.
set -eu
probe_container=rog-wine-api-contract
probe_base=ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
# Docker rejects a name collision; never reuse, delete or start an old container.
docker run -d --name "$probe_container" --label purpose=rog-wine-api-contract \
    "$probe_base" sleep infinity
docker exec -i "$probe_container" sh -s <<'SETUP'
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
  g++-mingw-w64-x86-64-posix=13.2.0-6ubuntu1+26.1 \
  mingw-w64-x86-64-dev=11.0.1-3build1 \
  binutils-mingw-w64-x86-64=2.41.90.20240122-1ubuntu1+11.4 \
  ca-certificates curl gnupg
mkdir -p /probe /etc/apt/keyrings
printf '#include <stdio.h>\nint main(void) { puts("compiler-loop"); return 0; }\n' \
  >/probe/hello.c
x86_64-w64-mingw32-gcc -std=c11 -Wall -Wextra -Werror \
  /probe/hello.c -o /probe/hello.exe
x86_64-w64-mingw32-objdump -f /probe/hello.exe
curl -fsSL --proto '=https' --max-time 30 \
  https://dl.winehq.org/wine-builds/winehq.key \
  -o /etc/apt/keyrings/winehq-archive.key
curl -fsSL --proto '=https' --max-time 30 \
  https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources \
  -o /etc/apt/sources.list.d/winehq-noble.sources
sha256sum -c - <<'HASHES'
d965d646defe94b3dfba6d5b4406900ac6c81065428bf9d9303ad7a72ee8d1b8  /etc/apt/keyrings/winehq-archive.key
b5962429ece1f831c9f713c13f9f0d26bb367117ef56706648ff385f004779fb  /etc/apt/sources.list.d/winehq-noble.sources
HASHES
dpkg --add-architecture i386
apt-get update -qq
apt-get install -y --no-install-recommends \
  winehq-stable=11.0.0.0~noble-1 wine-stable=11.0.0.0~noble-1 \
  wine-stable-amd64=11.0.0.0~noble-1 wine-stable-i386:i386=11.0.0.0~noble-1
dpkg-query -W >/probe/package-manifest.txt
sha256sum /probe/package-manifest.txt
SETUP
# Successful preparation leaves the new container offline, without Wine/prefix.
docker network disconnect bridge "$probe_container"
[ "$(docker inspect -f '{{len .NetworkSettings.Networks}}' "$probe_container")" = 0 ]
