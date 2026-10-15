# Integrated nativehdr10 Ubuntu delivery

Status: **qualified local software package kit**, 2026-10-13 (`t_3d4a8bba`).
Astra independently approved construction (`t_6a2529f0`) and the narrow GTK
frames correction/package binding (`t_b8974f0d`). The approved affected
qualification has valid scoped receipts for all89 invocation requirements,
with29 historical runner methods retained. Actual host audit, coordinated
installation/recovery and on-screen trial are separate `t_15b6204a` work;
this first delivery does not wait for open Dolby. PR16 remains held; PR17
has not been changed or merged. No live device or display was accessed.

## One local kit and supported baseline

The handoff names one combined `nativehdr10-ubuntu105-qualified-kit.tar.gz`,
with an extracted directory, SHA256SUMS, MANIFEST.json, INSTALL.txt,
RECOVERY.txt, package inventory and source/evidence receipts. These artifacts
remain outside public Git; exact local paths and final hashes are posted on
the HDR board and FINAL-HANDOFF.txt. Do not substitute the earlier review kit
or choose a package by version alone: the unpublished corrected common-bin
package has the same version as the earlier provisional build. Verify exact
hashes and explicitly select its bytes, including a coordinated reinstall if
that same provisional version is already installed.

Supported baseline: Ubuntu26.10 amd64 and compatible GNOME51 dependencies;
Mutter `51.0-1ubuntu3+nativehdr10`, hdr9 library
`0.3.0-1ubuntu1~hdr9` for amd64 and i386. The actual frames package requires
`libgtk-4-1 >=4.22.0`, stronger than the API's4.20 minimum. Official i386
libc/libc-gconv2.44 and gcc-base/libgcc16.2 packages must match the host's
amd64 Multi-Arch versions. An actual host solver must confirm compatibility;
never force unrelated core-runtime downgrades, removals or boot changes.

Kit contents:15 candidate .debs (nine Mutter amd64/all, six library
amd64/i386), four official i386 dependencies and five stock compositor
fallback .debs. Only normally rebuilt mutter-common-bin changes from the
previous reviewed kit; the other23 .debs are byte-identical. Eight Mutter
artifacts retain their Ubuntu104 construction identity, not a fictitious
Ubuntu105 rebuild. The full fresh nine-package build remains separate
compiler evidence. Do not wildcard-install candidate/*.deb: development/test
packages are optional, and the two decoder architectures are alternatives.

## Exact source and construction provenance

PR17's upstream0001–0077 and lifetime0078–0087 patch bytes are preserved;
offscreen0088–0089 preserve source bodies and authorship with documented
mail-envelope renumbering. GTK0090 yields upstream tree
`c113c0ca9ac046c43f85992aa81ffb0b57633b36`. The alternative Ubuntu series
ports40 source changes after0061, then packaging/symbol/test corrections
0102–0104 and GTK0105, giving tree
`08740f943fb2ddda60411fa4d72bb4ccc4238e5f`. Both full90/105 canonical
replays equal their pins. The library remains unchanged tree
`96d65c11ed0f408792c41cd42c2866255b1089d0`.

[Integration provenance](../evidence/full-integration-source.json),
[Ubuntu port](../evidence/full-integration-ubuntu-port.json),
[amd64 packages](../evidence/full-integration-ubuntu-packages.json),
[i386/kit construction](../evidence/full-integration-i386-and-kit.json) and
[GTK correction](../evidence/gtk-frames-correction.json) bind inputs, builds,
replays, inherited authorship, failures and actual artifacts. Mutter builds
use optimized distribution flags, assertions and-Werror/nocheck. Normal i386
library packaging retains two upstream decoder ratio warnings; the shared
library-Werror target passed separately, without source drift or suppression.
Native ELF32 execution is on x86_64, never ARM emulation. Both library
architectures have93 equal exports and13 identical shared installed files.

## Actual affected qualification and retained evidence

[Qualification receipt](../evidence/nativehdr10-ubuntu-qualification.json)
records all89 latest execution identities, fingerprints and log/sidecar hashes:
63 Ubuntu Meson selections, six new runner methods, six package-helper methods,
and seven actual packaged-library ABI/numerical consumers per architecture.
The29 unchanged runner methods retain their original historical identities
under Astra's AST/reachability review. No duplicate upstream/full parser batch
ran, and old receipts were not rewritten as passes on a new tree.

The first26 helper/library invocations passed. A D-Bus socket pathname failure
prevented all63 Meson targets launching; only those failures retried under a
short owned TMPDIR. Stageviews then exposed GTK's direct deprecated-property
warning despite an environment-only retry. Its source correction uses the
exact former DARK/LIGHT semantics, not a warning filter, theme workaround,
watchdog or wider timeout. Four wholly and two partly issue4200-skipped monitor
selections required completion, not waiver.

After independent correction review, native request620750c2 completed only
seven authorized invocations in26.81seconds: full17-case stageviews and61
previously skipped monitor cases. All78 required TAP cases pass non-skipped;
five genuine prior monitor passes are excluded via GLib-s and retained.
Per-invocation guards verify absent absolute helper (including a dangling
symlink), new builddir CWD, exact corrected packaged helper
`d69defc9b5c7fd137a1d303ce5fe9a615bbd126cc8616d83bb9a5285895deba2`,
--no-rebuild, actual package DSOs inside the unchanged original D-Bus wrapper,
fatal-warnings and the original120s stage bound. Loader traces show all six
packaged DSOs actually initialized in every invocation. Diagnostic opt-in
is removed only for these seven; lifecycle diagnostic1 stays. Existing distro
DEB_ALLOW_FLAKY_TESTS=1 executes omitted X11 assertions in the six monitor
selections. No source test gate or warning suppression was introduced.

All82 unselected histories are unchanged. The ledger preserves160 actual
executions plus71 explicit invalidations, including earlier failures. A dirty
.pc quilt-bookkeeping prelaunch was refused before any execution/invalidation;
a clean exact source clone repaired that prerequisite without source edits.
All160 execution logs and retained Meson sidecars hash-verify. The old153-attempt
archive is unchanged; the new logs, guards and loader traces are separately
hash-bound in the combined kit.

Limits: `/color-pipeline/to-string-locale` remains an unexecuted locale-availability
case, not a behavioral pass. Intentional Wayland umbrella skips are covered by
real separate-case receipts. Four older successful selections had incidental
frames-child warnings; their monitor-model/DisplayConfig/scale/Wayland-tiling
assertions remain valid at old identities, not clean frames-runtime evidence.
The new fullstageviews supplies corrected frames coverage. No successful check
was repeated merely for a new package/source stamp or another reviewer.

## Dependency, installation and recovery boundary

The kit manifest points to exact-final solver evidence, not earlier historical
plans. Four disposable native solver plans exit0 with zero removals: amd64,
multiarch, stock baseline and candidate-to-stock reverse. The reverse uses an
exact-control candidate-installed **status MODEL**, yielding five stock
downgrades while real dpkg status stays unchanged. The matching candidate.status
is supplied with the receipt; evidence relocation did not trigger a solver
rerun. This is not an actual host post-upgrade or physical recovery receipt.

Five supplied official Ubuntu51.0-1ubuntu3 packages are a **stock compositor
fallback**, not restoration of the previous private HDR compositor. The trial
must preserve actual previous private package bytes/holds and each relevant
user's pre-upgrade monitors.xml (including original absence/owner/mode).
Older parsers reject targetpeakluminance, targetminluminance and hdrgamutsource;
restore the compatible backup before reverting compositor versions. An unaware
Settings client may replace/drop overrides on layout changes; no new Settings
UI is claimed.

INSTALL/RECOVERY give exact simulation lists and a bounded trial checklist.
Only the existing first-trial coordinator asks for actual target access and a
logout/recovery window after checking the ready kit. No installation, session
restart, optical calibration, Dolby agreement, upstream acceptance or held-PR
merge follows from source/package checks. Apple TV, AirPlay and CEC remain
entirely excluded. Broader programme requirements stay visibly open in the
[full handoff ledger](FULL_HDR_HANDOFF.md).
