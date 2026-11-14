# GTK and WebKit image colour — preserve values and describe the surface

**Status:** Proposed; diagnosis reproduced, GTK compiler prerequisite passed; implementation in progress.
**Date:** November 13, 2026 Eastern / November 14 UTC.
**Deciders:** Project maintainer and coordinating agent. No upstream acceptance
or deployment is claimed.

Companion to [image colour](GNOME_IMAGE_COLOUR.md), [WebKit delivery](WEBKIT_NATIVE_HDR.md)
and [current status](STATUS.md). This topic owns a normal image/page pipeline
correction, separate from the completed Player session-control repair.

## Context: appearance agreement hid a measurable mismatch

A bounded owner-approved installed-desktop comparison used one ICC-tagged
Display P3 chart and its retained unclipped float reference. Image Viewer
presented both; GNOME Web presented the original. The reference is normal
CoreGraphics output retained privately, not inspection of a reference binary.
The source profile, reference files and desktop captures remain outside Git.

The chart has sixteen opaque patches in an eight-column, two-row layout.
Registration used grid geometry before paired errors were inspected. Every
patch contributed its central 32×32 physical pixels; no gain, white adjustment,
channel fitting or patch exclusion was applied. The diagnostic bound of two
PQ10 median codes was fixed before capture.

| Comparison | Maximum absolute patch-median channel difference | Mean absolute difference |
|---|---:|---:|
| Installed Image Viewer original versus float reference | 0.5 PQ10 code | 0.01042 |
| GNOME Web original versus float reference | 140 PQ10 codes | 13.1667 |

These are all 48 median channels, not every pixel or an optical measurement.
Neutral patches agree exactly; saturated colours differ. Both captures were
2560×1600 packed ten-bit RGB with BT.2020/PQ capture metadata. The output's
reference-white declaration was 203 cd/m² around each capture and returned to
142 after the test windows closed. Coding-volume extrema and physical target
extrema are separate fields; none measures emitted panel light.

The first Web capture was invalid because a default-browser prompt dimmed the
image. Only that scene was repeated, with the prompt disabled in an isolated
test configuration. Passing Image Viewer captures were retained. Exact temporary
Pictures copies, owned test windows and private browser profiles were removed;
monitor configuration and Night Light were unchanged. Confinement remained in
place. The earlier appearance-only check retains its limited scope.

## Source contracts explain the diagnostic

The installed WebKit source/build records select the libpng decoder with LCMS.
Its RGB-profile branch converts ICC input into 8-bit BGRA sRGB using relative
colorimetric intent. The common backing store holds uint32 pixels; its Skia
bridge uses N32/sRGB. The ordinary page framebuffer uses RGBA8, and its GTK
DMA-BUF import supplies no explicit colour state. Correcting only PNG decoding
would leave other precision/clipping boundaries in place.

Valid client traces show Image Viewer attaching ABGR16161616F buffers while
Web uses ARGB8888. They contain preferred-target feedback, but no explicit
surface image-description setter. Preferred PQ/BT.2020 information does not
establish the encoding of a submitted client buffer. Float storage alone does
not establish linear encoding or HDR.

Retained Mutter source gives untagged actors sRGB primaries with gamma 2.2.
Retained GDK source distinguishes that from its own piecewise-sRGB state and
separates target discovery from experimental managed rendering. Protocol v1's
named-sRGB mapping is also gamma 2.2 here; the v2 compound-power transfer or an
unambiguous supported linear representation is needed for the piecewise
contract. Simply flipping the rendering flag is insufficient.

An independent prediction used public P3/sRGB/BT.2020 matrices, the verified
source-profile sRGB transfer curve, sRGB clamp/quantize-to-eight-bit, the
source-audited gamma-2.2 fallback and the witnessed output white. It predicts
all 48 Web median channels exactly, without fitted parameters. Ignoring the
ICC profile instead misses by up to 39 codes. An earlier prediction assuming
a proper sRGB final EOTF failed near black and is retained privately as a
rejected model. This supports the clipping plus transfer-contract diagnosis
for this fixture; it does not qualify other formats or all rendering paths.

[Selected PNG implementation](https://github.com/WebKit/WebKit/blob/webkitgtk-2.52.6/Source/WebCore/platform/image-decoders/png/PNGImageDecoder.cpp#L347)
and [protocol definitions](https://github.com/wayland-mirror/wayland-protocols/blob/1.48/staging/color-management/color-management-v1.xml)
are explanatory public anchors. The private receipts bind retained package,
configuration and source identities. Exact source authentication has now reproduced GTK's pinned tree by replaying
all sixteen existing patches into a private index; relevant WebKit files match
its exact recorded Git object. The qualified Mesa manifest reconstructs the
pinned Merkle tree, and its canonical WSI file matches the qualified receipt;
the different stale working copy is not used. Original stores were unchanged.
These checks authenticate inputs. The four selected unchanged GTK translation
units subsequently compiled with GCC 15.3 and authenticated pinned source
dependencies. This is an object-level compiler prerequisite, not a full
link/package or runtime proof. The four selected unchanged WebKit objects also passed with Clang 22.1.8
and authenticated pinned dependencies. GTK source and regression preparation
is committed; WebKit implementation is active. Candidate compilation/linking,
package/runtime binding and actual Vulkan fallback remain open. Nothing
from this batch is installed.

The live compositor advertises colour-manager version 2 and transfer function
14 (`compound_power_2_4`). A version-2 output-only client receives that precise
capability, while the normal GTK applications bind version 1 and receive the
deprecated named-sRGB alias. No new display surface or setting was needed for
that capability query.

## Compiler prerequisite and implementation scope

Four unchanged GTK objects compiled with GCC 15.3, with pinned source
dependencies authenticated. The owned compiler container was stopped after
confirming it was idle, and its original resource limits were restored.
This establishes the selected object loop; it grants no link, package or
runtime colour claim. WebKit's separately admitted four-object baseline also passed with Clang
22.1.8; its container was stopped and original limits restored. No candidate
is installed.

Further source tracing found RGBA8 assumptions in coordinated tiles and
native-image uploads as well as the final page buffer. The selected design
uses one nonlinear-sRGB F16 working contract across supported accelerated
pages and tiles. This doubles pixel-buffer storage but avoids a new
content-promotion and first-draw repaint state machine. Actual allocation
and import support must be negotiated. Unsupported transports retain an
explicitly limited fallback. Colour metadata travels separately from pixel
format, preserving native Dolby/PQ buffers' distinct contract.

## Proposed decision

GTK should own the normal negotiated surface-description and render-state
contract. Vulkan transport must have one colour-description owner; an
advertised pass-through WSI path is a candidate, not permission to force an
unsupported colour space. Negotiate exact transfer/primaries/reference-white
semantics and retain an honest legacy path when the contract is unavailable.
Do not rely on an environment debug flag or change the global untagged fallback
to conceal a missing producer description.

WebKit must preserve source colour and precision through decoding, backing
store, Skia, page rendering, buffer transport and GTK import. Preserve original
samples/profile where supported, with a profile-aware float conversion path
where needed. Evaluate extended nonlinear sRGB in non-clamped half-float
storage to retain existing encoded-sRGB CSS composition semantics. A global
linear-BT.2020 page conversion is not accepted without proving that blending,
filters, alpha and canvas semantics remain correct. The exact implementation
choice is still proposed, not a qualified capability.

## Options and trade-offs

| Option | Assessment |
|---|---|
| Debug environment override | Does not repair the default contract, protocol-v1 ambiguity or WebKit's earlier clipping; rejected as a shipped solution. |
| Change Mutter's global untagged default | Changes unrelated legacy clients and leaves eight-bit clipping; rejected for this batch. |
| PNG-only float conversion | Leaves shared backing-store, page and import boundaries; insufficient. |
| Shared profile/precision transport plus negotiated GTK ownership | Addresses the demonstrated boundaries; requires broader source/build and semantic qualification. Proposed. |

Float buffers increase memory/bandwidth and affect shared decoder/compositor
code. Content precision and actual transport capabilities must be handled
truthfully. No new user feature gate, forced decoder/renderer rank or watchdog
belongs in the correction.

## Implementation and acceptance work

1. Authenticate exact source/package inputs and WSI ownership; confirm there is
   no overlapping implementation owner. Coordinate compiler resources with CI.
2. Establish unchanged native GTK and WebKit object compiler loops before any
   C/C++ or build-metadata edit; historical package passes are not those loops.
3. Resolve the working-space/blending contract, then implement related source
   changes as normal commits in one larger draft PR.
4. Retain correct SDR startup, profile fallback, alpha, animation and other
   decoder paths. Qualify normal negotiated and legacy behaviour without
   shipping debug overrides or suppressing unsupported-path evidence.
5. When merge-ready, obtain independent adversarial review, address findings,
   then run the required affected lane once. Retain passing receipts and rerun
   only failures or checks invalidated by later changes.
6. Prepare exact candidate/recovery packages before requesting a coordinated
   installed acceptance window. No live compositor/session/boot or package
   activation follows from this document. Optical and full cross-app/video
   qualification remain separate.

## Prepared default-renderer ownership fixture

The [controlled GTK/Vulkan fixture](GTK_COLOUR_OWNER_FIXTURE.md) prepares an
ordinary changing scene and target-bound interposer for the eventual native
check. It forwards actual advertisements, then removes only pass-through
for the negative case. It never adds formats or selects a renderer. Missing
interception, real alternatives or private-frame evidence is inconclusive.
Source is prepared only: no compilation or execution is claimed. Run it
only after final review and resource admission, outside the owner session.

## WebKit product and packaging integration

The prepared product series now retains decoded RGB samples and ICC meaning,
preserves meaningful PNG16 precision through interlace and animation, and
uses typed nonlinear-sRGB F16 working storage through supported accelerated
tiles, copies/effects, page transport and GTK import. Other codecs retain
their explicit inherited precision limits. One-pixel image optimization and
frame-cache accounting also follow the actual storage. No candidate build,
link, test or runtime pass is claimed yet.

Ordinary page colour metadata is separate from native-video PQ texture
metadata. The production frame helper couples allocation, incoming fence
and native serial/plane state; same-allocation updates retain ownership,
and a later different allocation releases it once. Focused regression
sources cover these transitions, but they have not run.

The original product patch remains unchanged. The appended mail patches
preserve their authors and the original Ubuntu Debian tree; the strict
[package recipe](../packaging/webkitgtk-native-hdr/README.md) authenticates
the ordered series before mutation, then applies a separate Debian overlay.
The proposed WebKit `+rogdv7` runtime requires GTK `+rogdv6`; its existing
GTK `+rogdv5` development-header minimum is retained because no new public
build ABI is introduced. This separates the runtime behaviour dependency
from the build-header requirement.

F16 payload is eight bytes per pixel before stride, depth/stencil and
driver overhead. Unsupported-ICC conversion can temporarily retain source
storage and two F32 images plus row scratch; eight bytes per pixel is not a
total-memory promise. Cache costs use actual raster row storage or a
checked nominal GPU estimate, not a measurement of driver residency.

## Focused tests without another producer build

The excluded `TestWebCoreImageColour` target reuses shipping WebCore OBJECT
files and the existing harness. `ENABLE_API_TESTS` stays off and unified
builds stay on; no product SDK exports or global float API are added. The
consumer adds five harness/regression translation units, two gtest units
and one substantial object-level executable link. Link resource fit remains
unmeasured. Neither normal package builds nor default CTest runs execute it.

After final review and qualified resource admission, build the target
explicitly and run the four prepared suites with GoogleTest XML output:

```sh
cmake --build "$webkit_build" --target TestWebCoreImageColour --parallel 1
"$webkit_build/bin/TestWebKitAPI/TestWebCoreImageColour" \
  --gtest_filter='SkiaDecodedImageColour.*:SkiaWorkingTextureTest.*:SkiaWorkingTile.*:RendererBufferFrame.*' \
  --gtest_output="xml:$webkit_receipts/image-colour-focused.xml"
```

Use an admitted existing candidate build and a fresh owned receipt directory.
The prepared inventory is14 cases: seven decoded-image, four working-texture,
two working-tile and one frame-owner case. Require zero failures, errors,
disabled cases and skips for the intended float route. The inherited console
printer can label skipped cases PASS; use XML rather than that label. A
zero-case filter or unavailable capability is not preservation qualification.
Record source/configuration, producer objects and linked/loaded libraries.
Actual shipping framebuffer, IPC, GDK import and native-lease checks remain
separate. No command above has run for this candidate.
