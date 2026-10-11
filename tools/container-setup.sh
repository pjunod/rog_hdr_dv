#!/bin/sh
# Prepare a disposable Ubuntu 26.10 container for building and testing the
# libdisplay-info and Mutter series. Run as root inside the container only;
# it changes the container's package state, never a host or a laptop.
#
# Optional: HTTPS_PROXY (and CA_BUNDLE for a proxy's CA) when the container
# reaches the archive through a proxy.
set -eu
export DEBIAN_FRONTEND=noninteractive
sed -i 's#http://archive.ubuntu.com#https://archive.ubuntu.com#; s#http://security.ubuntu.com#https://security.ubuntu.com#; s#^Types: deb$#Types: deb deb-src#' /etc/apt/sources.list.d/ubuntu.sources
if [ -n "${HTTPS_PROXY:-}" ]; then
    printf 'Acquire::https::Proxy "%s";\n' "$HTTPS_PROXY" > /etc/apt/apt.conf.d/90proxy
    if [ -n "${CA_BUNDLE:-}" ]; then
        printf 'Acquire::https::CaInfo "%s";\n' "$CA_BUNDLE" >> /etc/apt/apt.conf.d/90proxy
        git config --global http.sslCAInfo "$CA_BUNDLE" 2>/dev/null || true
    fi
fi
apt-get update -q
apt-get install -y -q --no-install-recommends ca-certificates build-essential devscripts \
    dpkg-dev equivs git python3 meson ninja-build pkg-config hwdata quilt fakeroot \
    uncrustify wayland-protocols libwayland-dev
apt-get build-dep -y -q mutter libdisplay-info
if [ -n "${HTTPS_PROXY:-}" ]; then git config --global http.proxy "$HTTPS_PROXY"; fi
echo "container ready"
