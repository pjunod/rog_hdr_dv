# Package delivery — one APT repository for every project package

Companion to the [APT repository](UBUNTU_APT_REPOSITORY.md), which describes
the current Forgejo registry for Mutter and libdisplay-info, and to the
[software handoff](SOFTWARE_DELIVERY.md), which records what is installed now.
This document is the **design** that replaces both delivery paths. The
server (phase 1) and the manifest and publisher (phase 2) exist; no machine
uses the repository yet, and nothing has been published to it. The
[status page](STATUS.md) records each phase as it lands.

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

[`packaging/delivery/manifest.json`](../packaging/delivery/manifest.json) is the
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

## Server as built (phase 1, November 27)

lab3 now serves an empty published repository; no machine uses it yet.

| Part | As built |
|---|---|
| aptly | Ubuntu's `aptly` 1.6.2, run as the system account `aptly` (home `/srv/aptly`, mode 0750); config in `/srv/aptly/.aptly.conf`, data in `/srv/aptly/data`, signer `gpg2` |
| Local repository | `rog-stonking`, distribution `stonking`, component `main`, architectures amd64 and i386 |
| Published | Snapshot `rog-stonking-0000-empty`, `Origin: rog-hdr`, `Label: rog-hdr` |
| Repository key | ed25519 signing key `2DA6B7DE09D5671941650C1A36DDB628371F0745` (`ROG HDR package repository <rog-hdr@invalid>`), no expiry; the private key and its revocation certificate stay in the `aptly` account's GnuPG home. The public key is served as `rog-hdr-archive-keyring.asc` |
| Web server | Ubuntu's nginx on port 8095 only (the stock default site removed), serving `/srv/aptly/data/public` with basic authentication; `www-data` reads the tree through the `aptly` group |
| Reader | One user, `rog-apt-reader`, in `/etc/nginx/rog-apt.htpasswd` (root:www-data 0640). The password is kept in the operator's secret store as `rog-apt-reader`, never in Git |

Anonymous requests get 401. An authenticated fetch of `dists/stonking/InRelease`
returns the signed release with `Origin: rog-hdr`.

Publishing runs as the `aptly` account:

```bash
sudo runuser -u aptly -- env HOME=/srv/aptly GNUPGHOME=/srv/aptly/.gnupg \
  aptly repo add rog-stonking <debs…>
# then: aptly snapshot create <name> from repo rog-stonking
#       aptly publish switch -gpg-key=<fingerprint> stonking <name>
```

The phase 2 publisher (below) wraps these steps.

## Manifest and publisher (phase 2, November 27)

Everything is under [`packaging/delivery/`](../packaging/delivery/), in
Python with only the standard library. It reads `.deb` files itself, so no
dpkg is needed; zstd members need Python 3.14 or newer.

| File | What it does |
|---|---|
| `manifest.json` | One entry per delivered source package (fields below), plus `unconfirmed` (ours, owner not known) and `excluded` (vendor or stock), each with a reason |
| `publish.py` | The single publisher: checks a directory of `.deb` files, then adds, replaces, snapshots, switches and prunes over ssh |
| `pins.py` | Generates `rog-apt-config/preferences.d/rog-hdr` from the manifest |
| `fetch-key.py` | Fetches the served public key into `rog-apt-config/keyrings/`, refusing any other fingerprint |
| `rog-apt-config/` | The debhelper source package for machines |
| `delivery.py` | The shared code: manifest schema, `.deb` reader, pin generator, OpenPGP fingerprint |

### The manifest

Each entry has `source`, `project`, `class`, `binaries`, `architectures`,
`shadows_ubuntu` and `version`, which is the version installed on the ROG,
or null when the package is not installed. Optional fields:

- `series`: for a `built` entry, where its series lives in this repository;
- `reconcile_with`: for an `imported` entry, the series that phase 4
  reconciles it with. This is a pointer, not a claim that the installed bytes
  were built from it;
- `multiarch_same`: names that must arrive on every listed architecture
  together;
- `binary_versions`: binaries whose installed version differs from the
  source's, which today means the `+depfix` repacks;
- `kernel`: the publisher never removes a kernel's older versions;
- `note`.

The manifest was populated on November 27 from a read-only inventory of the ROG:
`apt list --installed` for local packages, and `dpkg-query` for their source names.
It has 28 sources and 61 binaries:

| Project | Built | Imported |
|---|---|---|
| `rog_hdr_dv` | 3: Mutter, libdisplay-info, `rog-apt-config` | 23, including two kernels |
| `plurx` | 0 | 1: `plurx-player` |
| `rog_audio` | 0 | 1: `rog-audio-easyeffects` |

Mutter and libdisplay-info are the only sources CI builds today. Everything else installed on the ROG was built by hand, so it stays `imported` until phase 4.

The asus-rog tools and NetworkManager are `unconfirmed`, so the publisher
refuses them until their owner is known. The vendor packages, and bzip2 (a
stock Ubuntu build), are `excluded`.

### Publishing

```bash
# Every check, and the plan; contacts nothing.
packaging/delivery/publish.py --project rog_hdr_dv DIR --dry-run

# On the publishing runner, as the aptly account on the repository host.
ROG_APT_HOST=aptly@<repository host> packaging/delivery/publish.py --project rog_hdr_dv DIR
```

The host comes only from the environment; the repository never names it.

**Checks on each `.deb`.** The publisher refuses the whole directory, before
it contacts the host, when any of these fails:

- the binary name is not listed, or its entry belongs to another project;
- its `Source` is not the entry's source, or its architecture is not listed;
- a name or architecture appears twice;
- a `multiarch_same` pair is incomplete;
- a `Multi-Arch: same` package present on two architectures differs in version or in any shared file;
- it has an exact `(= …)` dependency on a binary of another manifest entry.

`--allow-baseline-exact-deps` accepts that last case for `imported` entries,
for the baseline import of the installed bytes only. It never applies to a
`built` entry. Exact pins on names the manifest doesn't list are printed as
notes. Those names are Ubuntu binaries or virtual ABI names such as
`rog-dv-hevc-runtime`.

**Remote steps.** Every remote step runs over ssh, under a lock directory in the account's home:

1. Upload into a fresh staging directory and compare SHA-256 sums.
2. `aptly repo add`.
3. Remove every other version of each published name and architecture. Kernels are never removed, and no other name is touched.
4. Create the snapshot `rog-stonking-<UTC timestamp>-<project>`.
5. `aptly publish switch -gpg-key=2DA6B7DE…0745 stonking <snapshot>`.
6. Drop all but the newest 20 publisher snapshots. The published snapshot is never dropped; neither is the original `rog-stonking-0000-empty`.
7. `aptly db cleanup`.

A failure before step 5 changes nothing that machines see.

A crashed run leaves the lock `~/.rog-apt-publish.lock` behind. The next run then refuses to start until someone removes the lock by hand.

`ROG_APT_SSH` and `ROG_APT_APTLY` override the transport and the aptly
command. That is how the tests run the publisher against a scratch state. A
throwaway aptly also works: `ROG_APT_APTLY='aptly -config=<scratch>/aptly.conf'`.

### Pins and the config package

```bash
packaging/delivery/pins.py --write   # after any manifest change
packaging/delivery/pins.py --check   # what scripts/check_repository.py enforces
```

`rog-apt-config` installs three files:
- `/etc/apt/sources.list.d/rog-hdr.sources`, whose URL `http://forge.lan:8095/` appears only in `debian/rog-hdr.sources`;
- `/usr/share/keyrings/rog-hdr-archive-keyring.asc`;
- `/etc/apt/preferences.d/rog-hdr`.

It has no maintainer scripts, so it runs no apt, and it installs no credential.

The key file is not checked in yet. `fetch-key.py` fetches it with the
reader account and checks the fingerprint; then it is committed.
`debian/rules` refuses to build without it, or with any other fingerprint.

### Repository checks

`scripts/check_repository.py` now also checks:
- the manifest schema, and that the `series` and `reconcile_with` paths exist;
- that each binary is listed by one source only, and is not also unconfirmed or excluded;
- that the checked-in pin equals the generated one;
- that the package's recorded fingerprint, and the key file once present, match the manifest;
- that no maintainer script runs apt.

The cross-source rule for `built` entries needs the built `.deb` files, so the
publisher enforces it, not the offline check.
`tests/test_package_delivery.py` covers the publisher against
`tests/delivery_fakes.py`, an ssh and aptly double.

### Limits found in phase 2

- **Partial sources.** For FFmpeg, Mesa, glycin and WebKitGTK we deliver only some binaries; Ubuntu supplies the rest. `libavfilter11` pins Ubuntu's `libavutil60 (= 7:8.1.2-2ubuntu2)` exactly, so an Ubuntu FFmpeg update is held back until we rebuild. Following Ubuntu has to cover these sources too.
- **ABI-named sources.** `libplacebo-rog1-360`, `libplacebo-rog387` and the two `librog-dv-provider` libraries are each their own source, named after the binary. Each ABI is therefore a separate entry, and a new ABI needs a manifest entry before it can be published. Old ABI names are never removed automatically; retiring one is a manifest change plus an explicit `aptly repo remove`.
- **Versioned names accumulate.** The same applies to `libmutter-51-0` when Mutter moves to 52, and to kernels.
- **`+depfix` repacks** give binaries versions that differ from their source's (`binary_versions`). They retire as phase 4 rebuilds each source.
- **NetworkManager.** On the ROG, Ubuntu's `1.58.1-1ubuntu3.1` is already the apt candidate over our `+rogsleep1` for `libnm0` and `network-manager-tui`.

## Decisions

Recorded November 27, when the owner accepted all four recommendations after
an independent review.

1. **One private repository for everything,** read by a read-only machine account. Splitting the public and private builds across two repositories would break the dependency chains that cross them.
2. **A single publisher holds the only write credential.** The pin is generated from the manifest, so no unlisted name can win.
3. **Kernels go through apt with no meta package and no hold.** The owner installs each kernel and keeps the GRUB default.
4. **aptly replaces the Forgejo registry** for delivery, and is set up before any package moves, so each machine's source changes once.
