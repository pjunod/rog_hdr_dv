#!/usr/bin/env bash
# Build one patched Ubuntu desktop package from Ubuntu's source, in a clean
# container.
#
#   packaging/ubuntu/build.sh PACKAGE OUT [--release 26.10] [--arch amd64|i386]
#                             [--version V] [--with DIR]
#
# PACKAGE is mutter or libdisplay-info; --version picks Ubuntu's source
# version (default: the newest Ubuntu publishes). The series in
# patches/ubuntu-PACKAGE is applied on top of Ubuntu's source with its own
# patches applied; the series' historical debian/changelog entries are left
# out, and one entry is written for this build instead. The version is
# Ubuntu's version followed by +nativehdrN, N from packaging/ubuntu/REVISION.
#
# --with installs the .debs in DIR first: Mutter builds against the patched
# libdisplay-info.
#
# amd64 builds the source package and every binary package. i386 cross-builds
# the architecture-dependent packages only: Ubuntu keeps the i386
# libdisplay-info3 for 32-bit programs, and a Multi-Arch: same library must
# carry the same version on both architectures.
set -euo pipefail

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[ $# -ge 2 ] || usage
pkg=$1 out=$2; shift 2
release=26.10 arch=amd64 with= source_version=
while [ $# -gt 0 ]; do
  case $1 in
    --release) release=$2; shift 2 ;;
    --arch) arch=$2; shift 2 ;;
    --version) source_version=$2; shift 2 ;;
    --with) with=$(cd "$2" && pwd); shift 2 ;;
    *) usage ;;
  esac
done
case $pkg in mutter|libdisplay-info) ;; *) echo "build.sh: unknown package $pkg" >&2; exit 2 ;; esac
case $arch in amd64|i386) ;; *) echo "build.sh: unknown arch $arch" >&2; exit 2 ;; esac
[ "$arch" = amd64 ] || [ "$pkg" = libdisplay-info ] || {
  echo "build.sh: only libdisplay-info has an i386 build" >&2; exit 2; }

repo=$(cd "$(dirname "$0")/../.." && pwd)
patches=$repo/patches/ubuntu-$pkg
[ -f "$patches/series" ] || { echo "build.sh: no series in $patches" >&2; exit 1; }
revision=$(tr -d '[:space:]' < "$repo/packaging/ubuntu/REVISION")
commit=$(git -C "$repo" rev-parse --short=12 HEAD)
commit_epoch=$(git -C "$repo" log -1 --format=%ct)
if [ -n "$(git -C "$repo" status --porcelain -- patches packaging)" ]; then
  commit="$commit+local"
fi
mkdir -p "$out"
out=$(cd "$out" && pwd)

docker run --rm -i \
  -e PKG="$pkg" -e ARCH="$arch" -e REVISION="$revision" -e SOURCE_VERSION="$source_version" \
  -e COMMIT="$commit" -e COMMIT_EPOCH="$commit_epoch" \
  -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
  -v "$patches:/patches:ro" -v "$out:/out" ${with:+-v "$with:/with:ro"} \
  "ubuntu:$release" bash -s <<'CONTAINER'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources
printf 'Acquire::Retries "5";\n' > /etc/apt/apt.conf.d/80-retries
[ "$ARCH" = i386 ] && dpkg --add-architecture i386
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  build-essential ca-certificates devscripts dpkg-dev fakeroot git libdistro-info-perl >/dev/null
[ "$ARCH" = i386 ] && apt-get install -y -qq --no-install-recommends crossbuild-essential-i386 >/dev/null

mkdir /work && cd /work
apt-get source -qq "$PKG${SOURCE_VERSION:+=$SOURCE_VERSION}" >/work/source.log 2>&1 \
  || { cat /work/source.log >&2; echo "build.sh: no source for $PKG $SOURCE_VERSION" >&2; exit 1; }
cd "$(find . -mindepth 1 -maxdepth 1 -type d -name "$PKG-*" | head -1)"
ubuntu_version=$(dpkg-parsechangelog -SVersion)
ubuntu_epoch=$(dpkg-parsechangelog -STimestamp)

applied=0
while IFS= read -r patch || [ -n "$patch" ]; do
  case $patch in ''|'#'*) continue ;; esac
  # git apply, not patch: the series carries binary test fixtures. Each
  # patch's own changelog entry named an earlier build; this build writes
  # its own below.
  git apply -p1 --exclude=debian/changelog --whitespace=nowarn "/patches/$patch" \
    || { echo "build.sh: $patch does not apply to $PKG $ubuntu_version" >&2; exit 1; }
  applied=$((applied + 1))
done < /patches/series

# Build dependencies of the patched tree, after any packages it needs from
# this repository.
if [ -d /with ]; then
  apt-get install -y -qq --no-install-recommends $(ls /with/*_amd64.deb | grep -v -- -bin_) >/dev/null
fi
apt-get build-dep -y -qq $([ "$ARCH" = i386 ] && echo "-a i386") ./ >/dev/null

version="$ubuntu_version+nativehdr$REVISION"
codename=$(. /etc/os-release; echo "$VERSION_CODENAME")
DEBFULLNAME="rog_hdr_dv" DEBEMAIL="noreply@rog-hdr-dv.invalid" \
  dch -v "$version" -D "$codename" --force-distribution \
  "Ubuntu $ubuntu_version with the rog_hdr_dv HDR series ($applied patches, patches/ubuntu-$PKG at $COMMIT)."
# Date the entry by the later of the commit and Ubuntu's entry, never the
# clock: the amd64 and i386 builds of a Multi-Arch: same library must ship
# identical changelogs, and an entry must not predate the one below it.
epoch=$(( COMMIT_EPOCH > ubuntu_epoch ? COMMIT_EPOCH : ubuntu_epoch ))
sed -i "0,/^ -- /s/^\( -- .*>\)  .*/\1  $(date -R -u -d "@$epoch")/" debian/changelog

options="parallel=$(nproc)"
# Mutter's tests need a display server and a session bus; a cross build
# cannot run its tests.
{ [ "$PKG" = mutter ] || [ "$ARCH" = i386 ]; } && options="$options nocheck"
if [ "$ARCH" = i386 ]; then
  DEB_BUILD_OPTIONS="$options" dpkg-buildpackage -ai386 -B -us -uc >/work/build.log 2>&1 \
    || { tail -60 /work/build.log >&2; exit 1; }
else
  DEB_BUILD_OPTIONS="$options" dpkg-buildpackage -sa -us -uc --source-option=--auto-commit \
    >/work/build.log 2>&1 || { tail -60 /work/build.log >&2; exit 1; }
fi
cd /work
# Only this build's files: apt-get source also left Ubuntu's .dsc here.
cp -- *_"$version"_*.deb *_"$version"_*.buildinfo *_"$version"_*.changes /out/
if [ "$ARCH" = amd64 ]; then
  # The source package: the .dsc and every file it lists.
  dsc=$(ls -- *_"$version".dsc)
  cp -- "$dsc" $(awk '/^Checksums-Sha256:/ {f=1; next} /^[^ ]/ {f=0} f {print $3}' "$dsc") /out/
fi
cp build.log "/out/$PKG-$ARCH-build.log"
chown -R "$HOST_UID:$HOST_GID" /out
echo "built $PKG $version ($ARCH, $applied patches)"
CONTAINER
