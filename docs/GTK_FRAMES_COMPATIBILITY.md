# GTK frames compatibility correction

Task `t_6341a7a5`, starting at qualification checkpoint `43a4af5`.
Programme status remains owned by qualification `t_3d4a8bba`.

## Done

The failed Ubuntu104 stage-views selection remains a failure. Removing an
unintended diagnostic opt-in did not fix it: the actual phase3 sidecar contains
GTK's direct warning to use `gtk-interface-color-scheme`. All 153 original
attempts and the old package archive remain preserved; nothing here converts
historical execution identities into new-tree passes.

Astra's decision `t_e5144474` specifies the exact DARK/LIGHT mapping. The
correction changes only `src/frames/meta-window-tracker.c` and `meson.build` in
each candidate. It keeps existing desktop preference interpretation, libadwaita,
theme selection, signal wiring and X11 helper restart behavior. GTK's old shim
maps false to LIGHT, not DEFAULT. The new enum/property first appeared in4.20.

Native baseline `d389230f` verifies GTK4.24.1 and the exact header hash, the old
Ubuntu104 source tree and successful optimized-Werror package compiler receipt
and log hash. This valid baseline is reused, not rebuilt before editing.
Upstream0090 yields tree `c113c0ca9ac046c43f85992aa81ffb0b57633b36`;
Ubuntu0105 yields tree `08740f943fb2ddda60411fa4d72bb4ccc4238e5f`.
Full local90/105 canonical replay reaches those exact trees. All old89/104 patch
bytes remain unchanged. The unchanged library is tree `96d65c11`.

Meson requires GTK4.20. Ubuntu's existing Build-Depends stays4.22, and the old
actual mutter-common-bin generated Depends already requires libgtk-4-1>=4.22.0.
The corrected package must re-establish that stronger runtime floor; a named
property alone would not introduce a symbol-version requirement.

## Compiled and constructed

Fresh isolated native package construction passed in521.11seconds, producing
nine real packages with normal dpkg/debhelper distribution flags, optimized-Werror
and nocheck. The upstream frames target also configured/compiled successfully.
Full native90/105 replay and exact canonical hash equality passed. All2305
compiled Ubuntu source files match the committed tree. No unit or display probe
ran. The stronger generated GTK runtime floor4.22.0 was reverified.

The full rebuilt artifacts are separately preserved. Final kit conservatively
replaces ONLY normally rebuilt mutter-common-bin; other8 Mutter and all six hdr9,
four official dependencies and five stock fallback packages retain exact bytes.
Their old construction identities remain explicit, not restamped as105 builds.
All142 nonframes .text/.rodata sections are byte-identical after the fresh full
rebuild, but some .dynstr/.dynamic/build-ID/debuglink and one D-Bus executable's
relocation/data layout differ. These compiled artifacts are not substituted for
previously observed inputs. Source changes remain only frames+Meson metadata.
Owned qualification binaries are copied from the immutable prior optimized
build, while the ordinary fallback holds exact corrected packaged helper bytes.
This minimizes genuine invalidation; the reviewer still owns retention approval.

Final exact-package amd64, multiarch and stock-baseline solver simulations pass
with0removals. A disposable candidate-installed MODEL passes five exact stock
downgrades, leaving real dpkg status unchanged. It does not prove actual-host
installation, prior private-HDR restoration or physical recovery.

## Current

Builder phase and independent Astra focused review `t_b8974f0d` are delivered.
Qualification`t_3d4a8bba` now passes the reviewed full17-case stageviews and61
previously omitted monitor cases in seven invocations (26.81s), with five old
successes excluded and82 other histories unchanged. Actual package/helper guards
and loader traces verify runtime binding. Original153-attempt archive remains
unchanged; all160 execution logs/sidecars verify. See the
[qualification receipt](../evidence/nativehdr10-ubuntu-qualification.json).
Local software kit is qualified; actual host audit/window/trial and publication
remain separate. No warning suppression, broader timeout or repeated-success batch.

## Remaining and retention

The focused reviewer decides source/package readiness, not installation.
Original qualification then executes only the failed full stage-views selection
and61 issue4200-skipped cases across six selections, excluding five already
successful subcases from Astra's machine allowlist. No blanket89 rerun.
Mandatory lifecycle diagnostic1/fatal-warnings policy remains unchanged.
Locale availability and historical skipped/partial receipts stay explicit.

The native source first tries the configured absolute helper, then the ordinary
uninstalled builddir fallback. Qualification must establish that the absolute
path is absent and the fallback contains exact corrected package bytes, use
Meson --no-rebuild, and bind actual packaged libraries inside the original D-Bus
wrapper. If the absolute path exists, stop and resolve binding; never override
production source or install a helper to make a test pass. This intended binding
is not a claimed helper execution before review.

Old artifacts/receipts retain their executing trees. Source, package and solver
reconstruction are separate from post-review units. No install, publication,
merge, physical/optical or Dolby claim follows. PR16 stays held. No credentials,
Apple TV or other device access is part of this task.
