# Shared Dolby Vision display management on Ubuntu

## Where the grade is applied

The decoder exposes Dolby reconstruction data and a raw reference processing unit (RPU) for each frame. The existing libplacebo adapter carries the reconstruction data, but its stock rendering API has no input for the full RPU and a target display mapper. The patched adapter keeps the bytes with the frame. The renderer reconstructs the BT.2020/PQ RGB image, calls the provider with the frame’s own metadata and destination display, and uses its output before final scaling and encoding. Successful mapping bypasses the generic highlight mapper. Unsupported inputs can take the ordinary rendering path. A provider error fails the render.

The new renderer has a distinct SONAME, `libplacebo.so.360rog1`, and distinct exported symbols. A process may load it alongside Ubuntu’s stock libplacebo. Installing the provider alone does not change existing binaries. Clients must use the matching frame and rendering interfaces.

## Clients

| Ubuntu client | Destination | Normal entry point |
|---|---|---|
| Installed mpv 0.41.0, gpu-next | HDR output described to the player by the display system | `mpv --vo=gpu-next movie.mp4` |
| Staged mpv 0.42.0, gpu-next | Physical display target. Supports native 4K Profile 7 FEL composition | Open an MP4 or Matroska video in mpv |
| Staged GtkVideo widget | Display target of each realized view, including views sharing a media stream | Open a local Profile 5 video in an application using GtkVideo |
| Staged GNOME Showtime | Per-surface GTK target for a GStreamer movie | Open the video in Showtime |
| FFmpeg 8.1.2, libplacebo video filter | Explicit export target, because a filter graph can run without a display | Example below |

### One system mpv for native launchers

The system-player contract candidate is mpv `0.42.0-0ubuntu0+rogdv5.2`. It adds the read-only `native-dovi-api-1` token to the enabled-features line of `mpv --no-config --version`. A launcher can query the actual selected binary, including an explicit override, before advertising native Dolby formats. A failed or missing probe does not prevent launching that binary. `+rogdv5.2` was installed on November 11 and has since been replaced (below). [Source replay and focused IPC qualification](../evidence/mpv-system-player-contract.json).

The read-only IPC property `native-dovi-target-state` contains `active` and `generation`. Active means automatic physical-target eligibility, and a matching successful rendering record is still required before reporting a mapped Dolby picture. Target transitions and video-output teardown notify observers. A source change discards previous success facts. `video-target-params` continues to describe the encoded signal, whose maximum can differ from the physical panel peak.

**An idle window before the first title (`+rogdv5.4`).** plurx-player 0.5.0 opens mpv's window idle and loads the title afterwards. With colour hints enabled and no video yet, mpv set no hint, so the idle window presented on an sRGB Vulkan swapchain. The NVIDIA 615 Vulkan WSI then created its own colour-management surface for the window. The first video frame's `wp_color_manager_v1.get_surface` failed with "surface already requested", and Mutter closed the connection before any picture. [Patch 0008](../patches/mpv-fel-system-dv/0008-keep-describing-a-Wayland-Vulkan-window-colour-without-a-hint.patch) makes mpv describe a Wayland Vulkan window as sRGB itself whenever it has no hint or no video. The swapchain therefore stays pass-through, and the driver never takes the surface's colour management. That also covers `--target-colorspace-hint=auto` when the display target becomes known after the first frames. Other contexts keep their previous behaviour. The bundled mpv 0.41 in plurx-player 0.4.1 already behaved this way for idle windows. On the ROG desktop, the plurx sequence (idle window, then `loadfile`) failed with `+rogdv5.2` and played Profile 7 FEL, Profile 5, HDR10 and SDR clips with the fix. Plain `mpv FILE` was unaffected. `+rogdv5.3`, installed first, covered only an idle window with explicit hints.

Reproduce this candidate by applying all eight registered `mpv-fel-system-dv` patches to the pinned upstream source. Apply the existing Ubuntu packaging, live-configuration and raw-xy overlays, followed by [the system-player changelog overlay](../packaging/system-dv/mpv-042-ubuntu-system-player-contract.diff) and [the idle-window changelog overlay](../packaging/system-dv/mpv-042-ubuntu-idle-window-colour.diff). The application delta belongs in the normal Debian quilt series before `dpkg-source -b`. Preserve the source archive, fresh extraction and focused IPC qualification together. Public source recipes do not carry private SDK binaries or a separately bundled launcher player.

### Paused GNOME playback

On the ROG, the packaged Showtime client retained one decoded Profile 5 picture while a private GNOME monitor changed from 616 to 308 cd/m² and back. The mapper received both peaks with an unchanged 203 cd/m² reference white. GNOME’s 1280×800 PipeWire capture changed over 375,877 pixels inside the movie rectangle. The last capture matched the first byte for byte. The monitor advertised synthetic HDR capabilities, with the normal Mutter configuration, renderer and capture code. An independent late-HDR window also updated correctly on installed GNOME Shell. [Methods and measured differences](../evidence/gnome-showtime-paused-retarget.json).

The normal GtkVideo widget and Showtime both showed a subtitle while grading the underlying Profile 5 picture. To reproduce the carrier check, prepare two excerpts of the same length from the start of the same video, with one cue visible at the selected frame and one outside it. This command checks the first 819 source packets against every video packet in each excerpt. It compares the Dolby configuration, codec initialization, sample sizes, encoded bytes, presentation and decode timestamps, and durations. For complete movies omit the prefix option. The test clips stay on the machine where they were obtained.

```sh
python3 packaging/quality/verify-subtitle-carrier.py --reference-prefix-packets 819 ORIGINAL ACTIVE INACTIVE
```

Capture both players on the same paused frame at the initial target, the second target and the restored target. Wait for the completed mapped redraw each time. Compare the subtitle region between the two controls and the video region across target changes. [Observed subtitle and video results](../evidence/gnome-embedded-dolby-subtitles.json).

### Inspect a native GNOME screen pixel

On the ROG, capture format matters when checking a wide-gamut image or an HDR movie. The same green patch measured (339, 582, 302) in 10-bit BT.2020/PQ and (0, 255, 0) in an 8-bit BT.709 capture. The corrected Mutter package writes the pixel format advertised to the recorder. [Native format controls](../evidence/mutter-shared-memory-color-formats.json).

The [PipeWire pixel sampler](../tools/sample-screen-pixel.c) reads a single coordinate from an already authorized monitor stream. Build it against the PipeWire development headers. Pass the monitor node ID from the recording session and run it on that session’s PipeWire connection.

```sh
cc -std=gnu11 -O2 tools/sample-screen-pixel.c -o sample-screen-pixel \
  $(pkg-config --cflags --libs libpipewire-0.3) -lm
./sample-screen-pixel "$node" xr30 520 399
```

Coordinates use the captured frame’s pixel grid. The three printed numbers are red, green and blue. `xr30` and `xb30` return 10-bit PQ code values, `rgba-f16` returns floating-point PQ signals, and `bgrx` returns 8-bit SDR codes. The sampler requests the chosen encoding and a shared-memory buffer and times out after ten seconds. These measurements describe digital compositor output. Physical luminance and white point require panel measurements.

### Browser playback on the ROG

Stock Chrome 156.0.8078.47 and Firefox 159.0 both presented a local AVC control frame. Both rejected the same local unencrypted Profile 8.1 MP4 with media error 4 (`MEDIA_ERR_SRC_NOT_SUPPORTED`). The chart has matched Dolby configuration and RPU data and plays through the native consumer pipeline. Each browser used a fresh profile. Chrome ran on its own NVIDIA-backed Wayland display and Firefox ran headless.

For ordinary MP4 files and Media Source Extensions, both browsers declined `dvh1.05.06`, `dvhe.05.06`, `dvhe.07.06`, `dvh1.08.06` and `dvhe.08.06`. Firefox accepted the Main and Main 10 HEVC capability queries. Chrome declined those queries in this configuration. This result covers clear content on these builds. A streaming service's protected playback requires separate evidence.

WebKitGTK 2.52.6 played the clear Profile 8.1 chart through an HTML video element. Removing all Dolby metadata and playing the same HEVC base reproduced every one of the 3,276,800 canvas pixels. Its Dolby codec capability queries returned an empty string. This distinguishes base-layer playback from applying the grade on this fixture. [WebKit pixel comparison](../evidence/webkit-clear-dolby-base-comparison.json).

The stock GTK4 engine (WebKit API 6.0) also displayed the chart on a private Wayland monitor. All 480,000 pixels in the accelerated 10-bit compositor capture matched the HEVC base. The green AVC control was visible in that capture. The accelerated canvas returned transparent black for the control, so it could not be used for the comparison. The software video sink produced the expected green canvas and identical chart/base pixels at full resolution. [GTK4 compositor and software controls](../evidence/webkit-clear-dolby-base-comparison.json).

The matching Ubuntu WebKit source identifies two integration points. In the GTK port, `ScreenManager::collectScreenProperties` sends monitor geometry, depth and DPI, and `screenColorSpace` returns sRGB for every widget. The browser needs the active monitor's luminance and primaries in the process that presents each video. In the GStreamer player, the GL sink links upload and colour conversion directly to its appsink. The little-endian software sink accepts only 8-bit BGRx or BGRA. Both paths need to apply the picture's grade before conversion, and the compositor must preserve the resulting precision and colour state. A browser implementation can use the paired compositor and canvas controls to demonstrate where the authored grade first becomes visible. [Ubuntu WebKit source package](https://launchpad.net/ubuntu/+source/webkit2gtk/2.52.6-1ubuntu1).

Chromium's public media configuration controls Dolby demuxing and leaves decoding to the platform. Its demuxer switches to the Dolby codec only when the requested type is supported. A Linux integration needs a decoder and renderer that retain the frame's metadata through composition, followed by a capability declaration for the supported profiles. [Chromium media build configuration](https://chromium.googlesource.com/chromium/src/+/cb3d3d1c5e989cc6792773dc6b1e46cefe68efb7/media/media_options.gni) · [Demuxer codec selection](https://chromium.googlesource.com/chromium/src/media/+/b677a686cfbe98c4b504845a15c2dfc046d2836a/ffmpeg/ffmpeg_common.cc).

### FFmpeg export

For a 600 cd/m² P3-D65 mastering display, the filter accepts the following invocation. This example stores the resulting 10-bit PQ video losslessly. Select the peak, black level and primaries for the **destination** you intend to reproduce.

```sh
ffmpeg -i input.mp4 -map 0:v:0 \
  -vf 'libplacebo=target_peak=600:target_black=0.001:target_gamut=p3:format=yuv420p10le' \
  -c:v ffv1 -an graded.mkv
```

The export contains already display-mapped pixels in BT.2020/PQ encoding. It is a rendered deliverable. The source retains the original Dolby Vision bitstream and its reusable grade. A transcoder or container may need its own settings to persist frame-level mastering data in a file.

## Packages and recovery

The source series start from Ubuntu libplacebo `7.360.1-1`, mpv `0.41.0-2ubuntu5` and FFmpeg `7:8.1.2-2ubuntu2`. The three `ubuntu-*-system-dv` entries and `ubuntu-mesa-wayland-hdr` (Mesa `26.2.4-1ubuntu1`) in [sources.json](../sources.json) pin the distro source archives, patches and resulting trees. [The provider interface](../packaging/system-dv/include/dv_provider.h) defines the data exchanged with the mapper. Building the consumers requires the matching private SDK, including its namespaced renderer headers. The private provider, SDK and signed or device-specific material are distributed separately from this repository.

For Vulkan Wayland output both ROG architectures of Ubuntu’s `mesa-vulkan-drivers` were rebuilt at `26.2.4-1ubuntu1+rogwsi1`. The amd64 and i386 driver payload inventories each matched their stock package. Six executable, constant, data and relocation sections of the packaged 64-bit Intel and software Vulkan drivers matched their respective linked binaries after Debian stripped debug information.

The offline APT install simulation on the ROG used seven local files with empty repository lists. It upgraded mpv, libavfilter11 and both architectures of mesa-vulkan-drivers. It added the namespaced renderer, the provider and Ubuntu’s libshaderc1. The FFmpeg filter depends on the exact stock libavcodec62 and libavutil60 versions for the private symbols it calls. The existing amd64 and i386 copies of those libraries satisfy the transaction.

Keep the seven files, the four original Ubuntu packages and their hashes together. Before installation, record APT holds and auto/manual marks, verify every hash, and simulate the complete transaction against the current host. The offline recovery simulation started from the projected installed state, restored both stock Mesa architectures, mpv and libavfilter11, and removed the three new libraries. Recheck reverse dependencies and restore the original marks during actual recovery. No session or compositor restart is required to install these packages. A newly launched player loads the new libraries.

The earlier seven-package installation produced the following observations, before the November 9 combined release. The normal system FFmpeg binary mapped a genuine, nonblack Profile 5 frame at 30 seconds on the integrated Intel GPU, with a target of 0.0004–616 cd/m² and P3-D65 primaries. Normal mpv loaded the system libraries and mapped the same title on Intel through a private Wayland compositor reproducing the panel declaration. The trace shows BT.2020/PQ and a rounded maximum of 881 cd/m². This confirmed the automatic target discrepancy on that earlier player. The GNOME session stayed open throughout.

### Rehearse a local package bundle

On the destination Ubuntu system, place the candidate archives and the exact previously installed versions in separate directories. Include each changed architecture. Omit rollback archives for newly introduced packages. Choose a fresh private receipt directory outside this checkout.

```sh
python3 tools/qualify-ubuntu-bundle.py /path/to/candidate /path/to/rollback /path/to/private/receipt
```

The tool runs APT in simulation mode against a copy of the installed package database and empty repository lists. It rejects extra installations and removals. It then builds a package-state snapshot representing the upgrade and checks the inverse transaction against the supplied rollback archives. It records both solver logs and archive SHA-256 hashes. Preserve the receipt privately because its starting snapshot lists all installed packages. The simulations cover dependency resolution. Maintainer scripts, live-session changes and optical behavior require their own checks.

### November 9 installation and offline execution

The coordinated November 9 install completed all 45 planned package changes with zero removals and a clean `dpkg --audit`. Installed versions include mpv 0.42 `+rogdv5.1`, FFmpeg libavfilter `+rogdv4.2` and Mutter `nativehdr15`. The running GNOME Shell PID remained unchanged during installation. A later normal login loaded the installed Mutter library. Its display state reports the internal panel at 2560×1600 and 240 Hz with colour mode 1. Post-login visual acceptance remains pending. Historical private-compositor playback receipts retain their original scope. Exact rollback is retained, not executed.

After installation, the system FFmpeg chart output matched the qualified output byte for byte across 19,660,800 bytes. The installed Display P3 loader preserved 16 colors with mean absolute error 0.00012436 and maximum error 0.0004883 in normalized linear channels. These checks cover installed software output; post-login visual acceptance and optical measurement remain pending.

A fresh installed `/usr/bin/mpv` played the genuine 3840×2160 Profile 7 FEL clip on a private native GPU-backed Weston compositor. The run requested 24 frames, reported `EL composed=1`, selected the 616 cd/m² target and logged zero Vulkan errors. A separate software-rendered Weston harness could not create a Vulkan swapchain and was inconclusive. These are private-compositor software checks; post-login visual and optical acceptance remain pending.

The qualification helper above only simulates transactions. For an actual transaction using explicit local `.deb` files, do not copy its `--no-download` flag: APT can fail before unpacking with `Pathname to install is not absolute`. Keep repository sources disabled and use an isolated empty lists directory. First run `apt-get --print-uris` with the exact proposed install arguments and require every acquisition URI to be a `file:` URI resolving to an archive in the hash-verified candidate allowlist; reject every other URI or path. Require the simulated actions to match the complete intended package set, then execute the same local-file transaction with the same isolated APT configuration and without `--no-download`. Repeat these checks against the retained rollback set before recovery. Preserve holds and auto/manual marks, and verify installed versions and `dpkg --audit` afterward. This is operator guidance, not behavior implemented by the simulation helper.

For the combined media, display and photo release, APT accepted 45 forward package changes and the inverse 36 restorations plus nine removals. The recovery set includes both native and 32-bit Vulkan drivers. [Exact release versions and rehearsal](../evidence/gnome-desktop-release-bundle.json).

On the ROG, the configured archive has priority 1001. After projecting the local Mutter upgrade, normal APT policy selected the older archive version for all five Mutter packages. A version-specific preference at the same priority selected the new version for all five while allowing later, higher-version archive updates at priority 1001. The coordinated local install uses the following preference until its reviewed version is available in the configured archive. Include this file in the rollback inventory and remove it when reverting. The rehearsal used a private preference file.

```text
Package: gir1.2-mutter-51 libmutter-51-0 mutter mutter-common mutter-common-bin
Pin: version 51.0-1ubuntu3+nativehdr15
Pin-Priority: 1001
```

### Vulkan presentation timing on Intel

With a compositor using a raw monotonic clock, the installed Intel driver used presentation feedback converted to the Vulkan clock when scheduling its next Wayland FIFO commit. On the ROG the two clocks differed by about 4.1 seconds. The driver queued deadlines seconds in the future, and mpv blocked acquiring a reusable swapchain image. Keeping the Wayland scheduler in the compositor clock reduced the median deadline from 4,124 ms to 16.17 ms at 60 Hz. The first corrected Intel build played the 4K FEL sample to EOF with eight output drops. With the normal amd64 Ubuntu driver package, 2.25 seconds of media took 2.26 seconds, with 17 output drops over the clip during concurrent builds. Both runs had zero decoder drops. NVIDIA played the same sample with zero drops. These were private hardware-backed compositor runs. [Wire and playback measurements](../evidence/mesa-wsi-presentation-clock.json).

### Physical trim selection and the staged dual-layer player

The reviewed mpv 0.41 `+rogdv4` passes the compositor's physical peak and black level to the creative mapper. For the laptop declaration, it chooses the trim at 616 cd/m², then scales linear light by 203/142 for the compositor encoding. A change of physical target invalidates cached mappings even when the desktop reports the same normalized headroom. Explicit targets and native exports retain their own target rules. The private rollback restores the installed `+rogdv2`. [Runtime qualification](../packaging/system-dv/physical-target-runtime-receipt.json) · [Package hashes](../packaging/system-dv/physical-target-package-receipt.json).

The separate mpv 0.42 candidate decodes both layers of Profile 7. Its libplacebo 7.387 integration calls the mapper after successful native-size enhancement-layer composition. A 4K picture at 0.5 s passed on Intel Vulkan using an explicit 616 cd/m² target. The corresponding base-only control declined the grade. Stock upstream mpv also produced different full-layer and base-only pictures at that timestamp, independently exercising the residual. These tests establish a digital reconstruction path on the ROG. A later staged 0.42 build retained the composed enhancement layer with automated 616 and 308 cd/m² target changes. A paused cached redraw preserved the presented PQ signal and changing to ordinary HDR cleared the Dolby capture state. The normal 0.42 Debian package subsequently passed on Intel with the real profile and a PQ window-capture framebuffer. Ubuntu package deployment and independent Dolby reference agreement remain open. [Measurements and controls](../evidence/profile7-intel-dual-layer.json).

#### Reconstruct the staged 0.42 package source

The source registry contains `mpv-fel-system-dv` (upstream 0.42.0), `libplacebo-fel-system-dv` (upstream 7.387.0) and the extended Ubuntu FFmpeg series. Use `tools/reconstruct.py COMPONENT WORKDIR` with each component and a task-owned work directory. For Debian packaging, copy the `debian/` directory from the exact Ubuntu `mpv 0.41.0-2ubuntu5` source archive listed in [the source registry](../sources.json) into the reconstructed mpv tree. Apply [the distro packaging overlay](../packaging/system-dv/mpv-042-ubuntu-packaging.diff) with `patch -p1`. Run `dpkg-buildpackage -b -us -uc` in an Ubuntu build environment containing the matching codec headers and the private ABI 387 development package. The package rules verify that the enhancement-layer codec API was detected. The corrected mpv and libmpv packages require the exact decoder build that provides the splitter and enhancement-layer configuration. Both ABI 387 libraries and the compatible ABI 360 provider require the parser revision that safely rejects unsupported interpolation. The package manager rejected a modeled downgrade to the stock parser with the player stack retained.

The following GNOME development batch adds a [small packaging delta](../packaging/system-dv/mpv-042-ubuntu-live-configuration.diff) after the original overlay. It accepts a decoder that provides the versioned live-configuration capability. The merged ten-package release retains its exact original decoder requirement.

The mpv 0.42 `+rogdv4` development package fixes window screenshots with normal colour tagging. On the ROG, the PNG itself contained BT.2020 primaries, PQ transfer and full-range RGB. Changing only a Profile 8.1 Level 8 trim changed 851,446 of 6,220,800 decoded RGB channels in the edited frame. The unedited frame matched exactly. The native source export and ordinary HDR10 controls each matched the previous package across 12,441,600 decoded bytes. To check a tagged file during paused-cache qualification, add `--check-tagged-png` to `packaging/system-dv/qualify-physical-cache.py`. [Paired-frame and file evidence](../evidence/mpv-window-grade-capture.json).

The final package test loaded the staged shared objects on the laptop's Intel GPU. The ordinary HDR10 comparison used the same input, same upstream player version and same screenshot export on both arms. All 12,441,600 decoded RGB bytes matched. The separate Dolby window capture selected the presentation signal and confirmed PQ in the framebuffer. Its untagged PNG carried no PQ declaration. With this package, enabling default PNG tagging also bypassed the display grade during window capture. The [packaged playback and recovery receipt](../evidence/profile7-ubuntu-packages.json) identifies the ten candidate artifacts and the eight previous packages. An automatic PNG export follows its own color-space policy. These digital results do not establish optical accuracy.

The 32-bit codec package retains Ubuntu's normal shared-codec feature set, the original SONAME and all previous exports. It adds five parser APIs. The higher WebP dependency floor matches both installed architectures. The separate libdovi fix changes the public C parser’s handling of an unsupported interpolation encoding. Stock aborted on a CRC-valid synthetic record. The patched library returned an error and parsed a valid record afterward. [Parser regression](../evidence/libdovi-unsupported-interpolation.json).

## Scope of the evidence

A decoded frame, a PQ screenshot, and a successful process exit each leave open whether the authored trims reached the output. Check the provider mapping result, the selected target and captured pixels together. [Status](STATUS.md) records what has actually passed. Earlier four-title comparisons against a reference renderer apply to the earlier engine and test conditions.

This path requires a reconstructed master. Profile 7 FEL requires a decoded enhancement-layer residual. Compressed metadata needs its effective frame state. Unsupported cases remain outside the shared path’s qualification. Other video engines, browsers and protected streaming require their own integration. Panel black, peak, chromaticities and optical agreement require measurement; the firmware’s declared values are available for target selection.

## Comparison with Dolby CM Offline

The current player and filter both processed a Profile 8.1 carrier derived from the same original RGB chart and XML as a retained Dolby CM Offline render. The virtual display described the reference target of BT.2020/PQ, 0.005–1,000 cd/m². The staged mpv selected that target automatically on NVIDIA. FFmpeg used the same target explicitly on Intel. Each candidate logged CM4 display mapping.

| Full-raster comparison at frame 0 | Mean ΔE ITP | p95 | Maximum |
|---|---:|---:|---:|
| Dolby reference vs. mpv window | 0.619 | 1.122 | 56.491 |
| Dolby reference vs. FFmpeg export | 0.923 | 1.636 | 56.494 |
| Original chart vs. decoded 10-bit base | 0.634 | 0.982 | 63.297 |
| Dolby reference vs. decoded base without grading | 34.598 | 91.617 | 112.641 |

All four comparisons cover all 3,276,800 pixels. The largest errors for both candidates and the codec control were near a source color transition. The mpv window’s maximum in patch interiors was 4.107. The reference target carries neutral Level 8 controls, so agreement here leaves creative-trim fidelity on other content open. The separate frame-local trim tests below verify that authored changes affect the intended frames. [Inputs, output encoding, metric and edge populations](../evidence/dolby-official-chart-consumer.json).

At the chart’s second target, Dolby CM Offline 5.6.4 rendered the unchanged frame and original XML for target 28 (BT.2020/PQ, 0–600 cd/m²). At the same physical target the mpv window’s mean ΔE ITP was 0.578 and p95 was 1.057. FFmpeg measured 0.834 and 1.431. Leaving the decoded base ungraded measured 47.13 and 124.57. The chart contains nonneutral Level 2 fields for this target; a matched render by itself cannot attribute the result to a particular trim field. Both targets use the same source scene. [Complete second-target results](../evidence/dolby-official-chart-consumer.json).

For the ROG panel comparison, the official renderer accepted the actual firmware-derived red, green, blue and white chromaticities, with a 616 cd/m² peak and 0.0004 cd/m² black. The private compositor advertised the laptop’s 142 cd/m² reference white. The mpv window encoded a linear gain of 203/142 for the compositor. Removing this known gain before comparing absolute light gave mean ΔE ITP 0.651 and p95 1.274. Leaving the desktop encoding in place gave 15.186 and 27.201. These are digital measurements of the window.

The provider currently chooses canonical P3-D65 for this panel. To measure the effect of that choice, the official renderer processed the same frame twice at 616 cd/m², changing only the target chromaticities. Across the full chart, 25,923 pixels differed by more than 3 ΔE ITP and the largest difference was 5.169. Using the panel’s exact coordinates in the runtime mapper remains an engineering task. [Target definitions, controls and full-raster results](../evidence/dolby-official-chart-consumer.json).

### Movie-frame comparison at 600 cd/m²

At frame 714 of *Sol Levante*, the official renderer processed the original 4K P3-D65 master and unchanged CM v2.9 XML. The staged Intel filter processed a carrier built from that same master at native resolution. Across all 8,294,400 pixels, mean ΔE ITP was 2.61 and p95 was 7.20. Giving the reference tool the reconstructed 10-bit base reduced those figures to 2.02 and 6.49. The ordinary 1080p Profile 5 release scored 9.21 and 26.31 against the 4K official render downsampled in linear light. The normal NVIDIA mpv window measured 9.19 and 26.31 on the same frame. Sequential playback and an interactive seek produced identical screenshots. Starting directly at 29.750 s skipped the in-band parameter sets on this asset and landed at 30 s. Both installed and staged FFmpeg reproduced that cold-start result. The Profile 5 figures include differences between two releases. [Source attribution and all full-raster controls](../evidence/dolby-sol-levante-frame714.json).

The original XML and both consumer RPUs describe the same shot. The XML minimum corresponds to roughly 583 on the 12-bit PQ scale. Both RPUs contain 12. The middle and maximum agree to rounding. On identical uncompressed master pixels, the same CPU mapper measured mean 0.114 and p95 0.497 with the authoring anchors, and 1.607 and 6.291 with the delivered anchors. The consumer stream alone cannot distinguish original minima collapsed to the same encoded value. Consumer accuracy needs a reference that processes that stream’s delivered state. [Measured controls](../evidence/dolby-sol-levante-frame714.json) · [Generator’s range handling](https://github.com/quietvoid/dovi_tool/blob/2.3.4/dolby_vision/src/rpu/extension_metadata/blocks/level1.rs).

With only the shot’s three brightness anchors replaced by their delivered RPU values in a copy of the XML, the reference comparison on the same 4K decoded pixels gave mean ΔE ITP 0.650 and p95 1.596 for the Linux filter. Over 8,294,400 pixels, 93,700 exceeded 3. The CPU mapper on original master pixels scored 0.127 and 0.543 against the corresponding reference. This isolates the available metadata and source pixels on one shot. The official processor used its XML input for both comparisons. [Matched-input measurements](../evidence/dolby-sol-levante-frame714.json).


## Digital qualification

| Check | Result |
|---|---|
| Explicit FFmpeg export | A real Profile 5 frame and a synthetic Profile 8.1 frame mapped. An SDR control and a second control with unspecified transfer/primaries bypassed the provider. The latter FFV1 fixture lost its intended HDR10 tags before decoding. A replacement HEVC Main 10 clip carried verified PQ/BT.2020 tags, MDCV and CLL on its decoded frames. Normal mpv output matched stock mpv pixel for pixel on that HDR10 control; FFmpeg and mpv differed under their respective render settings. All four exports carried the selected 1,000 cd/m² target metadata. |
| Ordinary mpv on Wayland Vulkan | A genuine nonblack Profile 5 frame at 30 s rendered to a signalled 100 cd/m² BT.2020/PQ destination. The earlier player confirmed an exact authored Level 2 target at this timestamp. On a 32,400-pixel grid, mpv versus FFmpeg had mean ΔE_ITP 0.067 and p95 0.295. Against the previous private player, mean was 0.396, p95 0.667 and the largest sampled difference was 7.97. |
| Per-frame creative trims | Two six-frame Profile 8.1 streams used identical decoded base pixels. Changing only the 600 cd/m² trim power on frames 2 and 3 changed exactly those two output frames. Separate CM v2.9 Level 2 and CM v4.0 Level 8 runs both passed. |
| Intel Vulkan | The ordinary FFmpeg binary rendered a real 1920×1080 Profile 5 frame through the shared provider on the ROG’s integrated Arc GPU, with a 616 cd/m² P3-D65 target and BT.2020/PQ encoding. This was an offscreen digital check. |
| Source crop and interpolation | Native-size mapping and cropped output pixel checks passed for equal-size and bilinear-scaled output. A deliberately failing non-reference mixer frame propagated a render error. |
| Export side data | An already-PQ synthetic frame carrying HDR10+ and Dolby side data produced the new 600 cd/m² mastering metadata and removed both obsolete source metadata blocks. |

Clean replay of all four series reproduced the base and candidate source trees pinned in the registry. The second mpv patch omits undefined MaxCLL and MaxFALL requests from Wayland image descriptions. A separate Wayland trace showed that Ubuntu Mesa 26.2.4’s Vulkan WSI submits its own image description and sends an unknown MaxFALL as zero. Weston rejected that description. The Ubuntu Mesa patch omits unknown optional values at that second producer and validates the encoded v1 luminance bounds. The corrected driver submitted a PQ/BT.2020 image description accepted by Weston.

The [digital receipt](../evidence/shared-display-management-20261107.json) records the source trees and test scope. The trim fixtures used dovi_tool’s public [metadata generator](https://github.com/quietvoid/dovi_tool/blob/main/docs/generator.md). They test the effect and lifetime of a known input change. Optical panel accuracy and numerical agreement with an independent Dolby reference are separate measurements.

To run the native regressions in a build environment with the candidate libraries and a Vulkan device:

```sh
cc -std=c11 packaging/system-dv/renderer-regression.c -o renderer-regression \
  $(pkg-config --cflags --libs libplacebo-rog1)
./renderer-regression crop
./renderer-regression crop-bilinear
./renderer-regression mix-failure
cc -std=c11 packaging/system-dv/export-metadata-regression.c -o export-metadata-regression \
  $(pkg-config --cflags --libs libavfilter libavutil)
./export-metadata-regression
```

## ROG panel target

A read-only query returned a firmware-derived target of 0.0004–616 cd/m², with a reference white of 142 cd/m². Replaying that exact description on an isolated compositor selected the P3-D65 gamut automatically. mpv normalized the working peak to 880.644 using its 203 cd/m² reference white. Mesa described a rounded 881 cd/m² mastering maximum on the surface. That result applies to the installed mpv 0.41 build. The later staged player selects the creative trim at the physical 616 cd/m² peak and applies the reference-white scaling separately. The light emitted by this panel still needs measurement.

## Other GStreamer desktop players

The normal GNOME Showtime package uses the GTK GStreamer sink. The staged software, Intel VA and NVIDIA decoders keep reconstruction data and the raw RPU with each reordered picture. The sink grades that picture for its GTK surface before ordinary color conversion. Other GStreamer applications choose their own decoders, sinks and presentation paths. [Native metadata transport](GSTREAMER_DOLBY_TRANSPORT.md) · [Qualified app and plugin revisions](../evidence/gstreamer-gtk-final-packages-20261108.json).

## Physical xy target candidate

At the firmware-declared 616 cd/m² target, the normal Ubuntu FFmpeg filter produced all 19,660,800 chart bytes from the qualified development render on Intel Vulkan. Both codec architectures preserve their common package files exactly. The 32-bit decoder maintained all 544 decoders, 218 encoders and 67 hardware configurations and parsed a genuine Profile 7 metadata packet. [Release packages, source replay and digital checks](../evidence/ffmpeg-panel-xy-release.json).

The separate raw-xy candidate adds an optional target-v2 API to the shared
provider. The existing target structure, ABI number, named options and entry
points stay unchanged. The public headers and adapters are reconstructible
from this repository and the pinned upstream sources; the private mapping
implementation and SDK payload remain outside the repository.

Normal mpv passes the preferred Wayland surface target through its physical
auto-target branch. The GTK mapper passes the surface target already retained
in its frame/cache context. FFmpeg accepts an explicit
`target_xy=rx/ry/gx/gy/bx/by/wx/wy` with `target_peak`; `target_gamut` supplies
the complete named fallback. The adapters discover the additive symbols at
runtime, so an older provider remains usable and reports named fallback.

Debian builds request a versioned, public SDK capability. The development package that provides the interface declares the capability for its renderer ABI. The build verifies the version-2 target structure and declarations against the installed headers. An older runtime still uses the existing named-target path when the optional mapping symbol is unavailable. Private binary revisions and inventories stay on the build host.

Raw xy currently applies to neutral creative-colour fields in CM4. Creative
colour trims, unsupported models and invalid raw coordinates retain the full
named mapping. Diagnostics distinguish these choices. This does not establish
arbitrary-xy creative-gamut weighting or optical accuracy.

The coordinated release contains mpv `+rogdv5.1`, FFmpeg `+rogdv4.2` on amd64 and i386, the GTK mapping core `+rogdv3.1`, GTK `+rogdv4`, and the GTK sink and Showtime `+rogdv4.1`. The build resolves its SDK through public interface version 2. FFmpeg derives exact sibling-library dependencies from its source version. A normal mpv process also played the chart using the older runtime's named-target fallback. [Normal source replay and SDK compatibility](../evidence/sdk-api-v2-normal-products.json).

Offline APT on the ROG accepted all 45 changes with zero removals. The inverse transaction restores all 36 previously installed versions and removes the nine additions. All 81 archives passed hash verification on the laptop. The original rollback also exists on a separate private drive. A preference covering five Mutter packages selects the staged compositor under normal APT policy. The running desktop still uses the earlier release. [Package rehearsal](../evidence/panel-desktop-release-bundle.json) · [GTK sink and Showtime source replay](../evidence/panel-showtime-release-packages.json).
