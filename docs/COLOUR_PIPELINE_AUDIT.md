# Colour pipeline audit — separate encoding, display targets and calibration

**Status:** source audit complete; corrections and physical acceptance open ·
**Audited:** 2026-10-09 UTC.

Companion to [the quality plan](DOLBY_VISION_AND_QUALITY.md) and
[hardware findings](HARDWARE.md). This answers which component owns each
colour operation in the delivered Ubuntu Mutter source candidate,
cross-checked against the upstream-facing morning candidate. It is a source receipt,
not a measurement or a claim that a particular application used this route.
[Display diagnostics](DISPLAY_DIAGNOSTICS.md) provide runtime context; the
capture with scanout disabled cannot qualify visible output.

## Source identity and reproducibility

Two clean source checkouts were inspected; they are different candidates:

| Role | Candidate commit | Base commit |
|---|---|---|
| Delivered Ubuntu package source (`ubuntu-mutter` in the manifest) | `f8b71478843220c0de2d68b73add82231c6f3909` | `f8b113189f8c67beabf7475adf26f6ebcbf36684` |
| Upstream-facing proposal (`mutter` in the manifest) | `ab7633fd411d159ca588ba52f01e07ecd940d390` | `d82671c3035bfdb10fdc1ffd2c0e31859bb00ff7` |

File names and line numbers below bind to the **Ubuntu candidate**, unless
explicitly labelled otherwise. Installed-source conclusions use that candidate
identity from the manifest, not the upstream proposal identity. This does not
independently establish the installed executable's bytes or runtime execution.
Recheck references when either source pin moves.

The 28 traced source/test files were compared directly: 27 are byte-identical
between candidates. `src/backends/native/meta-onscreen-native.c` differs in
Ubuntu power-save frame lifetime, shutdown and main-context handling. Its
traced colour-mode and gamma/CTM producer bodies are unchanged, with line
numbers shifted by 20. That difference is material to power-save acceptance;
it must not be treated as proof the candidates behave identically when a
screen sleeps. The production-reader searches were repeated on the Ubuntu
candidate and confirm the colour conclusions below. Neither candidate's
native-DisplayID patch changes these luminance-transform/profile paths.

The audit read the source without modifying its checkout. It did not build,
run tests, query a desktop, change the display, activate a profile or touch
an application repository. Source pins and reconstruction paths are in
[the manifest](../sources.json) and [development](DEVELOPMENT.md).

In a reconstructed source checkout, these commands reproduce the scope:

```bash
git rev-parse HEAD                         # Check the candidate identity.
git status --short                         # Check whether local changes exist.
git diff --name-only f8b113189f8c67beabf7475adf26f6ebcbf36684 HEAD
                                           # Identify candidate-specific files.
rg -n 'desired_content_.*luminance|has_adaptation_matrix|adaptation_matrix' src clutter
                                           # Find physical-target/matrix readers.
rg -n 'tone.?map|src_mastering_max_lum|dst_mastering_max_lum' src clutter
                                           # Distinguish names from actual ops.
rg -n 'meta_kms_update_set_crtc_degamma|set_crtc_gamma|set_crtc_ctm' src
                                           # Find CRTC update producers.
```

**How to read it:** inspect the functions and their callers, rather than
counting keyword matches. Unused tone-mapping uniform names are not an
implemented tone mapper. A test that reads a field is not its production
consumer. No commands above qualify a physical panel.

## Pixel conversion and signalling have distinct owners

```text
client image description + committed buffer
                    |
        Wayland surface colour state
                    |
        source EOTF / primaries conversion
                    |
        linear BT.2020 D65 intermediate
                    |
        reference-white / encoding-normalisation scale
                    |
        view blending state (normally sRGB primaries, gamma 2.2)
                    |
        final view -> output encoding transform
                    |
        BT.2020 / PQ framebuffer
                    |
        CRTC gamma LUT or temperature CTM, if programmed
                    |
        KMS connector signalling -> driver -> panel

output mode -> PQ + BT.2020 static KMS metadata
output colour state -> Wayland output/preferred image description
```

The KMS signalling path does not inspect each application's metadata. This
is also not a Dolby Vision processing chain: no creative-trim or Dolby
configuration processor occurs in the traced functions.

| Boundary | Exact candidate source | Demonstrated behaviour |
|---|---|---|
| Untagged/default content | `clutter/clutter/clutter-context.c:354`, `clutter_context_get_default_color_state()` | Creates sRGB primaries with gamma 2.2; default luminance is derived from that EOTF. |
| Parametric client description | `src/wayland/meta-wayland-color-management.c:1259`, `creator_params_create()` | Builds a `ClutterColorStateParams` from declared primaries, EOTF and luminances. |
| Surface commit | `src/wayland/meta-wayland-color-management.c:817`, `set_image_description()`; `src/wayland/meta-wayland-surface.c:889`, `meta_wayland_surface_apply_state()` | Places the state in pending surface state, then commits it. Unsetting uses the compositor default. |
| Buffer/actor colour state | `src/wayland/meta-wayland-actor-surface.c:187` in actor state synchronization | Transfers the committed colour state to the actor and shaped texture. |
| Sample conversion | `src/compositor/meta-shaped-texture.c:458`, `attach_color_transform()`; `clutter/clutter/clutter-color-pipeline-shader.c:926`, `clutter_color_pipeline_shader_set_color_state()` | Builds and attaches a source-to-paint-target transform. |
| Output state | `src/backends/meta-color-device.c:689`, `get_color_metadata_from_monitor()`; `:746`, `update_color_state()` | Default mode uses sRGB/gamma 2.2; BT.2100 mode uses BT.2020/PQ; SDR-native mode uses EDID primaries/gamma. Assigned ICC characterization does not select this state. |
| Blending/output states | `src/backends/meta-renderer-view.c:75`, `set_color_states()`; `clutter/clutter/clutter-color-state-params.c:205`, `clutter_color_state_params_get_blending()` | Separates the blending state from the output state. Normal PQ output uses an extended gamma-2.2/sRGB blending state; forced-linear debugging changes that choice. |
| Final encoding | `clutter/clutter/clutter-stage-view.c:239`, `ensure_stage_view_offscreen_pipeline()` | Attaches the view-to-output colour transform to the offscreen pipeline. |
| Direct scanout | `src/compositor/meta-compositor-view-native.c:337` in `find_scanout_candidate()` | Rejects direct scanout when surface and output states require a colour transform. Other scanout constraints still apply. |

An ICC description supplied by a **client** is a supported source path.
`clutter/clutter/clutter-color-transform.c` handles matrix/shaper and more
general ICC conversions; `clutter-color-state-icc.c:110` assigns ICC states
the default SDR luminance. This is separate from selecting an assigned
**display** ICC as the compositor's output characterization. Do not conclude
that client ICC support means all output profiles are applied.

## PQ encoding range is not physical peak luminance

`clutter/clutter/clutter-color-utils.c:98` defines SDR defaults
`min=0.2`, `max=80`, `ref=80`, `mastering_max=80` cd/m². Its PQ defaults at
`:114` are `min=0.005`, `max=10000`, `ref=203`, `mastering_max=10000` cd/m².
`update_color_state()` takes those EOTF defaults and multiplies only reference
white by the device reference-luminance factor. It reads neither a panel peak
nor a full-frame luminance there.

`clutter_color_state_params_new_full()` at
`clutter/clutter/clutter-color-state-params.c:323` deliberately makes an
explicit PQ state's `max` equal `min + 10000`, even if another `max_lum` was
provided. PQ shader functions at `clutter-color-pipeline-shader.c:184` and
`:200` normalize linear values to the PQ range. Changing only a nominal
maximum to 616 would not implement a panel tone mapper.

The [Wayland colour-management 1.48 protocol](https://github.com/wayland-mirror/wayland-protocols/blob/1.48/staging/color-management/color-management-v1.xml)
separates encoding's primary colour volume from the targeted colour volume.
PQ has approximately a 10000 cd/m² encoding swing; `target_luminance` carries
a theoretical target, which need not equal measured emitted light.

### Reference-white scaling is implemented; highlight compression is absent

`clutter-color-transform.c:299` decodes the source transfer function and maps
primaries to linear BT.2020/D65. `add_luminance_mapping_op()` at `:1001`
adds a scalar multiply:

```text
factor = (target.ref / source.ref) * (source.max / target.max)
```

`build_transform_pipeline()` at `:1022` then converts from linear BT.2020
to the target primaries and inverse EOTF. With the default SDR and PQ states,
SDR white maps to normalized PQ linear `203 / 10000 = 0.0203` before PQ
encoding. This algebra explains reference-white mapping; it is not an optical
receipt that this screen emits 203 cd/m².

The traced pipeline has no nonlinear highlight roll-off, panel-peak argument
or source-to-panel gamut-compression operation. Names such as
`UNIFORM_NAME_TONEMAPPING_REF_LUM` in `clutter-color-state-params.c` have no
production consumer in this tree. `mastering_max` affects the required
buffer format and extended blending headroom (`:169` and `:246`), but is not
used by the scalar luminance mapping to compress highlights.

The normal PQ blending state asks for FP16 when its extended mastering range
exceeds its nominal maximum; this avoids treating the gamma/sRGB blending
state as a conventional bounded SDR destination. Actual buffer selection,
precision, clipping and visible colour still need runtime evidence. The
absence of a host tone mapper does not establish how the panel firmware maps
PQ or prove that a known application is double mapping.

### The advertised Wayland target repeats the encoding volume

`get_output_color_state()` at `meta-wayland-color-management.c:338` obtains
the device state. Output image descriptions and surface preferred feedback
use it (`:1037`, `:670`). `send_information_from_params()` at `:556` sends
`luminances` from `lum.min/max/ref`, then sends `target_luminance` from the
same `lum.min/max` at `:607`. `send_primaries()` at `:529` likewise sends the
same primaries as both encoding and target primaries.

**Demonstrated gap:** the candidate has no distinct output target-volume
representation, so BT.2100 feedback repeats its nominal BT.2020/10000 range.
An application receiving 10000 as its preferred target has not discovered
this panel's physical peak. Which clients use that target for their own
mapping remains unverified.

Client mastering-display primaries/luminances are explicitly rejected by
`creator_params_set_mastering_display_primaries()` and
`creator_params_set_mastering_luminance()` (`:1511`, `:1528`); MaxCLL and
MaxFALL setters (`:1539`, `:1548`) are ignored. The supported-event list at
`:1833` advertises parametric descriptions, luminances and ICC, but not the
mastering-primaries feature. These limitations cannot qualify dynamic Dolby
metadata transport or display management.

## KMS sends PQ and primaries, with zero luminance metadata

`meta_output_get_color_metadata()` at `src/backends/meta-output.c:536`
initializes BT.2100 metadata with `active=TRUE`, PQ EOTF and BT.2020
primaries/D65 white. The remaining C initializer fields are zero:

| KMS metadata field | Value from this producer |
|---|---|
| `mastering_display_max_luminance` | `0` |
| `mastering_display_min_luminance` | `0` |
| `max_cll` | `0` |
| `max_fall` | `0` |

It does **not** send 10000 or 616 in those fields.
`src/backends/native/meta-onscreen-native.c:939`, `set_color_mode()`, queues
colours and metadata only where connector properties exist.
`meta-kms-update.c:447`, `meta_kms_update_set_hdr_metadata()`, stores the
metadata and requests a modeset. `meta-kms-connector.c:659`,
`meta_set_drm_hdr_metadata()`, serializes these zero luminance values into the
DRM type-1 payload. Atomic `process_connector_update()`
(`meta-kms-impl-device-atomic.c:153`, HDR branch at `:268`) creates its blob
and assigns `HDR_OUTPUT_METADATA`. The legacy/simple implementation also
serializes it (`meta-kms-impl-device-simple.c:381`).

These are output stream/mastering/content metadata fields in the
[DRM userspace contract](https://www.kernel.org/doc/html/latest/gpu/drm-uapi.html#c.hdr_metadata_infoframe),
not a measured physical-target receipt. Setting them to a panel peak without
specifying the composition's mastering/content semantics is not justified.
The source proves the requested userspace payload; it does not prove the
blob was committed on this laptop, how an eDP driver uses it, or what panel
firmware does with it.

`meta_edid_info_new_parse()` in `src/backends/edid-parse.c:116` retains the
library HDR static metadata structure. Native DisplayID capability detection
is separate from populating CTA-style luminance fields. `check_native()` in
`src/tests/native-hdr-tests.c:160` explicitly expects native-only fixtures
to retain zero CTA desired peak/full-frame/minimum fields. Searches found
no production reader of those desired luminance fields in this candidate.
The [400/616 cd/m² DisplayID observations](HARDWARE.md) therefore cannot be
assumed to reach colour-state construction or KMS luminance metadata through
these structures. This audit did not rerun that test.

## Calibration is a LUT/temperature path, not general HDR characterization

`meta_color_calibration_new()` at `src/backends/meta-color-profile.c:527`
extracts VCGT, optional brightness metadata and a supplied adaptation matrix.
`create_device_icc_profile()` at `meta-color-device.c:1188` can compute that
matrix for an EFI factory-calibration path (`:1345`). `create_icc_profile_from_edid()`
at `:1029` otherwise constructs a matrix/TRC profile from EDID chromaticity
and gamma; that is model metadata rather than an optical calibration.

**Demonstrated gap:** the stored `has_adaptation_matrix` and
`adaptation_matrix` have no production reader under `src/` or `clutter/` in
this snapshot. The calibration accessor is only used by a source test. The
output state's construction likewise does not select an assigned display
ICC's matrix/TRC. Storing or assigning such a profile is therefore not proof
of compositor output characterization.

`update_white_point()` at `meta-color-device.c:1486` selects the assigned
profile and temperature, then prefers the monitor's gamma LUT. With VCGT,
`meta_color_profile_generate_gamma_lut()` (`meta-color-profile.c:486`)
samples the curves and multiplies their channels by blackbody temperature
scales (`:411`). Without VCGT it builds a temperature ramp. Without a gamma
LUT it can use a diagonal CTM for temperature only, not the stored adaptation
matrix.

This path has no BT.2100/PQ guard. `meta_onscreen_native_prepare_frame()` at
`meta-onscreen-native.c:2456` queues invalidated gamma LUTs and CTMs regardless
of colour mode; atomic `process_crtc_color_updates()` at
`meta-kms-impl-device-atomic.c:872` programs them separately from connector
HDR metadata. A degamma setter exists, but searches found no production
caller establishing a matching linearizing degamma in this tree.

**Conditional risk, not a measured defect:** a profile's SDR VCGT or a
linear-light calibration matrix cannot be assumed suitable for a PQ-encoded
CRTC path. Its intended encoding, driver stage ordering and transition/reset
behaviour must be established before a correction. The recovered OEM profiles
have no VCGT according to [the prior inspection](DOLBY_VISION_AND_QUALITY.md#21-the-current-compositor-needs-a-deeper-calibration-audit),
so that specific inherited result does not demonstrate an active bad VCGT.
No `MHC2` or `DVB1` handler was found in the audited source tree.

HDR brightness currently changes reference white:
`meta_output_kms_create_backlight()` at `meta-output-kms.c:398` selects the
reference-white control in BT.2100 mode and attempts to reset an available
sysfs backlight to maximum. `meta-backlight-ref-white.c:43`, `set_factor()`,
and its asynchronous brightness handler at `:70` set the reference-luminance
factor. This affects colour-state reference white, not a measured panel peak.

## Smallest separable correction and the evidence still required

1. **Represent output target volume separately from encoding.** Add explicit
   target primaries/luminance and provenance to output image-description
   state. Keep PQ's normalization/range and SDR reference-white scaling.
   Resolve DisplayID versus CTA precedence and missing/invalid data explicitly;
   do not synthesize CTA HDR type-1 declarations from native capability alone.
   Publish the selected target through Wayland target events, and update image
   description identity/feedback when it changes. This is the first separable
   upstream patch candidate; it repairs the demonstrated conflation without
   implementing a new tone mapper or changing KMS content metadata.
2. **Specify target policy before selecting a number.** Preserve full-frame
   and small-highlight declarations separately, including operating mode and
   measurement provenance. A firmware-declared peak may be a useful target
   input, but it is not a calibrated per-unit value. Missing evidence must not
   be replaced by an ASUS-specific 616 constant or a global PQ clamp.
3. **Give calibration an explicit domain and owner.** Characterization,
   calibration, temperature/comfort and mastering/content metadata are
   different operations. Establish SDR/PQ eligibility and reset semantics
   before applying a profile at KMS or shader output. Do not enable a dormant
   adaptation matrix indiscriminately in PQ or disable all calibration merely
   because HDR is selected.
4. **Add target-aware mapping only with a defined contract.** A later mapping
   patch must specify its inputs, reference white, target gamut, peak/full-frame
   limits, roll-off and single owner. Pixel mapping, preferred target feedback
   and KMS content metadata must agree. Dolby display management remains its
   own processor contract and cannot be replaced by that generic HDR mapper.

**Acceptance for the first patch:** synthetic PQ descriptions keep their
encoding swing while target events reflect independently supplied display
limits; SDR white conversion stays unchanged. Cover CTA-only, native
DisplayID-only, malformed/missing and conflicting declarations, plus target
updates and immutable image-description identity. Build and run focused
source regressions at the agreed premerge stage; then inspect an active
output and instrumented patches separately. No such patch or new test result
is claimed by this document.

**Open runtime evidence:** application buffer encoding and Wayland declaration,
actual blending/output buffer formats, driver LUT/CTM stages, committed KMS
metadata, active panel mode, white/peak/full-frame response, comfort adjustment
state, and composition-versus-direct-scanout equivalence. Scanout disabled at
capture time leaves all visible-output acceptance open. No profile activation,
brightness change, compositor restart or optical accuracy claim follows from
this source audit.

## Follow-up source findings — input contracts and mapping ownership

Read-only follow-up at Ubuntu candidate
`4db354c816e7ac72091a246b7b2eb8adee9a9412` identifies additional work after
the independent target-feedback corrections. These are source observations;
no new runtime reproduction or physical result is claimed here.

- `creator_params_set_primaries()` receives signed protocol coordinates but
  uses `scaled_uint32_to_float_chromaticity(uint32_t)`, then clamps every
  coordinate to `[0,1]`. Negative coordinates can therefore wrap and acquire
  a different meaning. The output conversion helper also returns unsigned
  values. The [protocol's custom-primary arguments](https://github.com/wayland-mirror/wayland-protocols/blob/1.48/staging/color-management/color-management-v1.xml)
  are signed; physical-panel domain rules must not automatically be imposed
  on imaginary encoding primaries. A correction needs signed preservation,
  explicit unsupported/degenerate-matrix handling and an independent input
  regression, rather than silently clamping a client's declaration.
- `creator_icc_set_icc_file()` tests an existing descriptor with `fd > 0`,
  although descriptor zero is valid, and checks file bounds after computing
  `offset + length` in the protocol's 32-bit type. A focused correction needs
  an explicit unset sentinel and widened bounds arithmetic. Later asynchronous
  parsing failure does not replace validation of the requested range.
- `cicp_transfer_to_clutter()` explicitly rejects HLG. Adding a name or an
  inverse OETF alone would be insufficient: HLG requires its display-light
  interpretation, including the OOTF. Source EOTF, output adaptation and
  physical-target policy need separate ownership.
- Transform construction skips work when source and destination encoding
  states compare equal. Its cache key contains source, destination and flags.
  Direct scanout uses this same encoding-transform decision. Future physical
  mapping therefore needs an explicit target/mapping identity in both render
  and scanout decisions; changing feedback alone cannot activate it.

The next mapping design must preserve source target-volume metadata through
surface commits, distinguish already display-managed content, map each surface
for the destination before composition, and apply output characterization once.
It must cover alpha, cross-monitor movement, HDR/SDR mixing and scanout parity.
Algorithm selection and measured target parameters remain open; no placeholder
mapper or guessed panel curve is introduced by the current feedback work.
