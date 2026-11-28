# Ubuntu APT repository — installing and updating the HDR desktop packages

Companion to [operations](OPERATIONS.md) (inspecting the laptop safely) and
[merged Ubuntu packages](MERGED_UBUNTU_PACKAGES.md) (the hand-built release
before this repository existed) — this is *how a machine gets the patched
Mutter and libdisplay-info, and how they stay current with Ubuntu*.

## Current update contract (November 20)

The November 18 WebKit replacement exposed a coverage gap: the automatic
builder below covered only Mutter/libdisplay-info. Browser and video builds
had been installed separately. [Recovery and evidence](UBUNTU_UPDATE_RECOVERY.md)
records the incident; current deployment acceptance is in [status](STATUS.md).

[The delivery manifest](../packaging/delivery/manifest.json) defines
public binary families for Mutter, libdisplay-info, WebKit/JavaScriptCore,
GTK, GStreamer and its GTK consumers. The publisher checks required family
members before mutation and verifies indexed hashes afterwards. A version's
bytes are immutable: interrupted uploads resume with the same retained files;
changed files require a new version. Rebuild output validation precedes pruning.

Package-scoped origin preferences and derivative-version fallback preferences
both use priority 999. The latter protects an installed patched version when
the registry is unavailable or its entry is absent. Equal priorities preserve
a numerically newer installed patch generation over an older registry build.
The generic installer refuses downgrades and checks the complete indexed
family before releasing holds. A genuinely newer reviewed source that sorts
lower requires a separately reviewed exact-version transaction; it is never
an implicit rollback by the generic installer.

mpv, the patched FFmpeg library subset, Mesa Vulkan, the extension bundle and
NetworkManager receive scoped derivative preferences and source monitoring.
They remain separately qualified releases, excluded from generic family
publication/installation. Private provider packages and custom kernel/boot
selection remain separate. The mpv monitor observes its Ubuntu packaging base;
it does not claim that the separately imported mpv 0.42 source is rebuilt
from Ubuntu's 0.41 source.

The daily workflow builds the original two desktop families only when
authenticated Ubuntu discovery exactly matches their reviewed source pins.
A changed Ubuntu source fails before building, pruning or publishing. An additional always-run monitor refreshes signed Ubuntu source
indexes and fails with the exact stale source and required rebase action for
all managed public sources. This is visible pending maintenance, not automatic
acceptance of an unreviewed source tree. Pins protect functionality while a
refresh is prepared; they do not prove current security fixes are installed.

The following original-builder details remain useful for that narrower build
path; source pins, family inventory and current status determine each release.

### Consumer pin re-releases

The GTK sink and Showtime depend on exact versions of the GStreamer families,
the GTK Dolby mapper and GTK, so a re-release of any of those forces new sink
and Showtime versions. These are recorded repacks of the qualified payload:
[`repack-consumers.py`](../packaging/gstreamer-gtk-dovi/repack-consumers.py)
changes only `Version` and the exact pins, and
[`consumer-releases.json`](../packaging/gstreamer-gtk-dovi/package-inputs/consumer-releases.json)
records each base and release hash with its receipt. `verify` proves the payload
is identical and the control is the generated one. The publisher takes these
versions from that file. A payload change needs a new recipe version above
every recorded release.

## Original automatic builder

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

**Versions.** The original two families use Ubuntu's reviewed source version
followed by `+nativehdrN`, with N from
[`packaging/ubuntu/REVISION`](../packaging/ubuntu/REVISION). Other families use
their own source pin, qualified binary manifest or consumer recipe. The shared
resolver checks each full intended version; a derivative suffix alone is not
an authorization to publish or install a package.

Some Ubuntu source transitions sort below the preceding derivative. Both
origin and installed-derivative preferences use 999: above normal Ubuntu and
target-release priorities, below APT's forced-downgrade threshold. Routine APT
updates retain the newer installed patch generation. The fallback uses APT's explicit version-regex form, for example
`Pin: version /.*[+]rogdv.*/`. The leading-and-trailing wildcard form failed
real APT matching during qualification. Solver checks verify the installed
version actually has priority 999, including an absent project repository,
foreign i386 packages and a target-release priority of 990.

The generic installer
refuses numerical downgrades. A lower-sorting reviewed replacement needs an
explicit exact-version, coherent transaction after its own APT rehearsal.
Superseded registry versions may be pruned only after complete local bundle,
prerequisite and existing-target identity checks pass. Preserve exact rollback
archives independently; the registry is not a recovery archive.

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
task_scratch="${HDR_WORK:?set HDR_WORK to owned durable storage}/scratch"
install -d -m 0700 "$task_scratch"                    # private operation scratch
sudo env TMPDIR="$task_scratch" rog_hdr_dv/packaging/ubuntu/setup-apt.sh
# Passing TMPDIR explicitly avoids sudo dropping it under its default policy.
# log out and back in: the running GNOME Shell keeps the old Mutter until then
```

[`setup-apt.sh`](../packaging/ubuntu/setup-apt.sh) adds the signing key and
deb822 source, generates scoped preferences, refreshes authenticated indexes,
and preflights complete project candidates for installed fully managed
families. It simulates the exact transaction and rejects removals, unmanaged
dependency changes and downgrades before releasing holds. It restores automatic
marks and failure-path holds. Separate-release policy-only packages are not
installed or unheld by this command. Set `TMPDIR` to private durable task
storage; keep exact rollback packages/configuration separately before running.

Failed setup restores the exact previous key/source/preferences, including
ownership, modes, symlinks or original absence. Every simulated install must
match an approved source/version/architecture from the authenticated project
index; matching a managed package name alone is insufficient. The real
transaction also refuses removals. Successful no-op setup intentionally leaves
the configured protection in place.

Forgejo carries architecture-independent packages in a separate `binary-all`
index. Completeness and publication checks include it explicitly; the ROG's
pre-existing APT source already acquired that index. The new source declaration
makes this layout explicit with `Architectures-Add: all`.

The signing key is initially fetched over the configured LAN HTTP connection;
that bootstrap retains the existing LAN trust assumption. Subsequent APT
metadata verification does not independently authenticate that first key fetch.
The preferences scope package names, although the origin match still names the
registry host rather than an individual URL path. Review same-name packages
from other repositories on that host.

**After a release upgrade.** `do-release-upgrade` disables third-party
sources. Run `setup-apt.sh` again once the registry has builds for the new
release; it rewrites the source for the new codename.

**How to read the result.** `apt-cache policy mutter` should show the
installed derivative and its `999` priority. Check WebKit and GStreamer
companions as well as Mutter; an installed fallback is not proof of repository
availability or source freshness. `gdctl show` should report `color-mode ⇒ bt2100` on an HDR panel
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
 ask signed Ubuntu indexes for libdisplay-info and mutter source versions
        │
 require exact equality with reviewed source pins (otherwise fail before mutation)
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
 verify retained inventory, intended family, scratch/tools and existing-target hashes
        │
        ▼
 delete the source's older versions ──▶ publish.sh (verify indexed hashes)
        │
        ▼
always-run signed-source monitor for every managed public source
        │
        └── stale reviewed pin ⇒ failed job with source/version/rebase action
```

**Running it by hand.** Nothing needs waiting for the night. To run the
workflow now, use Forgejo's Actions tab (`Ubuntu packages` → `Run workflow`),
or the API:

```bash
curl -X POST -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
  -d '{"ref": "main"}' \
  http://forge.lan:3000/api/v1/repos/pjunod/rog_hdr_dv/actions/workflows/ubuntu-packages.yml/dispatches
```

Or run both stages from a checkout with Docker. A current original-builder
registry does not imply that all separately built browser/video sources are fresh:

```bash
export FORGEJO_TOKEN=...                      # write:package scope
export FORGEJO_URL=http://forge.lan:3000      # the default; set it if the name does not resolve
packaging/ubuntu/rebuild.sh ~/.local/state/rog-hdr-dv/ubuntu-packages
packaging/ubuntu/monitor.sh 26.10             # signed source drift, no install
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

The host-mode workflow resolves the runner account's home from the operating
system account database, independently of any job-level `HOME` override. It
retains outputs in `.local/state/rog-hdr-dv/ubuntu-packages` under that home,
outside checkout and runner temporary-directory cleanup. Each run contains `libdisplay-info-amd64/`,
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

[`publish.sh`](../packaging/ubuntu/publish.sh) checks the entire intended
family, every prerequisite and all existing target identities before any
upload. A sentinel package alone never establishes completeness. Verification
covers each required package, version, architecture and SHA256 in the actual
indexes, including Forgejo's separate `binary-all` index. An interrupted
publication resumes only with the identical retained payloads. Different bytes
under an existing version require a newly reviewed version; partial uploads
are not permission to replace them. An unreadable registry, indexed missing
payload or conflicting target stops the run before mutation. The rebuild
performs the same preflight before deleting superseded versions.

**When a patch stops applying.** A proposed Ubuntu source rebase can change the context a
patch expects. Source discovery first refuses unreviewed versions. During the
reviewed build, an incompatible patch then fails with `build.sh: <patch> does not apply to
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
