# Upstream submissions

Every change in cinema, Runner, Curator, rog_hdr_dv and rog_audio that modifies a third-party project, where it goes, and its status.
Live tracker: https://claude.ai/artifact/UQrcE4WxHqca31HLwTYu3b (this file is a snapshot of it, 2026-10-27 15:35 ET).
Submission kits: `upstream/` in rog_hdr_dv and rog_audio, `contrib/rqbit/upstream/` in Runner, `upstream/` in cinema (in progress).

## Mutter (GNOME)

Venue: gitlab.gnome.org/GNOME/mutter · MR. No written AI rule; GNOME-wide policy being debated — disclose; Issue/MR URL in every commit; GNOME GitLab account.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| MUT-M | frames: use gtk-interface-color-scheme (1 patch) | rog_hdr_dv | Being prepared |  |
| MUT-A | Colour-management protocol robustness: signed primaries, ICC ranges, creator errors (8) | rog_hdr_dv | Being prepared | Check against open !4604 and !5313 |
| MUT-B | Offer HDR on native DisplayID BT.2020 PQ eDP panels (1) | rog_hdr_dv | Being prepared | Needs libdisplay-info LDI-2..4 released; fixes #4847 family |
| MUT-C | Publish native target luminance/primaries separately from encoding (12) | rog_hdr_dv | Being prepared | Overlaps open !5068 |
| MUT-D | HLG transfer function + BT.2100 system gamma (4) | rog_hdr_dv | Being prepared | No competing upstream MR found |
| MUT-E | Target colour volume, mastering metadata, light levels (8) | rog_hdr_dv | Being prepared | Overlaps !5068; folds the Ubuntu-only init fix |
| MUT-F | Highlight mapping toward a declared target (4) | rog_hdr_dv | Being prepared | Depends on MUT-E |
| MUT-G | Gamut compression toward a declared display gamut (7) | rog_hdr_dv | Being prepared | Depends on MUT-E |
| MUT-H | Target sources: CTA peak, base-EDID native SDR primaries (5) | rog_hdr_dv | Being prepared | Depends on MUT-C, MUT-E |
| MUT-I | White adaptation + Night Light in linear light (10) | rog_hdr_dv | Hold: design talk first | Likely superseded by open !5177 (colour management rework) |
| MUT-J | Per-monitor target overrides: config, D-Bus API, gdctl (12) | rog_hdr_dv | Hold: design talk first | New API; collides with !5177 |
| MUT-K | Colour device / colord lifecycle robustness (16) | rog_hdr_dv | Hold: design talk first | Obsolete if !5177 lands; 84/85 (teardown) could go alone |
| MUT-L | Offscreen buffer reuse across colour-state changes (2) | rog_hdr_dv | Being prepared |  |
| MUT-0 | Design-discussion issue for the whole series | rog_hdr_dv | Being prepared | Open this first; asks how to coordinate with !5068 and !5177 |

## libdisplay-info

Venue: gitlab.freedesktop.org/emersion/libdisplay-info · MR. No written AI rule — disclose; Signed-off-by required; freedesktop account + user verification to fork.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| LDI-1 | displayid2: bound padding scans (ASan fix) + test | rog_hdr_dv | Being prepared | Smallest first submission |
| LDI-2 | Parse DisplayID 2.0 Display Interface Features | rog_hdr_dv | Being prepared | Same block as open MR !210 (Sean Paul) — offer as review input |
| LDI-3 | Reject unsupported nested CTA headers in DisplayID | rog_hdr_dv | Being prepared |  |
| LDI-4 | Structured extension-failure status API | rog_hdr_dv | Being prepared | New public API — needs a design nod |
| LDI-5 | Native physical luminance from Display Parameters | rog_hdr_dv | Being prepared |  |
| LDI-6 | Lossless native DisplayID2 chromaticity | rog_hdr_dv | Being prepared |  |

## Linux kernel (DRM / i915)

Venue: dri-devel, intel-gfx · email (b4). Tool use must be disclosed; AI may not sign off; Signed-off-by required (yours); b4 web-submission or SMTP set up.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| LNX-1 | drm/edid: DisplayID 2.0 luminance range; i915 accepts any source | rog_hdr_dv | Not for upstream | Cristian La Spina's posted series (Aug 2) — not ours. Reply with a Tested-by instead |
| LNX-2 | Bounded physical-range validation + KUnit coverage (2 patches) | rog_hdr_dv | Being prepared | Sent as a follow-up on Cristian's thread |
| LNX-3 | i915: SCL lost when VRR toggles with PSR (Wa_14015401596) | rog_hdr_dv | Being prepared | Bug report only; no patch written. Matches Mutter #5079 |

## Proton (ValveSoftware/wine)

Venue: github.com/ValveSoftware/wine · PR to proton_11.0. No written AI rule — disclose (WineHQ bans LLM code); GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| PR-1 | kernelbase: CreateFileFromAppW | rog_hdr_dv | Being prepared | Applies cleanly |
| PR-2 | win32u: monitor provenance and connector technology | rog_hdr_dv | Being prepared | Hand-merge against Proton's Gamescope EDID code |
| PR-3 | windows.devices.display: DisplayMonitor statics | rog_hdr_dv | Being prepared | Hand-merge + regenerate configure |

## rqbit

Venue: github.com/ikatson/rqbit · PR. AI_POLICY: disclose; human must explain every line; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| R8 | Configurable max metadata size (BEP 9) | Runner | Ready | PR 01 · full cargo test 169/0 · send first |
| R9 | Stop initialization on file-sizing errors (ENOSPC) | Runner | Ready | PR 02 · 170/0 · send first |
| R2 | Bound HTTP tracker responses and request time | Runner | Ready | PR 03 · 170/0 · behaviour change, ask maintainer |
| R1 | SessionOptions::disable_auto_restore | Runner | Ready | PR 04 · 169/0 |
| R3 | Optional session-wide peer limit | Runner | Ready | PR 05 · 171/0 |
| R6 | Per-peer response budget | Runner | Ready | PR 06 · 170/0 · budget now follows max_request_window |
| R5 | Bound retained known peers | Runner | Ready | PR 07 · 176/0, 10/10 repeat runs · after PR 05; overlaps open #667 |
| R7 | Bound DHT queues (PR 08) and metadata-resolver work (PR 09) | Runner | Ready | 169/0 and 170/0 · overlaps open #706 / #708; read PR 08 hardest |
| R10 | Per-torrent discovery health (design issue first) | Runner | Hold: design talk first | Large API; post an issue before any PR |
| R13 | Tracker announce lifecycle: completed/stopped, trackerid | Runner | Hold: design talk first | 2,053-line patch; split into an issue + small PRs later |
| R11 | SessionOptions::disable_pex | Runner | Hold: design talk first | Needs a port to main; later |
| R4 | Pending-handshake cap | Runner | Already fixed upstream | Upstream main has max_pending_incoming_handshake_checks |
| R12 | Test-only DHT bootstrap feature | Runner | Not for upstream | Runner-specific test hook |

## hiqlite

Venue: github.com/sebadob/hiqlite · PR. Has an AI-contribution policy — disclose; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| HQ-1 | Reject duplicate node ids in NodeConfig | cinema | Being prepared | Partly upstream (#368); remainder ready |
| HQ-RP | Don't follow redirects with X-API-SECRET (redirect Policy::none) | cinema | Being prepared | Security hardening — may go privately first |
| WAL-1 | Restore last_purged_log_id when the only WAL file is 1 | cinema | Being prepared | Voter panics after snapshot install without it |
| HQ-8 | Keep snapshot RPC peer errors as RemoteError | cinema | Being prepared | Needs port to v0.15.3 |
| HQ-9 | Write-and-flush budget for WebSocket frames | cinema | Being prepared | Large (9 files); may be written up instead |
| HQ-10 | Supervisors own and join split socket tasks | cinema | Being prepared | Partly overlapped by #373 |
| HQ-11 | Dropped RPC notifies its WS manager reliably | cinema | Being prepared | Needs port |
| HQ-19 | Install rustls crypto provider before building clients | cinema | Being prepared | Latent upstream |
| WAL-3 | WAL incarnation identity + layout guard | cinema | Being prepared | Partly upstream (#367) |
| HQ-17 | Gate cryptr's S3 feature behind hiqlite's s3 feature | Runner | Being prepared | Runner-only change in its hiqlite copy |
| HQ-26 | TCP_NODELAY on accepted streams | cinema | Already fixed upstream | Upstream #374 |
| WAL-2 | Atomic meta.hql replacement | cinema | Already fixed upstream | Upstream #357 |
| HQ-2 | Split-brain probe TLS policy | cinema | Already fixed upstream | Upstream removed the check (#385) |
| HQ-POL | 21 plurx-policy changes in the vendored copy | cinema | Not for upstream | cinema-specific behaviour |

## mpv

Venue: github.com/mpv-player/mpv · PR. Allowed; name model + tool in PR text only, never in commits; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| MPV-1 | wayland: don't send unknown MaxCLL/MaxFALL | cinema | Being prepared | Regression from mpv 042bfd9e0 |
| MPV-2 | demux/dovi_split: split the P7 enhancement layer without FFmpeg 9's BSF | cinema | Being prepared |  |
| MPV-4 | vulkan/context: Wayland swapchains start in pass-through colour space | cinema | Being prepared | NVIDIA 615 'surface already requested' |
| MPV-5 | osc.lua: whole-film timeline for embedders | cinema | Being prepared | Niche feature; may be declined |
| MPV-3 | vo_gpu_next: plurx closed-form DV mapping | cinema | Not for upstream | Embeds plurx's own display-management code |

## FFmpeg

Venue: code.ffmpeg.org · PR, or ffmpeg-devel. No ban found; human review standard enforced; Signed-off-by (-s); code.ffmpeg.org account.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| FF-1 | videotoolboxenc: count SEI sizes in RBSP bytes | cinema | Being prepared |  |
| FF-2 | configure: static Vulkan probe via pkg-config | cinema | Being prepared |  |
| FF-3 | hevcdec: skip suppressed RASL before PPS lookup (frame threads) | cinema | Being prepared | Needs rebase onto master |
| FF-POL | 2 Dolby-state policy patches | cinema | Not for upstream | cinema-specific |

## jellyfin-ffmpeg

Venue: github.com/jellyfin/jellyfin-ffmpeg · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| JF-1 | bwdif_videotoolbox: params buffer bound at the wrong index | cinema | Being prepared | 1-line bug fix |
| JF-2 | tonemap_videotoolbox: Hable reference_white option | cinema | Being prepared |  |
| JF-3 | subtitles_vt_images filter + overlay composite | cinema | Being prepared | 880 lines, new feature |
| JF-4 | macOS builder: call /usr/bin/libtool | cinema | Being prepared |  |
| JF-SEI | VideoToolbox caption SEI | cinema | Already fixed upstream | Jellyfin fixed it differently (Oct 8) |
| PI-1 | Raspberry Pi port (rpi-ffmpeg onto 8.1.3) | cinema | Not for upstream | Port of a third-party tree; at most a 1-line Makefile fix |

## dovi_tool (dolby_vision)

Venue: github.com/quietvoid/dovi_tool · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| DV-5 | Mixed mapping_idc no longer panics | cinema | Being prepared |  |
| DV-1-4,6 | Other parser bounds fixes | cinema | Already fixed upstream | Upstream PR #430 (Oct 23) or moot |

## bitvec_helpers

Venue: github.com/quietvoid/bitvec_helpers · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| BV-1 | read_ue/read_se overflow-safe | cinema | Being prepared |  |

## gemm

Venue: github.com/sarah-quinones/gemm · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| GM-1 | FP16 helpers declare target_feature(neon,fp16) | cinema | Being prepared |  |

## ksni

Venue: github.com/iovxw/ksni · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| KS-1 | get_all_item returns real item ids | cinema | Being prepared |  |

## EasyEffects

Venue: github.com/wwmm/easyeffects · PR. Check before sending; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| EE-3 | Bound programme-loudness makeup + analyser fixes | rog_audio | Being prepared | Rebase onto master and split |
| EE-2 | Keep output routes when a device returns | rog_audio | Being prepared | May become an issue draft |
| EE-1 | Per-device-route speaker correction + rebrand | rog_audio | Not for upstream | Product-specific |

## Cavern

Venue: github.com/VoidXH/Cavern · PR. Check before sending; non-OSI licence; GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| CAV-1 | BlockBuffer: keep metadata with returned PCM | rog_audio | Being prepared | 1 line |
| CAV-2 | JOC: wrap QMF timeslots at the PCM frame boundary | rog_audio | Being prepared | 1 line |
| CAV-3 | EMDF: expose HasOAMD | rog_audio | Being prepared |  |

## Expo

Venue: github.com/expo/expo · PR. GitHub.

| Unit | Change | From | Status | Notes |
|---|---|---|---|---|
| EX-1 | Android splash tools:targetApi plugin | Runner | Needs Paul's call | Plausible PR but needs a repro first |
| EX-2 | iOS scene-lifecycle plugin (Runner + Curator) | Curator | Already fixed upstream | Expo SDK 58 generates it |

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
| S3-1/2 | quick-xml bump, drop unused deps | cinema | Already fixed upstream | In upstream 0.9.0 |
