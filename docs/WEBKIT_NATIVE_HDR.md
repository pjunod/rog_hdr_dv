# WebKitGTK clear video and native HDR

**Status:** GTK4 Ubuntu packages built. Normal-sandbox runtime qualification passed all 30 steps, including Profile 7 FEL on NVDEC (`+rogdv3`, see below). · **Updated:** 2026-11-12

This browser change gives ordinary clear MP4/HEVC HTML video an explicit
100-nit BT709/sRGB destination and adds an independent tagged HDR video plane
when the realized GTK view grants a current native HDR lease. The page itself
remains sRGB. It contains application integration and CPU probes only: no
mapping provider, decoder payload, licensed engine, binaries, media or
reference output.

The [product patch](../patches/ubuntu-webkitgtk-native-hdr/0001-webkitgtk-clear-video-and-native-hdr.patch)
applies to Ubuntu `webkit2gtk 2.52.6-1ubuntu1` after its own patches. Its
base and candidate trees are pinned in [sources.json](../sources.json)
(component `ubuntu-webkitgtk-native-hdr`). For Ubuntu packages use
[the GTK4-only packaging recipe](../packaging/webkitgtk-native-hdr/README.md);
it records this patch in the normal quilt series.

## Build with the real public SDKs


Use the destination-aware mapping SDK (destination ABI1 and source-lease ABI2; runtime core package 0.1.0+rogdv7 or newer, build headers from 0.1.0+rogdv5) and the modified GTK public development headers that declare GdkWaylandHdrRendering. The matching GTK source candidate is 4.24.1+ds-1+rogdv5. The ordinary backend remains available when optional APIs are absent. Discovery of the common gdkwaylandsurface.h filename alone does not prove the HDR declarations exist.

Reuse an owned isolated compiler slot, with normal distribution build dependencies. Set the final prefix and helper directory to owned absolute runtime paths before compiling; DESTDIR alone does not rewrite compiled helper locations. Keep standard WebKit bubblewrap sandboxing enabled.

```bash
# Supply the exact owned source, warm build, runtime and install-staging paths.
cmake -S "$task_source" -B "$task_build" -G Ninja \
  -DPORT=GTK -DUSE_GTK4=ON -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_LTO=OFF -DENABLE_MINIBROWSER=ON \
  -DENABLE_DOCUMENTATION=OFF -DENABLE_INTROSPECTION=OFF \
  -DENABLE_BUBBLEWRAP_SANDBOX=ON \
  -DGTK_DOVI_SDK_ROOT="$task_core_prefix/include" \
  -DGTK_NATIVE_VIDEO_GDK_SDK_ROOT="$task_gtk_prefix/include/gtk-4.0" \
  -DCMAKE_INSTALL_PREFIX="$task_runtime" \
  -DLIBEXEC_INSTALL_DIR="$task_runtime/libexec/webkitgtk-6.0"
# Retain the workflow resource guard around this single-job build.
cmake --build "$task_build" --parallel 1 --target WebKit MiniBrowser \
  WebKitWebProcess WebKitNetworkProcess WebKitGPUProcess webkitgtkinjectedbundle
DESTDIR="$task_stage" cmake --install "$task_build"
```

Materialize only owned files from `$task_stage$task_runtime` into the compiled `$task_runtime` path. The measured private builder uses 6GiB, two CPUs, nice15 and one job. Its host guard launches above 10GiB available memory/40GiB free disk and stops below 4GiB/20GiB. These are operational limits of this workflow.

Before claiming the native branch was compiled, inspect the actual UI adapter compile command and preprocess it with those same include flags: `GDK_TYPE_WAYLAND_HDR_RENDERING` must be defined. For the native frame adapter, verify `GST_GTK_DOVI_DESTINATION_ABI >= 1` and `GST_GTK_DOVI_SOURCE_LEASE_ABI >= 2` from the same actual command. A manually added include during a diagnostic does not prove the normal target selected the new headers.

## Viewport suspension keeps the latest requested state

WebKit suspends a muted video that leaves the viewport and restores a saved
pipeline state when it returns. The native source-replacement drain moves the
pipeline to READY before the first viewport notification, so a suspension
saved READY; `changePipelineState()` recorded only requests above PAUSED, so
the load's PAUSED preroll was not remembered and becoming visible restored
READY, stopping typefinding. The patch records every request made while
suspended and still defers requests above PAUSED until the element is visible.

## The mapper leads the page video sink

The mapper sits at the head of the page video sink inside one sink bin. It is not a playsink
`video-filter`, because playbin answers decodebin's pre-exposure CAPS queries from the video sink
alone and never consults a filter. With the filter placement, a VA decoder settled on a tiled
DMABuf for a qualified stream. The mapper cannot import that memory, so the chain failed to
negotiate once linked (media error 4). In the sink bin, every query a decoder makes is answered
by the mapper and what lies behind it.

## Byte holders autoplugged after typefinding

uridecodebin creates its download buffer, and decodebin creates its inner typefind, only after the
source's first bytes have been typefound. A holder observed after the source started was
previously born tainted, so no Dolby load could ever be attested and every load stayed ordinary.
"Before bytes" is now judged per input. A pending input is armed from its own sink probe while its
first buffer is still undelivered, behind an upstream route that must already be attested. Every
attestation decision is logged at debug level.

## The sandbox keeps its own GStreamer registry

The WebKit sandbox binds the host's GStreamer cache read-write, but it cannot reach every device the
host can: CUDA needs `/dev/nvidia-uvm`, so inside the sandbox the NVIDIA plugin registers no elements.
A sandboxed WebKit app (GNOME Web, Yelp…) that scanned plugins first after a package update wrote
that into the host's registry. Host GStreamer applications then lost the NVIDIA decoders, and with
them Showtime's Profile 7 FEL composition, until the plugin files changed. Reproduced with GNOME Web
50.4 in the private compositor: afterwards `gst-inspect-1.0 nvh265dec` failed on the host.

Since `2.52.6-1ubuntu1+rogdv2` (product `1d380b37`), sandboxed processes use their own registry,
`$XDG_CACHE_HOME/webkitgtk/gstreamer-1.0/registry.<cpu>.bin`, unless `GST_REGISTRY` or `GST_REGISTRY_1_0`
names one explicitly, and the host's registry directory is read-only inside the sandbox. Browser
playback is unchanged.

## Source and picture lifetime

The browser requires a before-first-byte witness from the exact original WebKitWebSrc instance through allowed transparent holders to the selected qtdemux. Unknown adaptive/decrypting paths, late observations, protection events and ambiguous topology stay on the ordinary route. Input histories cannot rearm without a confirmed whole READY drain. The proof is bound to the actual live demux pad and its complete coded configuration, not a reused stream-id string.

Selected leases carry process-qualified origin and selection tokens. Source/CDM changes and filter-local stream switches revoke old retained pictures and already-exported UI planes. Target generation and view revision are separate fences. The bounded UI registry prevents delayed old activations, revocations or exported buffers from affecting another view or a newer source.

The native plane carries its own authoritative RGBA64/PQ/BT2020 tags. It is eligible only for an opaque upright unobscured axis-aligned video region with a valid current target lease. Unsupported CSS/orientation/subtitles/overlay combinations retain the intact graded SDR page. Export bounds are checked before expensive regrading and again afterward.

## Runtime qualification

The steps ran in a private headless GNOME compositor: a virtual 1280×800 monitor in colour
mode 1 at 616 cd/m², with its own session bus. Each run used a staged MiniBrowser, the normal
bubblewrap/seccomp sandbox, and the exact public package archives (WebKit, GTK, mapper core,
bad/extra and bridge). Captures are ten-bit PQ, or BGRx when the target is SDR. Values are
nominal, not optical.

- **Native verdict:** the video's 99.9th percentile exceeds page white by more than 5%. An
  ordinary page video can never exceed page white.
- **Dim pictures:** a dim native picture can stay below page white. Then the decisive control
  is the same picture forced ordinary by CSS clipping (its twin). Native must change the inner
  region by more than 5% and the run must have mapped pictures. It must also be brighter than the
  twin, or the compositor must have recorded a visible native redraw of the picture shown at that
  step. An untrusted load shows an ungraded picture, which also differs, but it never reaches the
  native redraw. The redraw alternative exists because a Dolby grade can be dimmer than its base
  layer's page-white rendering, as in the Profile 7 clip at 2.5 s.
- **Evidence:** only a run whose receipt records a captured, process-qualified run is analysed,
  with the step list and every capture digest matching the files. The PipeWire reader that writes
  the captures is digest-pinned like the other helpers, and its digest is in every receipt.
- **Repeat:** the release candidate was qualified twice, before and after the review fixes,
  with identical verdicts.

| Case | Expected | Result |
|---|---|---|
| Profile 5 at 30 s | native | native: p99.9 462 cd/m² vs page white 203; differs from its clipped twin by 49% |
| Profile 8 at 0 s | native | native, 478 cd/m² |
| Profile 5 HDR → SDR → HDR target, paused | native, ordinary, native | identical native capture restored |
| Profile 5 seek, then base and original sources | native, ordinary, native | pass |
| SDR, HDR10, clean base, SDR target | ordinary | pass |
| CSS opacity, clip, rotation, covering element; native controls | ordinary | pass; page patches unchanged |
| Profile 5 playing for 10 s | native | native; no QoS drops with mapper core `0.1.0+rogdv8` (core `rogdv7` dropped 14 pictures in the first 0.55 s) |
| Profile 7 FEL at 2.5 s | native | native on NVDEC (`EL composed=1`): differs from its clipped twin by 14%, visible native redraw recorded; a dim grade, p99.9 170 cd/m² |
| Profile 7 → base → Profile 7, and Profile 7 → Profile 5 → Profile 7 | native, ordinary, native | pass |

Profile 7 FEL composition exists only in the CUDA decoder. cuInit needs `/dev/nvidia-uvm`, which
the WebKit sandbox did not bind before `+rogdv3`.

- **Device and decoder choice.** `+rogdv3` binds the device. Binding it alone let the equal-rank
  NVIDIA decoder win for all browser HEVC/H.264, so decodebin's candidates are now ordered from
  registry metadata: the decoder on the page's rendering GPU first, unless the stream has an
  enhancement layer and another decoder declares that it composes it. Ordinary video stays on the
  Intel GPU, and Profile 7 FEL goes to NVDEC. gst-plugins-bad `rogdv7` declares that metadata, and
  WebKit Breaks older bad packages. The ordering applies to ordinary playback through
  uridecodebin; MSE and encrypted media keep GStreamer's order. A bad package without the metadata
  (for example a later stock Ubuntu revision) leaves the default order in place.
- **Sandbox surface.** Every web process now reaches the NVIDIA unified-memory driver interface;
  `nvidiactl` and `nvidia0` were already bound for GL. The bind is skipped when the node is absent,
  and CUDA then stays unavailable until a host process loads `nvidia_uvm`.
- **Later video after an NVDEC source.** In one web process, ordinary video shown after a native
  NVDEC picture used to present nothing. The retained native frame held the decoder's CUDA picture,
  and WebKit's compositor dropped it on its own thread. The last reference finalized the decoder's
  CUDA context there. Mapper core `0.1.0+rogdv9` releases decoder pictures on a thread of its own,
  and WebKit Breaks older cores. The exact GL-side effect of the finalization was not isolated: a
  standalone EGL and CUDA program kept its context. The fix point is proven by the same runs
  passing with NVDEC everywhere.
- **Source change after Profile 7 (`0.1.0+rogdv10`).** Profile 7 under a CSS clip, then the base,
  then Profile 7 again, crashed the web process in WebKit's tile painter (a null Skia surface).
  Setting the new source frees the old pipeline on the main thread, and with it the last mapper,
  which destroyed the process-shared Vulkan instance there. The Vulkan loader then unloaded the
  NVIDIA driver library, whose unload calls `eglReleaseThread` and so released the main thread's
  current EGL context, the Skia context WebKit still believed current. The next tile textures were
  created without a context (texture name 0), Skia could not wrap them, and the painter crashed.
  The core now destroys Vulkan devices on a thread of its own. The case passes, and the main thread
  no longer loses its context. The CUDA finalization above probably released the compositor's
  context in the same way; that was not traced.

The first-frame drops came from the compositor's mapper creating its own Vulkan device on the
first visible picture. Mapper core `0.1.0+rogdv8` shares one device per process, so the first
native picture reaches the compositor about 70 ms after playback starts instead of about 690 ms.
[Details](GSTREAMER_DOLBY_RECONSTRUCTION.md#browser-runtime-fixes-november-11).

## Qualification boundary

Reviewed CPU evidence covers source topology, first-byte ordering, active-pad rejection, selected-lease revocation, late-plane registry rejection and the export size envelope. Focused compilation includes the GTK4 native branch and an actual no-video translation unit. The earlier 100-nit page-video screenshot proves only its historical SDR floor.

The runtime table above covers this exact source and package family in a private compositor. Encrypted (CDM) routes, owner-desktop presentation and optical panel accuracy remain separate.
