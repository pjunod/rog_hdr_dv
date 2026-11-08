# Preferred display targets for GTK playback

## Requesting high-precision presentation

A client that already knows its source needs HDR can request a Wayland HDR rendering lease on its own surface. Its state reports the current target generation, transfer, primaries and actual framebuffer precision after presentation. Moving the window, replacing the draw context or releasing the last request invalidates the previous witness. The app can use the same preferred-target snapshot to regrade the source for a new monitor.

In the native EGL fixture, an SDR window first used eight bits, then acquired a ten-bit PQ framebuffer. Four framebuffer samples covered 203 and 101.5 cd/m² SDR UI, a 400 cd/m² PQ video patch and their 301.5 cd/m² linear-light mix. The quantized samples matched those four PQ values. Replacing the renderer with Cairo restored eight-bit sRGB, and destroying the surface cleared the request. The fixture used a private compositor. Default backend and normal player evidence have a separate scope.

**State, November 7, 2026:** proposed source prerequisite for native GTK/GStreamer
playback. Ubuntu GTK `4.24.1+ds-1` and the candidate GDK libraries compile on
amd64. A clean patch replay reproduces the complete pinned candidate tree.
Independent source review and ordinary native target/destruction checks pass.
The Ubuntu-default package build and offline forward/rollback simulation passed. Physical output hotplug remains open. Nothing is installed on
the user's desktop, and no playback or optical acceptance follows from this work.

## Why an accessor is needed

GTK already owns the Wayland color-management surface and its preferred-target
feedback. Its private `gdk_surface_get_color_state()` reports pixel encoding,
not the physical target. The public `GdkColorState` API exposes CICP encoding
information; it does not expose the display's black, peak, reference white and
chromaticities. In `gdkwaylandcolor.c`, `ImageDescription` receives those values
but `image_desc_info_done()` reduces them to a color state and discards them.
The encoding cache can also skip the information query entirely.

The [GTK series](../patches/ubuntu-gtk4-display-target/series) keeps
that existing ownership. It publishes a copied target from the existing
preferred parametric description. It creates no second color-management
surface object and makes no monitor guesses. It also corrects the existing
handler assignments that write green, blue and white Y coordinates into red Y.

## Ordinary discovery and rendering policy

The first reviewed runtime found a stock GTK restriction: without
`GDK_DEBUG=color-mgmt`, GTK never binds the advertised color manager. Even with
that diagnostic opt-in, GTK destroys the manager on this Weston 16 compositor
because it lacks GTK rendering's required named sRGB transfer capability.
Both initial runs correctly reported unavailable generation zero. The current
[runtime receipt](../evidence/gdk-display-target-runtime-20261107.json) retains
those failed prerequisites separately from the corrected native passes.

The current candidate separates input feedback from rendering. It binds one
shared manager under default settings, still honoring an explicit existing
`GDK_WAYLAND_DISABLE` request. A surface with a callback receives one preferred
parametric feedback object only when the compositor advertises parametric
support. Default discovery creates no content color-management surface and
keeps GTK's existing sRGB surface encoding. The existing experimental rendering
opt-in and its perceptual/sRGB capability checks continue to govern content
color descriptions. Their failure leaves target feedback available.

Manager binding schedules its own startup roundtrip. The initial registry
roundtrip, or another global's roundtrip, may already be queued before the
manager bind; neither proves its initial capabilities have arrived. The
manager-specific synchronization completes before preparation or surface
construction can classify feedback as available.

This avoids enabling a broad GTK pixel-encoding path merely to read target
metadata. It changes no advertised capability and supplies no fallback target.
Its native compilation, complete replay and independent review pass. Under
ordinary settings, the native observer now reports the exact declared target,
and both pending/ready reentrant-destruction negatives pass.

## Consumer contract

Include `<gdk/wayland/gdkwayland.h>` from the candidate GTK headers and obtain
the real surface through `gtk_native_get_surface()`. On the GTK main context,
connect `color-target-changed`, then call:

```c
GdkWaylandColorTarget target;
gboolean ready = gdk_wayland_surface_get_color_target (surface, &target);
```

| Snapshot member | Meaning |
|---|---|
| `generation` | Surface-local generation; increments when feedback becomes stale or the native surface is destroyed |
| `identity` | Wayland v1 image-description identity, local to the display connection |
| `primaries[8]` | Actual target-volume CIE 1931 xy, ordered red, green, blue, white |
| `min_luminance` | Target black, in cd/m², including the protocol's ambient flare term |
| `max_luminance` | Target peak in cd/m² |
| `reference_luminance` | Primary encoding's reference white in cd/m² |

The snapshot belongs to the caller. GTK/Wayland objects stay on the GTK main
context; a consumer may copy the values into its own synchronized rendering
state. Reference white remains separate from black and peak: the accessor
performs no `203 / reference white` normalization.

`FALSE` means pending, incomplete, unsupported or destroyed. Only the
`generation` member is meaningful then; the other members are cleared. There
are no hard-coded display values or SDR defaults. An encoding fallback to sRGB
inside GTK does not become a physical display target.

After construction, the signal fires immediately when `preferred_changed`
begins a new query, before that query completes. The initial query starts
during construction without a signal; consumers connect and query after
obtaining the fully installed surface. It fires again on completion or failure. Pending
and completion share one generation: consumers must process availability on
every signal, even when the generation is unchanged. Frames mapped to an old
generation require remapping or rejection after invalidation.

The compositor chooses the preferred target for a surface spanning outputs.
Output moves and compositor policy changes are followed through its feedback;
the accessor does not pick the last-entered monitor. Replaced queries are
cancelled using GTK's existing description lifetime. Native surface teardown
clears the target and increments the generation. Its notification runs from a
private core `after_destroy` boundary after `destroyed=TRUE`, with the core's
strong reference held across remaining cleanup. Signal emission also holds a
strong reference. It never calls application code midway through backend
teardown. Query state is retired before completion notification. A handler may
destroy the native surface and release its own reference; repeated calls to
`gdk_surface_destroy()` must each supply an owned reference, because that API
always consumes one.

GTK's private `GdkWaylandSubsurface` offload path owns a different Wayland
surface and currently creates its color owner with no target callback.
That private subsurface is not a `GdkSurface`; this API reports the actual
`GtkNative` surface used for ordinary composition. A video consumer using
subsurface offload must establish the target of that owning surface separately,
or use GTK's normal mapped composition path for those frames. The accessor
neither disables offload globally nor claims a parent target is always valid
for a child surface spanning a different set of outputs.

## Native build and observation

The [source registry](../sources.json) pins the Ubuntu source archive hashes,
imported base and candidate Git trees. The
[compile and replay receipt](../evidence/gdk-display-target-build-20261107.json)
records exact commands, source hashes and the scope of completed checks.
Source import includes all extracted files after Ubuntu's distribution patches,
except quilt's `.pc` bookkeeping. The fixed import timestamps and neutral Git
identity are recorded in the registry.

In an isolated builder, extract the authenticated Ubuntu source, apply the
series, then build without installation:

```sh
meson setup build gtk4-4.24.1+ds \
  -Dbuild-demos=false -Dbuild-testsuite=false -Dbuild-examples=false \
  -Dbuild-tests=false -Ddocumentation=false -Dintrospection=disabled
ninja -C build -j4 gdk/wayland/libgdk-wayland.a gdk/libgdk.a
ninja -C build -j4 gtk/libgtk-4.so.1.2400.1
export PKG_CONFIG_PATH="$PWD/build/meson-uninstalled"
cc -std=c11 -Wall -Wextra -Werror \
  packaging/system-dv/gdk-display-target-probe.c \
  -o gdk-display-target-probe $(pkg-config --cflags --libs gtk4-wayland) \
  -Wl,-rpath,"$PWD/build/gtk"
```

The [native observer](../packaging/system-dv/gdk-display-target-probe.c) prints
JSON for the real GTK window's target and invalidation events. It creates no
Wayland color objects and changes no display profile. It is compiled, linked and passed ordinary startup target observation on the
reviewed source. Its GUI would be a plain window; diagnostics go to stdout.

The [native lifecycle negative](../packaging/system-dv/gdk-display-target-reentrancy.c)
is compiled, linked and passed in both modes on the reviewed source. Its `pending` mode destroys a real
`GdkSurface` before the initial parametric query completes; `ready` destroys it
from the asynchronous ready notification. In both modes a destruction handler
calls `gdk_surface_destroy()` again with its own reference. It checks that the
public destroyed flag and native teardown precede notification, exactly one
teardown signal occurs, construction emits nothing, and the object finalizes.
It then dispatches cancelled-query replies to check for late delivery. Both
modes require real parametric feedback and fail qualification if that path is
unavailable; they do not replace it with fabricated metadata.

The [late-manager relay](../packaging/system-dv/late-color-manager.py) is a
native startup regression that passed against the reviewed source. It forwards a real isolated
compositor's protocol and descriptors, advertising its existing color-manager
global after the other initial globals. It delays the first actual capability
burst by 50 ms while preserving subsequent protocol order. A successful run
requires a post-manager-bind sync before surface construction and a passing
native lifecycle negative; it fabricates no capability or target values. Both
corrected modes passed. The pre-synchronization candidate failed both modes
with unavailable generation zero and no post-bind sync, distinguishing the fix
from an accidental later roundtrip.

After independent review, runtime qualification must cover initial pending to
ready, a move between outputs, a spanning surface, a compositor target update,
rapid replacement of an outstanding query, hide/show and destruction, and a
missing or failed parametric target. A renderer consumer must separately prove
that an old mapping cannot survive invalidation and that no worker accesses
GDK directly. The packaged GIR built; application-level introspection acceptance remains open. The observer
alone does not prove any GStreamer mapper or standard player integration.

The new per-surface request also passed through Python introspection with GTK's default Vulkan renderer. The submitted client image used a floating-point RGB framebuffer and BT.2020/PQ, with reference white at 203 cd/m². The reported physical display peak and reference white changed from 616/142 to 308/71 cd/m² in the fixture. In a separate EGL readback the largest absolute error across four uniform test patches was 0.59 of a 10-bit code value. Those samples exercised 203 cd/m² SDR white, half white, 400 cd/m² HDR and their 301.5 cd/m² linear-light mix. Both checks used a private compositor on the ROG.

## OpenGL ES video texture readback

On the ROG, a one-pixel opaque 400 cd/m² PQ source in a normalized 16-bit OpenGL ES texture reproduced the GNOME player’s black video with the default Vulkan renderer. The SDR UI stayed visible. The NVIDIA driver declined EGL image export, so GTK had to read the bound framebuffer. Its framebuffer-parameter query raised `GL_INVALID_ENUM` and its texture downloader returned transparent black. Querying the preferred read format and type with `glGetIntegerv` returned RGBA and unsigned short. A direct read recovered all four stored words (42767, 42767, 42767, 65535). The source correction is in GTK `+rogdv3`. A complete rendered-player check is pending. [OpenGL ES 3.1 framebuffer-dependent state](https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.pdf).

## Package staging and recovery

The host currently has GTK source version `4.24.1+ds-1`: amd64
`libgtk-4-1`, `libgtk-4-bin`, `libgtk-4-dev`, `gir1.2-gtk-4.0` and
`gtk-update-icon-cache`, plus `libgtk-4-common` for all architectures. No GTK4
i386 runtime is installed. The exact six stock packages are downloaded into
the private task slot; their architecture, version and hashes are in the
[staging receipt](../evidence/gdk-display-target-packages-20261107.json).

Version `4.24.1+ds-1+rogdv1` built using the ordinary Ubuntu packaging rules. Its additive symbol and version are pinned in the second patch. Offline APT simulation upgraded the six packages listed above and restored the corresponding stock six from a modeled candidate state, with no removals or host changes. The snapshot provides display information to consumers. The GStreamer rendering integration remains in development. [Candidate and rollback hashes](../evidence/gdk-display-target-packages-20261107.json).
