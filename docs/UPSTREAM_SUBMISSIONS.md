# Upstream submissions — material, evidence and remaining decisions

**Updated:** 2026-10-28 · **Scope:** the handoff's 85 original entries across
20 upstream projects, plus four previously unlisted mobile/converter
observations. Nothing has been submitted to a third-party upstream.

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
| LNX-1 | drm/edid: DisplayID 2.0 luminance range; i915 accepts any source | rog_hdr_dv | Third-party work | [kit](../upstream/linux/README.md) · unit 01: needs-human-hardware-evidence; Fresh hardware scope/reproduction and latest-thread verification are not established. |
| LNX-2 | Bounded physical-range validation + KUnit coverage | rog_hdr_dv | Ready for human review | [kit](../upstream/linux/README.md) · unit 02: ready-for-human-review; Confirm latest original-thread Message-ID and owner DCO/mail setup before email delivery. |
| LNX-3 | i915: SCL lost when VRR toggles with PSR (Wa_14015401596) | rog_hdr_dv | Held | [kit](../upstream/linux/README.md) · unit 03: needs-human-hardware-evidence; Fresh hardware scope/reproduction and latest-thread verification are not established. |

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

## mpv

Venue: github.com/mpv-player/mpv · PR. Allowed; name model + tool in PR text only, never in commits; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| MPV-1 | wayland: don't send unknown MaxCLL/MaxFALL | cinema | Ready for human review | [kit](../upstream/mpv/README.md) · unit 01: ready-for-human-review |
| MPV-2 | demux/dovi_split: split the P7 enhancement layer without FFmpeg 9's BSF | cinema | Ready for human review | [kit](../upstream/mpv/README.md) · unit 02: draft PR; ready-for-human-review |
| MPV-4 | vulkan/context: Wayland swapchains start in pass-through colour space | cinema | Ready for human review | [kit](../upstream/mpv/README.md) · unit 04: draft PR; ready-for-human-review |
| MPV-5 | osc.lua: whole-film timeline for embedders | cinema | Held | [kit](../upstream/mpv/README.md) · unit 05: design-hold; Maintainer agreement on the embedding interface; propose the design before a merge request |
| MPV-3 | vo_gpu_next: plurx closed-form DV mapping | cinema | Not for upstream | Embeds plurx's own display-management code |

## FFmpeg

Venue: code.ffmpeg.org · PR, or ffmpeg-devel. No ban found; human review standard enforced; Signed-off-by (-s); code.ffmpeg.org account.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| FF-1 | videotoolboxenc: count SEI sizes in RBSP bytes | cinema | Ready for human review | [kit](../upstream/ffmpeg/README.md) · unit 01: draft PR; ready-for-human-review |
| FF-2 | configure: static Vulkan probe via pkg-config | cinema | Ready for human review | [kit](../upstream/ffmpeg/README.md) · unit 02: ready-for-human-review |
| FF-3 | hevcdec: skip suppressed RASL before PPS lookup (frame threads) | cinema | Superseded upstream | [kit](../upstream/ffmpeg/README.md) · unit 03: superseded |
| FF-POL | 2 Dolby-state policy patches | cinema | Not for upstream | cinema-specific |

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
| LP-DM | Dolby Vision display-management API (5 WIP patches) | rog_hdr_dv | Not for upstream | Private by policy; your call if any part should ever go |

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
