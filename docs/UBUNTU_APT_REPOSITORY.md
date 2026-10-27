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
| `mutter` · `mutter-common` · `mutter-common-bin` · `libmutter-51-0` · `gir1.2-mutter-51` · `-dev` and debug packages | Ubuntu's current `mutter` source + 105 patches | amd64 |

i386 exists for one reason: Ubuntu keeps a 32-bit `libdisplay-info3` for
32-bit programs (Wine), and a `Multi-Arch: same` library must carry the
same version on both architectures or APT refuses to upgrade either.

**Versions.** Ubuntu's version followed by `+nativehdrN`, N from
[`packaging/ubuntu/REVISION`](../packaging/ubuntu/REVISION): Mutter
`51.0-1ubuntu3+nativehdr12`, libdisplay-info `0.3.0-1+nativehdr12`. That
sorts above both Ubuntu's package and every earlier build (`+nativehdr10`,
`~hdr9`), so APT treats each rebuild as an ordinary upgrade. Raise
`REVISION` in the same commit as any change to either series; without that,
the changed series would never be published, because the registry refuses a
second upload of a version it has.

## Installing on a machine

```bash
git clone http://forge.lan:3000/pjunod/rog_hdr_dv.git   # or any checkout
sudo rog_hdr_dv/packaging/ubuntu/setup-apt.sh         # key, source, pin, upgrade
# log out and back in: the running GNOME Shell keeps the old Mutter until then
```

[`setup-apt.sh`](../packaging/ubuntu/setup-apt.sh) adds the registry's signing
key and a deb822 source, pins these packages to the registry at priority
1001, releases any `apt-mark hold` on them (the 2026-10-13 hand install held
them) and upgrades whatever of them is installed.

**Why priority 1001.** Above 1000, APT installs the registry's build even
when Ubuntu has published a newer, unpatched version. Without the pin, an
Ubuntu security update would replace the HDR build with stock Mutter
overnight and the panel would lose HDR detection. With it, the machine keeps
the HDR build until the nightly rebuild (below) publishes Ubuntu's new
version with the series — a delay of at most a day, which is the trade
accepted.

**How to read the result.** `apt-cache policy mutter` should show the
installed version ending in `+nativehdrN` and a `1001` priority line for the
registry. `gdctl show` should report `color-mode ⇒ bt2100` on an HDR panel
after the next login.

**Going back to Ubuntu's packages.** Remove the pin and source, then
downgrade explicitly:

```bash
sudo rm /etc/apt/preferences.d/rog-hdr-dv /etc/apt/sources.list.d/rog-hdr-dv.sources
sudo apt update
sudo apt install --allow-downgrades mutter/<codename> libmutter-51-0/<codename> ...   # every package setup-apt upgraded
```

## Keeping it current — `.github/workflows/ubuntu-packages.yml`

Every night at 07:23 UTC, on any push to `main` that touches the series or
`packaging/ubuntu/`, and on demand, the workflow runs
[`rebuild.sh`](../packaging/ubuntu/rebuild.sh):

```
 ask Ubuntu for its current libdisplay-info and mutter source versions
        │
        ▼
 registry has <ubuntu version>+nativehdr<REVISION>? ── yes ──▶ nothing to do
        │ no
        ▼
 build.sh in a clean ubuntu:<release> container ──▶ publish.sh
 (libdisplay-info amd64 + i386 first; Mutter then builds
  against the registry's libdisplay-info)
```

[`build.sh`](../packaging/ubuntu/build.sh) applies the series with
`git apply` (it carries binary test fixtures) on top of Ubuntu's source with
Ubuntu's own patches applied, leaves out the series' historical
`debian/changelog` entries, writes one entry naming the series commit, and
builds the source package and binaries. libdisplay-info's test suite runs;
Mutter's does not (`nocheck`), because it needs a display server and a
session bus. [`publish.sh`](../packaging/ubuntu/publish.sh) uploads each
`.deb`, and treats an already published identical file as done and a
different file under a published version as an error.

**When a patch stops applying.** An Ubuntu update can change the context a
patch expects. The run then fails with `build.sh: <patch> does not apply to
mutter <version>`, nothing is published, and machines keep the previous HDR
build (the pin holds them). Refresh the patch against the new source, raise
`REVISION`, and push.

## Non-goals

- **Not upstream.** These are downstream builds of Ubuntu's packages; the
  upstream-facing series in `patches/mutter` and `patches/libdisplay-info`
  are separate and unsubmitted.
- **No kernel.** The DisplayID luminance kernel patches (`patches/linux`)
  are not packaged here; a kernel is installed deliberately, per
  [operations](OPERATIONS.md).
- **No signing with a project key.** APT trusts the registry's own key,
  which Forgejo generates per owner.
