# Dolby Vision mapping core (`librog-dovi-map`)

The one owner of the project's per-picture Dolby Vision mapping rules, with a
plain C ABI and no GLib or GStreamer dependency
([design](../../docs/FIREFOX_DOLBY_VISION.md#4-the-shared-mapping-core-librog-dovi-map)).
The GTK element ([`gstreamer-gtk-dovi`](../gstreamer-gtk-dovi)) is an adapter
over it, and Firefox will call it from its decoder process.

The rules were moved, unchanged, from the GTK element's `mapper.c`,
`stream.h` and `render-preconditions.h` (`0.1.0+rogdv11`):

- Stream qualification: Profile 5 compatibility 0, Profile 8 compatibility 1
  (and Profile 7 compatibility 6 with a FEL decoder), version 1.0, RPU and base
  layer present, uncompressed metadata.
- Profile 5 has no base fallback: it maps or fails.
- The base-layer bit depth equals the decoded picture's, and the picture's
  geometry, enhancement state and record match its configuration.
- Target validation (finite, `min < max`, reference above 0, valid primaries,
  the 203/10000 PQ declaration); an invalid target declines Profile 8.
- The provider call order (`map_v2`, else `map`), the target-strategy witness
  and the physical transport gain, and the logical 100 cd/m² SDR destination.
- A picture without its own record is never mapped with another picture's RPU.
- One process-shared Vulkan device per render node, destroyed off the
  caller's thread.

## ABI

[`rog-dovi-map.h`](rog-dovi-map.h) documents every call. In short:
`rog_dovi_map_abi`, `rog_dovi_map_set_log`, `rog_dovi_mapper_new/free/reset`,
`rog_dovi_map_planes` (host pictures), `rog_dovi_map_dmabuf` (NV12/P010
DMABuf, imported as DRM-PRIME), `rog_dovi_map_last_decline/last_failure`,
`rog_dovi_map_decline_reason`, `rog_dovi_map_profiles`,
`rog_dovi_map_stream_profile`, `rog_dovi_map_profile5_has_no_base_fallback`,
`rog_dovi_map_profile5_destination_supported` and `rog_dovi_map_same_config`.
Both picture routes build an `AVFrame` and go through `pl_map_avframe_ex`.
Output is either the caller's host memory or a GBM DMABuf the core allocates
on the output render node from the caller's modifier list. Results are `1`
mapped, `0` declined, `-1` failed.

With no render node the core uses libplacebo's default Vulkan device, which is
what the GTK element does. Only callers that pass explicit nodes (Firefox)
select a device by node.

## Build and probes

```sh
meson setup build && ninja -C build
./build/rog-dovi-map-rules      # CPU-only rule checks, no GPU or media
```

`core-map-dump` decodes a picture with FFmpeg and maps it through either route;
`probes/compare-dumps.py` compares its output with the GTK element's
`probes/mapper-dump`. Both need the private provider, a GPU and a clear Dolby
fixture, none of which are in this repository. Results are in
[evidence/dovi-map-core-extraction-20261127.json](../../evidence/dovi-map-core-extraction-20261127.json).

Debian packages: `librog-dovi-map1` and `librog-dovi-map-dev`.
`libgstgtk-dovi-core0` depends on `librog-dovi-map1` with an exact version.
