# Experimental2 qualified install/playback kit

Source/package independent review is approved by Astra (`t_4980e991`) at
`80c7ec0` / tree `f65e8768`. The single post-review native x86_64 batch passed
all **30 methods and 34 subtests**, with zero failures/retries. Actual package
extraction matched all six files, hashes and modes; its executable `--help`
returned 0. No launcher media trial, installation or device action happened.
See [qualification evidence](../../evidence/experimental-player-qualification.json)
for source identities, receipt hashes and deliberately scoped applicability.

**Done:** exact-package forward and reverse solver receipts also PASS on the
coordinator's coherent read-only host snapshot, 2026-10-13 19:54:13–19:54:18 UTC.
Forward adds only the launcher (`Inst`/`Conf`); reverse candidate-installed
**MODEL** removes only the launcher (`Remv`), never `autoremove`. Both exit 0,
with no runtime/compositor/audio changes; captured package status, indexes,
holds and auto/manual state are unchanged, with no active transactions/locks.
Four runtime binary hashes match the original successful stock trial.
Independent Astra recovery `t_53d49af2` verified all ten artifact hashes and
the actual control-derived copied status MODEL. Private receipt/archive and
verification hashes are bound in the qualification evidence; no raw host
status or device captures enter public source.

**Current:** qualification is complete for the experimental install/playback
kit, NOT an installation, corrected-launcher media execution or exercised
rollback. The coordinator owns the next actual installation/observed launcher
trial and must recheck the exact package hash and current scoped plan immediately
before installation. The solver receipt describes captured state, not future
state or permission to mutate a device. No successful checks were repeated.

The successful original silent stock Profile5 BL+RPU playback and positive owner
observation retain their actual identities; no successful trial or unit suite
is repeated. Upstream runtimes and source inventories are unchanged, so that
reviewed genuine consumer metadata/reshaping evidence remains applicable, not
an invented corrected-launcher execution receipt. Profile8 is source-supported
only; Profile7 FEL is excluded. Full creative trims/reference accuracy, exact
preferred black/object tagging/no-double-mapping, normal audio and optical
acceptance remain separate programme requirements.

[Usage](USAGE.txt) and [architecture/source inventory](README.md) describe the
unchanged package. Diagnostics are startup-only, bounded per run and advisory
once the child starts; late drag/drop/every playlist item is not confirmed.
These qualification evidence/doc additions change no implementation or package
bytes and invalidate no passing unit result. Programme-wide README/status pages
are maintained separately by the combined-delivery owner `t_aedfa272`.
