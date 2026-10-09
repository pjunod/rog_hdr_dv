# Native luminance — preserve physical declarations for explicit consumers

The additive libdisplay-info API exposes DisplayID 2 physical luminance without
manufacturing CTA desired-content metadata or selecting a rendering target.
This supplies the missing data boundary identified by the
[colour pipeline audit](COLOUR_PIPELINE_AUDIT.md). It does not change compositor
rendering, establish calibration, or enable full Dolby Vision.

## API and interpretation

`di_displayid2_data_block_get_luminance()` returns an object owned by the parsed
DisplayID object. Its lifetime ends when that parsed object is destroyed.

| Field | Meaning | Presence flag |
|---|---|---|
| `min_luminance` | Minimum declared luminance, cd/m² | `has_min_luminance` |
| `max_luminance_full` | Maximum at full coverage, cd/m² | `has_max_luminance_full` |
| `max_luminance_10pct` | Maximum at 10% rectangular coverage, cd/m² | `has_max_luminance_10pct` |

These are minimum-guaranteed physical declarations from firmware, not measured
values for a particular unit. Independent `float` fields retain binary16
fractions, positive zero and subnormal values exactly. Negative values,
including the negative-zero do-not-use sentinel, infinities and NaNs clear only
the corresponding presence flag; its scalar remains zero. A consumer must
check the flag, not use zero as an absence test.

The parser accepts the known 29-byte Display Parameters payload, revisions 0
and 1 with either image-size unit flag, and the minimum-guaranteed luminance
class. It returns NULL for other tags, lengths, revisions or classes. Unsupported
optional data remains an opaque block with the same legacy diagnostics and
extension status. Existing envelope truncation errors remain errors.

The low-level API deliberately preserves independent declarations even if their
ordering is physically inconsistent. A rendering consumer must validate range
relationships and choose its target policy. Presence of luminance data does
not imply PQ, HDR, bit depth or gamut support. Existing public structs and
high-level CTA getters are unchanged; private parsed storage and one public
function are added. The existing `di_*` export map covers the new function.

## Source and package boundaries

[sources.json](../sources.json) pins the complete alternative series. The
upstream candidate adds API patch 5 and fixture correction 6; the Ubuntu
candidate adds corresponding patches 15 and 16. All 28
original imported patch files remain byte-identical. Their import receipt
continues to describe those historical candidates.

The Ubuntu prefix through patch 14 is the delivered hdr6 source. Patch 15
adds an **UNRELEASED hdr7** changelog and introduces the symbol at
`0.3.0-1ubuntu1~hdr7~`. That records the new ABI requirement without claiming
that installed hdr6 exports it. Candidate and delivered pins are separate in
the manifest. Neither new candidate is installed or package-qualified.

| Source | Candidate commit | Candidate tree |
|---|---|---|
| Upstream | `1ddb6ea03a59d2758d28c994eb5d91f969f36314` | `b9bb408efc36d2c139141a9d57af6800543eac43` |
| Ubuntu | `051af9ad21839a017f9fcc6d2f291902eb82136e` | `dd88089aed845002aae17b08ca4cbc9939f3a476` |

## Qualification

The [compiler receipt](../evidence/native-luminance-compile.json) binds source
commits, trees and archive hashes. Both baselines compiled before edits. Both final candidates and their new
regression executable compiled with GCC 12.2, Meson 1.0.1 and Ninja 1.11.1,
using `-Dwerror=true`, on Linux ARM64 and Docker-emulated Linux x86-64.
The compiler used `-Wall -Wextra -Wpedantic -Werror -std=c11 -Wconversion`.
Only source archives entered the disposable containers; no credentials,
repository metadata or OEM payloads were transferred.

Independent adversarial review approved the API and the subsequent fixture-only
correction with no findings. The [focused test receipt](../evidence/native-luminance-tests.json)
records all 12 selected tests passing across the initial run and two failed-test-only
retries. The synthetic CTA fixture initially set a reserved colourimetry bit;
the fix changes test data and assertions only. The focused
`displayid2-luminance` regression exercises the production parser/public API
with synthetic EDID, including fractional and exceptional values, independent
field presence, supported/unknown formats, truncation, object lifetime and
unchanged high-level CTA semantics with either extension order. Existing
parser, legacy-consumer and ABI regressions accompany it on each source base.
The [legacy binary receipt](../evidence/native-luminance-legacy.json) records
both consumers built against the previous libraries passing against the new
libraries on ARM64. These production library inputs are unchanged by the fixture
correction. The [reconstruction receipt](../evidence/native-luminance-reconstruction.json)
records complete patch-series equality with both final candidate trees. No
passing suite was rerun for the fixture correction. i386, full Debian packaging
and physical-output acceptance remain outstanding. The two owned library build
containers were removed after retaining receipts.

## Next consumer boundary

Mutter needs a physical target volume separate from its PQ encoding state.
Encoding normalization stays at the existing PQ range. Output and preferred
Wayland descriptions need immutable target snapshots and their own identities,
so an existing description never changes when the target changes. Target-only
notifications must reach primary-monitor fallback surfaces and end with the
required `wl_output.done`. Shader state and scanout encoding comparisons should
remain unaffected by a target-only change.

Absent data remains absent internally; required protocol target events use an
explicit theoretical encoding fallback. Firmware declarations must not become
content mastering metadata, fabricated MaxCLL, or a calibration claim. Target
selection, tone mapping, ICC application and optical validation remain separate
work, with acceptance tracked in [status](STATUS.md).
