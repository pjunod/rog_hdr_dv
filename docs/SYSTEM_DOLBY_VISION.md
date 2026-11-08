# Shared Dolby Vision display management on Ubuntu

## Where the grade is applied

The decoder exposes Dolby reconstruction data and a raw reference processing unit (RPU) for each frame. The existing libplacebo adapter carries the reconstruction data, but its stock rendering API has no input for the full RPU and a target display mapper. The patched adapter keeps the bytes with the frame. The renderer reconstructs the BT.2020/PQ RGB image, calls the provider with the frame’s own metadata and destination display, and uses its output before final scaling and encoding. Successful mapping bypasses the generic highlight mapper. Unsupported inputs can take the ordinary rendering path. A provider error fails the render.

The new renderer has a distinct SONAME, `libplacebo.so.360rog1`, and distinct exported symbols. A process may load it alongside Ubuntu’s stock libplacebo. Installing the provider alone does not change existing binaries. Clients must use the matching frame and rendering interfaces.

## Clients

| Ubuntu client | Destination | Normal entry point |
|---|---|---|
| mpv 0.41.0, gpu-next | HDR output described to the player by the display system | `mpv --vo=gpu-next movie.mp4` |
| FFmpeg 8.1.2, libplacebo video filter | Explicit export target, because a filter graph can run without a display | Example below |

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

The ROG now has the seven verified packages. The normal system FFmpeg binary mapped a genuine, nonblack Profile 5 frame at 30 seconds on the integrated Intel GPU, with a target of 0.0004–616 cd/m² and P3-D65 primaries. Normal mpv loaded the system libraries and mapped the same title on Intel through a private Wayland compositor reproducing the panel declaration. The trace shows BT.2020/PQ and a rounded maximum of 881 cd/m². This confirms the automatic target discrepancy on the installed player. The GNOME session stayed open throughout.

## Scope of the evidence

A decoded frame, a PQ screenshot, and a successful process exit each leave open whether the authored trims reached the output. Check the provider mapping result, the selected target and captured pixels together. [Status](STATUS.md) records what has actually passed. Earlier four-title comparisons against a reference renderer apply to the earlier engine and test conditions.

This path requires a reconstructed master. Profile 7 FEL requires a decoded enhancement-layer residual. Compressed metadata needs its effective frame state. Unsupported cases remain outside the shared path’s qualification. Other video engines, browsers and protected streaming require their own integration. Panel black, peak, chromaticities and optical agreement require measurement; the firmware’s declared values are available for target selection.

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

A read-only query returned a firmware-derived target of 0.0004–616 cd/m², with a reference white of 142 cd/m². Replaying that exact description on an isolated compositor selected the P3-D65 gamut automatically. mpv normalized the working peak to 880.644 using its 203 cd/m² reference white. Mesa described a rounded 881 cd/m² mastering maximum on the surface. The virtual run identifies the mapper’s current trim-selection input; physical-target trim choice and emitted panel light are separate questions.

## Other GStreamer desktop players

The GStreamer libav plugin links FFmpeg; that alone does not run the libplacebo filter in a player. The default Intel VA H.265 decoder also bypasses the FFmpeg software decoder. For GStreamer 1.28 the software integration point is `gst_ffmpegviddec_video_frame()`, while decoded side data still belongs to its AVFrame. The VA path needs the RPU associated with the corresponding `GstH265Picture` through picture reordering. Both require an owned per-buffer metadata representation and a sink that maps reconstructed pixels for the downstream display before ordinary GL colour conversion. The ROG currently has no Showtime, Totem or Clapper package installed. Application defaults and decoder ranks are independent of this integration. [Software decoder](https://github.com/GStreamer/gstreamer/blob/1.28.7/subprojects/gst-libav/ext/libav/gstavviddec.c) · [H.265 decoder base](https://github.com/GStreamer/gstreamer/blob/1.28.6/subprojects/gst-plugins-bad/gst-libs/gst/codecs/gsth265decoder.c).
