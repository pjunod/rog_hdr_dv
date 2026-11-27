# Package delivery — one APT repository for every project package

Companion to the [APT repository](UBUNTU_APT_REPOSITORY.md), which describes
the current Forgejo registry for Mutter and libdisplay-info, and to the
[software handoff](SOFTWARE_DELIVERY.md), which records what is installed now.
This document is the **design** that replaces both delivery paths. Nothing
here is deployed yet; the [status page](STATUS.md) records each phase as it
lands.

## Goal

Every package built by the owner's projects reaches a machine from one APT
repository and is updated by ordinary `apt update` and `apt upgrade`.
Nothing of ours is installed from a local `.deb`. "Our projects" means this
repository, plurx (plurx Player), rog_audio, and the ROG tools, once their
owners confirm them. Vendor packages (browsers, game clients, VPN, GPU
container tooling, kernel installers) keep their vendors' channels.

## Why the Forgejo registry is not enough

| Need | Forgejo Debian registry | Consequence |
|---|---|---|
| Publish several packages as one release | One `.deb` per upload, and each upload rebuilds the index | During a multi-source release the index is inconsistent; `apt upgrade` keeps packages back, and `full-upgrade` can propose removals |
| Rollback archive | Superseded versions are deleted (see the APT guide) | Rollback depends on hand-kept `.deb` files |
| Distinct Origin and Label | Generic Forgejo strings | A pin can only match the whole forge host |
| Private visibility | Per owner only | Workable, but every package of that owner shares it |

## Design

### Server

- **aptly**, from Ubuntu's archive, runs on lab3, the forge host, as a dedicated service account.
- aptly holds one local repository per suite and signs with a **project repository key**.
  - The private key stays on lab3, under that account.
  - The public key is published and shipped in the config package (below).
- Releases carry `Origin: rog-hdr` and `Label: rog-hdr`. Pins can therefore name this repository rather than a host.
- A static web server, which is a small container on lab3, serves the published tree over HTTP with basic authentication.
  - There is no anonymous read: some builds are not cleared for publication.
  - Machines read as one read-only machine account. The credential lives in `/etc/apt/auth.conf.d/rog-hdr.conf` (mode 0600) and never in Git or in a package.

### Releases are snapshots

1. The publisher adds each release's packages to the local repository.
2. It takes a snapshot.
3. It runs `aptly publish switch` to that snapshot.
4. It keeps the last 20 snapshots.

Every release is therefore atomic: a machine sees either the whole previous set or the whole new set. Rolling back means switching the published snapshot back. Pinned at 1001, apt follows a rollback as an ordinary downgrade. That closes the "not a rollback archive" gap in the APT guide.

Within the local repository, each **binary package name** keeps one version. A new version replaces that name only. Versioned names coexist and are never removed by a newer release:
- library ABIs such as `libplacebo-rog1-360` and `libplacebo-rog387`;
- kernels.

### The manifest

`packaging/delivery/manifest.json` (phase 2) will be the
one list of what is delivered. Each entry is a source package with these fields:

- `project`: which repository owns it (`rog_hdr_dv`, `plurx`, `rog_audio`, …).
  The publisher accepts a binary only from the project its entry names.
- `class`:
  - `built`: CI builds it from a source pin and series in this repository.
  - `imported`: the source is held elsewhere, and a build produced there is published as is, with its hash recorded.
- `binaries` and `architectures`. `Multi-Arch: same` pairs (libdisplay-info, Mesa Vulkan) are checked for byte-identical shared files and always land in the same snapshot.
- `shadows_ubuntu`: whether it replaces an Ubuntu package. Those packages get priority 1001 and a follow-Ubuntu policy (below).

### Dependencies

Exact `(= version)` pins remain only **within** one source package. Between
source packages, dependencies come from `shlibs` or symbols files, or from an
explicit ABI `>=`. A source package whose `shlibs` file is empty is a
packaging bug fixed in that package, not a repack. The `+depfix` repacks
retire as each source is rebuilt or re-imported with correct metadata.

### Who publishes

One publishing job, on the repository's own runner on lab3, holds the only
credential that can change the repository.

- **This repository's packages:** its workflows build them and hand them to the publisher.
- **Other projects:** they attach their `.deb` files to a release in their own repository, as they already can. The publisher fetches the release with read access, checks every binary against the manifest's `project`, and publishes it. No other project holds a repository credential.

### Machines: the config package

`rog-apt-config` installs three things:
- the deb822 source;
- the public repository key;
- the pin file, generated from the manifest:

| Packages | Priority |
|---|---|
| Listed names that shadow Ubuntu | 1001: always ours, even over a newer Ubuntu version |
| Other listed names | 500, the normal priority |
| Any other name from this origin | -1: never installed |

Changes to the source, key or pin then arrive through apt like everything else. A one-time setup step installs the config package and writes the auth file. That step is the only manual part.

`unattended-upgrades` must not act on this origin. Ubuntu's default `Allowed-Origins` doesn't include it; the setup step checks this and records it.

### Following Ubuntu

At 1001, Ubuntu's security fixes to a shadowed package stop reaching the
machine until we rebuild. For every `shadows_ubuntu` entry, a scheduled job
compares Ubuntu's current version with the base we built from and does one of two things:
- for a `built` entry, it rebuilds, as the Mutter rebuild already does;
- for an `imported` entry, it reports the lag on the status page.

This covers Mutter and libdisplay-info today. It is to extend to WebKitGTK, FFmpeg, GTK 4, Mesa,
GStreamer and NetworkManager.

### Kernels

Kernels are signed by hand with the owner's key, so they are `imported` and
published from signed artifacts, never built or signed on a runner. There is
no meta package. `apt upgrade` never installs a new kernel; the owner runs
`apt install linux-image-<version>` when releasing one. The saved GRUB default
stays the owner's.

## Phases

1. **Server.** Set up aptly, the key, the authenticated web server and the machine account on lab3, then publish an empty snapshot.
2. **Manifest and publisher.** Write the manifest; build the publisher, the pin generator and `rog-apt-config`; add repository checks:
   - the manifest's binaries are unique;
   - the pins match the manifest;
   - no cross-source `(= …)` dependency is left among `built` entries.
3. **Baseline import.** Publish the exact `.deb` files installed on the ROG. To prove they are the installed bytes, compare each file's control fields and per-file md5sums with `/var/lib/dpkg`. Switching the ROG to this repository then changes no installed file.
4. **Source reconciliation.**
   - Bring this repository's series up to what is installed. For example, the plugins-bad paused-subtitle change is in `rogdv10` and `rogdv11` but not in the series.
   - Record where each `imported` source lives.
   - No rebuilt revision ships until its source is reconciled.
5. **Project publishing.** plurx and rog_audio attach their `.deb` files to their releases, through PRs in those repositories, and the publisher picks them up.
6. **Migration.** In a window agreed with the owner:
   - save the ROG's package inventory, holds, marks, sources and `.deb` files to private storage;
   - install `rog-apt-config` and the auth file;
   - run `apt-get update`;
   - require that `apt-get -s upgrade` changes nothing.

   Then retire the Forgejo registry source. No compositor or session restart, and no boot change, happens without the owner.
7. **Proof.** On the ROG:
   - no `,local` packages of ours;
   - `apt-cache policy` names this origin for each one;
   - one real new build reaches the machine through `apt upgrade`.

## Decisions

Recorded November 27, when the owner accepted all four recommendations after
an independent review.

1. **One private repository for everything,** read by a read-only machine account. Splitting the public and private builds across two repositories would break the dependency chains that cross them.
2. **A single publisher holds the only write credential.** The pin is generated from the manifest, so no unlisted name can win.
3. **Kernels go through apt with no meta package and no hold.** The owner installs each kernel and keeps the GRUB default.
4. **aptly replaces the Forgejo registry** for delivery, and is set up before any package moves, so each machine's source changes once.
