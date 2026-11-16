#!/bin/sh
# PID 1 inside the reproducer VM. SCENARIO comes from the kernel command line.
mount -t proc proc /proc; mount -t sysfs sys /sys; mount -t devtmpfs dev /dev; mount -t tmpfs tmp /run; mount -t tmpfs tmp /tmp
mkdir -p /run/rpcbind /var/lib/nfs/v4recovery /mnt/nfs /proc/fs/nfsd
SCEN=$(sed -n 's/.*scenario=\([a-z-]*\).*/\1/p' /proc/cmdline)
log() { echo "REPRO $*" > /dev/ttyS0; }
log "kernel $(uname -r) scenario $SCEN"
for m in veth nfsd nfsv4 sch_tbf; do modprobe $m || log "modprobe $m failed"; done
ip link set lo up
ip netns add srv
ip link add c0 type veth peer name s0; ip link set s0 netns srv
ip addr add 192.0.2.2/24 dev c0; ip link set c0 up
ip -n srv addr add 192.0.2.1/24 dev s0; ip -n srv link set s0 up; ip -n srv link set lo up
mkdir -p /srv/data; dd if=/dev/urandom of=/srv/data/big bs=1M count=1536 status=none
ip netns exec srv sh -c 'mount -t nfsd nfsd /proc/fs/nfsd; echo 10 > /proc/fs/nfsd/nfsv4gracetime; echo 10 > /proc/fs/nfsd/nfsv4leasetime; exportfs -o rw,no_root_squash,insecure,fsid=0,no_subtree_check 192.0.2.0/24:/srv/data; rpc.nfsd -N 3 -V 4.1 8; rpc.mountd -N 3'
ip netns exec srv tc qdisc add dev s0 root tbf rate 200mbit burst 64kb latency 50ms
sleep 12
mount -t nfs4 -o vers=4.1,hard,proto=tcp,nconnect=8,timeo=600,retrans=2 192.0.2.1:/ /mnt/nfs || { log "mount failed"; log DONE; echo o > /proc/sysrq-trigger; }
log "mounted $(grep /mnt/nfs /proc/mounts)"
mount -t debugfs debugfs /sys/kernel/debug
sync; echo 3 > /proc/sys/vm/drop_caches
echo 1 > /sys/power/pm_debug_messages
log "pm_freeze_timeout=$(cat /sys/power/pm_freeze_timeout) ms"
dd if=/mnt/nfs/big of=/dev/null bs=1M & R=$!
sleep 4
log "reader pid $R read_bytes=$(awk '/read_bytes/{print $2}' /proc/$R/io)"
case "$SCEN" in
  link-down) ip addr flush dev c0; ip link set c0 down; log "transport down: addresses flushed, link down (as NetworkManager deactivation does)";;
  link-up) log "transport left up";;
esac
sleep 3
log "reader wchan=$(cat /proc/$R/wchan) state=$(awk '/State/{print $2}' /proc/$R/status)"
log "reader stack: $(cat /proc/$R/stack 2>/dev/null | head -8 | tr '\n' '|')"
log "outstanding RPC tasks: $(cat /sys/kernel/debug/sunrpc/rpc_clnt/*/tasks 2>/dev/null | grep -c READ) READ, $(cat /sys/kernel/debug/sunrpc/rpc_clnt/*/tasks 2>/dev/null | wc -l) total"
cat /sys/kernel/debug/sunrpc/rpc_clnt/*/tasks 2>/dev/null | head -4 | while read l; do log "rpc: $l"; done
dmesg -C
echo freezer > /sys/power/pm_test
F0=$(cat /sys/power/suspend_stats/failed_freeze)
echo freeze > /sys/power/state; RC=$?
log "pm_test=freezer state=freeze rc=$RC failed_freeze $F0 -> $(cat /sys/power/suspend_stats/failed_freeze) last_failed_errno=$(cat /sys/power/suspend_stats/last_failed_errno 2>/dev/null)"
dmesg | grep -v -E "^\[ *[0-9.]+\] +(\[<|Call Trace|<TASK>|</TASK>| [a-z_]+\+0x)" | head -30 | while read l; do log "dmesg: $l"; done
dmesg | grep -E "^\[ *[0-9.]+\] +[a-z_]+\+0x" | head -12 | while read l; do log "dmesg-trace: $l"; done
log "reader alive=$(kill -0 $R 2>/dev/null && echo yes || echo no)"
log DONE
echo o > /proc/sysrq-trigger
