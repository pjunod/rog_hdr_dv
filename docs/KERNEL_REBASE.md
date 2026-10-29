# Kernel rebase — retain the display fixes on released Linux 7.3

Companion to [status](STATUS.md) (the running stack),
[development](DEVELOPMENT.md) (source and review rules), and
[operations](OPERATIONS.md) (deliberate installation and recovery).

**Status:** source replay, affected compilation and parser tests passed;
complete package build and boot acceptance pending.
**Written:** 2026-10-29 (America/New_York).

## Release and security evidence

[Kernel.org's release feed](https://www.kernel.org/releases.json) listed
Linux 7.3 as `latest_stable` on October 29. The series targets the released
`v7.3` tag, not a release candidate or linux-next. The exact base, full
candidate tree, ordered patches and hashes are in [sources.json](../sources.json)
and [SHA256SUMS](../SHA256SUMS).

The [upstream CVE-2026-98432 fix](https://github.com/torvalds/linux/commit/e3f33b0a1d89d738e2b913dab519226eaf76e15b)
changes IPv4 socket-option teardown to defer freeing until RCU readers
finish. Both corrected statements exist in pristine 7.3 and remain unchanged
after applying the display patches:

- `inet_sock_destruct()` in `net/ipv4/af_inet.c` uses `kfree_rcu()`.
- `tcp_v4_reqsk_destructor()` in `net/ipv4/tcp_ipv4.c` uses `kfree_rcu()`.

The inspected running `7.3.0-rc6-nativehdr2+` lacks both changes. Its GNU
build ID from `/sys/kernel/notes` equals the installed image's extracted
ELF ID, so that conclusion refers to the actual running build. No livepatch
overrides the functions. Raw machine captures stay outside this public repo.

## Display changes retained

| Patch | Purpose |
|---|---|
| 0001 | Read native DisplayID luminance into DRM connector information |
| 0002 | Let Intel AUX brightness consume the native luminance range |
| 0003 | Reject invalid physical luminance, revisions and malformed ranges |
| 0004 | Exercise native luminance parsing through the normal EDID iterator |
| 0005 | Preserve i915 set-context latency when VRR disables PSR |

The first four come from the recorded main series. Patch 0005 comes from
`claude/i915-vrr-fastset`, repository commit `a83638c`. Authors and author
dates are retained; no human signoff or upstream acceptance was added.
All five applied without conflicts to full 7.3 source. Independent review
then corrected patch 0005 to validate PSR setup timing before recording VRR
as the reason PSR is disabled. Without that ordering, an ineligible mode
could change set-context latency when VRR toggles and reproduce the original
page-flip failure. Re-review approved the corrected source for compilation.
The first four retain their original stable patch IDs; patch 0005 differs
by this disclosed correction. The upstream submission kit remains a separate
proposal with its own base and receipts.

## Build configuration and acceptance

The replacement release is `7.3.0-nativehdr3`. Configuration starts from
the running kernel's `/boot/config-*` and uses `olddefconfig` against 7.3.
Existing upstream hardware options are retained; `localmodconfig` is not used.

Two upstream/Ubuntu differences need deliberate choices:

- Upstream lacks Ubuntu's automatic Secure Boot lockdown option. Select
  `LOCK_DOWN_KERNEL_FORCE_INTEGRITY=y` to retain the running integrity
  policy. This also enforces integrity if that kernel boots without Secure
  Boot. Leave early lockdown and module signature support enabled.
- Upstream Binder IPC and binderfs are booleans rather than Ubuntu's
  tristates. Select both as built-ins, keeping the empty default device
  list, rather than silently losing their support at `olddefconfig`.

Ubuntu-only AAEON, EtherCAT, Ubuntu-host and version-signature settings have
no upstream counterpart. Their removal is recorded in the private config
diff. The core ASUS WMI, ASUS Armoury, Intel and NVIDIA compatibility checks
remain part of qualification; a source replay alone does not prove them.

Compile in a fresh owned output slot with the fixed unprivileged native
x86_64 wrapper. The compiler environment is Ubuntu 26.10 with GCC 15.3;
task-local HOME/XDG/TMPDIR and the shared compiler cache keep generated
files separate from source and recovery material. The source tree must
match the manifest before building.

The package build retains DWARF and BTF configuration but excludes the large
debug-symbol package through the upstream packaging profile:

```bash
make -C "$KERNEL_SOURCE" O="$KERNEL_BUILD" -j12 \
  CC='ccache gcc' LOCALVERSION= KDEB_PKGVERSION=7.3.0-1+nativehdr3 \
  DEB_BUILD_PROFILES=pkg.linux-upstream.nokerneldbg bindeb-pkg
```

**How to read the evidence:** patch replay proves source application;
warnings-enabled DRM/i915/xe compilation checks the changed display paths;
the focused `drm_displayid_luminance` KUnit suite checks parser behavior.
A complete package build plus an NVIDIA build against the delivered headers
is required before installation. Verify the two IPv4 destructor functions
in the resulting binary as well as the source. Record actual results and
limitations in a source-bound receipt; do not inherit the rc5/rc6 build pass.

## Qualification receipt

The [source-bound receipt](../evidence/kernel-7.3-rebase.json) records
the exact candidate and private-log hashes. Fresh export replay reproduced
the recorded tree. All five affected DRM/i915/shared-xe objects compiled
with `W=1` and zero warnings. All four focused parser KUnit tests passed.
Complete package, binary CVE and delivered-header NVIDIA checks are still
pending; installation and physical boot acceptance are separate.

## Installation and recovery

Keep the current signed test kernel and a stock kernel available. Before
installing, verify `/boot` space, the enrolled signing certificate, image
signature, module trust, NVIDIA modules, initramfs and the saved boot entry.
Build-time autogenerated signing material stays private and never replaces
the enrolled machine key.

Installation and a reboot require the coordinated window described in
[operations](OPERATIONS.md). After boot, confirm `uname -r`, the running
build ID, integrity lockdown, NVIDIA loading and HDR/VRR behavior. A new
image sitting in a package or under `/boot` does not fix the running kernel.
No compositor or display-library update is part of this kernel rebase.
