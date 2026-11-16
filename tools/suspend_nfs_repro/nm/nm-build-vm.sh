#!/bin/bash
# Inside ubuntu:26.10: build /w/vm/root.img with stock NetworkManager plus the patched debs in /debs.
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends linux-image-generic initramfs-tools nfs-kernel-server nfs-common iproute2 kmod procps e2fsprogs qemu-system-x86 network-manager udev dbus systemd >/dev/null
V=$(ls /lib/modules | sort -V | tail -1); mkdir -p /w/vm; cp /boot/vmlinuz-$V /w/vm/vmlinuz; cp /boot/initrd.img-$V /w/vm/initrd.img
R=/w/vm/rootfs; rm -rf $R; mkdir $R
for d in bin sbin lib lib64 usr etc var; do [ -e /$d ] && cp -a /$d $R/; done
mkdir -p $R/{proc,sys,dev,run,tmp,mnt,srv,root,debs}
cp /w/debs/*.deb $R/debs/
install -m 755 /w/nm-init.sh $R/nm-init.sh
rm -f /w/vm/root.img; mkfs.ext4 -q -d $R /w/vm/root.img 8G; rm -rf $R
echo "built kernel $V NM $(dpkg-query -W -f='${Version}' network-manager)"
