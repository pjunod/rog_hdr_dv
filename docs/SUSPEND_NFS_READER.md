# Suspend with an NFS reader — why the attended attempts did not sleep

Companion to [Status](STATUS.md) and [Operations](OPERATIONS.md). This records
the bounded November 13, 2026 suspend failure and the source work needed to
resolve it. It does not prescribe a host policy change or claim an upstream
submission or repair.

## The kernel stopped at the user-task freezer

One normal GNOME suspend request produced two kernel suspend/freezer attempts
within one sleep-service invocation and one NetworkManager sleep/wake cycle.
After NetworkManager took the transport down, an owned installed Showtime
player remained blocked in a hard-NFS buffered read; each kernel attempt
timed out after about 20 seconds with `-EBUSY`. The refusing thread was the media
demuxer; its stack ran through locked-folio waiting, generic buffered reads
and `nfs_file_read`. Suspend statistics recorded two freeze failures, no
failed device and no actual sleep in either attempt. Playback resumed after
the failed transition and network recovery.

This identifies the observed blocker before kernel device PM. It does not
identify a GPU suspend defect. The NVIDIA presuspend service did run, so the
failure also does not establish that no NVIDIA work occurred.

Linux requires tasks to freeze before later suspend stages and cancels the
transition when they cannot. The [kernel freezer documentation](https://www.kernel.org/doc/html/latest/power/freezing-of-tasks.html)
and [upstream timeout/error path](https://github.com/torvalds/linux/blob/v7.3-rc5/kernel/power/process.c#L24)
explain the observed timeout and error. The [NFS read path](https://github.com/torvalds/linux/blob/v7.3-rc5/fs/nfs/file.c#L151)
calls generic buffered reads; the [locked-folio wait](https://github.com/torvalds/linux/blob/v7.3-rc5/mm/filemap.c#L2420)
includes a `TASK_KILLABLE` wait, which is not the same as a freezable wait.
These upstream anchors explain the mechanism; the exact running kernel
source, patches, configuration and instruction remain necessary for a fix.

The explanatory upstream [NFS I/O bracket](https://github.com/torvalds/linux/blob/v7.3-rc5/fs/nfs/io.c#L15)
holds a shared inode `i_rwsem` until the buffered read returns. Dropping the
inner mapping lock before a folio wait therefore does not establish a
lock-free freezing point. Marking generic folio waits freezable without a
caller-lock audit is not a demonstrated repair. Relevant installed wait/freezer
headers and selected NFS/PM configuration semantics match between the older
and corrected kernels; exact implementation bodies and failed-instruction
binding remain necessary. The corrected display-kernel boot does not establish
NFS suspend acceptance.

The mount used hard NFS 4.1 over TCP with a 60-second initial request timeout.
Hard requests retry indefinitely; the retransmission setting does not turn
them into bounded reads. [NFS option semantics](https://man7.org/linux/man-pages/man5/nfs.5.html).
A transport-dependent read can therefore outlast the freezer budget. The
captured stack does not prove which folio branch, held lock or outstanding
RPC caused this instance, nor whether server latency preceded disconnection.

## Reproduced in an isolated VM (November 16)

A freezer failure with the same reader stack reproduces without the ROG.
[`tools/suspend_nfs_repro/`](../tools/suspend_nfs_repro/) boots an Ubuntu
7.3.0-10 guest under KVM, with an NFS 4.1 server in a network namespace behind
a rate-limited veth link. The client mounts it hard over TCP with the ROG's
options (`nconnect=8`, `timeo=600`). A buffered `dd` reads a large file. The
kernel freezer then runs with `pm_test=freezer` (freeze tasks, no sleep), the
default 20 s timeout, and `pm_debug_messages` on so it names refusing tasks.

| Scenario | Reader, before the freeze | Freezer |
|---|---|---|
| link left up | D in `folio_wait_bit_common` ← `filemap_read` ← `nfs_file_read`; 2 READ RPCs queued | completed in 0.039 s |
| addresses flushed and link down first, approximating NetworkManager's deactivation | same | failed after 20.007 s: the refusing task is `dd`, in the same wait, `-EBUSY` |

The only difference is whether the transport can complete the queued READs.
Runs that caught the reader in an `OPEN` RPC wait froze even with the link
down, so NFS's own RPC waits are freezable and the generic folio wait is not.
Differences from the ROG: veth rather than Wi-Fi, one mount rather than four,
and NetworkManager not running in the guest. The ROG's exact folio, held locks
and RPC state were never captured.
[Receipt](../evidence/suspend-nfs-freezer-repro-20261116.json).

NetworkManager 1.58.1's `do_sleep_wake` takes every managed hardware device
down before sleep. It skips software devices and devices whose driver currently
reports wake-on-LAN or wake-on-WLAN; its comment says those are "taken down
post-suspend rather than pre-", and in practice they are re-checked on wake. Its
sleep design therefore already allows a device to stay up through the freeze.
The ROG uses Wi-Fi, with WoWLAN supported but disabled, so its link is taken
down first.

### The fix: NetworkManager keeps network-filesystem devices up

Paul chose the NetworkManager direction on November 16. The kernel direction
(freezable folio waits in generic page-cache code) and the configuration-only
direction (wake-on-WLAN, which changes what wakes the laptop) were not taken.

[`ubuntu-network-manager-suspend`](../patches/ubuntu-network-manager-suspend/series)
patches Ubuntu's `network-manager 1.58.1-1ubuntu3` as `1.58.1-1ubuntu3+rogsleep1`.
Once per suspend, NetworkManager reads the init namespace's mount table
(`/proc/1/mountinfo`; its own unit runs in a private mount namespace). It takes
each `nfs`, `nfs4`, `cifs` or `smb3` mount's `addr=` option, including IPv6
link-local `addr%iface`, and asks the kernel which link reaches that server.
That link, its VLAN parent and its bridge or bond ports are then skipped before
sleep, as Wake-on-LAN devices already are. They are recorded, and on wake exactly
those devices are re-checked the way NetworkManager re-checks Wake-on-LAN
devices. That wake-time reset is no more disruptive than stock behaviour, which
takes them down before sleep. Devices that carry no such mount are taken down as
before.

Known limits: a server reached through a VPN tunnel keeps the tunnel's software
device but not the underlay, because the patch does not follow the VPN endpoint's
route. The lookup uses the kernel's default routing for the server address, so
source-based policy routing that steers the NFS socket elsewhere is not modelled.

The package builds with its test suite (85 OK, 0 fail); the suite has no test of
the new function. In a KVM guest
([`tools/suspend_nfs_repro/nm/`](../tools/suspend_nfs_repro/nm/)), NetworkManager
manages a virtio NIC with a static address, a hard NFS 4.1 reader is running, and
sleep is entered through NetworkManager's own `Sleep(true)` D-Bus method followed
by `pm_test=freezer`:

| NetworkManager | Topology | NFS reader | Hardware port after `Sleep(true)` | Freezer |
|---|---|---|---|---|
| stock `1.58.1-1ubuntu3` | NIC | yes | taken down | failed after 20 s, `dd` refusing, `-EBUSY` |
| `+rogsleep1` | NIC | yes | kept up | completed in 0.022 s |
| `+rogsleep1` | NIC | none | taken down, as before | completed |
| stock | bridge with the NIC as port | yes | taken down (bridge stays up) | failed after 20 s, `-EBUSY` |
| `+rogsleep1` | bridge with the NIC as port | yes | kept up | completed in 0.007 s |

In every run the link was back within 2 s of wake and the reader finished.
[Receipt](../evidence/networkmanager-suspend-netfs-20261116.json). The test did
not cover a real suspend, a driver suspend, Wi-Fi, DHCP or NetworkManager under
its systemd unit. The single ROG run below covers those once.
**One real suspend passed on the ROG (November 16).** With `+rogsleep1` installed (4 packages
upgraded, none removed; `libnm0` built for both amd64 and i386, because Steam's
32-bit libraries use it), a buffered reader on the media NFS mount was blocked in
`folio_wait_bit_common` when `systemctl suspend` ran. NetworkManager logged
`device wlo1 carries a network filesystem, skipping`. The kernel froze user space
in 0.025 s, entered s2idle and woke on an RTC alarm, and suspend statistics
recorded one success and no freeze failure. On wake NetworkManager re-checked
`wlo1`, which reconnected in about 5 s, and the reader carried on.
[Receipt](../evidence/networkmanager-suspend-rog-20261116.json). This is one
cycle, not a soak. Still to do: propose the change upstream, which needs a
freedesktop GitLab account.

## A delay inhibitor does not order consumers before NetworkManager

[NetworkManager's power monitor](https://github.com/NetworkManager/NetworkManager/blob/1.58.1/src/core/nm-power-monitor.c#L132)
takes its own delay inhibitor, receives `PrepareForSleep`, notifies its
manager and releases the inhibitor when its outstanding handles permit it.
The [manager's sleep path](https://github.com/NetworkManager/NetworkManager/blob/1.58.1/src/core/nm-manager.c#L6751)
takes hardware interfaces down. That is consistent with the observed
transport loss before kernel entry.

[logind delay inhibitors](https://systemd.io/INHIBITOR_LOCKS/) provide bounded
time before final sleep, not an ordering relationship between clients
receiving the same notification. An application callback or delay inhibitor
alone therefore cannot guarantee that media I/O quiesces before the transport
is removed, or release a read already blocked in the kernel. This conclusion
follows from the API and NetworkManager source. A consumer/transport ordering
contract would need coordinated design; an application watchdog or forced
pause/kill hook would not repair the demonstrated dependency.
[systemd's sleep-service documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd-suspend.service.html)
also distinguishes proper application integration from parallel system-sleep
hooks.

## NVIDIA's prefreeze setting is a separate contract

A preexisting installed NVIDIA integration drop-in sets
`SYSTEMD_SLEEP_FREEZE_USER_SESSIONS=false`. Its comment records a historical
Xorg/VT-switch deadlock when systemd freezes the session before a driver VT
request. This skips systemd's session-cgroup prefreeze; it does not disable
the later kernel PM freezer that failed in these attempts.

The inspected open NVIDIA driver had kernel suspend notifiers enabled. The
[exact-version NVIDIA documentation](https://download.nvidia.com/XFree86/Linux-x86_64/615.71.09/README/powermanagement.html)
distinguishes that mechanism from explicit service/proc integration. The
present necessity of the installed drop-in requires a driver/distribution
contract audit. Neither its removal nor a broader freezer override follows
from this NFS stack.

## Correct ownership and the next attended qualification

The source loop belongs with distribution NFS/MM/PM kernel maintainers and
NetworkManager/logind integration, with NVIDIA integration audited separately.
The isolated reproducer above now exists. Next, establish the exact-source compiler loop for the chosen fix. Audit wait and lock lifetimes before
considering safe filesystem cancellation/freezing behavior or a coordinated
transport lifecycle change. No source fix or upstream submission is claimed.
Soft mounts, longer freezer timeouts, blanket freezer disablement and a
keep-network policy shortcut do not establish a repair.

A new physical test needs a new coordinated owner window. A bounded comparison
of the same player and segment on an ordinary local file versus NFS can
isolate filesystem dependence while preserving normal suspend/network policy.
Capture service order, task stacks, read activity, suspend counters and
post-resume state. Local-file success would qualify only that case. NFS
acceptance requires actual sleep and resume, correct reader continuation,
normal network recovery and restored display state, with freezer, device PM
and NVIDIA results recorded separately. No such follow-up test has run.

## Ten-cycle ROG soak — November 16 protocol

The owner authorized a bounded repeated-cycle run on the installed
`+rogsleep1` package. The planned run is ten normal `systemctl suspend`
cycles, each with a 30-second RTC wake alarm, on the existing s2idle kernel.
Each cycle starts a buffered reader at a different offset of a large hard-NFS
file and must observe `folio_wait` before requesting sleep.

The acceptance checks are one new suspend success, every exposed failure
counter unchanged, at least ten seconds actually suspended measured by the
BOOTTIME-minus-MONOTONIC clock difference, unchanged boot identity and GNOME
Shell process, Wi-Fi connected within 60 seconds, and reader I/O advancing
from a fresh post-connection sample within ten seconds. The harness stops at
the first failure without retrying. It preserves private per-cycle kernel and
service journals, then restores the exact NetworkManager logging state, clears
only its own RTC alarm and terminates its owned reader.

Results are pending. This protocol does not grant a long-duration, alternate
network topology, hibernate, display-quality or upstream acceptance claim.
