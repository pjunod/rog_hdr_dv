#!/bin/bash
for s in ${@:-stock patched patched-nomount}; do
  rm -f /w/vm/a.sock /w/vm/b.sock
  timeout 900 qemu-system-x86_64 -enable-kvm -m 4096 -smp 2 -nographic -no-reboot \
    -kernel /w/vm/vmlinuz -initrd /w/vm/initrd.img -drive file=/w/vm/root.img,format=raw,if=virtio,snapshot=on \
    -netdev dgram,id=n0,local.type=unix,local.path=/w/vm/a.sock,remote.type=unix,remote.path=/w/vm/b.sock \
    -device virtio-net-pci,netdev=n0,mac=52:54:00:00:00:01 \
    -netdev dgram,id=n1,local.type=unix,local.path=/w/vm/b.sock,remote.type=unix,remote.path=/w/vm/a.sock \
    -device virtio-net-pci,netdev=n1,mac=52:54:00:00:00:02 \
    -append "root=/dev/vda rw console=ttyS0 init=/nm-init.sh scenario=$s net.ifnames=0 panic=1 quiet" \
    -serial file:/w/vm/serial-$s.log -monitor none -display none >/dev/null 2>&1
  echo "$s exit=$?"; grep REPRO /w/vm/serial-$s.log
done
