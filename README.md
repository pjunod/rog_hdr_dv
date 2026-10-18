# rog_hdr_dv — Linux HDR, Dolby Vision and display quality

Linux display-stack work for the ASUS ROG Zephyrus G16 GU605MZ, with reusable
fixes for native DisplayID HDR detection and a programme for accurate colour,
panel calibration and full Dolby Vision. macOS-like consistency and ease of
use are the quality reference. Plurx is one consumer; this repository owns
the operating-system display work independently.

**Current status:** the patched kernel (`nativehdr1`), the hdr9 library and the
`nativehdr8` compositor are installed (the compositor and library since
2026-10-11), and Secure Boot is enabled. The owner reported working HDR10 on
the earlier stack; on the new compositor the HDR session runs in BT.2100 mode
and the owner accepted the picture. Full Dolby Vision, measured calibration
and remaining transition/resume acceptance are unfinished. The next batch
(`nativehdr9`) widens the colour targets to ordinary HDR and wide-gamut
hardware; a second laptop (`lab6`, Intel graphics, SDR panel) is the test
machine for that. The earlier mpv
DV-to-PQ sample does not qualify full Dolby Vision.

Start with [status](docs/STATUS.md) for what is proven, then
[hardware](docs/HARDWARE.md) for the exact panel and OEM findings.
[Architecture](docs/ARCHITECTURE.md) explains responsibility boundaries.
[Development](docs/DEVELOPMENT.md) covers source reconstruction and checks;
[operations](docs/OPERATIONS.md) covers inspection and recovery.
[Dolby Vision and image quality](docs/DOLBY_VISION_AND_QUALITY.md) is the
investigation and staged plan. [Provenance](docs/PROVENANCE.md) records where
the imported work came from and how to interpret its evidence.
[Licensing and attribution](LICENSES.md) explains the retained upstream terms.
[The status page](docs/STATUS.html) shows the active workboard;
[review findings](docs/REVIEW.md) records review dispositions and validation.
[Display diagnostics](docs/DISPLAY_DIAGNOSTICS.md) explains the read-only
Linux inspector and bounded Wayland colour probe, including their privacy-filtered reports.
[The Dolby activation probe](docs/DOLBY_ACTIVATION_PROBE.md) documents the
isolated Windows API experiment, compiler receipt and remaining contracts.
[Wine API contract](docs/WINE_API_CONTRACT.md) isolates the missing file API
from Dolby activation. [ICC characterisation](docs/ICC_CHARACTERISATION.md)
explains private inspection of factory profile data.
[The colour pipeline audit](docs/COLOUR_PIPELINE_AUDIT.md) traces encoding,
target-volume reporting, calibration and KMS metadata in pinned source.
[Native luminance API](docs/NATIVE_LUMINANCE_API.md) documents the additive
physical-declaration API and its source-only qualification boundary.
[Mutter target feedback](docs/MUTTER_TARGET_LUMINANCE.md) specifies independent
physical-target state, immutable descriptions and their qualification.
[Wine file API implementation](docs/WINE_FILE_FROMAPP.md) scopes the missing
function correction and its desktop-only compatibility evidence.
[HDR reference corpus](docs/HDR_REFERENCE_CORPUS.md) defines reproducible
synthetic PQ inputs and the separate official-reference workflow.
[Panel measurement](docs/PANEL_MEASUREMENT.md) defines the optical procedure,
initial accuracy targets and evidence required before calibration claims.
[Native target gamut](docs/NATIVE_TARGET_GAMUT.md) specifies lossless physical
chromaticity declarations and independent compositor feedback.
[Wine monitor discovery](docs/WINE_DISPLAY_MONITOR.md) defines the next
activation prerequisite, truthful topology and descriptor handling.
[HLG and tone mapping](docs/HDR_MAPPING.md) defines HLG decoding, mapping
highlights to the panel's declared target and compressing out-of-gamut
colours toward its declared gamut in the compositor, and defines the
deferred output-characterization contract.
[Display target sources](docs/DISPLAY_TARGET_SOURCES.md) extends those targets
beyond the ROG panel: DisplayID or CTA-861 luminance on any HDR output, and
the base EDID gamut in the native SDR mode, for general availability.
[Open RPU-aware display management](docs/OPEN_DV_DISPLAY_MANAGEMENT.md) is the
generally available Dolby Vision track: player-side mapping from the RPU,
validated against Dolby's reference renderer.
[Headless stage-1 harness](docs/DOLBY_HARNESS.md) provides the compiled baseline
consumer and BT.2124 comparison contract; adversarial review and units are pending.
[OPEN XML205 diagnostic](docs/OPEN_XML205_CANDIDATE.md) adds isolated analytic
PQ-Hermite L1 and explicitly hypothetical target-PQ SOP, with separate ABI362,
DVH3 and source-bound receipts. Its native warnings-as-errors source batch compiled;
its later reviewed/qualified three-variant303 experiment failed accuracy and does
not change the stock baseline. [Absolute-PQ SOP alternative](docs/OPEN_ABSOLUTE_PQ_SOP.md)
adds one previously documented public embodiment in isolated ABI364/DVH3 variant3.
Native full/noDV and matched consumer compilation passed with warnings as errors.
Its single development comparison FAILED unchanged limits (mean9.6113/p9516.3684).
Independent source review and new affected units remain pending. It is not
qualified/merged/packaged/released/installed.
[Source-grounded public RGB mapping](docs/PUBLIC_RGB_MAPPING.md) compares two
whole published chains against immutable official outputs, with explicit
continuous-XML adaptation and real ABI365 RGB/ABI366 scalar-Y PQ-pre/rational paths.
Its [genuine second-shot diagnostic](docs/PUBLIC_RGB_MAPPING.md#genuine-second-shot-development-evidence-run346)
retains the nonzero-SG714 failure and exact acquisition/interval evidence; it is
development evidence, not final accuracy acceptance.
Native full/noDV and consumer compilation passed; one ABI366 development render
tracks the scalar diagnostic closely but sampled agreement still fails. A fixed
cached HALF-interval audit is diagnostic only, not a fitted replacement curve.
Full-raster/independent accuracy, review, one affected batch and Ubuntu delivery
remain required. This active lane does not stop at an experimental operator.
[Authored-master baseline](docs/AUTHORED_MASTER_BASELINE.md) now includes a
source-only parser2/export4 shot-inheritance extension with explicit provenance
and no invented frame UUID; new units remain deferred. It separates sparse
P3D65/PQ HALF/XML2.0.5 transport from unresolved trim processing and acceptance.
Its isolated follow-up binds ordinary nonzero-frame references explicitly while
preserving v1 frame0 receipts; the actual frame0 numerical failure remains and
frame256 source review/affected validation are still pending, not Dolby parity.
[Night Light and target overrides](docs/NIGHT_LIGHT_AND_OVERRIDES.md) specifies
Night Light in linear light for HDR and per-monitor target overrides, and
records their implementation as Mutter patches 0050–0077, pinned at native
`de09d575` / tree `058bbf97`. Both adversarial reviews and focused correction
reviews are delivered, and every required unit check now has a valid passing
receipt: **42 native invocations and 29 runner methods**. Only the 17 approved
failed/genuinely invalidated checks were retried after the latest corrections;
the other 54 histories retain their actual executing trees and reviewed
retention grounds. All 92 execution logs are hash-verified. Repository integrity
is a separate final gate, recorded outside tracked source after the final
evidence/docs commit. Final evidence verification and PR preparation remain
the delivery child's work; PR16 stays held. No packaging or deployment occurred.
The earlier work-in-progress directories under `wip/` now only
point to it.
[nativehdr10 validation receipts](docs/NATIVEHDR10_VALIDATION.md) describes
the runner that executes a reviewed list of affected checks once. It records
source-bound receipts, so later runs retry only failed or explicitly
invalidated checks. All 29 individual runner methods passed in the first
Linux batch; [batch evidence](evidence/nativehdr10-validation-attempt1.json)
retains the 71 original attempts and two native failures.
The [focused retry evidence](evidence/nativehdr10-validation-attempt2.json)
preserves all original histories and the two new attempts without repeating
successful checks or rewriting their executing source trees.
The [next gated retry evidence](evidence/nativehdr10-validation-attempt3.json)
accounts for all required checks, their actual executing trees and Fable's
retention tiers without treating pending invalidated checks as accepted passes.
The [final scoped retry evidence](evidence/nativehdr10-validation-attempt4.json)
records all 17 new passes and all 71 valid unit receipts, with unchanged retained
histories, exact fingerprints, log hashes and per-ID retention rationale.
[Cancellation corrections](evidence/nativehdr10-cancellation-corrections.json)
retain compiler/replay evidence for the base async defects exposed during validation.
The [delivery verification](evidence/nativehdr10-delivery-verification.json)
records the read-only check of every final receipt and the decision to publish
the candidate as a draft PR stacked on the held PR 16.
[Handoff](docs/HANDOFF.md) is the continuation brief for a new session or
agent: state, next tasks, environments and commands.

## Work with the repository

This is a source-and-research repository, not a one-command system installer.
It requires Git and Python 3 for repository checks. Rebuilding the components
requires their pinned Linux build environments and dependencies.

```bash
python3 scripts/check_repository.py  # Check patches, manifest and doc links.
git status --short                  # Inspect local work before changing it.
```

No check installs packages, changes the display, or contacts the laptop.
Follow [development](docs/DEVELOPMENT.md) to apply a specific series in a
disposable source checkout. Follow [operations](docs/OPERATIONS.md) before
any live compositor or kernel update.

## Repository layout

- `patches/libdisplay-info/` · `patches/mutter/` — current upstream-facing
  proposals, with exact bases in `sources.json`. The Mutter series carries
  the whole colour programme ported to upstream main; neither series has
  been submitted upstream.
- `patches/ubuntu-libdisplay-info/` · `patches/ubuntu-mutter/` — complete
  local changes from authenticated Ubuntu source imports, including the
  delivered prefixes and explicitly marked unreleased candidates. In
  `sources.json` the `delivered_*` fields pin the earlier delivered prefix
  (now the rollback); the installed release is the candidate. These are alternative packaging paths to the upstream series.
- `patches/linux/` — four native luminance/backlight/parser-test patches.
- `patches/wine/` — bounded Windows API compatibility work for processor investigation.
- `sources.json` · `SHA256SUMS` — source identities and patch integrity.
- `docs/` — maintained technical documentation, indexed above.
- `evidence/` — small reproducible migration/validation receipts. Large or
  private captures, OEM binaries and signing keys do not belong in Git.
- `scripts/` — repository validation, with no installation side effects,
  and the nativehdr10 receipt runner, which executes only the commands in a
  reviewed manifest.
- `tools/` — the reconstruction, build, test and packaging harness for
  disposable containers ([development](docs/DEVELOPMENT.md#build-test-and-packaging-harness-tools)).
- `wip/` — unreviewed work in progress, kept out of the pinned series.
- Built packages are attached to draft GitHub releases (private to
  collaborators), not committed.

## Progress

- [x] Preserve the current HDR source series independently of Plurx.
- [x] Record the running stack and exact-panel OEM configuration findings.
- [x] Retain patch authorship and identify the historical evidence location.
- [ ] Complete HDR/SDR, brightness, DPMS and suspend/resume qualification.
- [ ] Establish a full Dolby Vision processor path for the internal panel.
- [ ] Implement and measure general colour consistency and panel calibration.
- [ ] Integrate and qualify multiple apps, including Plurx.
- [ ] Package the complete solution and pursue upstream acceptance.
