# backends/color: Publish native target luminance and primaries apart from the encoding

On the native DisplayID path the output colour state describes the PQ encoding (0.005 to 10000
cd/m²), not the panel. This parses the panel's own luminance and primaries from the DisplayID
Display Parameters block (with explicit unavailable / declared / invalid / conflicting states),
keeps them as a target volume on the colour device separate from its colour state, and
publishes them as the target luminance and target primaries of the output's and surfaces'
preferred image descriptions. Image descriptions sent to clients become immutable records with
identities that survive manager disposal; descriptions are republished when the target or the
primary output changes. Encoding, reference white and rendering are unchanged in this MR.

It also adds `meta_color_colorimetry_from_edid_primaries()` so the native SDR mode no longer
renders with unusable EDID primaries, a fallible definition of the linear BT.2020 matrices
shared by validation and rendering, a single rounding conversion to protocol units, and the
ability to run Wayland test cases as separate invocations (`separate_cases` in
src/tests/meson.build).

**Overlap**: !5068 also reads EDID HDR metadata into the protocol; see the design-discussion issue (@SERIES_ISSUE@) for the
comparison. **Blocked on libdisplay-info** (Display Parameters luminance and chromaticities,
libdisplay-info units 05-06). Related: [#5001](https://gitlab.gnome.org/GNOME/mutter/-/issues/5001) (panel values instead of placeholders).

Hardware: the ASUS ROG Zephyrus G16 (GU605MZ, Samsung ATNA60DL01-0 OLED eDP, Intel Meteor Lake): its EDID declares HDR only in DisplayID 2.0 (Display Interface Features RGB BT.2020/ST 2084; Display Parameters 400 cd/m² full, 616 cd/m² 10% window, native primaries), no CTA HDR block. There the output description publishes target luminance 0.0004-616 cd/m²
and the firmware primaries while the encoding stays BT.2020/PQ (Mutter 51 build of the same
change).

## How it was tested

On lab5 (Ubuntu 26.10 container: GCC 15.3, meson 1.10.1, GLib 2.90, GTK 4.24.1, Mesa 26.2.4
llvmpipe), on `main` b48811767 with the stacked units below this one, against libdisplay-info
`main` plus the libdisplay-info units 01-06 installed in a prefix:

```
PKG_CONFIG_PATH=<prefix>/lib/x86_64-linux-gnu/pkgconfig meson setup b -Dremote_desktop=true -Dwerror=true
git checkout <each commit>; ninja -C b        # every commit, oldest first
meson setup b-rel -Dremote_desktop=true -Dwerror=true -Dbuildtype=release; ninja -C b-rel   # tip
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe META_DBUS_RUNNER_DISABLE_LOGIND_PASSTHROUGH=1 \
  meson test -C b --setup mutter:default --no-rebuild --num-processes 4 --timeout-multiplier 3 <tests>
```

- Warnings-as-errors build of every commit: 11/11 OK. Release (`-O2`) `-Werror` build of the tip: OK.
- Tests on the tip (16 invocations): `actor-color-state`, `color-pipeline`, `color-state-transform`, `monitor-color-tests`, `monitor-config-tests`, `edid`, `color-management`, `color-management-profile-conflict`, `native-hdr`, `wayland-color-management`, `wayland-color-representation`; separate `wayland-color-management` cases: `target-luminance-v1`, `target-luminance-v2`, `target-primaries-v1`, `target-primaries-v2`, `sdr-native-unusable-edid-primaries`: 16/16 OK.
- `./check-style.py --dry-run` (allow-failure in CI): only suggestions from uncrustify re-indenting isolated chunks (parameter alignment of unchanged continuation lines, the closing parenthesis of `CLUTTER_TEST_SUITE`, a label), which contradict the surrounding upstream style; not applied.

Not run here: Mutter's full CI matrix (Fedora image, KVM and native KMS tests, X11 and Xwayland
jobs) and any test on real hardware with this exact series.

## The series

Overview of the whole series, its hardware evidence and the coordination questions with !5068 and !5177: @SERIES_ISSUE@.

## AI assistance

Prepared with AI coding assistants (OpenAI Codex; Anthropic Claude Opus 5.5 and Fable 5.1 via Claude Code). I reviewed the changes and take responsibility for them.
