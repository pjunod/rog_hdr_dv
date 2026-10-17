# Experimental native RPU-aware player

## Current delivery state

The playback-first milestone is real, not a future build estimate. The
coordinator's existing Ubuntu stock-player trial on 2026-10-13 played the genuine
official Sol Levante **Profile 5 BL+RPU** sample for 30 seconds (exit 0), with
advancing PTS, VO input `dolbyvision`, a real `reshaping` pass, and a separate
RGB10A2 BT.2020/PQ output target around 616 cd/m². No decoder/render drops were
reported. This lane does not repeat that successful trial or touch the intentionally
paused owner demo. Appearance, normal audio, Profile 8 playback, optical accuracy,
complete trims and no-double-mapping acceptance are not inferred.

This small launcher package reuses installed Ubuntu **mpv 0.41.0-2ubuntu5**, **libplacebo
7.360.1-1** and **FFmpeg 8.1.2**. It does not rebuild or replace those upstream
implementations, nativehdr10, audio packages, or the session. Construction and
syntax compilation preceded independent review `t_04bf0100`. That review accepted
the inherited genuine P5 path but required two launcher diagnostic fixes, now
implemented in `t_467eb9d9`: post-start persistence is advisory and continuous
mpv logging is omitted. Focused closure is `t_4980e991`, followed by the single
affected batch/package qualification in `t_64e178b2`. No units run during this lane.
Full accuracy and final combined delivery remain independent programme work.

See [usage](USAGE.txt) for launch/install/rollback commands and limitations.
The package is `hermes-hdr-experimental-player`, Architecture all (Python
launcher; the qualified runtime is Ubuntu x86_64). Its current version is the
top entry of [debian/changelog](debian/changelog); a kit selects one exact
package by SHA256, never by version alone.
There are no maintainer scripts, services, global config, audio settings or
profile activation. Desktop Open With and an idle drag/drop window are supplied.
Diagnostics are private and advisory, never a gate claiming full Dolby fidelity.
Collection is startup-scoped (35 seconds/35 attempts, bounded IPC/sample/receipt
bytes), not every playlist item or late drag/drop verification. A post-start
write/rename/serialization failure disables persistence and warns once without
terminating healthy mpv or masking its status. Last successful evidence remains
honestly incomplete; no invented final result. See usage for exact byte limits,
the bounded atomic temporary and manual retention across separate launches.

## Source and ABI inventory

[inputs.json](inputs.json) pins the official HTTPS source descriptions, source
archives and Ubuntu packaging by size/SHA256. Source archives were actually
acquired and hash-verified. DSC signatures/signed Release authentication are
NOT claimed; provenance scope is explicit. mpv's Ubuntu packaging carries no
`debian/patches` directory in the acquired archive; `debian/rules` sets ordinary
build switches and installs a stock mpv.conf which this launcher does not load.

Required installed shared ABI is libplacebo **SONAME360**, FFmpeg **libavcodec62**
and **libavutil60**. The launcher depends on mpv≥0.41.0, libplacebo360≥7.360.1,
libavcodec62/libavutil60≥7:8.1.2 and Python≥3.11. Installed target inventory and
actual playback are retained as external private evidence, not manufactured
package execution. Source-level inventories below use the acquired original
archives (upstream mpv archive root `mpv-player-mpv-2c219aa`, libplacebo commit
`cee9b076f2c63104ccfd497fa79c39a867293ec4`). Exact individual file hashes are in
`interface-inventory.json`.

| Boundary | Actual source path and contract |
|---|---|
| FFmpeg frame metadata → mpv | mpv `video/mp_image.c:1183–1203`: reads `AV_FRAME_DATA_DOVI_METADATA`; only when `disable_residual_flag` is true, maps via `pl_map_avdovi_metadata` (PL_API_VER≥343), retains metadata buffer. `1206–1209` additionally imports RPU-buffer dynamic HDR metadata. Stream configuration/profile alone is insufficient. |
| VO input → renderer | mpv `video/out/vo_gpu_next.c:638–665`: source frame representation/color are supplied to libplacebo. This is what `video-out-params` describes, NOT the PQ surface encoding. |
| Metadata → reshaping | libplacebo `src/shaders/colorspace.c:106–118` describes the actual pass as `reshaping` and emits `// pl_shader_reshape`; the Dolby representation decode branch calls it. Consumer P5/P8 without residual enhancement is intended. P7 FEL is excluded. |
| Dynamic L1 | libplacebo `src/utils/dolbyvision.c` and `src/include/libplacebo/utils/libav.h`: current metadata maximum/average path, not complete display management. L1 minimum and L2/L8 creative trims remain accuracy work. |
| Preferred target | mpv `video/out/wayland_common.c:2156–2203,2252–2273,2303–2320`: retrieves immutable preferred feedback, stores target primaries and luminance, responds to preferred changes. It rescales for libplacebo reference-white convention; exact preferred black is not retained in the observed target. |
| Render target | mpv `video/out/vo_gpu_next.c:1087–1215`: reads swapchain target, chooses target hint (`target`, not source/source-dynamic), restores target luminance/static metadata rather than source mastering peak. No forced peak/TRC/gamut supplied by launcher. |
| Output parameters → Wayland tag | mpv `video/out/wayland_common.c:3503–3564,4216+`: creates a parametric description from rendered `target_params`, sets named encoding plus target-derived mastering values and sets it on the surface (`2132–2139`). It does NOT reuse the exact preferred image-description object. |
| Observable evidence | Bounded startup IPC `current-vo`, advancing `video-pts`, `video-out-params` DV representation and `vo-passes` real reshaping pass together; `video-target-params` separately describes target. Detailed preferred-feedback/tag logs are retained from the separately coordinated original stock trial, not collected continuously by the launcher. No profile-header-only or HDR10 fallback success. |

## Normal source construction (native fixed builder only)

The launcher is an ordinary Ubuntu source package: `debian/control`, `rules`,
`copyright`, a versioned `changelog` and source format `3.0 (native)`, built
with debhelper 14 and `dpkg-buildpackage -F -us -uc`. Construction uses pinned
committed inputs; it is normal source packaging, not a bit-for-bit
reproducibility claim. Prepare the committed source before transfer, never
`.git` or credentials:

    git archive --format=tar -o launcher-source.tar COMMIT:tools/native_player
    sha256sum launcher-source.tar

Transfer only that archive, [build.py](build.py) and the deferred scoped tests
through the existing fixed wrapper's supported bounded import, then in a fresh
task-owned durable output on the native builder run:

    python3 build.py --source-archive launcher-source.tar --sha256 SHA256 \
        --commit COMMIT --output /work/<owned-lane>/launcher

`build.py` refuses an ephemeral or existing output directory, a short commit
or a mismatched archive hash, extracts the hash-verified source, and builds
with `nocheck`. It never installs, starts mpv or invokes units.

Artifact contract of one construction, all written beside each other and
listed with SHA256 in `SHA256SUMS` and `build-receipt.json`:

| Artifact | Meaning |
|---|---|
| `hermes-hdr-experimental-player_VERSION.dsc`, `_VERSION.tar.xz` | Normal native source package; the archive members are the committed `tools/native_player` tree |
| `hermes-hdr-experimental-player_VERSION_all.deb` | The only binary: `/usr/bin/hermes-hdr-player`, the desktop entry, `USAGE.txt`, `inputs.json`, `copyright` and `changelog.gz`; no maintainer scripts |
| `_VERSION_amd64.changes`, `_VERSION_amd64.buildinfo` | Closure of the files above by size and SHA256 |
| `committed-source.tar`, `build.log`, `build-receipt.json` | The consumed source archive, the construction log and the receipt binding the full source commit, archive hash and every artifact hash |

Scoped qualification is a single later affected batch, not build-time: the
`tests/test_merged_ubuntu_packages.py` artifact inspections (exact payload,
modes, dependencies, source-archive equality with the committed source, closure
of `.dsc`/`.changes`/`.buildinfo`) plus the one launcher method whose metadata
path changed. The 29 unchanged launcher algorithm methods keep their retained
receipts and are not re-executed by a packaging revision.

Each changed payload gets a new version. `1.0~experimental4` corrects only the
installed `USAGE.txt` (no stale hardcoded package version; it is shipped
uncompressed) and leaves `player.py` unchanged; `1.0~experimental3`, the first
normal source construction, stays immutable as a superseded construction and
is never relabelled.

Before coordinated installation, the exact host APT simulation must show only
one NEW launcher package with no core/audio changes, and a candidate-installed
status-model reverse simulation must remove only this package. Qualification
owns those checks; a simulated state is not an actual installation. Runtime
requirements already exist on the inspected target. Rollback is removal of only
this launcher, with no `autoremove`, stock package changes or session action.

## Historical experimental2 evidence

`1.0~experimental2` was a standalone `dpkg-deb` construction with an `--epoch`
builder interface that no longer exists. Its evidence is retained as history,
not rewritten: [QUALIFICATION.md](QUALIFICATION.md) records the single
post-review `python3 -m unittest discover -s tests -p test_native_player.py -v`
batch (30 methods and 34 subtests) under a durable task TMPDIR: deterministic
argv/literal filename separation, silent/idle behavior, DV-vs-HDR10 classifier
and correlated progress, malformed PTS, real pass descriptions, IPC
event/request correlation/bounds, private durable state and desktop/control
contract; mid-run/final write and rename failures, final serialization and
receipt overflow, actual child status, signal forwarding/restoration/races,
cancellation/fatal cleanup and reaping, IPC absolute deadline/aggregate bytes,
sample count/bytes, unavailable IPC and absence of continuous logs. Those
lifecycle tests use real private receipt bytes and fixture children/clocks,
not player execution; shape fixtures are not Dolby metadata, trims or reference
renders. The experimental2 package, its solver receipts and the original
successful installed-stock trial identities remain valid at their own scope.
No duplicate playback or renderer suite is run for another reviewer; any
launcher-specific trial requires a separately coordinated operator window.

## Precise remaining integration patches (not a first-playback gate)

1. Qualified libplacebo open display-management API/algorithm from mapping owner,
   including the genuine minimum and target-dependent L2/L8 semantics/coverage.
   Do not invent metadata or select a curve here.
2. mpv's preferred-description handling must preserve encoding and target as
   separate data, retain raw target black/peak/primaries and immutable wire
   identity across preferred changes, and associate that exact identity with
   frames rendered for it. Current preferred-to-libplacebo rescaling and
   parametric reconstruction are not exact identity proof.
3. Make output tagging describe the actual already-mapped pixels without source
   mastering metadata; prove exact matching preferred description or supported
   equivalent and no duplicate tone/gamut mapping while leaving intentional
   Night Light/output characterization intact. The observed 1e-6 target black
   vs preferred physical black is a concrete remaining mismatch.
4. Final combined lane owns headless target-change/tagging/no-double-mapping
   regressions, standalone native consumer, combined packages and rollback kit.
   Consumer Profile 8 and creative trims need actual separate evidence; P7 FEL
   remains excluded unless genuinely implemented. Full reference/optical/physical
   acceptance and Plurx native application integration remain separate.

No defensible full-fidelity date follows from this milestone. The earliest
experimental target trial has already happened with unchanged stock software;
the launcher is independent usability/diagnostic packaging, not new DV math.
