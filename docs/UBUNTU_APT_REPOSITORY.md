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
source: once a new version is completely published, the rebuild deletes the
older ones, and the priority-1001 pin (below) lets APT move to it even when
that is a numeric downgrade.

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

**Going back to Ubuntu's packages.** Remove the pin and source, then
reinstall each package from Ubuntu:

```bash
sudo rm /etc/apt/preferences.d/rog-hdr-dv /etc/apt/sources.list.d/rog-hdr-dv.sources
sudo apt update
apt list --installed 2>/dev/null | grep nativehdr     # the packages to revert
sudo apt install --allow-downgrades mutter=51.0-1ubuntu3 libmutter-51-0=51.0-1ubuntu3   # one name=version per line above
```

## Keeping it current — `.github/workflows/ubuntu-packages.yml`

Every night at 07:23 UTC, on any push to `main` that touches the series or
`packaging/ubuntu/`, and on demand, the workflow runs
[`rebuild.sh`](../packaging/ubuntu/rebuild.sh) on a self-hosted runner with
the `self-hosted` and `lab` labels and Docker:

```
 repository check (SERIES.lock agrees with the series and REVISION)
        │
 ask Ubuntu for its current libdisplay-info and mutter source versions
        │
        ▼
 registry has <ubuntu version>+nativehdr<REVISION> complete? ── yes ──┐
        │ no                                                          │
        ▼                                                             │
 build.sh in a clean ubuntu:<release> container, for that exact      │
 Ubuntu version (libdisplay-info amd64 + i386, checked identical;    │
 Mutter against the registry's libdisplay-info) ──▶ publish.sh        │
        │                                                             │
        ▼                                                             ▼
 delete the source's older versions from the registry ◀───────────────┘
```

**The token.** The automatic Actions token can only read an owner's
packages, so the workflow uses a repository secret `PACKAGE_TOKEN`: a
personal access token of the registry's owner with the `write:package`
scope. The scripts hand it to curl through a config on a file descriptor, so
it never appears in a process list.

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
