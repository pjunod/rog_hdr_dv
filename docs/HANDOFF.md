# Handoff — continuing this work in a new session

**Date:** 2026-10-11. Continuation owner from here: the bridged Sol 6.1 /
Opus 5.5 service (`rog_hdr_dv` project, a fresh clone per task). Read
[AGENTS.md](../AGENTS.md), [status](STATUS.md) and the topical documents it
links before changing anything. Everything needed is in this repository,
its draft releases or on the owner's machines; nothing depends on a previous
agent's workspace.

## Where things are

| What | Where |
|---|---|
| Source of record | `main`; patch series in `patches/`, pins in `sources.json` |
| Rebuild any pinned tree | `tools/reconstruct.py COMPONENT WORKDIR` (all five series reproduce their pinned trees exactly) |
| Build, test, package | `tools/` ([harness](DEVELOPMENT.md#build-test-and-packaging-harness-tools)) |
| Built packages | Draft releases `packages/hdr9-nativehdr8` (installed on lab5) and `packages/hdr9-nativehdr9` (installed on lab6): one tar each plus `SHA256SUMS` |
| Unreviewed work | nativehdr10 candidate, `patches/mutter` 0050–0061 (see [status](STATUS.md#nativehdr10--source-candidate-awaiting-adversarial-review)) |
| Status page | `docs/STATUS.html` in the repository; the owner's claude.ai workboard artifact is updated only from a session that owns it |

## Machines (addresses and keys from the owner; never in the repository)

- **lab5** (ASUS ROG GU605MZ, the Dolby Vision target): hdr9 + nativehdr8
  installed and held. Install kit `~/native-hdr-delivery-2026-10-10`;
  rollback packages `~/native-hdr-test-2026-10-08/candidate`. Two stopped
  containers are kept for the Dolby track (`claude-dv-activation-20261010`,
  `codex-wine-displaymonitor-20261009`). Private OEM files stay there.
- **lab6** (ThinkPad X1 Extreme, Intel, SDR panel): hdr9 + nativehdr9
  installed and held; kit `/root/native-hdr-delivery-2026-10-11/`
  (`candidate/`, `rollback/` with the stock packages, `INSTALL.txt`,
  `RECOVERY.txt`); eDP-1 in native SDR mode (persistent, via `gdctl`).
- Any live compositor install, display-manager restart or boot change needs
  a coordinated window with the owner logged out; keep the rollback set.

## Next tasks, in order

### nativehdr10 source candidate (2026-10-11)

Both parts are now Mutter patches 0050–0061. The pins name candidate
`fa7eb2cf55dd39464ef04042e3f085a5d6c18e5f`, tree
`18ba4b5a752f4ee383541757b20116060f18daf9`, and patches 0001–0049 are
unchanged. Every commit builds with warnings as errors, and the exported
series replays to the same tree; see the
[candidate receipt](../evidence/nativehdr10-source-candidate.json). The warm
native source is branch `codex/opus-nightlight` in the persistent peer work
directory; do not reconstruct over it. A Git bundle of the range is in the
ignored `.peer-linux/deliverables/opus-nightlight.bundle`.

No unit test has run on the candidate. Golden gdctl show fixtures are
source-derived expectations, not execution output. PR16 remains held unmerged.
No push, merge or display change is authorized. Ubuntu port/packaging and
optical acceptance remain separate stages; only Mutter's orig tar is recorded
in the offline Ubuntu cache, not the exact packaging imports.

1. **nativehdr10** ([contract](NIGHT_LIGHT_AND_OVERRIDES.md)). Sol's
   [validation receipt runner](NATIVEHDR10_VALIDATION.md) is integrated.
   Astra and Fable each review the same candidate adversarially. Fix the
   findings, rebuilding each affected commit. Then write the affected-check
   manifest and run it once through the runner on the native builder. Then
   the repository pre-merge lane and one substantial PR that depends on
   held PR16. After that, port to the Ubuntu series as 0062+ and package.
2. **Open Dolby Vision track, stage 1** ([contract](OPEN_DV_DISPLAY_MANAGEMENT.md)):
   a headless libplacebo harness and ΔE_ITP comparison, then the baseline
   against the private reference renders on lab5. Today libplacebo uses only
   level 1 maximum and average and no trims.
3. **With the owner present:** install nativehdr9 (or nativehdr10) on lab5,
   then the KMS HDR metadata on-screen comparison; the Windows trace of the
   OEM Dolby pipeline on lab5 (the owner runs a one-line elevated PowerShell
   command that enables OpenSSH for that session and authorizes the worker's
   own public key; traces stay private on the laptop).

## Owner decisions still open

- Access to M6 (AMD hardware), and whether it has a display and desktop.
- Colourimeter purchase (recommendation in [status](STATUS.md#owner-decisions-2026-10-11)).
- Upstream submission mechanics: the owner's identity and sign-off; agent
  `@invalid` authorship must not be submitted.
- Whether to delete a duplicate workboard artifact created by mistake.

## Commands

```bash
python3 scripts/check_repository.py                      # Repository gate (pre-merge).
python3 tools/reconstruct.py mutter /tmp/w               # Pinned tree, verified.
sh tools/build-upstream.sh /tmp/w/libdisplay-info /tmp/w/mutter /tmp/b mutter_51.0.orig.tar.xz
sh tools/test-mutter-colour.sh /tmp/b/mutter             # Colour fast lane (as root in the container).
sh tools/scan_publication.sh main..HEAD                  # Before any push.
```

`mutter_51.0.orig.tar.xz` comes from the Ubuntu archive URL pinned under
`ubuntu-mutter` in `sources.json`.
