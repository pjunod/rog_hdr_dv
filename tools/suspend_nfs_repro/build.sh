#!/bin/bash
# Runs inside ubuntu:26.10. Builds /w/root.img from this container's filesystem plus kernel and NFS tools.
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends linux-image-generic initramfs-tools nfs-kernel-server nfs-common iproute2 kmod procps e2fsprogs qemu-system-x86 >/dev/null
V=$(ls /lib/modules | sort -V | tail -1); K=/boot/vmlinuz-$V; I=/boot/initrd.img-$V
cp $K /w/vmlinuz; cp $I /w/initrd.img
rm -rf /w/rootfs; mkdir /w/rootfs
for d in bin sbin lib lib64 usr etc var; do [ -e /$d ] && cp -a /$d /w/rootfs/; done
mkdir -p /w/rootfs/{proc,sys,dev,run,tmp,mnt,srv,root}
install -m 755 /w/repro-init.sh /w/rootfs/repro-init.sh
rm -f /w/root.img; mkfs.ext4 -q -d /w/rootfs /w/root.img 6G
rm -rf /w/rootfs
echo "kernel $(basename $K)"
