# WebKitGTK clear video and native HDR

**Status:** reviewed source; GTK4 Ubuntu binary packages built; normal-sandbox runtime qualification pending · **Updated:** 2026-11-11

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


Use the destination-aware mapping SDK (destination ABI1 and source-lease ABI2, core package 0.1.0+rogdv5 or newer) and the modified GTK public development headers that declare GdkWaylandHdrRendering. The matching GTK source candidate is 4.24.1+ds-1+rogdv5. The ordinary backend remains available when optional APIs are absent. Discovery of the common gdkwaylandsurface.h filename alone does not prove the HDR declarations exist.

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

## Source and picture lifetime

The browser requires a before-first-byte witness from the exact original WebKitWebSrc instance through allowed transparent holders to the selected qtdemux. Unknown adaptive/decrypting paths, late observations, protection events and ambiguous topology stay on the ordinary route. Input histories cannot rearm without a confirmed whole READY drain. The proof is bound to the actual live demux pad and its complete coded configuration, not a reused stream-id string.

Selected leases carry process-qualified origin and selection tokens. Source/CDM changes and filter-local stream switches revoke old retained pictures and already-exported UI planes. Target generation and view revision are separate fences. The bounded UI registry prevents delayed old activations, revocations or exported buffers from affecting another view or a newer source.

The native plane carries its own authoritative RGBA64/PQ/BT2020 tags. It is eligible only for an opaque upright unobscured axis-aligned video region with a valid current target lease. Unsupported CSS/orientation/subtitles/overlay combinations retain the intact graded SDR page. Export bounds are checked before expensive regrading and again afterward.

## Qualification boundary

Reviewed CPU evidence covers source topology, first-byte ordering, active-pad rejection, selected-lease revocation, late-plane registry rejection and the export size envelope. Focused compilation includes the GTK4 native branch and an actual no-video translation unit. The earlier 100-nit page-video screenshot proves only its historical SDR floor.

The final full build, normal-sandbox clear MP4 negotiation, genuine-RPU versus clean matched base control, held paused target change, native plane tags/lease, source/CDM/unknown-route fallback and CSS/page pixel controls still require receipts on this exact source and package family. Until those pass, this is a source candidate, not qualified native HDR browser delivery. Optical panel accuracy remains separate.
