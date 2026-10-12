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
| Candidate being corrected | nativehdr10, `patches/mutter` 0050–0074 with reviewed corrections (see [status](STATUS.md#nativehdr10--adversarial-findings-being-corrected)) |
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

The first affected batch passed 69/71 checks on native `9570f9bb`/tree
`ac02a18f`; all29 runner methods and40 native invocations passed, including
gdctl, capture, isolated override and remaining backend/cursor cases. Colour
channel-bound and D-Bus restored-peak wait failed; acceptance is incomplete.
See [all original attempts](../evidence/nativehdr10-validation-attempt1.json).
The first restricted retry on native `a8847717`/tree `9111578e` passed
`color-hdr` and the target-overrides D-Bus case, then failed the subsequent
has-external-monitor case on a fatal existing-colord-device lookup. Latest
receipts: 70 passed, one failed; all 73 execution logs hash-verified and all
69 non-retried histories unchanged. See the
[retry evidence](../evidence/nativehdr10-validation-attempt2.json).
PR16 remains held unmerged.
Corrections 0072–0074 are now integrated at native `980bb21`/tree `41605eb0`;
Fable approved them and exactly 17 genuinely invalidated checks. The required
two-check gate passed all 20 color-management cases but monitor-dbus exited
245 after reconnect, with no old fatal-colord warning printed. Dependent 15
checks did not run. Raw ledger70pass/1fail is not acceptance: **55 valid passes,
one failure, 15 pending-invalidated**. All75 execution logs are hash-verified;
69 histories unchanged. See the
[latest gated retry](../evidence/nativehdr10-validation-attempt3.json).
No push, merge or display change is authorized. Ubuntu port/packaging and
optical acceptance remain separate stages; only Mutter's orig tar is recorded
in the offline Ubuntu cache, not the exact packaging imports.

1. **nativehdr10** ([contract](NIGHT_LIGHT_AND_OVERRIDES.md)). Sol's
   [validation receipt runner](NATIVEHDR10_VALIDATION.md) is integrated.
   Astra and Fable delivered both reviews and focused reports. Opus delivered
   corrections 0062–0068 at native `9570f9bb`/tree `ac02a18f`, now integrated
   into canonical patches/pins with individual -Werror builds and replay.
   Astra approves the anchored production design; 0068 hardens capture sanity.
   Fable confirms runner `cc82113`; mask/replay hygiene is fixed in `e4f981d`.
   Corrections 0069–0071 are now pinned at native `a8847717`/tree `9111578e`,
   individually built and replayed. 0070 fixes upstream restore-idle bookkeeping,
   separately from HDR; 0069/0071 repair precision and confirmation fixtures.
   Fable `t_bedcc81f` approved only the two failed IDs for retry. Its retention
   decision preserves original native passes at `ac02a18f`, not fictional
   passes on the new tree: test-only binary identity and production-callback
   source unreachability are distinct grounds. For 0072–0074 Fable `t_6b592492`
   retains25native receipts by source-unreachability or virtual-monitor observable
   equivalence, keeping actual trees. Sol owns Mac integration/evidence/status;
   Opus exclusively diagnoses the new monitor-dbus exit245 with compilation/export
   only (`t_ef832f3b`). Fable `t_c88207c7` reviews correction and recomputes scope.
   Preserve colour-management's new41605eb0pass and colour-hdr's9111578epass unless
   genuinely invalidated; the dependent15TEST checks still require valid receipts.
   Same persistent ledger: `/work/hdr-nativehdr10-20261011/validation/receipts.json`,
   SHA256 `480cbb50699512fce164b4ae23fe927de0fd51e77fc339856d893b383e0b9f13`.
   Full export and review/hash inventories: ignored
   `.peer-linux/deliverables/nativehdr10-validation-attempt3.tar.gz`
   (SHA256 `bcf35417ae5c01dfea7dbcccea5ebc0a384acbef593d42b1db6597761dabc7b8`).
   The exact17 manifest was split required2/dependent15 with identical objects,
   sources, ledger/runner to enforce a required-pass gate without runner edits.
   No further retry before focused diagnosis/review. Never reuse the executed
   retry3 manifests to accidentally rerun successes; preserve their evidence.
   Do not reconstruct, edit the frozen runner or start another full batch.
   Final integrity runs after final evidence
   and docs commit with receipt outside tracked source. Then
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
