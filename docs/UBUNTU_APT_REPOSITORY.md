# Ubuntu APT repository — installing and updating the HDR desktop packages

Companion to [operations](OPERATIONS.md) (inspecting the laptop safely) and
[merged Ubuntu packages](MERGED_UBUNTU_PACKAGES.md) (the hand-built release
before this repository existed) — this is *how a machine gets the patched
Mutter and libdisplay-info, and how they stay current with Ubuntu*.

## What it is

Ubuntu's own Mutter and libdisplay-info, rebuilt with this repository's
series (`patches/ubuntu-mutter`, `patches/ubuntu-libdisplay-info`) and
published to the Forgejo Debian registry of the repository's owner:

```
http://forge.lan:3000/api/packages/pjunod/debian   <codename> main
```

| Package set | Built from | Architectures |
|---|---|---|
| `libdisplay-info3` · `libdisplay-info-dev` · `libdisplay-info-bin` | Ubuntu's current `libdisplay-info` source + 23 patches | amd64, i386 |
| `mutter` · `mutter-common` · `mutter-common-bin` · `libmutter-51-0` · `gir1.2-mutter-51` · `libmutter-51-dev` · `mutter-dev-bin` · the test packages | Ubuntu's current `mutter` source + 105 patches | amd64 (`mutter-common`: all) |

i386 exists for one reason: Ubuntu keeps a 32-bit `libdisplay-info3` for
32-bit programs (Wine), and a `Multi-Arch: same` library must carry the same
version, with byte-identical shared files, on both architectures, or dpkg
refuses to install either.

**Versions.** Ubuntu's version followed by `+nativehdrN`, N from
[`packaging/ubuntu/REVISION`](../packaging/ubuntu/REVISION): currently Mutter
`51.0-1ubuntu3+nativehdr13` and libdisplay-info `0.3.0-1+nativehdr13`. That
sorts above Ubuntu's same version and above the hand-built `+nativehdr10` and
`~hdr9`, but **not** always above the previous build: Ubuntu's next
libdisplay-info would be `0.3.0-1ubuntu0.1`, and `0.3.0-1ubuntu0.1+nativehdr13`
sorts below `0.3.0-1+nativehdr13`. So the registry holds one version per
source: once a new version has built, the rebuild deletes the older ones and
uploads it, and the priority-1001 pin (below) lets APT move to it even when
that is a numeric downgrade. The deletions come first because Forgejo v16
does not rebuild the index when a version's last file is deleted (its delete
notifier reads the version's files after they are gone); every upload
rebuilds its architecture's index.

**A series change needs a new revision.** The registry refuses a second
upload of a version it has, and the rebuild treats a published version as
done, so a changed series under the same version would never ship. The
repository check enforces it: [`SERIES.lock`](../packaging/ubuntu/SERIES.lock)
records the digest of each Ubuntu series and the revision it was built as,
and `scripts/check_repository.py` fails when they disagree. After changing a
series, raise `REVISION` and run:

```bash
scripts/check_repository.py --lock-ubuntu-series   # refuses until REVISION is raised
```

## Installing on a machine

**November 2:** the ROG already has nativehdr13 from this repository, including
both libdisplay-info architectures; do not reinstall it to finish paperwork.
See the [software handoff](SOFTWARE_DELIVERY.md) for exact hashes and current
versus retained acceptance. The instructions below are for a new setup or a
deliberate later change, not permission to interrupt an active desktop.

Before running the installer, preserve the complete current package set,
holds, auto/manual marks, APT configuration and display settings in durable
private storage. Review `apt-cache policy` and simulate the exact target
package transaction with `apt-get -s install` first. Keep a verified independent
recovery route and coordinate logout/login; do not run the setup script as a
diagnostic. The kernel and plurx Player are separate installations.

```bash
git clone http://forge.lan:3000/pjunod/rog_hdr_dv.git   # or any checkout
sudo rog_hdr_dv/packaging/ubuntu/setup-apt.sh         # key, source, pin, upgrade
# log out and back in: the running GNOME Shell keeps the old Mutter until then
```

[`setup-apt.sh`](../packaging/ubuntu/setup-apt.sh) adds the registry's signing
key and a deb822 source, pins every package from the registry's host at
priority 1001, releases any `apt-mark hold` on these packages (the 2026-10-13
hand install held them), upgrades whatever of them is installed, and keeps
automatically installed libraries marked automatic. The key comes over plain
HTTP from the LAN registry; that is the trust the LAN already gives the
registry, nothing more.

The pin uses `Package: *` and matches the **host**, not just this registry's
path. If that host also serves other APT repositories, their packages match
too. Review all affected origins before enabling the pin. The setup script
changes holds and uses `apt-get install -y`; it is not a simulation and does
not retain a rollback archive for you. It preserves automatic marks after a
successful transaction, but recovery must also retain the original marks in
case an intermediate step fails.

**Why priority 1001.** Above 1000, APT installs the registry's build even
when Ubuntu has published a newer, unpatched version, and even when the
registry's build sorts lower. Without the pin, an Ubuntu update would replace
the HDR build with stock Mutter and the panel would lose HDR detection. With
it, the machine keeps the HDR build until the rebuild (below) publishes
Ubuntu's new version with the series. **The trade:** if a patch stops
applying, that wait lasts until someone refreshes the patch, and Ubuntu's
fixes to these two packages wait with it. The rebuild fails loudly when that
happens (below).

**After a release upgrade.** `do-release-upgrade` disables third-party
sources. Run `setup-apt.sh` again once the registry has builds for the new
release; it rewrites the source for the new codename.

**How to read the result.** `apt-cache policy mutter` should show the
installed version ending in `+nativehdrN` and a `1001` priority line for the
registry. `gdctl show` should report `color-mode ⇒ bt2100` on an HDR panel
after the next login.

## Rollback

The registry deliberately deletes superseded versions; it is **not** a
rollback archive. Retain all installed packages from both source families,
not just `mutter` and `libmutter-51-0`: exact-version GIR, development and test
companions may also be installed. If libdisplay-info3 is installed as amd64
and i386, both must move together to the same version. Preserve any installed
multiarch development companions as well. A stock library does not provide
the native HDR API required by patched Mutter, so replace the pair coherently.

First inventory the actual installed set and holds (read-only):

```bash
dpkg-query -W -f '${binary:Package} ${Version} ${db:Status-Abbrev}\n' \
  'mutter*' 'libmutter-*' 'gir1.2-mutter-*' 'libdisplay-info*'
apt-mark showhold
apt-mark showauto
apt-cache policy mutter libmutter-51-0 libdisplay-info3:amd64 libdisplay-info3:i386
```

Keep the installed records, not residual-config/not-installed matches; a
missing pattern can make `dpkg-query` return nonzero. Save original sources,
pin and key as well as the package inventory. In a coordinated recovery
window, disable `/etc/apt/preferences.d/rog-hdr-dv` and
`/etc/apt/sources.list.d/rog-hdr-dv.sources` (move to the private recovery
directory, do not destroy the only copy), then `sudo apt-get update`.

For **stock Ubuntu**, identify an available Ubuntu version for every installed
name/architecture using `apt-cache policy` after disabling the pin/source.
Construct one explicit `name:arch=version` argument per installed binary, with
the source family's versions coherent, and inspect
`apt-get -s install --allow-downgrades <complete exact-version set>`.
Do not paste the angle-bracket placeholder literally. Stop on unexpected
removals, missing architectures or changes outside the planned desktop set;
do not accept removal of GNOME to satisfy the native-HDR API dependency.
Only then perform that exact reviewed transaction while logged out.

For a **retained patched set**, verify its hashes and use the entire retained
`.deb` closure in the same simulated-then-deliberate transaction, not whichever
two runtime files happen to be at hand. The historical isolated rollback
receipts bind their older packages and baseline, not today's APT binaries.
After either rollback restore captured auto/manual marks and holds explicitly,
start a new login, and inspect loaded library identities and display state.
Do not autoremove recovery kernels or dependencies during this procedure.

Before reverting to a compositor predating target overrides, retain the
original `monitors.xml` and prepare a compatible copy while logged out: older
parsers reject unknown target-override children under `<monitor>`. A package
downgrade alone does not migrate configuration. Kernel rollback remains
separate; see [operations](OPERATIONS.md) and the [kernel ledger](KERNEL_REBASE.md).

## Keeping it current — `.github/workflows/ubuntu-packages.yml`

Every night at 07:23 UTC, on any push to `main` that touches the series or
`packaging/ubuntu/`, and on demand, the workflow runs
[`rebuild.sh`](../packaging/ubuntu/rebuild.sh) on the repository's runner
(below):

```
 repository check (SERIES.lock agrees with the series and REVISION)
        │
 ask Ubuntu for its current libdisplay-info and mutter source versions
        │
        ▼
 registry has <ubuntu version>+nativehdr<REVISION> complete? ── yes ──▶ done
        │ no
        ▼
 build.sh in a clean ubuntu:<release> container, for that exact
 Ubuntu version (libdisplay-info amd64 + i386, checked identical;
 Mutter against the registry's libdisplay-info)
        │
        ▼
 verify retained output inventory
        │
        ▼
 delete the source's older versions ──▶ publish.sh (rebuilds the indexes)
```

**Running it by hand.** Nothing needs waiting for the night. To run the
workflow now, use Forgejo's Actions tab (`Ubuntu packages` → `Run workflow`),
or the API:

```bash
curl -X POST -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
  -d '{"ref": "main"}' \
  http://forge.lan:3000/api/v1/repos/pjunod/rog_hdr_dv/actions/workflows/ubuntu-packages.yml/dispatches
```

Or run the same script from a checkout on any machine with Docker; it does
exactly what the workflow does, and nothing when the registry is current:

```bash
export FORGEJO_TOKEN=...                      # write:package scope
export FORGEJO_URL=http://forge.lan:3000      # the default; set it if the name does not resolve
packaging/ubuntu/rebuild.sh ~/.local/state/rog-hdr-dv/ubuntu-packages
# Retains an exclusive run-* child here when building; never empties the root.
```

The steps also run alone, for example to try a refreshed patch without
publishing anything:

```bash
packaging/ubuntu/build.sh libdisplay-info ~/work/ldi-amd64                     # newest Ubuntu source
packaging/ubuntu/build.sh libdisplay-info ~/work/ldi-i386 --arch i386
packaging/ubuntu/build.sh mutter ~/work/mutter --with ~/work/ldi-amd64          # against that libdisplay-info
packaging/ubuntu/publish.sh ~/work/ldi-amd64 ~/work/ldi-i386                   # only when it should ship
```

**The runner.** The job runs on `lab3-rog-hdr-01`, a Forgejo runner on lab3
registered to this repository only (the other runners belong to plurx's
organisation and never pick up these jobs). It lives in
`/opt/forgejo-runner-rog-hdr-01` as the `runner` user with Docker access, and
runs as the systemd service `forgejo-runner-rog-hdr-01`:

```bash
systemctl status forgejo-runner-rog-hdr-01        # on lab3
sudo systemctl restart forgejo-runner-rog-hdr-01
sudo journalctl -u forgejo-runner-rog-hdr-01 -f   # what it is doing
```

**The token.** The automatic Actions token can only read an owner's
packages, so the workflow uses a repository secret `PACKAGE_TOKEN`: a
personal access token of the registry's owner with the `write:package`
scope. The scripts hand it to curl through a config on a file descriptor, so
it never appears in a process list.

### Private source and recovery output retention

`rebuild.sh WORK` treats WORK as a durable retention root, not a disposable
build directory. When a build is needed, it atomically reserves a private
`run-*` child. Manual and concurrent invocations receive distinct children;
a fully published no-op does not create or change WORK. Existing successful,
failed, partial and unknown data are never deleted. This does not change
version detection, paired-architecture checks, registry pruning or publication.

The workflow retains outputs under the runner account's
`$HOME/.local/state/rog-hdr-dv/ubuntu-packages`, outside checkout and runner
temporary-directory cleanup. Each run contains `libdisplay-info-amd64/`,
`libdisplay-info-i386/` and/or `mutter-amd64/` as needed, plus Mutter's exact
downloaded dependencies in `with/`. Successful amd64 output includes the
original `.dsc` and every source archive it lists, binaries, `.changes`,
`.buildinfo` and the build log. i386 remains a binary-only cross-build.
Full builder stdout/stderr goes to private `invocation.log`, not public CI
artifacts. On failure, everything already written to the run survives, even
if publication fails. Files still inside a failed disposable build container
are not exported by `build.sh`; its captured invocation log is not a claim to
recover all container-internal records.

Each successful build has a sibling `<source>-<arch>.manifest.json`: sorted
relative paths, sizes and SHA256s of every retained output file, with the
source, Ubuntu version, patched version and architecture. Creation is exclusive
and immediately reverified before registry mutation. This is a byte inventory,
not a signature, build attestation or proof that an incomplete build succeeded.
No manifest is created for a failed build. To verify a retained directory:

```bash
python3 packaging/ubuntu/outputs.py verify \
  "$RUN/libdisplay-info-amd64" "$RUN/libdisplay-info-amd64.manifest.json"
```

Set RUN to the private run directory first. Verification rejects changed,
missing, additional or nonregular files. Keep manifests beside the outputs;
they deliberately do not contain their own checksums. A manual archive/copy
must be separately hash-verified before anyone relies on it or removes its
producer. This implementation performs no archive copy or automatic cleanup;
the operator owns capacity planning, backups and deliberate later retention
decisions. Durable local storage is not an off-host backup or an indefinite
availability guarantee. Preserve independent rollback packages before upgrades;
the binary registry still prunes superseded versions.

Raw logs/buildinfo may reveal infrastructure paths. Retrieve them privately
from that runner-owned path through the coordinator, never commit them or add
an automatic public GitHub artifact upload. `publish.sh` still uploads only
`.deb` files. This lifecycle repair **does not recover nativehdr13 originals**
and does not force a rebuild of published versions. For those existing records:

1. The coordinator's November 2 Forgejo Actions artifact listing was empty.
   Retrieved logs for run 6106/job 59118 and run 6383/job 61572 both show
   already-published no-ops, not the original builds. The logs and their hashes
   are retained privately; no new source-package recovery is claimed.
2. The coordinator's bounded filename search included hidden and ignored files
   in owned HDR collaboration and legacy owned team workspaces, excluding
   `.git`, `node_modules`, `target`, `.venv` and `vendor`. It found no matching
   nativehdr13 `.dsc`, `.buildinfo` or `.changes` files. Other machines and
   backups were not searched: this is not global loss proof.
3. Remaining recovery is coordinator-owned: locate the earlier original build
   invocation and then-resolved legacy `RUNNER_TEMP/ubuntu-packages` location
   using existing private runner/job records. The Forgejo read-only routes are
   `GET /api/v1/repos/pjunod/rog_hdr_dv/actions/runs/{run_id}/jobs` and
   `GET /api/v1/repos/pjunod/rog_hdr_dv/actions/jobs/{job_id}/logs`.
   Through authorized read-only runner inspection, check that exact legacy
   output path and configured private runner backup/snapshot, bounded
   to `.dsc` plus listed archives, `.buildinfo`, `.changes`, binaries and logs
   for the two exact nativehdr13 versions above. Do not reset the warm tree,
   launch builds or dispatch workflows to fill gaps.
4. If recovered, retain the original bytes privately, verify their source and
   binary checksum closure, and record provenance separately. If inaccessible
   or absent at those locations, report those exact limits, not global loss.

The [software handoff](SOFTWARE_DELIVERY.md) keeps the original-record recovery
gap separate from retained binary hashes and earlier package test receipts.

[`build.sh`](../packaging/ubuntu/build.sh) applies the series with
`git apply` (it carries binary test fixtures) on top of Ubuntu's source with
Ubuntu's own patches applied, leaves out the series' historical
`debian/changelog` entries, and writes one entry naming the series commit,
dated by the later of the commit and Ubuntu's own entry so both
architectures' changelogs match. libdisplay-info's test suite runs on amd64;
Mutter's does not (`nocheck`), because it needs a display server and a
session bus. No debug-symbol packages are published.

[`publish.sh`](../packaging/ubuntu/publish.sh) uploads each `.deb` and the
source's sentinel package (`mutter`, `libdisplay-info3`) last, so a version
whose sentinel is in the registry is complete. A version without its
sentinel is a partial upload from a failed run, and its files are replaced
on the next run; a complete version is never replaced. A registry that
cannot be read stops the run instead of reading as "not published".

**When a patch stops applying.** An Ubuntu update can change the context a
patch expects. The run then fails with `build.sh: <patch> does not apply to
mutter <version>` and the workflow goes red; machines keep the previous HDR
build (the pin holds them). libdisplay-info may already have moved to the
new version; that is safe, because Mutter's dependency on it is a minimum.
Refresh the patch against the new source, raise `REVISION`, lock, and push.

**A known future break.** The series' `debian/control` and symbols files
still name minimum versions in the old `0.3.0-1ubuntu1~hdrN` form. If Ubuntu
ever ships libdisplay-info as `0.3.0-1ubuntu0.N`, those minimums sort above
it and Mutter's build-dependencies cannot be met; the build fails at
`apt-get build-dep`, visibly, and the minimums need restating then.

## Non-goals

- **Not upstream.** These are downstream builds of Ubuntu's packages; the
  upstream-facing series in `patches/mutter` and `patches/libdisplay-info`
  are separate and unsubmitted.
- **No kernel.** The DisplayID luminance kernel patches (`patches/linux`)
  are not packaged here; a kernel is installed deliberately, per
  [operations](OPERATIONS.md).
- **No project signing key.** APT trusts the registry's own key, which
  Forgejo generates per owner.
