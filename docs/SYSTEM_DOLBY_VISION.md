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

The source series start from Ubuntu libplacebo `7.360.1-1`, mpv `0.41.0-2ubuntu5` and FFmpeg `7:8.1.2-2ubuntu2`. The three `ubuntu-*-system-dv` entries in [sources.json](../sources.json) pin the distro source archives, patches and resulting trees. [The provider interface](../packaging/system-dv/include/dv_provider.h) defines the data exchanged with the mapper. Building the consumers requires the matching private SDK, including its namespaced renderer headers. The private provider, SDK and signed or device-specific material are distributed separately from this repository.

The runtime packages are `libplacebo-rog1-360` and `librog-dv-provider1`. The ordinary playback and export entry points use the rebuilt Ubuntu `mpv` and `libavfilter11` packages respectively. Retain the exact stock client packages before deployment. On the tested Ubuntu installation the transaction upgrades mpv and libavfilter11 and adds the renderer, provider and stock libshaderc1. Retain all five local package files. Simulate installation with the files, inspect the changes, then install the same files. The filter pins the exact stock libavcodec62 and libavutil60 versions for the private FFmpeg symbols it calls. Both amd64 and i386 installations can keep those stock libraries. For recovery simulate reinstalling the retained stock mpv and libavfilter11 packages with `--allow-downgrades`, restore them and remove the two added libraries after checking reverse dependencies. No compositor restart is required.

## Scope of the evidence

A decoded frame, a PQ screenshot, and a successful process exit each leave open whether the authored trims reached the output. Check the provider mapping result, the selected target and captured pixels together. [Status](STATUS.md) records what has actually passed. Earlier four-title comparisons against a reference renderer apply to the earlier engine and test conditions.

This path requires a reconstructed master. Profile 7 FEL requires a decoded enhancement-layer residual. Compressed metadata needs its effective frame state. Unsupported cases remain outside the shared path’s qualification. Other video engines, browsers and protected streaming require their own integration. Panel black, peak, chromaticities and optical agreement require measurement; the firmware’s declared values are available for target selection.

## Digital qualification

| Check | Result |
|---|---|
| Explicit FFmpeg export | A real Profile 5 frame and a synthetic Profile 8.1 frame mapped. SDR and HDR10 controls bypassed the provider. All four exports carried the selected 1,000 cd/m² target metadata. |
| Per-frame creative trims | Two six-frame Profile 8.1 streams used identical decoded base pixels. Changing only the 600 cd/m² trim power on frames 2 and 3 changed exactly those two output frames. Separate CM v2.9 Level 2 and CM v4.0 Level 8 runs both passed. |
| Intel Vulkan | The ordinary FFmpeg binary rendered a real 1920×1080 Profile 5 frame through the shared provider on the ROG’s integrated Arc GPU, with a 616 cd/m² P3-D65 target and BT.2020/PQ encoding. This was an offscreen digital check. |
| Source crop and interpolation | Native-size mapping and cropped output pixel checks passed for equal-size and bilinear-scaled output. A deliberately failing non-reference mixer frame propagated a render error. |
| Export side data | An already-PQ synthetic frame carrying HDR10+ and Dolby side data produced the new 600 cd/m² mastering metadata and removed both obsolete source metadata blocks. |

Clean replay of all three series reproduced the base and candidate source trees pinned in the registry. The second mpv patch omits undefined MaxCLL and MaxFALL requests from Wayland image descriptions. A separate Wayland trace showed that Ubuntu Mesa 26.2.4’s Vulkan WSI submits its own image description and sends an unknown MaxFALL as zero. Weston rejected that description. Both producers matter to normal playback.

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

## Other GStreamer desktop players

The GStreamer libav plugin links FFmpeg; that alone does not run the libplacebo filter in a player. The default Intel VA H.265 decoder also bypasses the FFmpeg software decoder. For GStreamer 1.28 the software integration point is `gst_ffmpegviddec_video_frame()`, while decoded side data still belongs to its AVFrame. The VA path needs the RPU associated with the corresponding `GstH265Picture` through picture reordering. Both require an owned per-buffer metadata representation and a sink that maps reconstructed pixels for the downstream display before ordinary GL colour conversion. The ROG currently has no Showtime, Totem or Clapper package installed. Application defaults and decoder ranks are independent of this integration. [Software decoder](https://github.com/GStreamer/gstreamer/blob/1.28.7/subprojects/gst-libav/ext/libav/gstavviddec.c) · [H.265 decoder base](https://github.com/GStreamer/gstreamer/blob/1.28.6/subprojects/gst-plugins-bad/gst-libs/gst/codecs/gsth265decoder.c).
