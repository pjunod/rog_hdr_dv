# Kernel rebase — retain the display fixes on Ubuntu’s released Linux 7.3

Companion to [status](STATUS.md) (the running stack),
[development](DEVELOPMENT.md) (source and review rules), and
[operations](OPERATIONS.md) (deliberate installation and recovery).

**Status:** source replay, review, affected compilation, four parser tests,
complete packages, packaged CVE proof and five NVIDIA modules passed.
Signing, installation and physical boot acceptance remain pending. **Written:** 2026-10-29.

## Release and security evidence

The selected base is Ubuntu’s authenticated `linux-source-7.3.0` package
`7.3.0-10.10`, the newest offered by the configured archive at inspection.
Its Makefile is released Linux 7.3: `EXTRAVERSION` is empty. Kernel.org’s
[release feed](https://www.kernel.org/releases.json) also lists 7.3 as the
latest release. The complete source payload, base/candidate trees and
ordered patch hashes are pinned in [sources.json](../sources.json) and
[SHA256SUMS](../SHA256SUMS).

The [upstream CVE-2026-98432 fix](https://github.com/torvalds/linux/commit/e3f33b0a1d89d738e2b913dab519226eaf76e15b)
defers IPv4 socket-option freeing until RCU readers finish. Both corrected
statements are present in the unmodified Ubuntu source and unchanged by
the display patches:

- `inet_sock_destruct()` in `net/ipv4/af_inet.c` uses `kfree_rcu()`.
- `tcp_v4_reqsk_destructor()` in `net/ipv4/tcp_ipv4.c` uses `kfree_rcu()`.

The inspected running `7.3.0-rc6-nativehdr2+` lacks both corrections. Its
running GNU build ID matches the installed image’s extracted ELF ID. No
livepatch overrides those functions. Raw device captures remain private.

## Why this uses Ubuntu’s source

A vanilla 7.3 preparation was superseded before deployment. It omitted
Ubuntu’s additional deny-all-unprivileged perf gate and its AppArmor
restriction on unconfined user-namespace creation. Writing a larger value
to the upstream perf sysctl does not recreate Ubuntu’s extra permission
check. Disabling namespaces globally would also change unrelated behavior.

The Ubuntu base retains those implementations naturally, as well as its
automatic Secure Boot lockdown and modular Binder support. The running
system’s persistent AppArmor configuration remains applicable. No new
policy workaround or hand-ported security patch is introduced. Postboot
checks must still confirm `perf_event_paranoid=4`,
`apparmor_restrict_unprivileged_userns=1`, and integrity lockdown.

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
dates are preserved; no human signoff or upstream acceptance was added.
All five apply without conflicts to the selected Ubuntu source.

Independent review corrected patch 0005 to validate PSR setup timing before
recording VRR as the reason PSR is disabled. Otherwise, a timing-ineligible
mode could change set-context latency on a VRR toggle and reproduce the
original page-flip failure. The corrected series passed re-review on the
Ubuntu base. The first four retain their original stable patch IDs; the
fifth differs from the deployed patch only by that disclosed correction.

## Reconstruct the complete source

Use a fresh owned Linux workspace. Download the exact `.deb` from the
manifest or the configured Ubuntu archive. Before extraction, require its
SHA-256 and the APT metadata SHA-512 to match the pins. Extract its payload
with `dpkg-deb -x`; the inner archive is
`usr/src/linux-source-7.3.0/linux-source-7.3.0.tar.bz2`. Verify its pinned
SHA-256, then extract it with one leading directory removed.

Initialise Git in that fresh source tree and use `git add -f -- .` to retain
the complete source-archive payload, including ignored source files.
Require `git write-tree` to equal `base_tree` before creating a neutral
local import commit. Apply all files from `patches/linux/series` with
`git am`, then require `HEAD^{tree}` to equal `candidate_tree`.

The import commit IDs are local preparation identities, not fetchable
Ubuntu Git revisions. Different committer metadata changes commits but must
not change either tree. Authentication here is the configured Ubuntu APT
archive and matching package metadata; no independent source-maintainer
signature or official Git-tag verification is claimed.

## Build configuration and acceptance

The replacement release is `7.3.0-nativehdr3`, package version
`7.3.0-10.10+nativehdr3`. Start with the running kernel’s configuration and
run `olddefconfig`. The urgent build targets this laptop’s Intel i915/xe
and proprietary NVIDIA path: `DRM_AMDGPU`, `DRM_RADEON` and `DRM_NOUVEAU`
are disabled to avoid compiling unused graphics stacks. Kconfig removes
their unused dependent options. The original full configuration is retained
privately for broader GPU support; `localmodconfig` is not used.

Independent review confirmed that the derived removal of hidden
`PM_GENERIC_DOMAINS` is from unused AMD providers, not Intel/ASUS power
management. ACPI PM and `PM_SLEEP` remain enabled. All Ubuntu security,
Binder and target-hardware settings remain; the other intentional changes
are the two version labels. This package does not support AMD/Radeon or
Nouveau graphics; the generic source patches remain reusable.

Use the fixed unprivileged native x86_64 wrapper with Ubuntu 26.10 and
GCC 15.3. Source, logs, HOME/XDG/TMPDIR and output slots are task-owned.
The earlier upstream attempt is preserved separately. The Ubuntu output
slot is fresh; the shared compiler cache may reuse identical compiler
inputs, rather than reusing stale objects across source replacements.

The package build retains DWARF/BTF configuration and omits only the large
debug-symbol package through the upstream packaging profile:

```bash
make -C "$KERNEL_SOURCE" O="$KERNEL_BUILD" -j20 \
  CC='ccache gcc' LOCALVERSION= KDEB_PKGVERSION=7.3.0-10.10+nativehdr3 \
  DEB_BUILD_PROFILES=pkg.linux-upstream.nokerneldbg bindeb-pkg
```

**How to read the evidence:** the [receipt](../evidence/kernel-7.3-rebase.json)
binds results to the selected Ubuntu tree. Require warnings-enabled
DRM/i915/shared-xe compilation, the four `drm_displayid_luminance` KUnit
cases, complete packages, the two RCU calls in the resulting image, and
NVIDIA compilation against the delivered headers. Results from the
superseded upstream tree do not qualify this candidate.

All selected checks passed. The actual packaged image equals the built
image and its extracted GNU build ID matches the inspected `vmlinux`.
Both IPv4 functions call `kvfree_call_rcu`. All five NVIDIA 615.71.09 modules
compile/link against the extracted header package with the expected
`7.3.0-nativehdr3` vermagic. External-module BTF generation was skipped
because normal delivered headers omit `vmlinux`; this is not a BTF pass.
The packaged i915/xe modules have matching vermagic. Their signatures
are not present; module signing and image signing remain installation
prerequisites under Secure Boot.

## Installation and recovery

Install only the versioned image and kernel-header packages. The generated
`linux-libc-dev` package is not part of this kernel deployment. Keep the
current signed test kernel and a stock kernel available. Verify boot space,
the enrolled public certificate, image signature, module trust, NVIDIA
modules, initramfs and a recoverable boot entry before selecting the new
kernel. Signing material stays private and out of Git.

Installation and reboot use the coordinated window in
[operations](OPERATIONS.md). After boot, confirm the release and running
build ID, Ubuntu security controls, NVIDIA loading and HDR/VRR transitions.
An image on disk does not fix the kernel still running. No compositor or
display-library update is part of this rebase.
