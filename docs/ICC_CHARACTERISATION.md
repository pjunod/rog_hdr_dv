# ICC characterisation — inspect profile structure without applying it

Companion to [display diagnostics](DISPLAY_DIAGNOSTICS.md) (configured
display state) and [the quality plan](DOLBY_VISION_AND_QUALITY.md)
(physical acceptance): this guide explains the private profile report from
[the ICC inspector](../scripts/inspect_icc.py). OEM profiles and its reports
stay outside Git. The fixtures in
[the inspector tests](../tests/test_inspect_icc.py) are synthetic.

## Read a local profile into a private report

Use Python 3 and its standard library; no packages or privileges are needed.
Substitute a private source path and an existing private output directory.

```bash
python3 scripts/inspect_icc.py ~/private/profile.icc
                                                 # Print JSON to stdout.
python3 scripts/inspect_icc.py ~/private/profile.icc --output ~/private/icc-report.json
                                                 # Create a new 0600 report.
```

`--output` refuses existing paths and symlinks. Stdout inherits the privacy
of your terminal or redirection; shell redirection does not guarantee `0600`.
The script opens input read-only and nonblocking, requires a regular file,
rejects input symlinks, and limits input to 16 MiB. It detects changed file
size or timestamps during the read. It accepts at most 256 tag records and
65,536 entries per sampled ICC TRC; these are inspector resource limits.

Malformed structure returns `status: error` and a controlled `reason`.
Successful inspection exits `0`; input or profile rejection exits `2`;
output creation/write failure exits `1`. Paths and OS exception text never
appear in those reports. A successful parse is not full ICC conformance:
required-tag combinations and complete version-specific semantics remain
outside this inspector.

## Read the JSON as structure evidence

The report has `schema_version: 1` and `read_only: true`. Header fields are
limited to version, profile class, data colour space and PCS. Four-character
signatures use printable ASCII or `invalid_4cc`. Whole-file SHA-256 supports
private identity comparison; it can link captures and is not permission to
publish them.

| Field/tag | What the inspector reports | How to read it |
|---|---|---|
| `rXYZ` · `gXYZ` · `bXYZ` · `wtpt` | Signed XYZ and xy when XYZ sum is positive | RGB columns belong to the profile's PCS transform. They are not reconstructed native panel primaries or a measured gamut. |
| `lumi` | XYZ with Y in cd/m² | A profile luminance value, not a fresh optical measurement or current brightness reading. |
| `chad` | Signed 3×3 adaptation matrix | Context for adaptation to PCS D50. Reverse adaptation and native-primary reconstruction are not performed. |
| `rTRC` · `gTRC` · `bTRC` | Identity, gamma, sampled count/endpoints/nondecreasing flag, or parametric type and signed parameters | Describes the stored curve; parametric function validity and physical transfer accuracy are not evaluated. |
| `MHC2` | Minimum/peak luminance, matrix identity state, LUT entry counts, identity-at-stored-knots and nondecreasing flags | Microsoft pipeline metadata and adjustments; platform acceptance and actual loading are not evaluated. |
| `vcgt` | Presence only | No curve interpretation or calibration loading. |
| Other tags, including `DVB1` | Signature and byte size only | Proprietary semantics remain unknown. Presence does not establish Dolby Vision support. |

Sampled values and proprietary payloads are never dumped. The report omits
paths, descriptions, serials, model/manufacturer fields, raw profile bytes,
tag payload hashes and header profile IDs. Keep even these reduced reports
private because numeric characterisation and whole-file hashes may identify
a profile or unit.

## MHC2 follows the documented Microsoft layout

The decoder follows Microsoft's
[hardware calibration specification](https://learn.microsoft.com/en-us/windows/win32/wcs/display-calibration-mhc),
checked on 2026-10-09 UTC: a 36-byte header, relative offsets, a raw row-major
3×4 matrix and `sf32` LUT blocks. The effective matrix uses its first three
columns; the fourth is ignored. Zero matrix offset and zero LUT count denote
implicit identity. Stored LUT identity is exact at its knots; quantized
approximations are not labelled exact identity.

The matrix adjusts XYZ; LUT adjustments occur after wire-transfer encoding.
Those fields cannot be copied into an arbitrary Linux RGB/gamma stage and
assumed equivalent. Every embedded block is bounded within the tag; partial
overlap, invalid offsets, LUT values outside [0,1] and inconsistent absent
LUTs are rejected. Identical shared LUT blocks are allowed. These checks
interpret a layout, not certify a Windows-accepted profile.

## Structural rejection protects the read-only boundary

The parser requires the `acsp` header signature and exact declared/file size,
a complete tag table, aligned offsets and bounded payloads. Duplicate
signatures and partial tag overlaps are rejected; different signatures may
reference the exact same offset and size, as allowed by
[ICC.1:2022 §7.3](https://www.color.org/specification/ICC.1-2022-05.pdf).
Selected public types follow that specification's XYZ, curve, parametric
curve and fixed-point encodings. Unknown payloads are not interpreted.

The tool never installs or activates a profile, changes display state,
reads a network service, or claims calibrated accuracy. It does not prove
compositor consumption, HDR output, Dolby processing or optical performance.
Those need separate source-path and measurement receipts.

## Validate synthetic contracts at the agreed review boundary

```bash
python3 -m unittest discover -s tests -p 'test_inspect_icc.py' -v
                                                 # Synthetic regression suite.
python3 scripts/check_repository.py              # Repository/link contracts.
```

Fixtures cover shared tags, signed fixed-point values, supported curve types,
MHC2 identity and nonidentity transforms, malformed structure, private output,
nonregular input and source-file preservation. Run the checks after the
repository's adversarial review boundary; collect OEM evidence privately
after that review. Fixture results do not qualify a physical panel.

## Factory-profile receipt — identity MHC2 does not erase characterisation

After review and the affected synthetic tests, all four recovered factory
profiles parsed successfully. Each report was created privately with mode
`0600`; no profile was installed or associated with a display. Only this
summary is published; complete reports, payloads and per-profile fingerprints
remain private.

| Factory variant | Parsed structure |
|---|---|
| Intel standard and CMDEF | Three 256-entry nondecreasing sampled TRCs, with channel-specific nonzero low endpoints; `lumi` Y approximately 294.65 cd/m²; no VCGT |
| NVIDIA standard and CMDEF | Three 256-entry nondecreasing sampled TRCs, with channel-specific nonzero low endpoints; `lumi` Y approximately 373.12 cd/m²; no VCGT |
| Both CMDEF variants | MHC2 minimum approximately 0.005005 cd/m² and peak 616 cd/m²; effective matrix is identity; each channel's two-entry LUT is exactly identity at its knots |
| Both CMDEF variants | A 6,460-byte `DVB1` block is present; its proprietary contents remain uninterpreted |

The profiles contain meaningful standard characterisation, including different
GPU-route tone curves. Their MHC2 blocks do not contain a nonidentity
matrix/LUT calibration to copy into Linux. That does not make their standard
ICC curves identity, explain the proprietary block, establish their operating
conditions or prove which factory component consumes each field. Never apply
these TRCs directly to an arbitrary PQ-encoded KMS stage.

The source audit's missing display-characterisation/target-volume contracts
remain relevant. Optical measurement and an active-output trace are still
required before selecting or qualifying tuning for this physical unit.

## Measurement equipment

The owner currently has no colourimeter or spectrophotometer and is open to
obtaining one. Instrument selection follows the OLED measurement procedure and
required correction/reference data; no purchase is required for the ongoing
software work. Factory declarations and parsed profiles remain separate from
optical calibration of this unit.
