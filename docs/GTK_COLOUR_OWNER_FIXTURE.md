# GTK/Vulkan colour-owner fixture — exercise the default fallback

**Prepared source only. Nothing has been compiled or executed.** No product source, renderer preference, display, compositor, container or resource setting is changed by this preparation. These two small C files are outside the GTK source clone.

[The Vulkan interposer](../packaging/image-colour/vk-pass-filter.c) targets the authenticated GTK path that calls the public loader exports `vkGetPhysicalDeviceSurfaceFormatsKHR` and `vkCreateSwapchainKHR`. It also intercepts pointers returned by GIPA/GDPA, after calling the real query and preserving NULL. Every other function pointer is forwarded. It is an ELF test interposer, not a replacement ICD or universal Vulkan layer; a private `dlsym(handle, ...)`/deep-bound or future formats2 path would need separate coverage and cannot be called passed here.

Observe mode forwards the real formats call unchanged. Filter mode enumerates the actual format pairs, removes only PASS_THROUGH, preserves remaining order/values, respects count/capacity and VK_INCOMPLETE, and records swapchain attempts before forwarding. It never adds a format. An unstable/oversized list or absence of any real non-pass alternative produces fixture_error and forwards unmodified data: **inconclusive**, not an invalid zero-format capability or a forced unsupported path. Trace creation failure disables filtering and is ineligible. The normal Vulkan loader must remain the downstream public export provider.

[The ordinary GTK scene](../packaging/image-colour/gtk-default-scene.c) draws a changing marker and four public sRGB blocks using an ordinary GTK window/drawing area. It never selects a renderer, creates a native HDR lease or captures the desktop. Before creating its window it checks the actual Wayland peer socket, UID and expected private compositor PID. It records the actual default GSK type, own wl_surface ID, loaded GTK path, draw/after-paint counts and completed GDK frame-timing metadata. Three completed frames and draws are needed; the scene has a15s deadline. Its exit0 means scene completion only, **not** the whole paired qualification. GDK timing metadata on a private compositor is not proof of physical panel presentation or optical accuracy.

Run commands from an owned source checkout. This fixture complements the
[image pipeline correction](GTK_WEBKIT_IMAGE_COLOUR.md) and
[display-target contract](GDK_DISPLAY_TARGET.md). It is prepared source, not
a passing candidate receipt.

## Later recipe — review/admission first

1. After the whole batch is merge-ready and adversarial review is complete, obtain resource-owner admission for fixture compilation and the approved private compositor run. Use existing dependencies; report missing Vulkan/GTK Wayland development headers rather than install anything. Record actual compiler/toolchain, source hashes, linked candidate GTK path/hash, normal private-prefix environment and compositor executable/library identities. No new image/build framework is prescribed.
2. Build the two files in an owned output directory with the admitted native compiler. The app must use the **actual candidate** GTK pkg-config and normal private-prefix runtime paths. Example command shapes, **not executed**:

```sh
: "${HDR_WORK:?Set an owned durable output directory}"
FIXTURE="$HDR_WORK/gtk-colour-owner-fixture"
mkdir -p "$FIXTURE"
cc -std=c11 -O2 -Wall -Wextra -fPIC -shared packaging/image-colour/vk-pass-filter.c -o "$FIXTURE/libvk-pass-filter.so" -ldl -pthread
cc -std=c11 -O2 -Wall -Wextra packaging/image-colour/gtk-default-scene.c -o "$FIXTURE/gtk-default-scene" $(pkg-config --cflags --libs gtk4 wayland-client) -ldl
```

Set the candidate's PKG_CONFIG_PATH in that compiler's environment before expansion. Do not accidentally resolve system GTK. Do not add a Vulkan link dependency to the interposer itself; its next functions are the loaded public loader exports. Full native compilation/linking is still required before claiming these sources work.

3. Reuse only the reviewed task-owned private Mutter+D-Bus bootstrap later, outside the owner's session. Prove its PID/socket/runtime and output connector before launching. Preserve the compositor's normal options/advertisements; do not force HDR capability, physical display configuration or driver ranks. The app is not a session bootstrap. Provide its exact private runtime and verified compositor PID. Use task-owned XDG data/cache/config/TMPDIR and normal sandboxing. Keep DISPLAY/WAYLAND_SOCKET and renderer/feature overrides absent in this app child. Never export this interposer to Mutter, the bus, owner apps or the host environment.
4. Run exactly two fresh scenes on that same reviewed private fixture, default GSK selection in both: observe then remove-PASS. Scope these variables **only** to the app invocation, retaining the already reviewed private/candidate environment:

```sh
env -u DISPLAY -u WAYLAND_SOCKET -u GSK_RENDERER -u GDK_DEBUG \
  LD_PRELOAD="$FIXTURE/libvk-pass-filter.so" \
  GTK_COLOUR_FIXTURE_TRACE="$RUN/vulkan.jsonl" \
  GTK_COLOUR_FIXTURE_FILTER_PASS_THROUGH=0 WAYLAND_DEBUG=client \
  "$FIXTURE/gtk-default-scene" "$PRIVATE_RUNTIME" "$PRIVATE_MUTTER_PID" "$RUN/scene.json" \
  >"$RUN/app.log" 2>&1
```

Use a different fresh RUN directory and filter value1 for the second scene. Prefix/library paths must resolve the candidate GTK; keep retained compositor-only LD_LIBRARY_PATH additions out of the app. No GSK_RENDERER, device/ICD selection, GDK feature or sandbox override is used. Do not retry a failed/inconclusive scene automatically. Preserve failures and close only this owned app/private session through the existing reviewed lifecycle.

## Required evidence before granting the narrow result

Both runs need valid scene receipts (`completed-private-frames`, at least3 draws/complete GDK frames), the expected actual candidate GTK path/hash, verified private peer PID/UID, complete trace parsing, exports_resolved=true, no fixture_error/real-query error/truncation and intercepted array queries. A missing or different dispatch path is inconclusive. Inspect real arrays and returned_count/capacity; no new/changed non-pass pairs are allowed.

- **Observe:** default GSK is Vulkan; a real array advertises the trace's PASS_THROUGH enum; successful swapchain creation occurs, and every attempted swapchain declares that colour space. No filtering was applied.
- **Remove-PASS:** real arrays originally contain PASS_THROUGH plus valid alternatives; applied=true removes at least one entry, and after is exactly before with only that colour space removed. Default GSK is a non-Vulkan fallback, the ordinary scene completes, and **zero swapchain_attempt events** occur. This proves the exercised attach path rejected before attempting a swapchain; it is not a claim about every Vulkan implementation.
- **Both:** correlate the receipt's main wl_surface ID with WAYLAND_DEBUG. Count exactly one `wp_color_manager_v1.get_surface` owner for that native surface; exclude registry/global spam, representation surfaces and preferred feedback. Require its actual set_image_description followed by wl_surface.commit, and retain buffer/frame callbacks. Preferred information alone is insufficient. Check that the filtered run never adds a WSI colour owner. Frame metadata is private-compositor evidence, not optics.

If default selection never attempts Vulkan, if the real WSI lacks PASS_THROUGH or has no honest non-pass alternative, if it bypasses the intercepted dispatch, or if presentation metadata never completes, record the specific missing coverage. Do not force a renderer or manufacture capabilities to turn that into a pass. No-CM legacy and native lease unit cases remain separate; this counterfactual test does not certify all hardware. Root's independent image/near-black/extended-F16 acceptance is also separate.

Primary contracts: [Vulkan procedure-address semantics](https://docs.vulkan.org/refpages/latest/refpages/source/vkGetInstanceProcAddr.html) and [surface-format count/VK_INCOMPLETE semantics](https://docs.vulkan.org/refpages/latest/refpages/source/vkGetPhysicalDeviceSurfaceFormatsKHR.html). The authenticated candidate source and direct-call coverage bound why this small Linux interposer is appropriate here.
