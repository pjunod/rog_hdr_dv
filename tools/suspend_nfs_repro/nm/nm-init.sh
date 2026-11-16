#!/bin/sh
# PID 1 in the NetworkManager suspend test VM. scenario=stock|patched|patched-nomount
mount -t proc proc /proc; mount -t sysfs sys /sys; mount -t devtmpfs dev /dev; mount -t tmpfs tmp /run; mount -t tmpfs tmp /tmp
mkdir -p /run/dbus /run/rpcbind /var/lib/nfs/v4recovery /mnt/nfs /proc/fs/nfsd
SCEN=$(sed -n 's/.*scenario=\([a-z-]*\).*/\1/p' /proc/cmdline)
log() { echo "REPRO $*" > /dev/ttyS0; }
fin() { log DONE; echo o > /proc/sysrq-trigger; sleep 60; }
log "kernel $(uname -r) scenario $SCEN"
case "$SCEN" in patched*) dpkg -i /debs/*.deb > /dev/null 2>&1 || log "dpkg -i failed";; esac
log "NetworkManager $(dpkg-query -W -f='${Version}' network-manager)"
for m in veth nfsd nfsv4 sch_tbf virtio_net; do modprobe $m 2>/dev/null; done
/usr/lib/systemd/systemd-udevd --daemon; udevadm trigger; udevadm settle
ip link set lo up
ip netns add srv; ip link set eth1 netns srv
ip -n srv addr add 192.0.2.1/24 dev eth1; ip -n srv link set eth1 up; ip -n srv link set lo up
dd if=/dev/urandom of=/srv/big bs=1M count=1536 status=none
ip netns exec srv sh -c 'mount -t nfsd nfsd /proc/fs/nfsd; echo 10 > /proc/fs/nfsd/nfsv4gracetime; echo 10 > /proc/fs/nfsd/nfsv4leasetime; exportfs -o rw,no_root_squash,insecure,fsid=0,no_subtree_check 192.0.2.0/24:/srv; rpc.nfsd -N 3 -V 4.1 8; rpc.mountd -N 3'
ip netns exec srv tc qdisc add dev eth1 root tbf rate 200mbit burst 64kb latency 50ms
dbus-daemon --system --fork
mkdir -p /etc/NetworkManager/system-connections
printf '[main]\nplugins=keyfile\nauth-polkit=false\n[logging]\nlevel=DEBUG\ndomains=SUSPEND,DEVICE,CORE\n' > /etc/NetworkManager/NetworkManager.conf
printf '[connection]\nid=c\ntype=ethernet\ninterface-name=eth0\n[ipv4]\nmethod=manual\naddress1=192.0.2.2/24\n[ipv6]\nmethod=disabled\n' > /etc/NetworkManager/system-connections/c.nmconnection
chmod 600 /etc/NetworkManager/system-connections/c.nmconnection
mkdir -p /etc/NetworkManager/conf.d; printf '[keyfile]\nunmanaged-devices=none\n' > /etc/NetworkManager/conf.d/99-test-managed.conf
NetworkManager --no-daemon > /run/nm.log 2>&1 &
for i in $(seq 1 30); do [ "$(nmcli -t -f DEVICE,STATE dev 2>/dev/null | grep '^eth0:')" = "eth0:connected" ] && break; sleep 1; done
log "conf.d: $(ls /usr/lib/NetworkManager/conf.d /etc/NetworkManager/conf.d | tr '\n' ' ')"
log "eth0 before: $(nmcli -t -f DEVICE,STATE dev | grep ^eth0:) $(ip -br addr show eth0)"
sleep 10
if [ "$SCEN" != patched-nomount ]; then
  mount -t nfs4 -o vers=4.1,hard,proto=tcp,nconnect=8,timeo=600,retrans=2 192.0.2.1:/ /mnt/nfs || { log "mount failed"; fin; }
  sync; echo 3 > /proc/sys/vm/drop_caches
  dd if=/mnt/nfs/big of=/dev/null bs=1M & R=$!
  sleep 4
  log "reader wchan=$(cat /proc/$R/wchan)"
fi
busctl call org.freedesktop.NetworkManager /org/freedesktop/NetworkManager org.freedesktop.NetworkManager Sleep b true || log "Sleep(true) failed"
sleep 4
log "eth0 after Sleep(true): $(nmcli -t -f DEVICE,STATE dev | grep ^eth0:) $(ip -br addr show eth0)"
grep -E "sleep: |carries a network filesystem|wake-on-lan" /run/nm.log | tail -4 | while read l; do log "nm: $l"; done
echo 1 > /sys/power/pm_debug_messages; echo freezer > /sys/power/pm_test; dmesg -C
F0=$(cat /sys/power/suspend_stats/failed_freeze)
echo freeze > /sys/power/state; RC=$?
log "pm_test=freezer rc=$RC failed_freeze $F0 -> $(cat /sys/power/suspend_stats/failed_freeze) errno=$(cat /sys/power/suspend_stats/last_failed_errno)"
dmesg | grep -E "Freezing user space|task:" | while read l; do log "dmesg: $l"; done
busctl call org.freedesktop.NetworkManager /org/freedesktop/NetworkManager org.freedesktop.NetworkManager Sleep b false || log "Sleep(false) failed"
for i in $(seq 1 30); do [ "$(nmcli -t -f DEVICE,STATE dev | grep '^eth0:')" = "eth0:connected" ] && break; sleep 1; done
log "eth0 after wake: $(nmcli -t -f DEVICE,STATE dev | grep ^eth0:) after ${i}s"
grep -E "sleep: waking|unmanaged" /run/nm.log | grep -i eth0 | tail -3 | while read l; do log "nm: $l"; done
if [ -n "$R" ]; then
  for i in $(seq 1 60); do kill -0 $R 2>/dev/null || break; sleep 1; done
  wait $R 2>/dev/null; log "reader finished=$(kill -0 $R 2>/dev/null && echo no || echo yes) exit=$? after ${i}s"
fi
fin
