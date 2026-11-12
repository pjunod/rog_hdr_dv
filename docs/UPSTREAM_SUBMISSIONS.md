# Upstream submissions — material, evidence and remaining decisions

**Updated:** 2026-11-12 · **Scope:** 125 inventory entries: the original 85,
four mobile/converter observations, 35 additions from the November audit and
one November 12 addition (WK-2).
The original inventory covered 20 upstream projects; seven new destinations
bring that coverage to 27, plus local converter observations. No submission
is performed by this inventory refresh.

The [November review](../upstream/november-2026/README.md) audits public
source through `ac82059` and the recorded Runner and Plurx source heads. It
adds
18 held candidates, 15 discussion drafts and two upstream backport groups.
Those backports retain their original authors; they are not new submissions.
The 43 prepared patch units from October retain their exact historical
qualification. This pass does not rerun native suites or advance helper bases.

Start with the [submission commands](../upstream/README.md). Each linked kit
records its exact base, exported material, tests and limits. The
[machine-readable catalog](../upstream/catalog.json) is checked against every
row here by `scripts/check_upstream.py`. Update both in the same change.

**Ready for human review** means material is prepared for the contributor to
review and submit, with the recorded limits. It is not upstream acceptance,
human approval, physical qualification or a claim that every platform was
tested. Units marked draft stay drafts. **Discussion draft** supplies a design
question rather than promising a completed code port. **Held** identifies
missing evidence or a prerequisite that remains explicit in the kit.
Superseded and excluded entries are closed preparation dispositions.

The original October 27 tracker was a historical snapshot of
[the contribution inventory](https://github.com/pjunod/rog_hdr_dv/blob/7c413914fb4c7281bb24994cdbcbab09f8d1d8e2/docs/UPSTREAM_SUBMISSIONS.md).
It counted grouped changes, proposals and exclusions, not 85 ready patches.
Runner's kit remains in its own repository; the other preparation material
is consolidated here with its source repository and attribution retained.

## Mutter (GNOME)

Venue: gitlab.gnome.org/GNOME/mutter · MR. No written AI rule; GNOME-wide policy being debated — disclose; Issue/MR URL in every commit; GNOME GitLab account.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| MUT-M | frames: use gtk-interface-color-scheme | rog_hdr_dv | Ready for human review | [kit](../upstream/mutter/README.md) · Units 01; see current stack/design dependencies in the kit. |
| MUT-A | Colour-management protocol robustness: signed primaries, ICC ranges, creator errors | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 07; Check against open !4604 and !5313; see current stack/design dependencies in the kit. |
| MUT-B | Offer HDR on native DisplayID BT.2020 PQ eDP panels | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 05; Needs libdisplay-info LDI-2..4 released; fixes #4847 family; see current stack/design dependencies in the kit. |
| MUT-C | Publish native target luminance/primaries separately from encoding | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 06; Overlaps open !5068; see current stack/design dependencies in the kit. |
| MUT-D | HLG transfer function + BT.2100 system gamma | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 08; No competing upstream MR found; see current stack/design dependencies in the kit. |
| MUT-E | Target colour volume, mastering metadata, light levels | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 09; Overlaps !5068; folds the Ubuntu-only init fix; see current stack/design dependencies in the kit. |
| MUT-F | Highlight mapping toward a declared target | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 10; Depends on MUT-E; see current stack/design dependencies in the kit. |
| MUT-G | Gamut compression toward a declared display gamut | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 11; Depends on MUT-E; see current stack/design dependencies in the kit. |
| MUT-H | Target sources: CTA peak, base-EDID native SDR primaries | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 12; Depends on MUT-C, MUT-E; see current stack/design dependencies in the kit. |
| MUT-I | White adaptation + Night Light in linear light | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 13; Likely superseded by open !5177 (colour management rework); see current stack/design dependencies in the kit. |
| MUT-J | Per-monitor target overrides: config, D-Bus API, gdctl | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 04,14; New API; collides with !5177; see current stack/design dependencies in the kit. |
| MUT-K | Colour device / colord lifecycle robustness | rog_hdr_dv | Held | [kit](../upstream/mutter/README.md) · Units 03,15; Obsolete if !5177 lands; 84/85 (teardown) could go alone; see current stack/design dependencies in the kit. |
| MUT-L | Offscreen buffer reuse across colour-state changes | rog_hdr_dv | Ready for human review | [kit](../upstream/mutter/README.md) · Units 02; see current stack/design dependencies in the kit. |
| MUT-0 | Design-discussion issue for the whole series | rog_hdr_dv | Discussion draft | Prepared design issue; open before the stacked colour proposals. |
| MUT-N | Compare client mastering peaks at Wayland integer wire precision | rog_hdr_dv | Held | [November material](../upstream/november-2026/DISPLAY.md) · Avoid double mapping from rounded client declarations while preserving exact native declarations and mapping curve. Native /color-hdr/mapping/wire-peak control distinguishes 880/881/882; fixture display 616 at reference 142, client reference 203. Existing target-volume implementation is a prerequisite. Extract/rebase onto agreed current upstream design; no new standalone submission port is prepared. |
| MUT-O | Write shared-memory screen captures in the negotiated pixel format | rog_hdr_dv | Held | [November material](../upstream/november-2026/DISPLAY.md) · Monitor, area and virtual paths had hard-coded ARGB readback despite negotiated ten-bit/float layouts. Digital controls cover XR30/XB30/half-float/BGRx and same-stream format changes; XR30/XB30 agree exactly and half-float differs at most0.574 ten-bit code. MemFd evidence, not DMA-BUF or optical qualification. Upstream extraction/current base and focused native regression still required. |

## libdisplay-info

Venue: gitlab.freedesktop.org/emersion/libdisplay-info · MR. No written AI rule — disclose; Signed-off-by required; freedesktop account + user verification to fork.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| LDI-1 | displayid2: bound padding scans (ASan fix) + test | rog_hdr_dv | Ready for human review | [kit](../upstream/libdisplay-info/README.md) · Unit 01; Smallest first submission |
| LDI-2 | Parse DisplayID 2.0 Display Interface Features | rog_hdr_dv | Ready for human review | [kit](../upstream/libdisplay-info/README.md) · Draft proposal overlapping !210; coordinate before treating later units as accepted. |
| LDI-3 | Reject unsupported nested CTA headers in DisplayID | rog_hdr_dv | Ready for human review | [kit](../upstream/libdisplay-info/README.md) · Unit 03;  |
| LDI-4 | Structured extension-failure status API | rog_hdr_dv | Ready for human review | [kit](../upstream/libdisplay-info/README.md) · Unit 04; New public API — needs a design nod |
| LDI-5 | Native physical luminance from Display Parameters | rog_hdr_dv | Ready for human review | [kit](../upstream/libdisplay-info/README.md) · Unit 05;  |
| LDI-6 | Lossless native DisplayID2 chromaticity | rog_hdr_dv | Ready for human review | [kit](../upstream/libdisplay-info/README.md) · Unit 06;  |

## Linux kernel (DRM / i915)

Venue: dri-devel, intel-gfx · email (b4). Tool use must be disclosed; AI may not sign off; Signed-off-by required (yours); b4 web-submission or SMTP set up.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| LNX-1 | drm/edid: DisplayID 2.0 luminance range; i915 accepts any source | rog_hdr_dv | Third-party work | Retain Cristian authorship of firsttwo DisplayID prerequisites; newer Ubuntu build/install evidence never makes them our original work. [November review](../upstream/november-2026/README.md). |
| LNX-2 | Bounded physical-range validation + KUnit coverage | rog_hdr_dv | Ready for human review | Retain the October28 upstream outgoing two-patch source qualification at its exactbase65ba8f34 separately from later Ubuntu release replay. Firstfour Ubuntu patches have unchanged stable patch IDs. Do not silently advance upstream helper base from the downstream deployment evidence; do not count CVE security backport as our new contribution. [November review](../upstream/november-2026/README.md). |
| LNX-3 | i915: SCL lost when VRR toggles with PSR (Wa_14015401596) | rog_hdr_dv | Held | A real Ubuntu 7.3 i915 patch and bounded November 2 owner-attended VRR 0→1→0 pass now exist. Hold for a current-upstream port, focused qualification and owner DCO/mail route; broader mode/optical acceptance remains separate. [November review](../upstream/november-2026/README.md). |

## Proton (ValveSoftware/wine)

Venue: github.com/ValveSoftware/wine · PR to proton_11.0. No written AI rule — disclose (WineHQ bans LLM code); GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| PR-1 | kernelbase: CreateFileFromAppW | rog_hdr_dv | Ready for human review | [kit](../upstream/proton/README.md) · unit 01: ready-for-human-review |
| PR-2 | win32u: monitor provenance and connector technology | rog_hdr_dv | Ready for human review | [kit](../upstream/proton/README.md) · unit 02: ready-for-human-review |
| PR-3 | windows.devices.display: DisplayMonitor statics | rog_hdr_dv | Ready for human review | [kit](../upstream/proton/README.md) · unit 03: ready-for-human-review |

## rqbit

Venue: github.com/ikatson/rqbit · PR. AI_POLICY: disclose; human must explain every line; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| R8 | Configurable max metadata size (BEP 9) | Runner | Ready for human review | PR 01 · full cargo test 169/0 · send first; original native suites are inherited, with log hashes inspected; helper previews are new. |
| R9 | Stop initialization on file-sizing errors (ENOSPC) | Runner | Ready for human review | PR 02 · 170/0 · send first; original native suites are inherited, with log hashes inspected; helper previews are new. |
| R2 | Bound HTTP tracker responses and request time | Runner | Ready for human review | PR 03 · 170/0 · behaviour change, ask maintainer; original native suites are inherited, with log hashes inspected; helper previews are new. |
| R1 | SessionOptions::disable_auto_restore | Runner | Ready for human review | PR 04 · 169/0; original native suites are inherited, with log hashes inspected; helper previews are new. |
| R3 | Optional session-wide peer limit | Runner | Ready for human review | PR 05 · 171/0; original native suites are inherited, with log hashes inspected; helper previews are new. |
| R6 | Per-peer response budget | Runner | Ready for human review | PR 06 · 170/0 · budget now follows max_request_window; original native suites are inherited, with log hashes inspected; helper previews are new. |
| R5 | Bound retained known peers | Runner | Ready for human review | New atomic cleanup race regression; 177/0, fmt and Clippy on the corrected candidate. Depends on R3; overlaps #667. |
| R7 | Bound DHT queues (PR 08) and metadata-resolver work (PR 09) | Runner | Ready for human review | 169/0 and 170/0 · overlaps open #706 / #708; read PR 08 hardest; original native suites are inherited, with log hashes inspected; helper previews are new. |
| R10 | Per-torrent discovery health (design issue first) | Runner | Discussion draft | Prepared issue draft and one-command issue helper; no code PR until the design is agreed. Large API; post an issue before any PR |
| R13 | Tracker announce lifecycle: completed/stopped, trackerid | Runner | Discussion draft | Prepared issue draft and one-command issue helper; no code PR until the design is agreed. 2,053-line patch; split into an issue + small PRs later |
| R11 | SessionOptions::disable_pex | Runner | Discussion draft | Prepared issue draft and one-command issue helper; no code PR until the design is agreed. Needs a port to main; later |
| R4 | Pending-handshake cap | Runner | Superseded upstream | Upstream main has max_pending_incoming_handshake_checks |
| R12 | Test-only DHT bootstrap feature | Runner | Not for upstream | Runner-specific test hook |
| R14 | Read-only selected-piece verification over caller-owned storage | Runner | Discussion draft | [November material](../upstream/november-2026/OTHER_PROJECTS.md) · New public verify_selected_piece_ranges API reuses rqbit piece verification against callback-backed read-only storage, merges selected piece ranges, verifies neighboring boundary bytes and supports cancellation checkpoints. Existing source regression covers neighboring-file boundary bytes, corrupt payload and Interrupted callback. Discuss API shape first; export standalone current-upstream port and move tests into upstream before preparing a PR. Downstream stable delta alone is not an upstream kit. |
| R15 | Locate the first intersecting file before verifying a piece | Runner | Held | [November material](../upstream/november-2026/OTHER_PROJECTS.md) · The same maintained patch replaces a scan over every preceding torrent file with partition_point and skips directly to the first intersecting file. This generic FileOps optimization can be split from the new API. Needs current-upstream check, isolated export and dedicated boundary/zero-length-file/performance regression; inspected source test is not sufficient proof of lookup behavior or speed. |

## hiqlite

Venue: github.com/sebadob/hiqlite · PR. Has an AI-contribution policy — disclose; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| HQ-1 | Reject duplicate node ids in NodeConfig | cinema | Ready for human review | [kit](../upstream/hiqlite/README.md) · unit 01: draft PR; ready-for-human-review; Explicit local human approval; open Draft and leave Ready for Review to a human; Complete just verify or document its unrun S3/MSRV/example checks |
| HQ-RP | Don't follow redirects with X-API-SECRET (redirect Policy::none) | cinema | Held | [kit](../upstream/hiqlite/README.md) · unit 02: draft PR; security-hold; Paul must decide the private reporting route before any public patch or reproduction |
| WAL-1 | Restore last_purged_log_id when the only WAL file is 1 | cinema | Ready for human review | [kit](../upstream/hiqlite-wal/README.md) · unit 01: draft PR; ready-for-human-review; Explicit local human approval before Draft PR |
| HQ-8 | Keep snapshot RPC peer errors as RemoteError | cinema | Ready for human review | [kit](../upstream/hiqlite/README.md) · unit 03: draft PR; ready-for-human-review; Explicit local human approval before Draft PR |
| HQ-9 | Write-and-flush budget for WebSocket frames | cinema | Discussion draft | [kit](../upstream/hiqlite/README.md) · unit 05: draft PR; design-hold; Upstream-only reproduction and focused port; discuss the proposed contract first; Explicit local human approval |
| HQ-10 | Supervisors own and join split socket tasks | cinema | Discussion draft | [kit](../upstream/hiqlite/README.md) · unit 06: draft PR; design-hold; Upstream-only reproduction and focused port; discuss the proposed contract first; Explicit local human approval |
| HQ-11 | Dropped RPC notifies its WS manager reliably | cinema | Discussion draft | [kit](../upstream/hiqlite/README.md) · unit 07: draft PR; design-hold; Upstream-only reproduction and focused port; discuss the proposed contract first; Explicit local human approval |
| HQ-19 | Install rustls crypto provider before building clients | cinema | Held | [kit](../upstream/hiqlite/README.md) · unit 04: draft PR; design-hold; Maintainer agreement on the feature topology; Explicit local human approval before Draft PR |
| WAL-3 | WAL incarnation identity + layout guard | cinema | Discussion draft | [kit](../upstream/hiqlite-wal/README.md) · unit 02: draft PR; design-hold; Reproduce stale same-path mmap or suffix identity reuse on unmodified upstream; Split the remaining fix from upstream PR #367 |
| HQ-17 | Gate cryptr's S3 feature behind hiqlite's s3 feature | Runner | Held | [kit](../upstream/hiqlite/README.md) · unit 04: draft PR; design-hold; Maintainer agreement on the feature topology; Explicit local human approval before Draft PR |
| HQ-26 | TCP_NODELAY on accepted streams | cinema | Superseded upstream | Upstream #374 |
| WAL-2 | Atomic meta.hql replacement | cinema | Superseded upstream | Upstream #357 |
| HQ-2 | Split-brain probe TLS policy | cinema | Superseded upstream | Upstream removed the check (#385) |
| HQ-POL | 21 plurx-policy changes in the vendored copy | cinema | Not for upstream | cinema-specific behaviour |
| HQ-27 | Close upgraded API streams when their Raft group terminates | Runner | Held | [November material](../upstream/november-2026/OTHER_PROJECTS.md) · An upgraded API WebSocket can outlive the listener and keep returning stopped-leader errors to survivors. Watch the corresponding Raft group metrics and stop the existing writer loop on shutdown, fatal running_state or a closed watch channel. Focused source test covers live updates and all three terminal cases; Makefile names it. Split the generic library fix from Runner minority-shutdown adapter changes, reconcile with current upstream socket lifecycle and produce an independently qualified port before PR preparation. |

## mpv

Venue: github.com/mpv-player/mpv · PR. Allowed; name model + tool in PR text only, never in commits; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| MPV-1 | wayland: don't send unknown MaxCLL/MaxFALL | cinema | Ready for human review | unit 01: ready-for-human-review November 9 review: Same omit-unknown MaxCLL/MaxFALL correction now in Ubuntu mpv and native 0.42 with extra finite/quantized protocol-v1 bounds. Do not duplicate or imply newer bytes are in the October kit. [November review](../upstream/november-2026/README.md). |
| MPV-2 | demux/dovi_split: split the P7 enhancement layer without FFmpeg 9's BSF | cinema | Ready for human review | unit 02: draft PR; ready-for-human-review November 9 review: Native 0.42 and an explicit upstream FFmpeg dovi_split backport now exist. Review October fallback against current upstream before sending; source inspection alone does not prove the entire fallback superseded. [November review](../upstream/november-2026/README.md). |
| MPV-4 | vulkan/context: Wayland swapchains start in pass-through colour space | cinema | Ready for human review | [kit](../upstream/mpv/README.md) · unit 04: draft PR; ready-for-human-review |
| MPV-5 | osc.lua: whole-film timeline for embedders | cinema | Held | [kit](../upstream/mpv/README.md) · unit 05: design-hold; Maintainer agreement on the embedding interface; propose the design before a merge request |
| MPV-3 | vo_gpu_next: plurx closed-form DV mapping | cinema | Not for upstream | Embeds plurx's own display-management code November 9 review: Private closed-form renderer is excluded. Public generic hooks/target lifecycle proposals do not authorize private code. The custom reconstruction/cache source remains excluded from direct submission. New public upload/quantization candidates do not authorize private mapper implementation or equations. [November review](../upstream/november-2026/README.md). |
| MPV-6 | Preserve raw RPU ownership when inheriting matched enhancement-layer metadata | rog_hdr_dv | Held | [November material](../upstream/november-2026/MEDIA.md) · f_enhancement_pair refs raw RPU from matched EL onto BL, removes stale BL RPU and handles allocation failure. Distinct from October MPV-2 split fallback. Split this hunk from private provider/Wayland/build glue and add focused current-upstream pairing/lifetime regression. Staged 4K FEL and flip/failure controls are downstream evidence. |
| MPV-7 | Separate physical targets from PQ transport and retain mapped cached-capture state | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/MEDIA.md) · Physical min/max/xy and reference-white transport are separate; paused/cache window captures preserve displayed grade and invalidate state on source/target change. Tagged PNG tests changed only authored edited frames; ordinary HDR10/native-source controls byte-equal. Generic target/capture lifecycle proposal requires agreement and extraction from optional private provider integration. No optical claim. |
| MPV-8 | Preserve planar 10-bit software upload precision and required enhancement-layer cleanup | cinema | Held | [November material](../upstream/november-2026/OTHER_PROJECTS.md) · Owned high-aligned UNORM16 staging preserves low-aligned planar 10-bit software filtering for Dolby and limited BT.2020/PQ, including ordinary HDR10. Hardware/P010/integer paths retain their behavior; required enhancement mapping failures clean partially owned resources. Source controls cover code values, strides, eligibility and lifetimes. No new execution, generalized native-build or GPU-performance claim. Extract the generic upload/cleanup change from private consumer glue and qualify against current mpv before submission. |

## FFmpeg

Venue: code.ffmpeg.org · PR, or ffmpeg-devel. No ban found; human review standard enforced; Signed-off-by (-s); code.ffmpeg.org account.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| FF-1 | videotoolboxenc: count SEI sizes in RBSP bytes | cinema | Ready for human review | [kit](../upstream/ffmpeg/README.md) · unit 01: draft PR; ready-for-human-review |
| FF-2 | configure: static Vulkan probe via pkg-config | cinema | Ready for human review | [kit](../upstream/ffmpeg/README.md) · unit 02: ready-for-human-review |
| FF-3 | hevcdec: skip suppressed RASL before PPS lookup (frame threads) | cinema | Superseded upstream | [kit](../upstream/ffmpeg/README.md) · unit 03: superseded |
| FF-POL | 2 Dolby-state policy patches | cinema | Not for upstream | cinema-specific |
| FF-4 | Authoritative frame-owned Dolby metadata and a bounded public RPU resolver | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/MEDIA.md) · New public resolver/strictness API: authoritative SPS rectangle, invalid-RPU withholding, bounded/reserved config rejection, reset metadata on live config change without resetting normal HEVC references. Native reorder/gap/flush/lifetime/conformance/config and pixel controls exist. Discuss upstream parser/side-data API, isolate local symbol/runtime plumbing. Follow-up config checks repair the proposed resolver, not independent preexisting upstream bugs. |
| FF-5 | Explicit display-target mapping hook and export metadata replacement | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/MEDIA.md) · Public adapter selects physical xy/luminance before generic conversion, replaces obsolete source Dolby/HDR10+ side data with destination metadata and keeps named fallback. Export/trim/crop and native chart controls exist. Current implementation depends on private provider and private renderer namespace: discuss/extract generic contract; private mapper equations and SDK implementation remain excluded. |
| FF-BACKPORT | Imported dovi_split, split-NAL length validation and HEVC EL configuration | rog_hdr_dv | Superseded upstream | [November material](../upstream/november-2026/MEDIA.md) · These are explicit upstream backports, not novel patches to send. Preserve original Kacper Michajlow and Michael Niedermayer attribution/signoffs. Packet identity is adapted from upstream 5f6dff5e7dbd9b1f3221f7c37225365dbf1e1038. Local version/build glue is excluded. |

## jellyfin-ffmpeg

Venue: github.com/jellyfin/jellyfin-ffmpeg · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| JF-1 | bwdif_videotoolbox: params buffer bound at the wrong index | cinema | Ready for human review | [kit](../upstream/jellyfin-ffmpeg/README.md) · unit 01: ready-for-human-review |
| JF-2 | tonemap_videotoolbox: Hable reference_white option | cinema | Ready for human review | [kit](../upstream/jellyfin-ffmpeg/README.md) · unit 02: draft PR; ready-for-human-review |
| JF-3 | subtitles_vt_images filter + overlay composite | cinema | Discussion draft | [kit](../upstream/jellyfin-ffmpeg/README.md) · unit 03: design-hold; Maintainer agreement on filter and overlay API; Split the command protocol from generic filter plumbing; Mac render and lifetime tests |
| JF-4 | macOS builder: call /usr/bin/libtool | cinema | Ready for human review | [kit](../upstream/jellyfin-ffmpeg/README.md) · unit 04: ready-for-human-review |
| JF-SEI | VideoToolbox caption SEI | cinema | Superseded upstream | Jellyfin fixed it differently (Oct 8) |
| PI-1 | Raspberry Pi port (rpi-ffmpeg onto 8.1.3) | cinema | Not for upstream | [kit](../upstream/rpi-ffmpeg/README.md) · Third-party Raspberry Pi port is not resubmitted; optional one-line Makefile hypothesis remains unverified. |

## dovi_tool (dolby_vision)

Venue: github.com/quietvoid/dovi_tool · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| DV-5 | Mixed mapping_idc no longer panics | cinema | Ready for human review | [kit](../upstream/dovi_tool/README.md) · unit 01: ready-for-human-review |
| DV-1-4,6 | Other parser bounds fixes | cinema | Superseded upstream | Upstream PR #430 (Oct 23) or moot |
| DV-BACKPORT | Imported C-FFI ownership, recoverable parser errors and pivot bounds | rog_hdr_dv | Superseded upstream | [November material](../upstream/november-2026/MEDIA.md) · Patch bodies explicitly backport upstream commits 4e6b263c35f08bca9efe919effac9c09c26fba70, 73daa31a8ecc76a4eedff8cb8f6197a3d66c3b3c and f41b2809cd00f41118248fcd8a1a3dff6216efcf. Preserve Nomis101/quietvoid authors. CRC-valid unsupported RPU aborts stock but patched parser returns error and accepts subsequent valid input. Do not resubmit or conflate with DV-5 mixed mapping. |

## bitvec_helpers

Venue: github.com/quietvoid/bitvec_helpers · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| BV-1 | read_ue/read_se overflow-safe | cinema | Ready for human review | [kit](../upstream/bitvec_helpers/README.md) · unit 01: ready-for-human-review |

## gemm

Venue: github.com/sarah-quinones/gemm · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| GM-1 | FP16 helpers declare target_feature(neon,fp16) | cinema | Held | [kit](../upstream/gemm/README.md) · unit 01: upstream-overlap-hold; Review the existing upstream PRs and post validation to #47 or coordinate with #39; do not open a duplicate PR |

## ksni

Venue: github.com/iovxw/ksni · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| KS-1 | get_all_item returns real item ids | cinema | Ready for human review | [kit](../upstream/ksni/README.md) · unit 01: ready-for-human-review |

## EasyEffects

Venue: github.com/wwmm/easyeffects · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| EE-3 | Bound programme-loudness makeup + analyser fixes | rog_audio | Ready for human review | [kit](../upstream/easyeffects/README.md) · unit 01: ready-for-human-review / unit 02: ready-for-human-review |
| EE-2 | Keep output routes when a device returns | rog_audio | Discussion draft | [kit](../upstream/easyeffects/README.md) · unit 03: needs-upstream-design; Downstream patch combines product rebranding with routing policy; current upstream autoload/device-exclusion work must be compared on real device transitions before proposing a port. |
| EE-1 | Per-device-route speaker correction + rebrand | rog_audio | Not for upstream | [kit](../upstream/easyeffects/README.md) · Product-specific correction/rebranding stays local; the route discussion is separate. |

## Cavern

Venue: github.com/VoidXH/Cavern · PR. Check before sending; non-OSI licence; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| CAV-1 | BlockBuffer: keep metadata with returned PCM | rog_audio | Ready for human review | [kit](../upstream/cavern/README.md) · unit 01: ready-for-human-review |
| CAV-2 | JOC: wrap QMF timeslots at the PCM frame boundary | rog_audio | Ready for human review | [kit](../upstream/cavern/README.md) · unit 02: ready-for-human-review |
| CAV-3 | EMDF: expose HasOAMD | rog_audio | Ready for human review | [kit](../upstream/cavern/README.md) · unit 03: ready-for-human-review |

## Expo

Venue: github.com/expo/expo · PR. GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| EX-1 | Android splash tools:targetApi plugin | Curator | Ready for human review | [kit](../upstream/expo/README.md) · unit 01: draft PR; ready-for-human-review; Full Expo package checks, TypeScript check, prebuild and EAS Build remain before undrafting; Human review and editing remain |
| EX-2 | iOS scene-lifecycle plugin (Runner + Curator) | Curator | Superseded upstream | Expo SDK 58 generates it |

## libplacebo

Venue: code.videolan.org/videolan/libplacebo · MR. VideoLAN account (needs approval).

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| LP-DM | Dolby Vision display-management API (5 WIP patches) | rog_hdr_dv | Not for upstream | Private by policy; your call if any part should ever go November 9 review: Private display-management equations remain excluded; LP-1 is public renderer-hook discussion only. [November review](../upstream/november-2026/README.md). |
| LP-1 | Frame-owned display-mapping hook before ordinary scaling and conversion | rog_hdr_dv | Discussion draft | Public renderer callback receives authoritative frame metadata and reconstructed native master; propagates mapper failure before generic conversion. Discuss generic hook/lifetime design and exclude private ABI namespace/build glue. LP-DM private equation work remains excluded; no private provider implementation is proposed. New Plurx patch0006 normalizes only local reconstruction color metadata before the existing private display mapper. It is context for the public hook/contract discussion, not a new baseline upstream defect. [November review](../upstream/november-2026/README.md). |
| LP-2 | Honor flipped enhancement planes and contributing-frame failure/target ownership | rog_hdr_dv | Held | Source honors vertical flip, rejects failed contributing-frame acquisition and avoids double release of borrowed mixer target. Native flip: three composed/mapped frames; failing non-reference acquisition correctly fails rendering. Extract upstream-generic fixes from the new hook fatal-state behavior; add current-upstream regression. New Plurx patch0006 checks renderer error/disabled-hook state after the local reconstruction pass. Retain as contributing-frame failure context; do not duplicate it as another independent upstream unit. [November review](../upstream/november-2026/README.md). |
| LP-3 | Discuss reusable exact binary32-to-UNORM16 ties-to-even quantization | cinema | Discussion draft | [November material](../upstream/november-2026/OTHER_PROJECTS.md) · Public integer GLSL helper rounds the exact binary32 input times65535 with ties-to-even rather than rounding a prior float product. Its actual consumer is the custom Vulkan mapped UNORM16 cache, not a generic stock libplacebo correction. Test source compiles the extracted shader as a CPU control against an independent rational oracle; expected exhaustive totals are assertions, not newly run results. Discuss the reusable quantizer API/placement and add native GPU validation; private mapping equations remain excluded. |

## WineHQ

Venue: gitlab.winehq.org. Bans LLM-generated code.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| WINE | All 17 Wine patches | rog_hdr_dv | Not for upstream | WineHQ bans LLM-generated code — rerouted to Proton |

## rust_decimal

Venue: github.com/paupino/rust-decimal. .

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| RD-1 | Remove rkyv feature | cinema | Not for upstream | Breaking change done only to dodge an advisory |

## s3-simple

Venue: github.com/sebadob/s3-simple. .

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| S3-1/2 | quick-xml bump, drop unused deps | cinema | Superseded upstream | In upstream 0.9.0 |

## Additional inventory observations

These four entries were present in the handoff's source inventories but
not its original 85-row snapshot. They are questions or local policies,
not newly established upstream defects.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| EX-3 | Optional camera manifest option | Curator/Runner | Held | [material](../upstream/expo/README.md) · unit 03: held-feature-decision; Contributor must choose whether to propose the plugin option; Need merged-manifest reproduction and plugin tests |
| EX-4 | Unexplained uuid override | Curator/Runner | Not for upstream | [material](../upstream/expo/README.md) · Inventory E4: uuid override has no documented upstream defect; recover its local rationale. |
| ST-1 | Channel normalization semantics | rog_audio | Not for upstream | [material](../upstream/speaker-tuning-to-easyeffects/README.md) · unit 01: excluded |
| ST-2 | All-cut normalization semantics | rog_audio | Not for upstream | [material](../upstream/speaker-tuning-to-easyeffects/README.md) · unit 01: excluded |

## Tiling Assistant

Venue: https://github.com/ubuntu/Tiling-Assistant · PR to the actual upstream subproject; extract the six-patch source series before proposing it.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| TA-1 | Own synthetic tiling animations without consuming native Shell completion accounting | rog_hdr_dv | Held | [November material](../upstream/november-2026/DISPLAY.md) · Six patches on actual upstream v56. Keep ownership, cancellation, overlays, finite geometry and Shell callback ease correction together. Historical first-five source has35 distinct valid offline passes from26 initial+9 failed-only retries, not a new full clean35 run. Sixth callback-API patch has source/package proof; no invented fresh full-suite or broad fullscreen/cross-mode acceptance. Current upstream port, candidate commit explanatory bodies/attribution and latest six-patch focused qualification remain before submission. |

## GTK / GDK

Venue: https://gitlab.gnome.org/GNOME/gtk · GNOME MR; public API contracts need maintainer discussion.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| GTK-1 | Expose immutable per-surface preferred display targets with lifecycle invalidation | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/DISPLAY.md) · Existing shared Wayland color manager owns feedback; default target discovery remains separate from experimental content rendering. Copies physical primaries/black/peak/reference and rejects invalid generations. Native startup, late-manager and reentrant destruction controls passed on pinned Ubuntu source. Agree GTK public API, per-output move/spanning/hotplug coverage and current upstream port. Split unrelated coordinate fix GTK-2 out of the combined source patch. |
| GTK-2 | Store green, blue and white Y coordinates in their own Wayland fields | rog_hdr_dv | Held | [November material](../upstream/november-2026/DISPLAY.md) · Three listener paths (explicit primaries, named primaries, target primaries) overwrote red Y instead of setting g_y/b_y/w_y. It is embedded in GTK-1 patch, but independently upstreamable. Extract minimal baseline correction and focused listener regression, verify current upstream still affected; existing combined compilation/replay is not that standalone proof. |
| GTK-3 | Track a per-surface HDR rendering lease and actual presentation precision | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/DISPLAY.md) · Demand-scoped HDR lease invalidates target/draw-context/precision witnesses and returns to SDR when released. Native EGL four-patch PQ samples, normal Vulkan/introspection and lease lifecycle have scoped evidence. Public API and renderer/offload semantics require maintainer discussion; package symbol/changelog patches are distribution delivery only. |
| GTK-4 | Query implementation read format/type using GLES-supported framebuffer state | rog_hdr_dv | Held | [November material](../upstream/november-2026/DISPLAY.md) · A one-pixel normalized16-bit PQ source reproduced transparent black under the normal Vulkan GTK consumer when NVIDIA rejected EGL export. glGetFramebufferParameteriv generated GL_INVALID_ENUM; glGetIntegerv recovered the exact four stored16-bit words. Correction also gates desktop GL at4.5. Extract/rebase minimal generic fix and add upstream regression; combined package/player controls do not substitute for standalone current-upstream proof. |
| GTK-5 | Bind original video pictures and asynchronous target regrading to each GtkVideo view | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/DISPLAY.md) · Each realized view has copied target, lease and mapper; original pictures retained before playsink and stale stream/caps/view/target generations rejected. Default Vulkan two-view paused616→308→616 exact-return, source replacement, one-view destruction and absent/incompatible/incomplete SDK SDR startup pass. Agree generic upstream mapper/destination integration rather than sending the private provider or distribution SDK coupling. No private mapper equations or implementation belong in submission. |

## Glycin

Venue: https://gitlab.gnome.org/GNOME/glycin · GNOME MR; Loupe is the delivery carrier for this vendored code.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| GLY-1 | Preserve ICC gamut and precision in floating-point textures, with alpha and stride correctness | rog_hdr_dv | Held | [November material](../upstream/november-2026/DISPLAY.md) · Actual code belongs to Glycin3.1 embedded in Loupe50, not a Loupe application patch. Convert ICC into linear BT.2020 float16/32 instead of clipping/quantizing into source integer sRGB; preserve CICP precedence, invalid-profile fallback, alpha, source row stride and transactional failure. Alpha correction folds into this unit because it repairs the new conversion path. Digital fixtures cover256gray levels, RGB/RGBA8/16, associatedU8/U16/F32, padded rows and malformed data; optical/external monitor scope open. Extract vendor-independent current Glycin port/tests; omit Cargo overrides, Debian metadata and vendored checksums. |

## TIFF (Rust)

Venue: https://github.com/image-rs/image-tiff · Rust TIFF crate; Glycin is the delivery carrier, not the fix destination.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| TIFF-1 | Read BYTE and UNDEFINED metadata under the actual byte budget | rog_hdr_dv | Held | [November material](../upstream/november-2026/DISPLAY.md) · Actual code belongs to tiff0.11.3 at image-rs/image-tiff, carried inside Ubuntu glycin-loaders2.2.1. Read byte fields without allocating per-element Value objects; bound total metadata and grow only after successful reads.21,012-byte ICC fixture at80/320/1024pixels with BYTE/UNDEFINED and bad offset/excess count controls passes ordinary sandbox loader. Extract current TIFF crate change with crate-local regression; omit distribution overrides and checksum churn. |

## WebKitGTK

Venue: https://github.com/WebKit/WebKit · WebKit contribution workflow; only the public browser baseline and a design discussion are inventoried here.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| WK-1 | Honor an explicit SDR destination when grading clear Dolby video into ordinary GTK browser pages | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/DISPLAY.md) · Public baseline WebKitGTK2.52.6 controls show identical output with/without Dolby carrier metadata. Active implementation is private, not a public patch kit. November9 handoff reports guarded full build resumed after memory stop; native SDR adapter evidence is not finished browser product acceptance. Keep discussion scoped to clear/unprotected SDR page output. Full high-precision HDR page composition, per-view typed target lifecycle, protected services and final browser comparison remain open. Do not publish private source/header or inference equations. |
| WK-2 | End a seamless loop iteration at the end of playback, not at WebKitWebSrc's byte-range segment-done | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/DISPLAY.md#wk-2-seamless-looping-of-media-pushed-by-webkitwebsrc) · Reproduced on stock-equivalent WebKitGTK 2.52.6 behaviour: a 3 s H.264 `<video loop>` restarted after its first 0.75 s. Downstream workaround `ec69ce27`/`c1fcae69` uses flushing loops for HTTP(S)/blob media; a sink-side segment-done attempt failed because the event stops at the download queue. Upstream fix needs a design that reports the time-domain end in push mode. Report under the owner's account with a public test page; do not attach Dolby media. |

## Mesa

Venue: https://gitlab.freedesktop.org/mesa/mesa · MR; separate WSI fixes from Ubuntu packaging.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| MESA-1 | Validate and omit unavailable optional Wayland HDR metadata | rog_hdr_dv | Held | [November material](../upstream/november-2026/MEDIA.md) · Separate producer from MPV-1: Vulkan WSI emitted MaxFALL=0, rejected by Weston. Source adds finite/quantized unsigned luminance bounds and optional-request omission. Corrected driver accepted. Extract from Debian quilt/changelog, port to current Mesa, add source regressions before submission. |
| MESA-2 | Keep Wayland FIFO deadlines in the compositor clock domain | rog_hdr_dv | Held | [November material](../upstream/november-2026/MEDIA.md) · About 4.1 seconds of false deadlines from CLOCK_MONOTONIC_RAW versus swapchain clock. Separate internal deadline and public completion domains; retain zero-time sentinel. Native timing controls and amd64/i386 packages qualified; player output drops retained. Needs current upstream port/test/description. |

## GStreamer

Venue: https://gitlab.freedesktop.org/gstreamer/gstreamer · MR; keep per-library source ownership and public API discussion explicit.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| GST-1 | Picture-owned original RPU metadata across reordering and flushes | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/MEDIA.md) · New GstVideo meta owns AU bytes and uses matched GstVideoCodecFrame rather than last-picture state; only identity-compatible copies retain it. Native avdec/VA gap/reorder/seek/lifetime/transform controls exist. New meta/tag/copy API needs upstream agreement. Transport is not resolved metadata or FEL reconstruction. |
| GST-2 | Attach original HEVC RPU only from completed access units | rog_hdr_dv | Held | [November material](../upstream/november-2026/MEDIA.md) · h265parse owns completed-AU bytes with parser/reset/flush safety; scoped positive/negative transport controls exist. Depends on proposed GstVideo meta API; requires upstream source port and native test harness. |
| GST-3 | Bounded reusable HEVC Dolby configuration parser in pbutils | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/MEDIA.md) · Reusable dvcC/dvvC parser validates version/flags/profiles/length and writes output only on success; missing compatibility does not infer color space. New public API needs upstream agreement; exclude distro ABI metapackage/symbol packaging. |
| GST-4 | Preserve authoritative Dolby configuration per MP4 sample entry | rog_hdr_dv | Held | [November material](../upstream/november-2026/MEDIA.md) · qtdemux retains bounded sample-entry configuration with correct stream/caps transition and shared validation. Native no-config/replacement controls exist. Depends on pbutils API; compare current upstream and extract source-only patch from packaging. |
| GST-5 | Preserve bounded track-local Dolby configuration in Matroska | rog_hdr_dv | Held | [November material](../upstream/november-2026/MEDIA.md) · Validates bounded BlockAdditionMapping payload/type, duplicates/conflicts and independent track state. 25 focused controls pass; stock negative rejects expected config; native P5 resolved 3 pictures. P7 check is config-only with no residual/reconstruction claim. Prepare current upstream patch/test/description. |
| GST-6 | Bind software libav decoder Dolby state to each decoded picture | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/MEDIA.md) · avdec consumes authoritative strict frame metadata, conformance geometry and live config transitions without resetting ordinary video; transforms discard stale provenance. Native mid-GOP/reset/equal-pixel controls pass. Current gstdovipicture helper and FFmpeg resolver are local: agree upstream owned snapshot API/dependencies first. |
| GST-7 | Associate native VA Dolby state with the decode-order surface | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/MEDIA.md) · Owned resolved snapshot follows VA surface through reordering, flush/config generations and visible crop. Native gap/reorder/seek/lifetime/conformance and transform controls exist. Depends on proposed public snapshot/resolver API; does not itself establish mapped FEL output. |
| GST-8 | Keep picture-owned Dolby provenance and conformance geometry in NVDEC | rog_hdr_dv | Discussion draft | [November material](../upstream/november-2026/MEDIA.md) · Nine producer controls cover avdec/VA/NV; 95-picture config transitions retain normalized pixels; ordinary HEVC gains no Dolby metadata; transformations drop stale provenance. Depends on upstream snapshot/resolver design. Strip dependency/quilt wrappers. Native GStreamer P7 FEL reconstruction remains unfinished separately. |
| GST-9 | Preserve high precision through GL balance and invalidate changed color provenance | rog_hdr_dv | Held | [November material](../upstream/november-2026/MEDIA.md) · glcolorbalance accepts RGBA64_LE; neutral passthrough retains input, transformed pixels discard color-sensitive provenance. Saved patch mixes full Debian quilt export/autogenerated placeholder metadata with 11 source lines: extract generic source fix and add upstream precision/meta tests. |
