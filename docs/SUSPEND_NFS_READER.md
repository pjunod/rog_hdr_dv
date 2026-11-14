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

The mount used hard NFS 4.1 over TCP with a 60-second initial request timeout.
Hard requests retry indefinitely; the retransmission setting does not turn
them into bounded reads. [NFS option semantics](https://man7.org/linux/man-pages/man5/nfs.5.html).
A transport-dependent read can therefore outlast the freezer budget. The
captured stack does not prove which folio branch, held lock or outstanding
RPC caused this instance, nor whether server latency preceded disconnection.

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
First establish the exact-source compiler loop and a small ordinary read-only
NFS reproducer in an isolated lab. Audit wait and lock lifetimes before
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
