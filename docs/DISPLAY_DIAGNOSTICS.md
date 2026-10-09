# Display diagnostics — capture evidence without changing the display

Companion to [operations](OPERATIONS.md) and
[the display-quality plan](DOLBY_VISION_AND_QUALITY.md): this guide explains
what [the read-only inspector](../scripts/inspect_display.py) captures and
how to interpret its JSON. Synthetic regression coverage lives in
[the diagnostic tests](../tests/test_inspect_display.py). Physical laptop
qualification remains separate from fixture results.

## Run from the current Linux desktop session

Use Python 3 with its standard library. No package installation, downloads,
root privileges or `sudo` are needed. `gdbus` and `dpkg-query` are optional;
a missing tool yields an explicit `unavailable` result.

```bash
python3 scripts/inspect_display.py                  # Print JSON to stdout.
python3 scripts/inspect_display.py --timeout 3      # Bound each command to 3 s.
python3 scripts/inspect_display.py --output ~/display-report.json
                                                  # Create a new private file.
```

The default command timeout is 5 seconds; permitted values are 0.1–30
seconds. Each subprocess is limited to 65,536 combined stdout/stderr bytes.
Command stderr is never included in the report. Sysfs files are limited to
65,536 bytes; profile hashing is limited to 16 MiB. Inventories are limited
to 32 devices/profiles each. Multiple display profiles require multiple
bounded queries, so the full invocation can take longer than one timeout.

`--output` creates a new file with mode `0600` (the owner's read/write
permissions). It refuses existing paths and symlinks to avoid overwriting
private evidence. Its parent directory must already exist. The report is
private local evidence: review it before sharing and keep captures out of
Git even after redaction. Stdout inherits your terminal or redirection's
privacy; shell redirection does not guarantee mode `0600`.

GNOME inspection uses `gdbus --session` only when the current process already
has `DBUS_SESSION_BUS_ADDRESS`. The script never invents a session bus address,
selects another user, copies their environment or reads `/proc` to find a
session. Run it in a terminal belonging to the desktop you intend to inspect.
An SSH session without that bus environment produces unavailable GNOME
evidence while retaining the kernel/sysfs evidence.

On macOS and other non-Linux platforms, the report says
`status: unsupported_platform`, performs no Linux probes, and exits with
code 2. A Linux report exits with code 0 even when individual probes failed;
inspect their statuses. Failure to create the requested output file exits
with code 1.

## Read the schema and each evidence class

The top level has `schema_version: 1`, `read_only: true` and
`capability_verdict: not_evaluated`. Consumers should check the schema before
using fields. Successful observations have `status: ok`; absent sources have
`status: unavailable`; permissions, timeouts, malformed responses and other
probe failures have `status: error` with a short `reason`. An empty successful
inventory means that source returned no items at capture time.

| Evidence | What it records | What it proves and what remains open |
|---|---|---|
| `kernel_release` / `os_release` | Kernel release and selected distribution identity/version fields | Identifies software context; does not establish patch presence or correctness. |
| `gpus` | DRM card, sysfs PCI vendor/device IDs and bound driver name | Identifies GPU routes exposed by the kernel; does not establish which GPU composes an application. |
| `drm_connectors` | Connection/enabled states, advertised mode dimensions, EDID byte length and SHA-256 | Supports connector/baseline comparison; modes are not a refresh-rate or HDR acceptance receipt. A hash is identity evidence, not an EDID capability interpretation. |
| `backlights` | Interface/type, requested `brightness`, `actual_brightness`, `max_brightness` | Captures driver control units, which may differ from each other; units are not measured nits or a calibrated transfer curve. |
| `packages` | Installed matching display/media/kernel package versions from dpkg | Identifies installed packages; an installed kernel may not be running. Non-dpkg systems remain unavailable. An unmatched package glob may coexist with valid rows. |
| `gnome` | Connector, active mode dimensions/refresh/preferred scale, selected and advertised colour-mode integers | Captures Mutter's current reported state. Preferred scale is a mode recommendation, not necessarily the active logical scale. A BT.2100 mode does not prove application encoding, panel mapping, calibration or full Dolby processing. |
| `colord` | Display-only profile associations, hashed profile names, readable profile file lengths/SHA-256 | Records assigned profile identities, indexed in colord response order. The index does not identify a DRM connector. Assignment and matching bytes do not establish compositor/application consumption or optical accuracy. |

Mutter's colour-mode identifiers currently describe default (`0`), BT.2100
(`1`) and SDR native (`2`); unknown integers remain visible for later
interpretation. Missing properties remain absent. The parser follows the
[upstream DisplayConfig interface](https://github.com/GNOME/mutter/blob/main/data/dbus-interfaces/org.gnome.Mutter.DisplayConfig.xml).
A changed GVariant/API shape produces an error instead of dumping raw session
output. Colord queries only
[display devices](https://github.com/hughsie/colord/blob/main/src/org.freedesktop.ColorManager.xml)
and their profile properties; it does not enumerate printers or scanners.

## Privacy and side-effect boundaries

The report omits raw EDID, panel serials, monitor vendor/product strings,
mode IDs, colord object paths, profile filenames and profile contents. It
hashes profile titles instead of emitting names that may contain an owner
or device serial. Structured D-Bus fields are selected through an allowlist;
no raw command-output fallback is saved. Selected free-text fields redact
home paths, network-address forms, user/host identities present in the current
process's identity variables and `user@host` forms. The script does not emit
the environment, username or hostname, nor contact a network service.

Fingerprint hashes can still link two captures to the same device or private
profile. Redaction is not permission to publish a local capture. Custom
kernel/distribution strings and custom interface names should receive human
review before sharing because arbitrary text cannot be guaranteed anonymous.

The script reads local files and calls query methods. It never writes sysfs,
sets D-Bus properties, applies a profile, changes brightness or colour mode,
installs packages, restarts the desktop, selects a kernel or runs recovery.
System-bus queries may activate an installed colord service through normal
D-Bus activation; they do not change its profile assignments. Apart from an
explicit `--output` report, it creates no persistent capture files.

This is evidence collection, not a universal HDR/Dolby Vision verdict.
Successful decode, a PQ surface, an advertised colour mode and an assigned
ICC profile remain separate claims. Full Dolby display management and optical
calibration need the reference and measurement receipts in
[the quality plan](DOLBY_VISION_AND_QUALITY.md#5-work-in-stages-with-observable-acceptance).

## Validate without a physical display

```bash
python3 -m unittest discover -s tests -p 'test_inspect_display.py' -v
                                                  # Synthetic fixtures only.
python3 scripts/check_repository.py               # Repository/link checks.
```

The fixtures exercise evidence preservation, private-field omission,
read-only source preservation, absent session buses, missing commands/files,
permission failures, malformed interfaces, subprocess time/output limits,
profile read failures and private output creation. They do not qualify a live
Linux desktop. Run them at the repository's agreed review/test stage; then
capture the laptop baseline separately without changing its display.

## Live receipt — separate configured state from active output

On 2026-10-09 UTC the reviewed inspector ran read-only on the target laptop,
using the previously verified owner's session bus explicitly supplied by the
caller. It created its private report with mode `0600`; kernel, DRM, package,
GNOME and colord collection succeeded. GNOME reported eDP-2 at 2560×1600 and
approximately 240 Hz, with colour mode `1` (BT.2100), and colord returned one
display device.

At that capture, DRM reported the internal connector connected but disabled,
and Intel `actual_brightness` was zero despite requested/max values of 400.
This is consistent with inactive scanout, but the inspector does not determine
why it was inactive. Do not classify it as a brightness bug or a physical HDR
failure. An awake, enabled-output observation is still needed to bind logical
colour state to the actual scanout and optical measurements. No display was
woken, reconfigured or restarted for this capture.

## Inspect the compositor's actual colour descriptions

The separate [Wayland colour probe](../probes/wayland_color_info/probe.c)
reads the encoding and target-volume information available to applications.
It binds existing outputs without creating a surface, window or buffer. It
does not change any mode, profile, compositor setting or output property.
This complements the system inspector above: package versions and a selected
HDR mode do not establish what colour metadata the compositor publishes.

**Status:** client and synthetic server compiled on native amd64 with warnings
as errors; final adversarial review and runtime qualification are pending.
The [compiler receipt](../evidence/wayland-color-info-compile.json) binds all
seven source files and the protocol digest. No live laptop result is claimed.

### Build and acquire one report

Build on Linux with a C11 compiler, Python 3, pkg-config, wayland-scanner and
libwayland-client development files. The build uses the vendored, unmodified
Wayland Protocols 1.48 XML and verifies its pinned digest before generating
bindings. The upstream MIT notice remains in the XML. Generated files and
binaries belong in an explicit external build directory.

```bash
probe_build="$(mktemp -d)"
sh probes/wayland_color_info/build.sh "$probe_build"
"$probe_build/wayland-color-info"       # Print one bounded JSON report.
```

Run the binary as the desktop user in the intended Wayland session. It uses
that process's Wayland connection environment; it does not discover another
user's socket. The process suppresses libwayland error/debug text because
those messages can contain private server strings. Report output uses only
fixed labels and numerical values. Keep stdout captures private and outside
Git; shell redirection inherits the caller's permissions and overwrite rules.

The total acquisition deadline is five seconds, including connection and
protocol discovery. Bounds are one colour manager, 32 output globals, 8,192
event-accounting calls and 1 MiB of accounted payload. The client negotiates
colour-management version 1 or 2 and wl_output version 1 or 2. It records
32-bit or 64-bit image identities as appropriate. A registry/synchronization
sequence handles either global-announcement order without a blocking
roundtrip outside the deadline.

Exit `0` means a complete bounded observation. Exit `1` means missing support,
disconnection, a limit/deadline, unstable topology or incomplete/malformed
output information. Unexpected command-line arguments exit `2`. Always read
the top-level and per-output statuses; a partially populated record is not a
successful snapshot.

### Interpret raw values without inventing missing fields

Every information field has a presence flag and raw integer array. Missing
fields retain an empty array; they are never replaced with an assumed zero.
The JSON supplies scales and coordinate ordering.

| Field | Interpretation |
|---|---|
| `primaries`, `primaries_named` | Pixel encoding RGB primaries and white; signed xy coordinates use a scale of 1,000,000. |
| `tf_named`, `tf_power` | Declared transfer characteristic; power exponents use a scale of 10,000. |
| `luminances` | Encoding minimum, maximum and reference white. Only the minimum is scaled by 10,000. |
| `target_primaries`, `target_luminance` | Independent target RGBW and luminance, using the corresponding encoding-field scales. |
| `target_max_cll`, `target_max_fall` | Optional target content-light values in cd/m². |
| `icc_size` | Profile-event presence and declared size only. The received descriptor is closed immediately without reading the profile. |
| `description_identity`, `global`, `ordinal` | Session-local correlation values, not persistent hardware identity or a DRM connector mapping. |

Completion checks required fields and known contradictory named/power pairs.
It does not prove general mathematical colour validity, profile validity,
application usage, rendering accuracy, active scanout or optical output.
Unknown enum values remain visible for interpretation. A target changing
during acquisition marks the observation unstable instead of silently joining
two states. Removed outputs remain explicitly marked.

### Synthetic protocol qualification

The [socket fixture](../probes/wayland_color_info/fixture.c) uses
libwayland-server in a private temporary runtime directory; it never connects
to the real desktop. Compile it with the additional server development files.
After final adversarial review, run the selected tests once:

```bash
sh probes/wayland_color_info/build-fixture.sh "$probe_build"
WAYLAND_COLOR_INFO_BUILD="$probe_build" python3 -m unittest discover \
  -s probes/wayland_color_info -p test_protocol.py -v
```

Cases cover protocol versions and discovery order, encoding/target separation,
missing or contradictory events, removal, changed descriptions, deadline,
ICC descriptor closure and privacy with debug logging requested. Failed or
invalidated cases are retried individually under the project workflow.
