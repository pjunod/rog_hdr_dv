# Review notes for `code.diff`

These notes explain the change for the author's own line-by-line review. They
are not a commit message or an MR description; NetworkManager requires the
author to write those.

## The problem it addresses

With a hard NFS mount, a task in a buffered read can be sleeping in
`folio_wait_bit_common` (from `filemap_read` under `nfs_file_read`) on a page
that only an outstanding READ RPC will unlock. That wait is `TASK_KILLABLE`,
not freezable. NetworkManager handles logind's `PrepareForSleep` in
`do_sleep_wake()` by taking every managed hardware device down. If that device
carries the NFS traffic, the READ can never complete, the task never freezes,
and the kernel aborts the suspend after the freezer timeout with `-EBUSY`.
NFS's own RPC waits are freezable; the folio wait is not. With the link still
up, the same task freezes in milliseconds. The reproducer and the logs are in
[the diagnosis](../../../docs/SUSPEND_NFS_READER.md).

`do_sleep_wake()` already skips devices whose driver reports Wake-on-LAN/WLAN,
and on wake unmanages them once to re-check connectivity. The change routes
devices that carry a network filesystem through that same existing path.

## The code, region by region

- **`NMManagerPrivate.sleep_netfs_ifindexes`**: the set of ifindexes kept up at
  suspend. It is computed once per suspend and freed on wake and in `dispose()`.
  Remembering the set means wake re-checks exactly the devices that were skipped,
  even if a mount went away while asleep.
- **`netfs_add_link()`**: adds an ifindex, then its `parent` (VLAN, MACsec and
  similar) and every link whose `controller` is it (bridge or bond ports),
  recursively, depth-limited to 4. Without it, a server reached through `br0`
  keeps `br0` (a software device, skipped anyway) but loses the hardware port.
- **`network_filesystem_ifindexes()`**: reads `/proc/1/mountinfo`. NetworkManager's
  systemd unit runs in its own mount namespace, so the init namespace is the
  view that matters; it falls back to `/proc/self/mountinfo`. For each `nfs`,
  `nfs4`, `cifs` or `smb3` mount it takes the `addr=` super-option. The prefix
  test does not match `clientaddr=`, because options are compared from their
  start. An IPv6 link-local address printed as `fe80::1%ifname` is split, and
  the scope interface is passed as the route lookup's `oif`. It then calls
  `nm_platform_ip_route_get()` and adds the resulting ifindex.
- **`device_in_ifindex_set()`**: matches a device by `nm_device_get_ifindex()`
  or `nm_device_get_ip_ifindex()`. Bridge and bond ports have an ifindex but no
  IP ifindex.
- **`do_sleep_wake()`, suspending**: computes the set, then skips matching
  devices right after the Wake-on-LAN check, with a debug log line.
- **`do_sleep_wake()`, waking**: matching devices get the same belated
  `NM_UNMANAGED_MANAGER_DISABLED` as Wake-on-LAN devices, then the set is freed.

## Known limits worth stating in review

- A server reached through a VPN tunnel: the tunnel is a software device, and
  the underlay is not derived from the VPN endpoint's route.
- The route lookup uses the kernel's default routing for the server address
  (no source address, fwmark or oif except for IPv6 scope). Policy routing that
  sends the NFS socket elsewhere is not modelled.
- The mount table is read and parsed on the main loop once per suspend.
- There is no unit test of the new functions. The evidence is the VM harness and
  one real suspend on the Ubuntu 1.58.1 backport.
