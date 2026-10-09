# Provenance — imported work and evidence boundaries

**Imported:** 2026-10-08. This repository was created separately from Plurx
at the owner's request. It preserves current HDR source work and owns the
ongoing Dolby Vision and colour-quality investigation.

## Source origin

The prior workstation workspace is `~/code/libdisplay-info-hdr/`. Its root
was not a Git repository; it contains independent upstream/package checkouts,
patch exports, large build artifacts and historical documentation. It remains
intact. No source checkout, recovery package or signing key was moved away.

The current upstream library and Mutter exports were copied byte-for-byte.
The four frozen kernel patches were copied byte-for-byte from
`kernel/candidate/native-hdr1/`. Complete Ubuntu series were exported from
each authenticated source-import commit to the final delivered package source.
`sources.json` pins bases, candidate commits, candidate trees where available,
and series lengths. `SHA256SUMS` covers every imported patch.

The [userspace import receipt](../evidence/import-verification.json) records
exact tree equality after applying all four userspace series to their pinned
bases. The [kernel import receipt](../evidence/kernel-import-verification.json)
records exact matches for four affected source files. Its test Makefile hunk
could not be reapplied because that file is absent from the saved baseline
subset. This migration check is partial; the earlier full-build receipts
remain separate evidence. No new Linux compilation or hardware test ran.

Only the active source paths were imported. The earlier high-level native
HDR promotion proposal is superseded by the additive parser/explicit-consumer
design and must not be stacked onto these series.

## Historical validation evidence

Within the old workspace, the following records remain the original receipts:

- `docs/NATIVE_HDR_STACK_STATUS.md` — latest build and boot qualification.
- `docs/NATIVE_HDR_STACK_LIVE_TEST.md` — coordinated install and recovery.
- `evidence/native-stack/userspace-final/RECEIPT.md` and `ARTIFACTS.sha256` —
  exact library/Mutter source and package qualification.
- `kernel/NATIVE_HDR_IMPLEMENTATION_RECEIPT.md` — kernel reconstruction,
  compilation, parser tests, signing and NVIDIA evidence.
- `kernel/prior-work/` — byte-preserved original public patch messages.
- `evidence/native-stack/dolby-vision/` — earlier mpv sample result, which
  demonstrates partial processing and PQ output, not full DV acceptance.

Those paths refer to the historical workspace, not missing files in this
repository. Large evidence was not copied into Git. The current
[status](STATUS.md) summarizes the receipts and their known limitations.
New work must produce source-bound receipts rather than inheriting a pass
from a changed source tree.

## Attribution and licences

The first two kernel changes derive from Cristian La Spina's public series:

- [DRM luminance patch](https://lore-kernel.gnuweeb.org/intel-gfx/20260802170647.206880-2-cristian.laspina@kernel.srl/raw).
- [Intel backlight patch](https://lore-kernel.gnuweeb.org/intel-gfx/20260802170647.206880-3-cristian.laspina@kernel.srl/raw).

The adapted exports retain the original attribution and signoffs. Followup
validation and KUnit changes are separate patches with recorded assistance;
no new human signoff is implied by this import. Source-specific terms remain
in force; see [licensing](../LICENSES.md).

## Private device data

OEM Dolby/ASUS files and inspection hashes are retained on the laptop under
`~/.local/state/display-quality/2026-10-08/`. Hardware findings are summarized
in [hardware](HARDWARE.md) and [the investigation](DOLBY_VISION_AND_QUALITY.md).
No OEM DLL, profile payload, raw EDID, signing key, SSH credential or BitLocker
material is included in this repository.
