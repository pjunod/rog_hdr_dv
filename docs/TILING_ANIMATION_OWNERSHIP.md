# Tiling animation ownership — recoverable package candidate

**Updated:** 2026-11-02 · **Owner:** Sol 6.1, task `t_44f637a7`.
Current-main integration preserves the five reviewed patches and their 35
distinct valid offline passes. Astra's final evidence review approved donor
`4f71e166` on October 15; that frozen receipt's pending-review text is historical.
The recoverable Ubuntu candidate `51.26.10.6ubuntu+nativehdr2` is built (binary
SHA256 `43d4b3e1b015ede3aa14757273b5165144638c0d01ac77d6c5694e0ca93d5e74`),
with authenticated matching stock rollback retained, in draft Forgejo PR14.
Independent hdr-fable review verified source/package construction and requested
bounded documentation/provenance corrections; delta approval and the twelve new
packaging regressions remain pending. Nothing is installed, released to APT or
live-qualified by this work; PR16 history remains excluded.

## November 2 source and package delivery

[The delivery receipt](../evidence/tiling-animation-package-20261102.json)
binds the source, package artifacts and private complete inventories. The new
clone starts at current main, not at the donor history. Patch authorship and
bytes, replay helper, animation harness and historical receipts are retained.
The full replay again matches tree `03613a8236b6f200836df63acafa1e2359d94cb6`;
syntax checks passed with Node v26.8.1. No behavioral case was repeated.

Publication checks are distinct: the custom reachable/staged scan inspected
1,603 blob/commit objects with zero hits on `1bfc7de`; the coordinator's Gitleaks
new-history scan reported **one verified false positive**, the public stock
`keybindingHandler.js` SHA256 in `sources.json` line 44 at `572b745`. It is not a
credential. The private `PUBLICATION-SCAN-DISPOSITION.json` retains that finding
and the original report hash; this is not a claim that every scanner had zero
findings. No true secret or added infrastructure finding was identified.

The official enclosing source archive contains all 50 original extension files
byte-for-byte, including the dependencies used by the retained tests. Of all
86 upstream Git files, 85 match; Ubuntu filters only `.gitignore` and adds five
Meson/wrap files, enumerated and hash-bound in the complete source manifest.
The builder applies the patches inside the subproject, verifies all candidate
files/modes, and leaves those five packaging additions untouched. It does not
overlay an unowned or mutable installed extension directory.

Acquisition now also verifies the official `.dsc`, source tar and stock `.deb`
against SHA512 entries in complete Ubuntu APT indexes bound to a good archive
InRelease signature (retained October 11 metadata). This authenticates the exact
retained version, not a claim that it is today's latest package. The separate
maintainer signature on the `.dsc` still reports a missing key; it is not
relabeled as independently verified.

Native x86_64 construction uses the unchanged enclosing Debian rules and
`dpkg-buildpackage -us -uc -Pnocheck`. The candidate is
`gnome-shell-ubuntu-extensions 51.26.10.6ubuntu+nativehdr2`, architecture `all`.
It retains all other extension runtime files, the upstream Debian metadata,
maintainer scripts, dependencies, conflicts, replaces and provides. The only
changed existing payload files are the two callers, package changelog and
copyright; the reviewed helper is added. No other file/mode changes or removed
files remain. The final package uses Ubuntu's authenticated `pkgbinarymangler
158` distribution build wrapper with translation stripping enabled, matching
the stock package's omission of compiled languagepack catalogs. Its normal
233-entry raw-translations archive is retained privately in the `.changes`
closure. The earlier `nativehdr1` source-build artifacts, which added 113 `.mo`
catalogs, remain preserved as superseded evidence; they are not the candidate.
This reproduces the relevant declared Ubuntu packaging policy, not an attestation
of the original archive build's complete environment.
This is not a repack of the stock binary. The corresponding
native `.dsc`/source tar, `.changes` and `.buildinfo` are retained with the `.deb`.

No build dependencies were installed into the builder host. Three authenticated
missing tool packages were extracted into the task's own prefix; a private
copied dpkg inventory made their real declared versions visible to the normal
dependency check. There was no `--no-check-builddeps` bypass. Stock and candidate
builds succeeded. The initial candidate preparation failed because Node was not
installed in the builder; redundant syntax checking was removed from packaging
only, retaining the exact-tree Mac syntax receipt. A second attempt failed on
a GMT changelog trailer; the numeric-zone correction produced the first binary.
Both failed logs remain preserved. The final `nativehdr2` build succeeds with
the normal Ubuntu wrapper; all packaged extension JavaScript is byte-identical
to the reviewed candidate, and the complete stock/candidate diff contains only
the five paths above. An initial inspection overreached by requiring upstream
SVG bytes to survive the existing build transformations; the corrected check
requires reviewed JavaScript equality and full stock payload equality elsewhere.
The unsuccessful inspection is retained; it did not require rebuilding.
`nocheck` defers unrelated package tests; it
does not turn skipped tests into passes.

Forward and rollback APT simulations both resolve against the native builder's
authenticated archive indexes. The first simulations failed because the builder
does not have GNOME installed; failed-only retries explicitly request dependency
resolution with `--fix-broken`. These are builder-status simulations, not a
transaction on the laptop, an isolated maintainer-script execution test, or
proof of current-target solver readiness. Package runtime dependencies are
byte-identical to stock. The target-specific simulation remains part of the
coordinated acceptance window.

### Reproduction and non-executing installation handoff

Use the exact source replay described below. In an owned native Ubuntu build
environment with the package's declared build dependencies, provide the pinned
official `.dsc`, source tar and stock `.deb` in `INPUTS`. Keep them separate
from build outputs. Supply the six hash-pinned Ubuntu tool `.deb`s listed in
`scripts/package_tiling_animation.py:UBUNTU_TOOLS` in `UBUNTU_TOOLS`. Their exact
versions are `pkgbinarymangler 158`, `lockfile-progs 0.2.0build1`,
`liblockfile1` and `liblockfile-bin 1.17-2build2`, `advancecomp 2.5-1build2`, and
`optipng 7.9.1+ds-2build1`; these were authenticated through the same signed
archive metadata, not downloaded from an unpinned third-party build. The helper
refuses existing output directories and verifies every pinned input before
extracting source. A build without the declared packaging tool inputs fails
explicitly rather than silently producing the extra translation payload:

```sh
DEB_BUILD_OPTIONS='nocheck parallel=4' python3 scripts/package_tiling_animation.py \
  --inputs "$INPUTS" --candidate-repository "$REPLAY" \
  --output "$OWNED_WORK/package" --epoch 1793646237 --build \
  --ubuntu-packaging-inputs "$UBUNTU_TOOLS"
```

The optional `--build-admindir` is only for an explicitly isolated build-tool
inventory such as the one above, not the target package database. The script
extracts the pinned Ubuntu tools under `OUTPUT/build-environment/prefix`,
without installing them or registering diversions. `OUTPUT/build-environment/bin`
comes first on `PATH`; it exposes the unmodified `dpkg-deb` wrapper, its commands
and dependencies, with `dpkg-deb.pkgbinarymangler` pointing to the original tool.
The optional `dh_builddeb` wrapper is not exposed because it hardcodes `/tmp`;
the ordinary distro debhelper command remains in use. This source builds one
binary, whose task-local serialization file supplies the normal mangler lock.
Only `striptranslations.conf` changes from the authenticated defaults:
`enable: true` with `components: main`; sanity/file checks retain `enable: true`
and maintainer rewriting retains `enable: false`. Supported environment variables
`PKGBINARYMANGLER_CONF_DIR`, `PKGBINARYMANGLER_COMMON_PATH` and
`CURRENTLY_BUILDING_PATH` bind the local config/common and a local build-info
file (`Package: gnome-shell-ubuntu-extensions`, `Component: main`,
`Suite: stonking`). `TMPDIR` is a durable task-owned subdirectory. There is no
write to `/etc` or `/CurrentlyBuilding`, manual locale deletion, binary overlay,
or upstream source hook. Inherited mangler-bypass variables are removed.
`build-environment.json` records the complete tool hashes, configs, environment,
wrapper order and original tool path; `source-manifest.json` records source
provenance. The raw translations remain beside `.deb`, `.dsc`, source tar,
`.buildinfo` and `.changes`, whose entire checksum closure was verified.
The script
never installs a package, enables an extension or reloads a session. Existing
passing animation tests remain inherited; after independent review, the minimal
new lane is `test_tiling_animation_package` plus repository integrity once.

Before any later authorized installation, verify the kit manifest and retain
the exact stock `.deb` (SHA256
`6784ab2e51c29e75efb94ac4de224141741d51fe388f95d48f70e32272f35df5`),
package state, extension enablement and settings. In that coordinated window,
first simulate the exact local candidate with APT and inspect the complete
transaction; decline any unexpected removal or unrelated stack replacement.
The intended forward operation is ordinary APT installation of the candidate
`.deb`, not copying files into `/usr/share` or a user extension directory.
Rollback is the matching stock local `.deb` through APT with explicit downgrade
permission, followed by restoration of the saved enablement/settings. Any
logout/login or session reload requires the same separately coordinated window.
These are instructions only: no such operation has been executed here.

Visible tile/untile/center, native effects, rapid interruption, reduced motion,
disable/re-enable and SDR/HDR checks remain as listed below. Current warnings
still lack actor/start/completion attribution; neither the offline pass nor this
package proves their particular trigger. The independently delivered i915 VRR
fix is a separate kernel change, not an effect of this extension correction.

## Retained October source and qualification contract

The following source/qualification record is retained from October; November 2
package construction above supersedes its source-only delivery state, not its
behavioral or live-acceptance evidence limits.

### Defect and evidence boundary

Ubuntu Tiling Assistant metadata version 56, from
`gnome-shell-ubuntu-extensions 51.26.10.6ubuntu`, invokes Shell's private
`Main.wm._prepareAnimationInfo()` from tile, untile and center operations.
Both affected installed call-site files match Ubuntu's pinned v56 Git
source exactly; their digests and package acquisition identities are in
[the source registry](../sources.json). No unpinned upstream-main copy is used.
The source archive SHA256 agrees with its dsc; its maintainer OpenPGP signature
has not been independently verified (archive authentication is recorded above).
The package's wrap file pins upstream commit
`62b43228a8780bd435ec7a94892434e4950dcd41`.

Exact inspected Shell: `gnome-shell 51.0-2ubuntu3`; extracted
`ui/windowManager.js` SHA256
`b7a7e6ea249f77496f5b84f76d1b3ee7f14f2c3d659392513998b3c46827ae47`.
Its `_prepareAnimationInfo` freezes the actor and populates `__animationInfo`
and `_resizePending`. `_sizeChangedWindow` promotes it to `_resizing`;
`_sizeChangeWindowDone` calls `completed_size_change`. Mutter increments its
native `size_change_in_progress` only for an actual plugin SIZE_CHANGE start,
not every move or resize. Synthetic preparation is therefore not an owned
native start. Position-only moves also need not emit native size-changed.

Replacing Shell animation info is additionally unsafe: clearing a prior info
can complete an effect without removing prior pending/resizing membership.
This patch never replaces or clears any Shell animation data, and never
intercepts or overrides native completions. It does not patch Mutter's
counter clamp, silence warnings, disable animations or add a watchdog.

One retained real session warning proves an accounting imbalance, but lacks
an actor stack. Its particular caller/trigger is **not proven**. Four historical
atomic direct-scanout EINVAL failures remain a different hardware acceptance
item; this extension correction does not diagnose or resolve them. There is
no clean-log, colour-accuracy, optical or Dolby-completion claim here.

## Ownership and implementation

The patch adds `src/extension/windowAnimation.js` to the extension. One manager
is constructed and destroyed with TilingWindowManager. It owns:

- A per-actor snapshot widget, immutable source rectangle and cancellation record.
- An independent scalar snapshot of requested x/y/width/height, accessed through
  getters at the helper boundary. Default untile passes the real tile-created
  `Rect`, whose coordinates are prototype getters; enumerable spread would omit
  them. Caller mutation of that Rect cannot alter the saved visual intent.
- No live actor freeze reference at all (zero freezes, zero thaws). Synthetic
  effects never write live actor transforms, opacity, visibility or transitions.
- One compositor BEFORE_REDRAW callback, not a timer. It starts the overlay
  toward changed actual geometry present at that redraw, or the copied requested
  rectangle as a provisional visual destination when geometry is unchanged.
  It never retains a snapshot awaiting a delayed client resize signal; ordinary
  finite animation completion disposes of it even when the resize is refused.
- Transitions on its own overlay only. Cleanup destroys that overlay; it never
  removes or resets a live actor transition, including foreign replacements.
- Public native size-change/size-changed observations for collision avoidance,
  not accounting or ownership inference. Native start, map, minimize,
  unminimize, destroy and kill-window-effects cancel only extension records.
  The native pending interval prevents new synthetic preparation until native
  geometry notification. Existing foreign transforms/transitions are left alone.
- Actual Meta.Window position/size signals invalidate an active overlay when
  geometry changes to a different visual destination; matching changes may
  continue it. Separate observed geometry ignores duplicate old-frame signals
  during provisional motion. Unrelated pending movement
  and public display grab-op-begin cancel it before ordinary interactive changes.

The visual method retains an old-snapshot move/scale/fade and 250 ms ease-out
timing, revealing the stationary live destination underneath. Unlike the first
candidate, there is **no inverse live-actor transform**. Astra R1 demonstrated
that Shell's earlier size-change listener captures the live actor before any
extension listener can cancel; late cancellation cannot repair that snapshot.
An overlay outside the live actor cannot contaminate Shell's actor capture.
Reduced motion avoids positional/scale motion. Real unmaximize/fullscreen
effects are left to Shell rather than preparing a second effect over them.
Every tile/untile operation first cancels previous extension work, including
`skipAnim` and already-tiled rapid retile. If a previous record has not reached
its first redraw, that operation declines a replacement snapshot: public
geometry signals have no configure serial to correlate deferred A/B replies.
Stale stopped callbacks check record identity before cleanup.
The exact Ubuntu Shell environment returns a rejecting Promise for interrupted
`ease()` calls. Only the expected Gio cancellation of an owned ease is consumed;
unexpected errors still go to the extension error reporter. This is not native
warning suppression. The package/resource digests are in `shell_api_reference`
in the source registry; no target binary was executed during inspection.

The first-redraw rule addresses Astra R2 without pretending any size-changed
signal acknowledges the extension's request. Constrained dimensions already
present at redraw animate to their **actual** rectangle. If geometry is still
unchanged, Astra R3's finite visual-intent rule preserves delayed size-only
tile/untile motion: the overlay immediately scales/moves/fades toward the copied
requested rectangle for 250 ms. This provisional visual target is **not proof**
that the application accepted a configure. Later actual geometry matching that
destination may continue the effect; differing geometry cancels it rather than
animating a stale destination. No signal can resurrect a completed snapshot.
Refusal therefore leaves no waiting historical snapshot which an unrelated
later resize could accidentally animate. Ambiguous pre-redraw A/B replacement
is still skipped, and active supersession destroys only the previous overlay.

**Accepted source architecture, approved at round 4:** Astra round 2
accepted overlay-only rendering instead of inverse live transforms, but rejected
discarding unchanged first-redraw snapshots. The fourth patch implements the
finite provisional-target correction above. If an initial position-only portion
already changed, it uses that actual frame and a later differing size cancels it.
This is not identical to the former inverse-transform effect, nor a claim of
live smoothness. No timeout, blanket animation disable or native counter guess
is used. Astra round 4 closed all R1–R4 source findings. Offline host-double
qualification and later visible qualification remain separate requirements.

Ubuntu's subproject `meson.build` installs the extension source directory
recursively, so the new module needs no packaging file-list modification.
The patch applies inside `subprojects/tiling-assistant`, relative to its
upstream checkout. It is not a patch against the enclosing package root.

## Source identity and reproduction

Source candidate commit: `56448103ba956fb57c59abe40c80b9b9abdf01c2`.
Source tree: `03613a8236b6f200836df63acafa1e2359d94cb6`.
Five related patches: original ownership correction, typed cancellation-Promise
handling, review-driven overlay/geometry correction, finite provisional
visual intent for delayed sizes, then getter-backed rectangle value snapshots.
Earlier four patches remain byte-identical
for provenance; earlier candidates were not approved.
Patch SHA256 values respectively:
`2ba812231496c4c1428b529a9777c222e21ca3a57e35442452f891db20392abd` and
`f3a3bb408497c595dea361f1ee458dbab1db04cbfa7b029400010762ae2af6b3`, and
`ff4ae24cc1efbd253a31d28c613a5551fe2530861dd205e5ff2aa6d47bffc07e`, and
`68ecc0623977a14c0efe3523c7333babc1ee5dcd32aa625016215686539f67db`, and
`2de844f95bc767ef8517a51f8ea1aa1738610a301d48ed69e321d1b39397f710`.
The source commit is recorded as provenance; fresh replay may have a different
committer timestamp, so acceptance binds the exact candidate tree.

[Static preparation receipt](../evidence/tiling-animation-source-preparation.json)
records successful fresh patch replay/tree equality and JS syntax checks, not
behavioral tests or a GNOME session. SHA256SUMS was deliberately extended for
this new component and its review correction; no existing patch bytes or hashes changed.

For an owned durable v56 clone and a new owned output directory:

```sh
python3 scripts/prepare_tiling_animation.py \
  --base-repository /work/owned-tiling-base \
  --output /work/owned-tiling-replay \
  --receipt /work/owned-tiling-static-receipt.json
```

This only clones, verifies the pins/hashes, applies the series and runs
`node --check`. It never installs an extension, runs a unit or contacts a
session. Use durable agent-owned paths, not the owner's repositories or
system temporary directories. Mac paths under an owned collaboration
workspace are equally usable; no native mailbox is needed for this phase.

Attribution: existing Tiling Assistant context is Leleat's GPL-2.0 code
(2020–2025 per the Ubuntu copyright file). The new helper and test definitions
are GPL-2.0-only; the upstream LICENSE is retained in reconstructed source.
The patch does not copy Shell implementations into the public source tree.

## Focused regressions — 35 distinct cases have valid passing results

[The focused definitions](../tests/tiling-animation-ownership.mjs) load the
actual patched helper, TilingWindowManager, keybinding handler and utility
classes, with host API doubles. They extract the actual native resize methods
from the exact hash-bound Shell file supplied by the caller; they do not
hand-reimplement either lifecycle. The host actor/signal/ease doubles are
explicitly not a GNOME/Clutter runtime qualification.

Coverage includes:

- Actual tile, untile and center paths: zero native completions, no Shell
  animation info or pending/resizing memberships.
- Actual tile→finish→default untile using the real saved `Rect`, for synchronous
  movement and delayed same-position size: independent getter-value snapshot,
  post-prepare mutation of all four coordinates, finite move/scale/fade targets,
  matching late geometry, cleanup and zero native bookkeeping changes (Astra R4).
- Actual Shell native start/size-changed/completion: one completion, no extra
  completion after kill, and no replacement of native pending info.
- Native resize arriving during pending or active synthetic work; Shell-first
  maximize/fullscreen captures inspect live transform, opacity, freeze and rect.
- Rapid re-preparation, stale stopped callback and the actual rapid retile path.
- Pending/active interruption, minimize/map/destroy, unmanage and actor death.
- Late Wayland geometry/refusal, asynchronous A/B replies and actual tile→untile
  supersession; no stale waiting snapshot and zero synthetic freezes/thaws.
- Actual delayed same-position tile and size-only untile (`restoreFullPos:false`)
  must have finite scale/fade motion, with matching, constrained, refused and
  post-completion replies. Copied provisional targets and duplicate old-frame
  signals cannot turn visual intent into acknowledgement or resurrect snapshots.
- Ordinary geometry revisions, public user grabs and constrained actual sizes.
- Synchronous completion, reduced motion, extension disable and foreign
  live transition preservation (no synthetic writes/removal at all).
- Expected cancellation-Promise handling versus unexpected error reporting.

The initial batch ran once after independent source approval, against the exact
approved extension tree and retained Shell file:

```sh
node tests/tiling-animation-ownership.mjs \
  /work/owned-tiling-replay/tiling-assistant@leleat-on-github \
  /work/owned-shell-source/windowManager.js

```

Actual result: Node v26.8.1, 35 cases, 26 passed / 9 failed, exit 1. The
[path-neutral receipt](../evidence/tiling-animation-qualification-initial.json)
preserves input/review/output hashes, source trees and per-case results. Original
stdout/stderr and the exact review artifact remain in durable task-private
evidence, not public Git. The review was by hdr-astra (quota fallback), not an
invented hdr-fable approval; review artifact SHA256 is
`fee353ace5da8ef3922dbea9c3516371e0a51a767427d28172bb194528fcb714`.

All nine failures stop in actual Rect.equal at the missing Mtk.Rectangle.equal
host-double method before tile preparation. The owned harness correction adds
four-coordinate value equality only; production helper/callers/patches/pins and
all assertions remain unchanged. Exact case-name CLI selection rejects duplicate
or unknown names. Independent hdr-astra pre-retry review approved this correction
at delivery commit `744d13ccde2e65dc746eb0d6240322e6a46af755`, tree
`ef2be1298fa0c1d22d17573b5f3d770beadadbec`; corrected harness SHA256
`679ff51cbef6794e8191b78b0d553ef6adcc06cffe8f74cc0a2089408c451275`.
Review artifact SHA256:
`d5ed7a6d979c6d09f4f92a91e94ad66bed2240a604df52b3aeca1382c5bd81cc`.
The 26 original passes remain valid because none calls the added method.

After asserting the nonempty failed-case list was exactly the nine expected
names, the builder executed only those nine once with the reviewed harness,
unchanged approved extension tree and exact retained Shell file. Node v26.8.1
returned **9 passed, 0 failed, 26 skipped**, exit 0, empty stderr. The
[combined path-neutral receipt](../evidence/tiling-animation-qualification.json)
records the retained 26 passes separately from the nine retried passes, along
with both executions' input identities, review hashes, timestamps and raw-log
hashes. There are **35 distinct cases with valid passing results**, not a second
35-case clean run. The initial nine failures are not erased or relabelled.
Durable task-private `evidence/retry-r1/` retains exact argv/input receipt,
stdout, stderr and full receipt. Original evidence remains unchanged. No
successful behavioral cases were rerun; do not rerun them for another reviewer.

Retain raw stdout/stderr, source tree, patch/test hashes and engine version for
each retry. Reuse inherited static integrity PASS169 patches/7 series until
changed tracked documentation/receipts require one refreshed integrity check;
that check is not another behavioral suite. Final evidence review must also
reuse valid successful results rather than trigger a duplicate batch.

## Safe delivery and remaining acceptance

1. Independent Astra round-4 source approval preceded the initial batch;
   independent Astra harness correction review preceded the passing nine-case
   failed-only retry. All 35 distinct scoped cases now have valid passes.
   Final independent evidence review remains. Host-double results are not
   GNOME/Clutter runtime or visible-animation acceptance.
2. After qualification, integrate the additive registry/index/status hunks
   serially with any newer main work; do not import held PR16 ancestry. No PR
   publication, merge or deployment has occurred in this source phase.
3. Build a distinct, recoverable Ubuntu extension-package candidate from the
   exact enclosing package tar and patched subproject. Do not replace Shell
   or Mutter to deliver an extension change. Verify staged JS/import paths,
   metadata, package contents and solver result before any live change.
4. Before a coordinated install, retain and hash the exact original extension
   `.deb`, package state and extension enablement/settings. The original source
   archive is retained; that October source-only phase did not claim a binary
   rollback kit. November 2 now retains the authenticated stock binary and
   builder solver simulation, not an executed target rollback. No installer or
   profile activation is supplied here.
5. In a separately authorized owner/audio-coordinated session window, verify
   visible tile/untile/center in SDR and HDR, rapid retile, native maximize/
   unmaximize/fullscreen, interrupted effects, application close, reduced
   motion and extension disable/re-enable. Bind any lifecycle trace to actors
   and starts/completions; do not attribute the historical warning without it.
6. If rollback is needed, restore the exact saved original extension package
   and enablement/settings under the same coordination. Reload/login only in
   an explicitly coordinated window. Never blindly edit a running Shell.

No Apple TV, audio, live display, boot, package, session or installation action
is authorized or performed by this candidate. Broader KMS/OEM/optical and full
Dolby acceptance remain owned by their existing lanes.
