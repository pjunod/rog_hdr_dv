#!/bin/bash
# Runs inside the same image as build.sh: boot the VM once per scenario.
for s in link-up link-down; do
  timeout 600 qemu-system-x86_64 -enable-kvm -m 4096 -smp 2 -nographic -no-reboot \
    -kernel /w/vmlinuz -initrd /w/initrd.img -drive file=/w/root.img,format=raw,if=virtio,snapshot=on \
    -append "root=/dev/vda rw console=ttyS0 init=/repro-init.sh scenario=$s panic=1 quiet" \
    -serial file:/w/serial-$s.log -monitor none -display none >/dev/null 2>&1
  echo "$s exit=$?"; grep REPRO /w/serial-$s.log
done
