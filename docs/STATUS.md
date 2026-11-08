# Status — what is working and what remains

**Updated November 8, 2026.** The ROG runs the seven-package playback update, nativehdr13 desktop and nativehdr3 kernel. Normal mpv opens MP4 and Matroska by default. The staged player graded the complete three-second 4K Profile 7 FEL clip at 24 fps with zero decoder or output drops on the default NVIDIA path in a private hardware-backed compositor. The corrected distribution driver advanced 2.25 seconds of media in 2.26 seconds on Intel. It reported 17 output drops over the clip while package builds were active. [Player release and recovery](SYSTEM_DOLBY_VISION.md) · [Desktop and kernel versions](SOFTWARE_DELIVERY.md).

| On the laptop today | Current development result |
|---|---|
| mpv 0.41, FFmpeg filter and the installed Vulkan update | Staged mpv 0.42 played the 4K FEL sample at 24 fps on NVIDIA. |
| GNOME uses Mutter nativehdr13 and the existing GTK runtime | The updated GTK runtime fixes black Showtime output. The staged player regraded the same paused Profile 5 picture when a virtual GNOME monitor changed from 616 to 308 cd/m². Returning to 616 restored the exact original screen pixels. [GNOME capture](../evidence/gnome-showtime-paused-retarget.json). |
| Firmware provides panel color and luminance data | The staged player scored mean ΔE ITP 0.651 and p95 1.274 on one chart at the panel target. The current mapper approximates the gamut as P3-D65. Optical calibration is pending. |

**GNOME screen capture.** Mutter wrote 8-bit pixels into shared-memory buffers advertised as 10-bit HDR. With the corrected writer, two 10-bit channel layouts reproduced identical colors across six patches. The half-float capture agreed to within 0.58 of a 10-bit code value. The same paused Dolby movie changed across 397,853 native 10-bit pixels when retargeted from 616 to 308 cd/m². Restoring 616 reproduced the original capture byte for byte. Both checks used a private GNOME monitor on the ROG GPU. [Format and pixel evidence](../evidence/mutter-shared-memory-color-formats.json).

**Photographs.** The staged GNOME Image Viewer preserves Adobe RGB color on the HDR desktop. Across six patches its output matched an independent BT.2020 reference within one 10-bit value per channel. The normal loader also retained the embedded color profile in small TIFFs. [Image viewer, package versions and qualification](GNOME_IMAGE_COLOUR.md).

**Movie-frame quality.** At 600 cd/m² the staged Intel filter measured mean ΔE ITP 2.61 and p95 7.20 on one 4K *Sol Levante* frame against Dolby’s render of the original master. The published 1080p Profile 5 release measured 9.21 and 26.31 against the downsampled reference. When the official processor received the same decoded base and a private XML copy carrying the three brightness values actually present in the stream, the Linux filter measured mean 0.65 and p95 1.60. [Source, individual controls and interpretation](../evidence/dolby-sol-levante-frame714.json).

**Browser coverage.** Stock Chrome and Firefox on the laptop played the AVC control and rejected the clear Dolby Vision chart. Firefox accepted ordinary HEVC capability queries. [Browser versions, codec queries and playback conditions](SYSTEM_DOLBY_VISION.md#browser-playback-on-the-rog).

**The normal player was compared with Dolby’s reference output.** On one 2560×1280 Profile 8.1 chart at a matched 1,000 cd/m² BT.2020 target, the staged NVIDIA mpv window had mean ΔE ITP 0.62 and p95 1.12 over all pixels. At a second 600 cd/m² target, the corresponding mean was 0.58 and p95 was 1.06. The maximum at 1,000 cd/m² was 56.49 at a color boundary. The 10-bit 4:2:0 transport control also showed much larger errors at boundaries than within patches. The 1,000 cd/m² target has neutral Level 8 trims. Further moving-content, isolated nonneutral-trim and optical comparisons remain open. [Methods, population and controls](../evidence/dolby-official-chart-consumer.json).

**The default NVIDIA path sustained 24 fps.** On a private hardware-backed Weston compositor, mpv chose the RTX 4080 and NVDEC automatically. It graded the entire 4K sample for 616 cd/m² with the enhancement layer composed. From media time 0.25 to 2.50 s, 2.255 s elapsed, with zero decoder drops, output drops or delayed frames. Before the Intel clock fix, explicitly selecting Intel on that compositor took 71.71 s and dropped 16 output frames. The 2.999-second, 24 fps Dolby Vision Profile 7 FEL clip reached EOF in the staged Intel run. On the earlier software-compositor run, its first and last sampled positions were 63.46 seconds apart, with 24 output drops and zero decoder drops. This test selected the Intel Vulkan ICD and used a software-rendered Weston compositor. Automatic selection chose NVIDIA in that fixture and swapchain creation failed. On the actual GNOME desktop an invisible probe successfully created both 10-bit PQ swapchain formats on each GPU. Physical desktop playback speed still needs measurement. [Continuous playback receipt](../evidence/profile7-continuous-playback.json).

The Intel pacing fault was traced to Mesa comparing two different clocks. On a 60 Hz compositor advertising `CLOCK_MONOTONIC_RAW`, the installed driver requested the next frame about 4,124 ms after presentation. The source fix keeps Wayland deadlines in the compositor clock and converts completion timestamps only when reporting them to Vulkan. The corrected private driver requested a median of 16.17 ms. The full three-second clip reached EOF at playback speed with eight output drops and zero decoder drops. A separate Vulkan client requested both absolute and unspecified presentation times. All 69 returned timestamps were within 12 ms of its monotonic clock while the two clocks differed by 4.12 s. Distribution package qualification is in progress. [Timing and wire evidence](../evidence/mesa-wsi-presentation-clock.json).

The mpv 0.42 `+rogdv4` package and updated decoder played the complete three-second genuine 4K Profile 7 FEL fixture and a nine-second native Profile 5 interval at 24 fps with zero decoder or output drops on the default NVIDIA GPU. Its ten-package upgrade and exact rollback passed offline simulation and were backed up privately. It also preserves the displayed grade in a tagged window screenshot. Its saved PNG carries BT.2020/PQ. A Level 8 trim edit changed the intended frame, and an untouched frame plus ordinary HDR10 controls matched exactly. [File-level evidence](../evidence/mpv-window-grade-capture.json).

### GNOME still-image colour in development

The ordinary Image Viewer candidate preserves ICC-tagged photographs as linear
BT.2020 floating-point textures. Native analytic controls retained 256 gray
levels and adjacent 16-bit midtones, and verified alpha and metadata precedence.
A separate sandboxed decoder correction preserves valid ICC metadata in small
TIFF files. The ordinary candidate and an independently encoded reference agreed
within one 10-bit PQ code on six synthetic patches in an isolated compositor;
stock materially clipped wide colour. Both normal Ubuntu packages built from
reconstructed DSC source; the exact two-package offline upgrade and rollback
passed with zero removals. Nothing is installed, and physical
panel accuracy remains unmeasured. [Source, digital controls and recovery](GNOME_IMAGE_COLOUR.md).

### GNOME playback in development

The GTK default Vulkan renderer presented an actual floating-point RGB surface using BT.2020/PQ in the isolated Wayland session. A separate EGL framebuffer readback placed SDR white, half white, a 400 cd/m² patch and a translucent SDR overlay over that patch within one 10-bit code value of their expected encodings. These are digital checks of GTK composition. The GStreamer software and Intel VA decoder paths preserved frame metadata across a seek. Playback of a complete movie through the GNOME player and installation on the running desktop remain open. [GTK presentation](GDK_DISPLAY_TARGET.md) · [GStreamer picture ownership](GSTREAMER_DOLBY_RECONSTRUCTION.md).

The NVIDIA HEVC decoder now preserves each decoded picture’s Dolby configuration, crop and metadata across seeking and changes of configuration. All 95 cropped pictures matched the software decoder. Ordinary Showtime automatically chose NVIDIA, ran the Profile 5 mapper and retained the same paused native picture when the target changed. The CPU-side handoff contained nonblack, opaque pixels. The private compositor still saw an all-black Showtime output on the same frame that rendered visibly in mpv. A standalone GTK OpenGL ES texture reproduced the black output. GTK queried the framebuffer read format and type with an unsupported OpenGL ES command. The supported query returned the expected 16-bit format, and direct readback recovered the exact pixel. The corrected GTK library recovered the exact 16-bit pixel and showed 44,730 distinct colors in the Showtime framebuffer on the original GL path. A paused target change still produced identical framebuffer bytes and remains under investigation. [NVIDIA producer qualification](../evidence/gstreamer-nvidia-picture-qualification.json).

## Shared Dolby Vision renderer — November 7

Normal Ubuntu mpv and FFmpeg’s libplacebo filter now have source integrations with a separately packaged display mapper. Each passes frame-owned Dolby metadata and a destination target. The packaged FFmpeg filter passed Profile 5 and synthetic Profile 8.1 checks, ordinary fallback controls and separate Level 2/Level 8 creative-trim comparisons. The ROG’s Intel GPU mapped Profile 5 to a 616 cd/m² P3 target offscreen. With the reviewed mpv and Mesa fixes the Vulkan surface was accepted and a real nonblack frame with an authored Level 2 trim rendered. A separately verified HEVC Main 10 HDR10 control matched stock mpv pixel for pixel. Automatic replay of the panel profile used mpv’s normalized 880.644-nit mapper target for the 616-nit physical peak at reference white 142. Both Vulkan driver architectures built. APT simulated the seven-package installation and its exact stock rollback offline. All seven packages are installed and dpkg-verified. The installed FFmpeg mapped genuine Profile 5 on Intel at 616 cd/m². Installed mpv mapped the same title on a private Wayland surface, where the 880.644-nit automatic trim-selection issue remains reproducible. The existing GNOME session stayed open. [Source, operating commands and recovery](SYSTEM_DOLBY_VISION.md).

### Panel target correction and Profile 7

The staged mpv `+rogdv4` selects creative trims using the panel declaration of 0.0004–616 cd/m² at reference white 142. A private compositor changed the target to 308 cd/m² and back. The player selected each new physical target even though normalized headroom stayed constant. Desktop and native screenshot paths used their respective encodings. The Ubuntu-default package built and both offline APT plans changed only mpv. [Qualification and package](../packaging/system-dv/physical-target-runtime-receipt.json).

A separate staged mpv 0.42 rendered a genuine 3840×2160 Profile 7 FEL picture on the laptop’s Intel GPU. The renderer combined the matched enhancement layer at native resolution before applying CM v4 trims for an explicit 616 cd/m² destination. Disabling the enhancement layer made the shared mapper decline the residual-dependent picture. A subsequent 0.42 build also selected the 616 and 308 cd/m² trims with the enhancement layer composed, retained PQ on a paused cached frame, and cleared its display state when an ordinary video replaced it. Distribution and comparison with an independent Dolby reference remain open. [Matched-frame digital receipt](../evidence/profile7-intel-dual-layer.json).

### Packaged Profile 7 and MP4 configuration

The normal mpv 0.42 Debian package rendered a 3840×2160 Profile 7 FEL frame on Intel. It reconstructed the full enhancement layer, selected the CM v4 trim for 0.0004–616 cd/m², and presented BT.2020/PQ through an isolated compositor configured with the panel declaration. The screenshot framebuffer retained PQ with file tagging disabled. The resulting PNG carried no transfer declaration. An HDR10 control produced the same decoded screenshot pixels as upstream mpv 0.42. Package installation and optical validation remain open. [Source and qualification](SYSTEM_DOLBY_VISION.md#physical-trim-selection-and-the-staged-dual-layer-player).

The 32-bit decoder retained all 544 stock decoders, 218 encoders and 67 hardware configurations. A native 32-bit client parsed a genuine Profile 7 RPU into an owned metadata snapshot. The combined ten-package upgrade and eight-package rollback plus removal of the two new runtimes passed offline APT simulation. The signed stock packages and private candidate are backed up. [Playback and package hashes](../evidence/profile7-ubuntu-packages.json).

Ubuntu's MP4 demuxer now carries the sample description's Dolby configuration through `h265parse`. Genuine Profile 5 and synthetic 8.1 preserved all 24 bytes. Plain HDR10, duplicate boxes and invalid fields carried no Dolby configuration. A four-byte legacy record retained its explicit unknown base compatibility. GTK player rendering remains a separate work item. [Demux and parser controls](../evidence/gstreamer-dovi-isobmff-controls.json).

The corrected packaged player also ran with the laptop’s existing mpv video options and the Intel Vulkan ICD selected by the test environment. Both HEVC layers selected NVDEC copy-back, the Intel GPU performed the grade, and the captured picture matched the explicit-renderer check. The compositor source now preserves the correct 616 cd/m² grade where integer Wayland peak rounding had triggered extra highlight mapping. The five normal Ubuntu compositor packages built, and their upgrade and exact five-package rollback passed offline simulation. The running compositor still uses its previous version. [Compositor decision and controls](MUTTER_TARGET_LUMINANCE.md#integer-client-peak-declarations).

## GStreamer RPU transport — native scope passed, November 7

Exact Ubuntu base `1.28.7-1` and bad `1.28.6-1ubuntu1` source series now carry
immutable original RPU bytes with each matched decoded codec frame. Native
software avdec and Intel VA each verified 30 pre-seek and 60 post-seek pictures,
including real coded-order reordering and 12 RPU gaps. A native same-format,
same-size VA 180-degree rotation removed the original metadata from all 90
transformed outputs. Independent correction review and exact signed-source
replay/compilation passed. No packages or applications were installed and no
defaults changed. This remains unshipped metadata transport: reconstruction,
FEL residuals, normal GTK player rendering, physical target signalling and
full-feature/multiarch packaging remain open. Five supplementary controls passed. These cover malformed duplicate/oversize units, NAL-aligned output, partial region copies and 26 matched resized VA pictures with format and colorimetry retained. [Contract and receipt](GSTREAMER_DOLBY_TRANSPORT.md).

## GNOME playback integration

Software HEVC and Intel VA now publish owned, frame-matched Dolby state across seeks, reordered pictures and conformance crops. Both decoded all 95 pictures when the container changed Dolby configuration without changing the video sequence. Earlier software decoding lost 32 pictures at that transition. The normal Ubuntu base runtime and SDK and the shared picture library built. The GTK player and real high-precision surface still require end-to-end qualification. [Controls and package contract](GSTREAMER_DOLBY_RECONSTRUCTION.md).

## GTK preferred display target — November 7

GTK now exposes the compositor's preferred output through a surface-owned snapshot. The ordinary Wayland path passed initial discovery, target changes, destruction and delayed color-manager startup in an isolated compositor. The six GTK packages already present on the ROG were rebuilt with the normal Ubuntu feature set. Offline APT simulation accepted all six candidate packages and the exact six-package stock rollback. The ROG still runs stock GTK. GStreamer playback needs a renderer that consumes the snapshot. [Native observer and package receipt](GDK_DISPLAY_TARGET.md).

## Kernel security rebase — 2026-10-29

The signed `7.3.0-nativehdr3` was installed and booted in the owner-authorized
window on October 29. Its running GNU build ID matches the image whose two
IPv4 teardown functions call `kvfree_call_rcu()`: CVE-2026-98432 is fixed in
the running kernel. The superseded `7.3.0-rc6-nativehdr2+` lacked both fixes.

All five deployed display patches now apply to Ubuntu `7.3.0-10.10`, whose
Makefile is released Linux 7.3. Both CVE corrections are already in that
base. It retains Ubuntu's perf level-4 enforcement, AppArmor restrictions
on unprivileged user namespaces, automatic Secure Boot lockdown and modular
Binder. The urgent target build retains Intel i915/xe and proprietary
NVIDIA, omitting unused AMD/Radeon/Nouveau stacks; the original full config
is preserved. Independent configuration review approved the derived changes.

Fresh export replay matches the complete pinned source tree, and independent
re-review approved the Ubuntu candidate. All five affected display objects
compiled with warnings enabled and zero warnings; all four focused parser
KUnit cases passed. The image/header packages built successfully; the actual
packaged image has both RCU corrections, and all five NVIDIA 615.71.09
modules compile/link against its delivered headers. The image and all 6,942
in-tree modules were signed with the existing enrolled image MOK; DKMS built
and signed all five NVIDIA modules with its existing enrolled module MOK.
No new MOK enrollment was needed. Secure Boot, integrity lockdown, perf level
4, the AppArmor user-namespace restriction, NVIDIA 615.71.09 and the display
manager passed postboot checks. The new kernel is the persistent boot default;
the old custom and stock kernels remain available for recovery. The
[kernel rebase ledger](KERNEL_REBASE.md) separates these checks from the bounded
November 2 fullscreen/VRR pass and still-pending broader physical/optical acceptance.

## Where it stands (2026-11-07)

| Area | State | Evidence |
|---|---|---|
| Desktop | APT Mutter `51.0-1ubuntu3+nativehdr13`, libdisplay-info `0.3.0-1+nativehdr13` installed (library amd64+i386) | Coordinator read-only inventory and package verification; current effective target about 0.0005–616 cd/m², firmware-declared; no override, Night Light off |
| Ubuntu packages | Current registry versions equal the installed candidates at priority 1001 | All 15 registry binaries size/hash-checked; changelogs name `479d61de3f78`, unchanged Ubuntu series on current main. [Receipt](../evidence/software-delivery-20261102.json); not a new build/test/transaction |
| Package output lifecycle | Retention repair implemented | Exclusive durable private run directories, no destructive reuse, verified output inventories; [retention and original-record recovery limits](UBUNTU_APT_REPOSITORY.md#private-source-and-recovery-output-retention). No package rebuild or original nativehdr13 recovery claimed |
| Dolby Vision display mapping | Closed form for CM v4.0 and CM v2.9, in plurx main | Mean ΔE_ITP 0.0036–0.0055 from Dolby's reference on four titles at 600 nits (plurx #1289) |
| Dolby Vision playback | External plurx Player 0.4.1 installed | Exact package version in [handoff](SOFTWARE_DELIVERY.md); October 27 P7 FEL observation is retained history, not a new player acceptance |
| Fullscreen/VRR | Bounded owner-attended pass on nativehdr3/nativehdr13 | November 2 silent HDR 24 fps stock-mpv fixture: active i915 CRTC VRR 0 → 1 → 0, zero page-flip errors, owner saw normal output; [scope and retained receipt](SOFTWARE_DELIVERY.md#acceptance-ledger-retained-observations-versus-new-requirements) |
| Tiling animation | Installed November 2; bounded visible pass | `51.26.10.6ubuntu+nativehdr2` installed and dpkg-verified November 2 after PR14 merged at `663a0a2`; package and kernel `7.3.0-nativehdr3` reconfirmed November 7. Normal logout/login, system extension ACTIVE, and owner-observed tile/restore/drag/maximize/rapid left-right passed; no animation errors in that interval. Stock rollback retained, not executed; November 7 visible stages passed with two centering JS TypeErrors; nativehdr3 correction built, not activated; fullscreen/cross-mode unverified; historical warning attribution remains open ([handoff](TILING_ANIMATION_OWNERSHIP.md)) |

November 7 [local-video Open With](LOCAL_VIDEO.md) acceptance passed: the corrected
entry is installed/visible/file-capable in GIO All Applications, all eight implicit
defaults remain `mpv.desktop`, and a spaced filename reached packaged mpv as one
operand. A three-second silent P5/RPU fixture reached EOF, exit 0; active GPU
CM v2.9/L2 mapping is scoped to frames reporting it, with initial resize/no-RPU
log states retained. Renderer-relative 880.6 nits at reference white 142 corresponds
to firmware-declared 616 via `616 × 203 / 142`; neither is optical measurement.
[Target receipt](../evidence/local-video-target-20261107.json). The separate
nativehdr3 animation correction is built with all 28 packaged JavaScript files
matching replay and the exact five-path stock payload delta. Version
`51.26.10.6ubuntu+nativehdr3` was installed and package-verified November 7.
The existing Shell session continued running. A normal new login is needed
to observe centering with the corrected code.
[Build receipt](../evidence/tiling-animation-nativehdr3-build-20261107.json).

**Remaining.**

- APT setup/qualification on the second test machine; ROG already has the builds.
- Broader post-APT/nativehdr3 HDR/SDR transitions, brightness/DPMS and
  suspend/resume acceptance, Night Light/override visual checks, and plurx Player
  product acceptance. Fullscreen VRR engagement and visible stability passed
  in the bounded November 2 attended fixture; no optical, long-duration cadence,
  other-GPU/mode or external-monitor acceptance is inferred.
  **Do not mark October 15 observations outstanding:** the owner accepted the
  warm roundtrip, decorations, SDR video and HDR10 stability; persistence passed
  across logout/login. These remain bounded prior-stack results, not new-stack passes.
- Animation continuation on November 7: center, reduced motion, extension
  INACTIVE → ACTIVE, restored enablement/settings and normal application close
  passed visibly. Two centering JS TypeErrors at `windowAnimation.js:185`
  (`actor.ease(...)` returned undefined before `.catch`) were fixed in the
  installed nativehdr3 package. Runtime confirmation awaits a new login.
  Fullscreen transitions and cross-mode SDR/HDR remain unverified; the harness
  saw no F11 callbacks and only current eDP color-mode 1 was observed mid-run.
  Retain the 35 inherited offline passes and twelve packaging guards separately.
- Recover original current APT source archives/build records from retained
  runner output or backups; bounded searches so far have not found them. New retention does not recover those originals; the binary-only
  registry and changelog binding do not supply them.
- Upstream submission of `patches/mutter` and `patches/libdisplay-info`
  (the owner's identity and decision).
- Panel measurement and calibration (needs a colourimeter); the Windows
  trace of the OEM pipeline (needs a Windows boot).

## Upstream preparation — 2026-10-28

The [submission ledger](UPSTREAM_SUBMISSIONS.md) accounts for all 85 handoff
entries and four mobile/converter observations omitted from that snapshot.
[Per-project commands](../upstream/README.md) and the
[catalog](../upstream/catalog.json) separate review-ready material, design
questions, missing evidence, superseded fixes and excluded local work.
These are preparation states; nothing has been submitted to a third-party
upstream.

Independent review corrected a protocol luminance overflow in the Mutter
kit and moved teardown cleanup into the first commit that needs it. The
[fresh receipt](../evidence/upstream-saved-review.json) records exact source
trees, builds, tests and inherited limits. Runner's saved rqbit kit also
received an atomic peer-cleanup race fix with a failing-before regression,
177 passing upstream tests, formatting and Clippy; its source stays in
[Runner PR #257](https://github.com/pjunod/runner/pull/257).

Other kits retain their exact upstream bases and scoped evidence. Existing
gemm proposals receive a validation reply rather than a duplicate patch;
the old FFmpeg RASL issue is already fixed upstream. The converter's
normalization observations match its documented default and existing
`--enable level-restore` option. Private display-management code, physical
captures and credentials remain outside the submission material.

The owner still reviews and edits descriptions, supplies project account
tokens and a kernel mail route, and resolves the explicitly held design or
physical-evidence items. Preparation does not change the installed display
stack or establish new hardware acceptance.

## Snapshot — 2026-10-18

**Updated:** 2026-10-18 (America/New_York) · **Current:** frozen ABI368 mapping
main-based integration independently reviewed and affected checks qualified; publication in progress.
Exact unchanged full-raster256/27 and714/27 development PASS and independent
1200/48 PASS retained (mean0.535635380895007/p951.1341677325267563,
8,847,360pixels,GPUinvalid0). No new observations or broader Dolby claim.

Done: scoped transplantation directly on public mainb13ceae3 without heldPR16
ancestry; original library patch replay to frozen treefb4c3879/all249 hashes;
unchanged historical compiler/accuracy receipts; separate package-relative
consumer compile with actual ELF RUNPATH inspection and additive genuine parser
fixture preparation. The owner selected scoped MIT licensing for original
utilities/docs; the full grant, package copyright and licence propagation are
integrated without changing numerical/native/upstream bytes. Fable's final
independent review APPROVES exact `a6b8dcc` / tree `60c573e4` after resolving F1:
shipped demos CC0-1.0 and valid fast_float DEP5 Apache-2.0 or MIT terms
(BSL not elected). The reviewed out-of-BT.2020 source-domain rejection limit is
documented, not changed. The approved once-only supported-baseline fixture is
prepared; missing historical log retention was repaired with exact-SHA copies,
not manifest edits or new vendor calls. The single affected batch returned
75/76 Python passes (zero skips), four effective native passes and repository
gate PASS (249 patches, six series and documentation links). Its fifth native
check exited zero but skipped the CPU and remains INVALID/UNCOUNTED. Fable's
narrow review APPROVES test-only `5d6d1e2` and the CPU-enabled Vulkan recipe.
Only the failed binary64-PQ black expectation and invalidated CPU Vulkan check
were retried: both PASS, with actual llvmpipe texture/render markers and no skip
or failed markers. All 76 Python and five native checks now have valid passing
receipts; no production/numerical changes or successful-suite repeats.
[Granular qualification evidence](../evidence/abi368-qualification.json).
Current: scoped PR/exact-head CI/merge `t_656472e9`; final documentation links
are checked separately without repeating units.
Remaining: broader 30-new-frame/target-pair validation `t_857c31e4` (pending,
not a general-accuracy pass), then actual source+binary packages and isolated
install/rollback `t_c97cbefb`. Existing upstream terms and LGPL source/relink
obligations remain. No package construction/transaction, repeated official
renders/metrics or device action in this qualification.
[Current delivery boundaries](MAPPING_ABI368_DELIVERY.md),
[equations/evidence/limits](SQRTSUM_PQ_Y_POST.md). PR16 remains held/unmerged.

**Previous source state:** main-targeting HDR
foundations/tooling/experimental-launcher source independently reviewed and qualified;
three support-helper defects corrected and re-reviewed, all 29 affected methods passed.
Previously qualified component source and exact historical receipts are selected
without importing held PR16/17 history. [PR20](https://github.com/pjunod/rog_hdr_dv/pull/20)
records final publication/merge disposition. Full Dolby Vision and measured image-quality
acceptance remain open; source qualification authorizes no deployment.

The [visual status page](STATUS.html) shows the workboard. [Provenance](PROVENANCE.md)
distinguishes inherited evidence from new work, [development](DEVELOPMENT.md)
defines validation, and [review](REVIEW.md) records findings and their resolution.
Source qualification is separate from package delivery and physical measurement.

## Measurement-driven development — adopted 2026-10-18

The open mapping is now developed by measuring the reference tools with
synthetic colour grids (see [the method](MEASUREMENT_DRIVEN_DEVELOPMENT.md)),
not by scoring whole frames for each idea. Reason: the broader random30 batch
of new frame/target pairs passed 13 of 30; 12 failed on accuracy and 5
produced invalid native output pixels. Whole-frame scores could not show
where the model diverges. The owner reviewed synthetic-input use against the
tools' licences on 2026-10-18. Binary inspection remains excluded, vendor
outputs stay private, and the held-out acceptance bar is unchanged. Current:
grid viability and diagnosis on four shots, then the random30 shots, which
thereby become development shots and are retired from acceptance; new
held-out frames will be reserved before the next freeze. The native
invalid-pixel defect is being root-caused separately.

Since the same date the primary remote is the owner's forge, which mirrors
public branches here ([remotes and branches](DEVELOPMENT.md#remotes-branches-and-the-public-mirror)).

## HDR foundations — main-targeting candidate

Merged-package lane `t_b2f97e54` now owns [normal Ubuntu source/binary packaging](MERGED_UBUNTU_PACKAGES.md)
in a new isolated clone from actual main2735b97f. Done: source/receipt inventory;
done: launcher experimental3 and coherent nine-package Mutter nativehdr10.1 normal
source/binary construction, including .dsc/archive/.changes/.buildinfo and matched
debug symbols, with nocheck/no repeated upstream units. Retained hdr9 source
applicability, private kit and isolated-install qualification are now complete
within the explicitly recorded architecture/baseline limits.
Done: independent review REVIEW316 (CHANGES NEEDED) and its four corrections:
typed source manifests bound to the final .dsc, real artifact closure/ABI/debug/
source inspections with two negative regressions, current launcher instructions
with `1.0~experimental4` reserved, and a hash-bound provenance/errata companion;
focused closure of those corrections (two blockers fixed at `249ccf7`). Done,
run 317 ([receipt](../evidence/merged-ubuntu-packages-run317.json)): launcher
`1.0~experimental4` constructed once, existing-source audits clean, provenance
companion written, the one affected batch passed 14/14, the actual isolated
forward/rollback transaction adjudicated PASS with one labelled limit
(baseline-owned trigger directories), host state invariant, and the canonical
kit retrieved and hash-verified (78 checksum-listed files, 54 source-manifest
entries). Remaining: final repository fast lane and [PR21](https://github.com/pjunod/rog_hdr_dv/pull/21) landing. The kit is constructed,
qualified and retrieved — NOT released and NOT physically installed; a ROG
installation stays owner / Linux-Media coordinated. Unqualified Dolby work is excluded.

Done: selected nativehdr10 upstream90/Ubuntu105 source, unchanged library pins,
the qualified public schema1/schema2 headless harness and experimental2 launcher.
Imported source/test bytes and retained evidence are compared against qualified
donors, not described as new executions. Component receipts retain their actual
heads/trees; no unit suite runs in this preparation phase.
See [scope/provenance/applicability](QUALIFIED_HDR_FOUNDATIONS.md).

Done: canonical library10/upstream90/Ubuntu105 replay and all selected native
compiler stages, including both full Mutter builds. The [compiler receipt](../evidence/qualified-main-compiler.json)
binds the original 302-file source transfer, zero unit execution and recovered
original Ubuntu success. Final static binding finds 299 identical transferred
files plus three corrected shell helpers not invoked by the direct replay/compiler
drivers; actual consumed compiler inputs remain unchanged. Whole-candidate review of [PR20](https://github.com/pjunod/rog_hdr_dv/pull/20)
completed with changes required: unsafe commit-build prerequisites/ownership,
fail-open publication scanning, and masked Wine initialization/test exits.
All three findings closed in independent focused re-review at `2bf1912`;
the one hermetic helper batch passed 29/29, with no failures/errors/skips.
The [qualification receipt](../evidence/qualified-main-final.json) binds the actual
review, source hashes, executed IDs and logs. Component suites were not repeated.
Inherited support-tool prerequisites are explicit new review scope, not
implicitly qualified by use on an older branch. Main's audio ownership and security policy are preserved.
PR16 remains closed/unmerged and held; PR17 is superseded source history, not the qualified delivery.

Qualification lane `t_f06aa8f3` retains final source-integrity/publication and
actual merge readbacks. Whole-candidate review `t_c00009d9` required changes;
focused re-review `t_d1b8661c` approved their correction. Evidence/status-only
closeout does not change executable/test/patch/dependency/build/scanner/CI inputs.
Do not repeat successful component units without actual invalidation. The broader programme
still owns KMS scanout/size-warning causes, transitions/resume, exact target
handoff/no-double-mapping, Dolby minimum/creative trims/reference agreement,
Windows comparison, optical measurement and upstream disposition. A bounded
historical laptop trial is not clean-log or full hardware acceptance.

Owner clarification: main-only builds/installs apply only to mobile builds
intended for installation on physical devices, and those installations.
Non-mobile HDR pre-merge compiler work follows the existing authorized workflow;
all device restrictions, independent-review gates and PR16 hold remain.

The installation sections below are dated historical evidence, not a fresh
inventory or permission to install their artifacts.

## Audio — moved to rog_audio on 2026-10-12

At the owner's request, all active speaker, latency and Atmos implementation
moved to [rog_audio](https://github.com/pjunod/rog_audio). Its
[status ledger](https://github.com/pjunod/rog_audio/blob/main/docs/STATUS.md)
tracks the GPT-6.1 Sol builds, review, validation and remaining measurements.
The read-only hardware inventory and detailed build contracts moved with it.
The original documentation review remains below in the review history.
No live audio settings changed during the repository split.

## Installation — hdr9 and nativehdr8 (2026-10-11)

In a coordinated window with the owner logged out, the six packages were
installed (6 upgraded, 0 added, 0 removed), held, and the display manager
restarted. The new login screen runs on the installed compositor with no
colour or EDID warnings; it is in SDR mode and publishes a coherent
description ([receipt](../evidence/install-2026-10-11.json)). The kernel,
boot selection, Secure Boot, profiles and display settings are unchanged.
The previous hdr6/nativehdr2 packages remain the hash-verified rollback.
The owner's HDR desktop session then started on the new compositor in
BT.2100 mode. It now reports the panel's firmware-declared target to clients
(primaries and 0.0004–616 cd/m², not a measurement) separately from the
BT.2020/PQ encoding, with no colour warnings in the session journal. The owner then
checked the picture and accepted it ("the picture looks awesome"); that is
a subjective check, not an optical measurement. At the owner's request, the old agent build
containers from earlier batches were removed.

## Tenth batch — general availability: targets and upstream port

Until now only an internal panel whose DisplayID declares native RGB
BT.2020 PQ (the ROG route) had a declared colour target; every other output
used the encoding fallback, so nothing was tone-mapped or gamut-compressed.
[Display target sources](DISPLAY_TARGET_SOURCES.md) widens target selection
in the colour device. In BT.2100, the peak and black come from DisplayID
physical luminance (10% window peak required), else from CTA-861 HDR static
metadata. A peak at or below the encoding's nominal reference white is not
a target. The BT.2100 gamut still comes only from DisplayID. In the native
SDR mode, the base EDID gamut (the encoding's own) is the target, so wider
content is compressed rather than clipped. Gamut containment is now judged
after adapting the target to D65, in the frame the pixels use. Otherwise a
native SDR output whose white is not D65 judged its own encoding out of
gamut.

The whole colour programme was also ported to upstream Mutter main
(`d82671c`) as the upstream-facing series (`patches/mutter/`, 49 patches):
43 ported commits, debian excluded, with messages in upstream form, plus
the six target commits. Every commit builds with warnings as errors against
the upstream-facing libdisplay-info series. That series needed no rebase:
upstream libdisplay-info is still at its base. Neither series has been
submitted upstream. The Ubuntu series gained the same six commits as
`nativehdr9` (Mutter patches 0053–0061).

An adversarial Fable review found the white-point containment defect (by
executing a probe), the low-peak risk and the base-EDID-gamut-in-HDR risk,
plus smaller items. All were fixed or decided, and a Fable re-review found
no remaining code defects ([findings](REVIEW.md#tenth-batch--general-targets-and-upstream-port)).
The colour test set (23 invocations including two new compositor cases) passed on
the upstream-facing head ([receipt](../evidence/general-targets-fast-lane.json)).

A second test machine, `lab6` (ThinkPad X1 Extreme, Intel UHD 630, an SDR
panel with base EDID only), was inspected read-only
([hardware](HARDWARE.md#second-test-machine-lab6)). It cannot use BT.2100 on
its built-in screen. It tests the native SDR target path on Intel graphics.

`nativehdr9` was installed on `lab6` in a coordinated window: 5 upgrades, 0
added, 0 removed, held, with a stock rollback set. The login screen and the
owner's session run on it with no colour messages. In the default mode, the
session publishes sRGB with the fallback target. In native SDR mode
(selected with `gdctl`), the encoding and target primaries are the panel's
base EDID gamut ([receipt](../evidence/install-lab6-2026-10-11.json)). The
owner's visual check is pending.

An independent Fable review of the whole plan followed (strategy, design,
upstreaming, measurement, process). Its recommendations and the decisions it
puts to the owner are in [review](REVIEW.md#independent-plan-review-2026-10-11).

## Ninth batch — independent review and fixes

At the owner's request, independent Fable 5.1 reviews covered the whole
compositor stack, the library, Wine and Dolby activation work, and the
evidence, packaging and install kit ([findings](REVIEW.md#ninth-batch--independent-review-and-fixes)).
The most important finding: plain PQ video without a declared peak was being
tone-mapped from the 10000 cd/m² encoding capacity, which would have dimmed
ordinary HDR. `nativehdr8` (Mutter patches 0044–0052) now leaves such content
unmapped, publishes descriptions on the renderer's exact identity, and
applies the other fixes. The Wine DisplayMonitor took three fixes (lock, EDID copy, output
technologies; patches 0010–0017). A Fable re-review found no blockers and
approved the fixes (recorded in [review](REVIEW.md#ninth-batch--independent-review-and-fixes)),
and the affected fast lanes passed (synthetic headless tests;
[receipt](../evidence/review-fixes-fast-lane.json)).

The delivery set was the hdr9 library (hdr8 code; it provides the native
HDR API as a virtual package the compositor depends on) with `nativehdr8`
([receipt](../evidence/hdr9-nativehdr8-packages.json)). The install kit holds
the six packages, checks the rollback packages first and snapshots the
package state. The `nativehdr6` comparison set was dropped: it lacks the
review fixes. The hdr9 + `nativehdr8` set was installed on 2026-10-11 (see
above).

## Eighth batch — gamut compression and delivery (merged, PR 8)

`nativehdr7` (Mutter patches 0039–0043) compresses colours outside the
panel's declared gamut into it, using the ACES reference gamut compression
with limits derived from the source and target gamuts
([contract](HDR_MAPPING.md#gamut-compression-nativehdr7)). It applies only
when the content can exceed the declared gamut, so sRGB content on a
panel whose declared gamut contains sRGB, and P3 masters on a P3 panel, are
untouched. It was reviewed adversarially and
passed its affected fast lane on the first run (synthetic headless tests,
software rendering; [receipt](../evidence/mutter-gamut-compression.json)).
Whether the panel itself clips out-of-gamut input, and so how much this
changes on screen, needs the installed system and an instrument.

## Seventh batch — HLG and tone mapping (merged, PR 7)

`nativehdr6` (Mutter patches 0028–0038) implements the
[HLG and tone-mapping contract](HDR_MAPPING.md): HLG decoding with its OOTF,
validated source mastering metadata, and BT.2390 highlight mapping to the
panel's declared target luminance. Mapping is applied once per surface and
only when content exceeds that target. It was reviewed adversarially and
passed its affected fast lane (synthetic headless tests, software rendering;
[receipt](../evidence/mutter-hdr-mapping.json)).

## Sixth batch — colour input and processor activation (merged, PR 6)

With DisplayMonitor merged, the recovered OEM processor now **activates**
under Wine in the isolated fixture. It returns an `IMFTransform` that reports
one input and one output stream. It offers P010/NV12 input and 10-bit RGB,
half-float or 8-bit RGB output.
[The activation section](DOLBY_ACTIVATION_PROBE.md#displaymonitor-follow-up--the-processor-activates)
records what that does and does not prove. No media type has been set and no
frame has been processed. The next stage negotiates the offered types and
traces the metadata the transform requests. It has not started and awaits the
owner's scope confirmation.

The compositor's colour-input defects from the
[audit](COLOUR_PIPELINE_AUDIT.md#implementation-status) are fixed in
`nativehdr5`, which was reviewed and passed its affected fast lane
([receipt](../evidence/mutter-colour-input.json)).

## Fifth batch — display contracts and delivery (merged, PR 5)

Before this batch, the qualified Wine candidate loaded the exact recovered
Dolby DLL but its factory request stopped at the missing Windows
`DisplayMonitor` runtime class
([evidence](DOLBY_ACTIVATION_PROBE.md#wine-11-follow-up--the-dll-loads-displaymonitor-activation-is-missing)).
The batch delivered a [generic monitor contract](WINE_DISPLAY_MONITOR.md)
backed by actual display data, and native
[physical-target gamut reporting](NATIVE_TARGET_GAMUT.md) in the library
(hdr8 and upstream series) and the compositor (`nativehdr4`). It also added
the bounded read-only Wayland colour inspector
([guide](DISPLAY_DIAGNOSTICS.md#inspect-the-compositors-actual-colour-descriptions)).
The [optical measurement procedure](PANEL_MEASUREMENT.md) defines conditions,
initial accuracy goals and held-out validation; this unit has not been
measured.

Baseline packaging preceded the batch. The exact qualified hdr7 library
source produced amd64 and i386 packages, and nativehdr3 compositor packaging
completed in the isolated native builder. The
[package receipt](../evidence/baseline-native-packages.json) records source
identities and the six runtime artifacts. Read-only APT simulations found a
coherent six-package upgrade and modeled six-package rollback, with no
additions or removals. Recovery artifacts are hashed and retained privately;
the live installation is unchanged. Delivery now targets the newer reviewed
candidates instead of installing this baseline.

The adversarial review found two blockers and a set of should-fix defects;
all are addressed ([review](REVIEW.md#fifth-batch--display-contracts-pr-5)).
The pre-merge fast lane then passed: library groups and legacy consumers,
Mutter `native-hdr` and all Wayland target-volume invocations, 23 probe
cases, and the Wine `displaymonitor` and `displayconfig` tests
([receipt](../evidence/batch5-fast-lane.json)). Nothing was installed at that point.

On 2026-10-10 the previous agents' macOS temporary clones were gone and two
local commits had never been pushed. Every unfinished change was recovered:
the probe test selectors are byte-identical to their recorded hash, the
library, nativehdr3 and Wine baselines reproduce their recorded trees, the
Mutter edit was replayed from the implementing agent's log, and the Wine
component was copied from the retained offline compiler container. Recovered
work keeps its original authorship; corrections are separate commits.

## Fourth batch — native target feedback and processor prerequisites

[PR 4](https://github.com/pjunod/rog_hdr_dv/pull/4) adds three components:

| Component | Qualified evidence | Remaining delivery or acceptance |
|---|---|---|
| [Mutter physical-target feedback](MUTTER_TARGET_LUMINANCE.md) | Compiled with warnings as errors; independent review corrections addressed; all eleven selected checks passed across initial runs and focused retries | Package and verify active physical output |
| [Wine file API](WINE_FILE_FROMAPP.md) | Reviewed, compiled; 123 focused assertions passed with no failures or skips; loaded module identity verified | Continue processor activation investigation |
| [Synthetic HDR corpus](HDR_REFERENCE_CORPUS.md) | Eleven new tests passed; private official-reference experiment completed | Creative-trim and consumer-profile comparisons |

Mutter now keeps firmware-declared physical target luminance separate from PQ
encoding and renderer state. Immutable Wayland descriptions preserve old
snapshots and notify clients of target changes. The first test pass exposed a
shutdown lifetime defect; explicit manager cleanup before output destruction
fixes its demonstrated cause. Synthetic forced-HDR tests preserve
their manually selected output mode while testing target policy. This fixed-route
fixture does not qualify real monitor reconfiguration.

Wine is used to investigate the Windows Dolby processor recovered from the
factory image. The missing file function now passes its desktop API contract.
DLL loading now passes; actual processor activation remains open; Wine is a candidate compatibility
route, not a confirmed requirement of the final Linux solution. The HDR and
colour-management changes are native Linux code.

The owner supplied and accepted official Dolby Professional Tools v5.6.4.
Private offline reference processing has completed. Proprietary tools,
documentation, generated metadata, rendered outputs and numerical comparisons
remain private. This establishes a reference workflow, not general playback,
creative-trim fidelity or calibrated panel accuracy. Its processing container
and owned runtime image were removed after retaining private evidence.

No host package, live display setting, boot selection or calibration changed
in this batch. Mutter remains ARM64 source qualification; delivery needs amd64
Mutter and matching amd64/i386 library packaging.

## Overall remaining work

| Area | State | Remaining work or acceptance |
|---|---|---|
| Native HDR detection | Implemented and installed | Wider hardware and upstream acceptance |
| Kernel and AUX brightness | Test kernel booted with Secure Boot | HDR/SDR transitions, DPMS, suspend/resume, brightness and display-mode coverage |
| Physical luminance library | hdr9 (hdr8 luminance and gamut API) installed for amd64 and i386 | Wider hardware and upstream acceptance |
| Compositor feedback | nativehdr8 (target luminance and gamut, colour input, HLG, highlight mapping, gamut compression, review fixes) installed; nativehdr9 (targets on CTA HDR outputs and native SDR panels) packaged | Install and check nativehdr9 on lab5 and lab6; optical verification needs an instrument |
| Upstream | Upstream-facing Mutter series (49) and libdisplay-info series (10) current on upstream main | Owner decides submission (merge requests under the owner's identity) |
| Full Dolby Vision | OEM processor activates and describes its transform under Wine (proven with Wine patches 0001–0009; the review-fix modules 0010–0017 passed the DisplayMonitor tests but have not been re-run against the processor); reference workflow available; the OEM plugin does not register Profile 7, so P7 FEL is outside this route | Negotiate types, establish the device and metadata contract, process frames, validate profiles and trims, integrate playback |
| General colour quality | Audit complete; input defects fixed (nativehdr5); HLG and BT.2390 highlight mapping (nativehdr6); gamut compression (nativehdr7); all reviewed with fast lanes passed | Output characterization (contract defined; needs a measurement, see [HDR mapping](HDR_MAPPING.md#output-characterization--defined-deferred-until-measured)), SDR/HDR consistency and cross-application checks; optical verification (the owner's visual check passed) |
| Exact-panel tuning | Four factory profiles inspected privately | Obtain measurement equipment and measure this unit, then implement the [output-characterization contract](HDR_MAPPING.md#output-characterization--defined-deferred-until-measured) |
| Applications | Shared platform path first | Qualify independent consumers; Plurx integration belongs in its separate repository |

The owner has no colourimeter or spectrophotometer yet and is open to obtaining
one. Software work continues independently. Define the measurement procedure
and OLED correction before choosing equipment. Firmware and factory-profile
values are not measurements of this particular unit.

## Completed source batches

1. **Repository, diagnostics and activation probe:** ordered patch provenance,
   public source reconstruction inputs, read-only diagnostics and an isolated
   activation probe. Review findings resolved; 45 Python tests and repository
   integrity passed. Live capture reported BT.2100 at 2560×1600/240 Hz, but the
   display was powered off, so active scanout remains unqualified. The original
   Wine 9 probe initialized COM/WinRT/Media Foundation and stopped at DLL loading.
2. **Profile interpretation and colour audit:** four factory ICC variants were
   parsed privately. MHC2 transforms are identity; standard characterisation
   differs by GPU route. All 16 new ICC tests passed across the initial run and
   one corrected-fixture retry. Stock Wine 11 isolated the missing file export.
3. **[Native physical-luminance API](NATIVE_LUMINANCE_API.md):** merged in
   [PR 3](https://github.com/pjunod/rog_hdr_dv/pull/3). Additive API preserves
   fractional physical luminance and field presence separately from CTA metadata.
   ARM64 and emulated amd64 builds passed with warnings as errors; 12 selected
   checks passed with only the corrected synthetic fixture retried. Previous
   consumer binaries passed against the new libraries; both series reconstructed.

## Installed baseline and inherited evidence

- libdisplay-info `0.3.0-1ubuntu1~hdr9` (amd64, i386) and Mutter
  `51.0-1ubuntu3+nativehdr8`, installed and held on 2026-10-11.
- Kernel `7.3.0-rc5-nativehdr1`, from Ubuntu `7.3.0-8.8` plus four patches. The
  installed stock fallback kernel is now `7.3.0-9-generic` (the `7.3.0-8`
  image named in the older recovery notes has been removed).
- Replaced on 2026-10-11 and kept as the hash-verified rollback:
  libdisplay-info `0.3.0-1ubuntu1~hdr6` (amd64, i386) and Mutter
  `51.0-1ubuntu3+nativehdr2`.
- NVIDIA `615.71.09`; Secure Boot remains enabled.
- mpv `0.41.0`, libplacebo `7.360.1`, FFmpeg `8.1.2` at inspection.

Historical receipts record upstream library GCC/Clang suites at 75/75, Ubuntu
library suites at 40/40 per architecture, ABI/export checks and actual package
install/offline rollback. Mutter's six focused regressions passed; its ordinary
package batch had 190 passes and five expected failures. A marked-flaky batch
had one unresolved `map-after-headless` failure; isolated passes did not establish
that it was unrelated.

Kernel receipts record affected DRM/i915/xe compilation, sparse, four KUnit
groups, full package builds, signature checks and delivered-header NVIDIA
builds. Initial physical boot and working HDR10 were subsequently reported.
These are scoped historical results, not freshly repeated tests.

## Next work

`nativehdr9` is ready to install, in a coordinated window, on `lab6` (stock
26.10, native SDR path) and then `lab5`. An external HDR monitor on `lab6`
would test the CTA path. Submitting the upstream-facing series is the
owner's decision. Two further steps wait on the owner, and one comparison
is optional. The KMS
metadata question can be settled by an on-screen comparison if the owner
wants it; the owner's subjective check of the current picture passed. The Dolby processor's next
stage waits for the owner's scope confirmation and, before it can say
anything about this panel, a monitor descriptor source in Wine
([prerequisites](DOLBY_ACTIVATION_PROBE.md#displaymonitor-follow-up--the-processor-activates)).
Output characterization waits for a measurement instrument (owner to
obtain).
The staged acceptance criteria remain in
[Dolby Vision and display quality](DOLBY_VISION_AND_QUALITY.md#5-work-in-stages-with-observable-acceptance).

## Decisions taken without the owner

Recorded for review; each can be revisited.

- Audio implementation moved to rog_audio on 2026-10-12 and uses GPT-6.1 Sol chats in
  isolated clones. The coordinator owns design, review and integration; this
  does not change the existing display team or its held work.
- Since the fifth batch, display agent commits use `Claude Agent <claude-agent@invalid>`
  with a co-author trailer, and implementation and review agents are Claude
  agents. Earlier agent commits used `Codex <codex@invalid>`; recovered work
  keeps its original authorship.
- Compositor and library builds, compositor tests, the Wine fast lane and the
  packages run in disposable agent containers off the laptop (native amd64;
  the i386 library is cross-built; Wine tests use WineHQ 11.0 with the
  candidate modules overlaid). The Wine compiler and the Dolby activation
  probe run in agent-owned containers on the laptop (`lab5`) with no network,
  mounts or GPU. Package simulations and staging happened on the laptop
  before the coordinated installation of 2026-10-11; agent build containers
  from earlier batches were removed at the owner's request that day.
- The Wine DisplayMonitor uses base EDID 1.4 facts where DisplayID declares
  none.
- HLG is decoded for its declared nominal peak and then fitted by the common
  tone mapper, rather than rendered for the panel's peak.
- The BT.2390 tone mapper applies only when the content's effective peak
  exceeds the panel's declared peak. It never expands or raises black, and
  monitor screencasts are not mapped.
- `extended_target_volume` is advertised; declared mastering primaries set
  gamut-compression limits when compression applies.
- Gamut compression uses ACES reference gamut compression with limits derived
  from the source and target gamuts, tolerating the declaration's own
  quantization.
- Output characterization is not applied until a measurement exists.
- The delivery set is hdr9 with `nativehdr8`; the earlier `nativehdr6`
  comparison set was dropped because it lacks the review fixes.
- PQ content without a declared peak is not tone-mapped; its overshoot is
  left to the panel.
- KMS static metadata keeps zero ("unknown") luminance fields; whether to
  declare the target is decided by an on-screen comparison on the
  owner's HDR desktop session.
- Display targets use CTA-861 desired content luminance as the BT.2100 peak
  where DisplayID declares none. Its own provenance is `cta-declared`. It
  is a content preference, not a measurement, but most HDR displays declare
  no other peak.
- A target peak at or below the encoding's nominal reference white
  (203 cd/m² for PQ) is no target, so a bogus low peak cannot dim SDR. The
  rule uses the nominal value, not the brightness-scaled one, so a target
  does not appear and disappear with the brightness setting.
- Base EDID primaries are not a BT.2100 gamut target. Many HDR displays
  declare their SDR gamut there, so compressing toward it risks visible
  desaturation without a measurement. They are the native SDR target only.
- The upstream-facing Mutter series is a port of the reviewed Ubuntu series
  to upstream main, with commit messages rewritten to upstream rules
  (authorship, trailers and inherited validation claims preserved). A
  separate test machine, `lab6`, was added for general-availability
  checks; it stays a stock Ubuntu 26.10 baseline and is not used for builds.
