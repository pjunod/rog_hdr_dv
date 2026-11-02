# Software delivery — current install and rollback handoff

Reconciled 2026-11-02 against repository main `f064e91`. This is a software
handoff, not a new display trial, optical measurement or Dolby certification.
The [APT guide](UBUNTU_APT_REPOSITORY.md), [operations](OPERATIONS.md) and
[kernel ledger](KERNEL_REBASE.md) own the actual procedures. Historical
experimental player bundles are not the current product install path.

## Installed, published and retained are different states

| Component | Current disposition | Provenance and limits |
|---|---|---|
| Mutter | APT `51.0-1ubuntu3+nativehdr13`, installed on the ROG | Ubuntu `51.0-1ubuntu3` plus 105 patches; downloaded package changelog names `479d61de3f78` |
| libdisplay-info | APT `0.3.0-1+nativehdr13`, installed as amd64 and i386 | Ubuntu `0.3.0-1` plus 23 patches; changelog names the same repository commit; retain matching versions on both architectures |
| Kernel | Signed `7.3.0-nativehdr3`, installed and running | Ubuntu `7.3.0-10.10` plus five display patches; October 29 build-ID, CVE, Secure Boot and driver checks retained, not repeated |
| Dolby Vision player | External plurx Player, installed version `0.4.1+lp7.387.0.mpv0.41.0+git20261026.e59d90c-1` | Product source, packaging, upgrades and acceptance belong to plurx; not rebuilt or qualified by this documentation change |
| Tiling Assistant | Stock `51.26.10.6ubuntu` installed; recoverable candidate `51.26.10.6ubuntu+nativehdr2` built, Forgejo PR14 | Deb `43d4b3e1…`, authenticated stock rollback retained and 35 inherited offline passes; [package handoff](TILING_ANIMATION_OWNERSHIP.md). Candidate not installed/live-qualified; historical warning trigger unproven |

November 2 coordinator read-only receipts show the APT installed and candidate
versions agree at priority 1001. Package verification for the inspected Mutter,
libdisplay-info amd64 and extension packages returned no differences. The
active output reports 2560×1600 at 240 Hz with variable-refresh mode configured,
scale about 1.3333, BT.2100, no target override and Night Light disabled. Its
effective range is approximately **0.0005–616 cd/m²**, firmware-declared, not
measured. Configured VRR alone is not proof of playback engagement; the later
owner-attended November 2 fixture below provides that bounded evidence.

**Do not reinstall these builds merely to complete this handoff.** Other
machines need their own inventory and a coordinated transaction. Installation
of the kernel is separate from APT userspace setup; the userspace registry
contains neither the kernel nor plurx Player.

## Exact package and source binding

The November 2 read-only registry snapshot contains 15 binary packages across
amd64, i386 and all. All downloaded sizes and SHA-256 hashes match the indexes;
the indexes match the SHA-256 entries in the October 27 Release file. This is
byte-integrity evidence, **not independent signing-key authentication**, an
isolated install/rollback execution, or a new test pass for those binaries.
The [neutral receipt](../evidence/software-delivery-20261102.json) records the
runtime package hashes and source binding. Raw registry snapshots and binaries
are retained privately rather than committed.

The Ubuntu series, `REVISION` and `SERIES.lock` are byte-identical between the
package changelog's `479d61de3f78` and inspected main `f064e91`. Upstream-facing
series rebases and the later kernel rebase are not changes to those userspace
package inputs. Existing nativehdr10 source tests and older package transaction
receipts keep their original identities; they are not relabelled nativehdr13
executions. No unchanged package or successful unit suite was rebuilt/rerun.

`build.sh` produces normal source `.dsc`/archives, `.buildinfo`, `.changes` and
binary packages. **The current registry publishes only `.deb` files**:
`publish.sh` does not upload the source/build records and no source index was
available at inspection. The [output retention repair](UBUNTU_APT_REPOSITORY.md#private-source-and-recovery-output-retention)
uses exclusive durable private run directories and verified byte inventories
for future builds, without deleting previous runs or forcing published versions
to rebuild. It does not recover the existing nativehdr13 originals. The receipt
here binds binary bytes to their recorded series commit; it does not claim that
current source archives or exact build-environment records were retrieved.
Their bounded runner/artifact/backup discovery remains a separate provenance
follow-up, not a reason to rebuild already working bytes.

The kernel receipt distinguishes the original unsigned image package from the
separately signed deployed package. For recovery use the **signed** image
package hash `ad6412f7cc7f3ffa4f343ca8a5cc7e2da0972ef7f1d7b1804227f7c271a39fdc`
and matching header package hash
`421f379e0120da5fdc2a7f1a646d14a54a4f700a2521a3deeb7854b86610304b`,
not the unsigned package just because its version matches. Signing material
and packages stay private. Reverify availability and trust before any install.

## Install and recovery checklist

1. Inventory installed package names, architectures and versions, APT holds,
   auto/manual marks, sources/pins, running kernel and actual loaded libraries.
   Save the original `monitors.xml` with metadata and a separate settings
   snapshot. Keep these private in durable operator-owned state.
2. Retain a complete, hash-verified rollback package set **before** an upgrade.
   The registry prunes older versions and is not a rollback archive. Include
   every installed binary from both source families, both libdisplay-info
   architectures if present, and exact-version GIR/development/test companions
   if installed. Do not assume the old six-package example fits every host.
3. For a new machine, review `setup-apt.sh` and simulate the exact candidate
   set first. The script writes the key/source/pin, unholds matching packages
   and installs upgrades noninteractively; it is not a dry run. Its origin-wide
   pin affects other repositories on the same host too. Review the solver
   result and stop on unexpected removals or desktop replacement.
4. Replace compositor libraries only in a coordinated logout/login window
   with an independent recovery route. APT database state alone does not prove
   GNOME Shell loaded the new libraries. Confirm package versions, loaded-file
   hashes, target reporting and logs after the new login.
5. For rollback to a retained patched set, disable the HDR pin/source first so
   priority 1001 cannot immediately reinstall the newer set. Use one explicit
   `apt-get -s install --allow-downgrades` transaction over the hash-verified
   retained `.deb` set; inspect dependencies/removals before the actual offline
   transaction in the coordinated window. Restore captured marks/holds by
   exact name and architecture. Do not run autoremove as part of recovery.
6. For stock Ubuntu, follow the [complete-set rollback guidance](UBUNTU_APT_REPOSITORY.md#rollback).
   Stock libdisplay-info lacks the additive native HDR API, so roll back Mutter
   and libdisplay-info together. For an older compositor that cannot parse
   target-override XML fields, preserve the original and prepare a compatible
   configuration while logged out; do not silently discard the only copy.
7. Kernel recovery uses the retained signed old custom or stock boot entry and
   matching initramfs. The old custom kernel lacks the documented CVE fix; it
   is emergency recovery, not a secure steady-state replacement. Do not remove
   the working nativehdr3 image or alter its default merely for paperwork.

These are operator instructions, not actions performed by a repository check.
No live install, logout, reboot, display or audio change occurred in this audit.

## Acceptance ledger: retained observations versus new requirements

- **Accepted October 15, on the earlier stack:** the owner watched the warm
  HDR/SDR roundtrip and found it normal; light/dark decorations looked fine;
  SDR video looked normal; HDR10 was stable in windowed and fullscreen modes.
  The persistence receipt passed after logout/login, and settings/XML were
  restored. The final owner-observation companion supersedes the early
  scripted receipt's `owner_visual_acceptance: pending`. These are completed
  bounded observations, not outstanding requests to repeat the old trial.
- **Retained October 29:** nativehdr3 installed/booted, running build ID bound
  to the CVE-fixed binary, security controls and drivers verified. This is not
  a new visual, VRR-transition, resume or optical pass.
- **November 2 read-only observation:** zero matching page-flip errors and two
  size-change-accounting warnings in the earlier bounded current-boot query.
  That query had no controlled fullscreen/VRR stimulus; the later attended
  fixture, not error absence or a configured `+vrr` mode, establishes the
  bounded acceptance below.
- **Accepted November 2, on nativehdr3/APT nativehdr13:** an owner-attended,
  silent HDR 24 fps stock-mpv fixture verified fullscreen/windowed stability
  on this panel. The active i915 CRTC's `VRR_ENABLED` changed **0 windowed →
  1 fullscreen → 0 windowed**. Both owned players exited 0, there were zero
  page-flip errors, and DisplayConfig (except its serial) and `monitors.xml`
  were unchanged. The owner answered, “Yes, everything looked normal”. The
  first visual run's debugfs samples did not expose the VRR property, so only
  the missing live-property acquisition was repeated in a 16-second follow-up,
  not the whole fixture. The private acceptance receipt and both run-receipt
  hashes are bound in the [neutral receipt](../evidence/software-delivery-20261102.json).
  This is a bounded pass on this panel, not optical/calibration or long-duration
  cadence evidence; suspend/resume, DPMS/brightness, other GPUs/modes and
  external monitors were not qualified by it.
- **Animation correction:** `t_5bfea0b5` independently approved 35 distinct
  offline host-double cases at retained private delivery `4f71e166` (26 retained
  passes plus nine failed-only retries after a reviewed missing-double-method fix).
  This applies to unpublished extension tree `03613a8236b6f200836df63acafa1e2359d94cb6`;
  neither identifier is a resolvable public source pin in this repository.
  It does not apply to Mutter or the current installed extension by assumption.
  The ordinary APT recipes still package only Mutter/libdisplay-info; the
  separate extension helper now produces a recoverable candidate
  `51.26.10.6ubuntu+nativehdr2` (deb SHA256
  `43d4b3e1b015ede3aa14757273b5165144638c0d01ac77d6c5694e0ca93d5e74`).
  Forgejo PR14 (`t_44f637a7`) retains its authenticated stock rollback and
  ordinary source/build records. Independent reviews approved the corrected
  integration; all twelve packaging guards passed on `6206b7c` in
  [the fast lane](https://github.com/pjunod/rog_hdr_dv/actions/runs/41514650977). Both installed callers still match October 15
  stock source: no target simulation/installation/live qualification is claimed.
  Do not blindly reapply old patches or rerun the 35 cases.
  The two warnings do not identify their exact caller without further evidence.
- **Still unperformed for the new stack:** broader HDR/SDR transitions,
  brightness/DPMS, suspend/resume, and Night Light/override visual checks after the
  APT/nativehdr3 updates. External-monitor/second-machine qualification,
  plurx Player product acceptance, same-panel Windows/OEM comparison and
  optical characterization remain separately tracked. No colourimeter is
  available as of November 2; declared panel values are not calibration.

Upstream preparation already landed at `a15684b`; preparation is not submission
or acceptance. Do not duplicate submissions or send messages as part of this
handoff. PR16 stays held/unmerged. Broader programme acceptance remains open.
