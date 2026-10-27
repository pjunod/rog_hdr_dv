# Mutter submissions

Upstream: <https://gitlab.gnome.org/GNOME/mutter> (merge requests into `main`).
Base: `b48811767189fb5446bd1b831e98271a21866e09` (`main` on 2026-10-27, "ci: Set committer
identity for intermediate builds"). Nothing here has been submitted, pushed or posted.

Start with [00-ISSUE.md](00-ISSUE.md): a design-discussion issue for Paul to open first. It
describes the series and its hardware evidence and asks how to coordinate with !5068 and
!5177. Its URL is also the natural value for the commits' `Link:` lines (below).

The 90 patches of `patches/mutter/` became 81 commits in 15 units. Every commit is authored by
Paul Junod, has a body, a capitalised subject of at most 72 characters after its prefix, and an
issue or MR URL line; none has a `Signed-off-by` (added by `submit.sh` when Paul runs it).

## Units, in submission order

| NN | Slice | Unit | Commits | Stacked on | Status | Overlap / notes |
|---|---|---|---|---|---|---|
| 01 | MUT-M | frames: GTK interface color scheme | 1 | - | ready | Raises gtk4 to 4.20 (justified in the commit; alternative offered) |
| 02 | MUT-L | clutter/stage-view: offscreen reuse | 2 | - | ready | Second commit is 0089's stage-view test only (see below) |
| 03 | MUT-K (0084, 0085) | backend, seat/native teardown | 2 | - | ready | No dedicated test (the one that found them is in 15) |
| 04 | from MUT-J (0070) | monitor-manager: restore handle | 1 | - | ready | Applies alone; its test is in 14 |
| 05 | MUT-B | native DisplayID RGB BT.2020 PQ on eDP | 1 | - | blocked on libdisplay-info 02-04 release | Related #4847 (#5093) |
| 06 | MUT-C | native target luminance and primaries | 11 | 05 | blocked on libdisplay-info 05-06 release; design questions in the issue | !5068; Related #5001 |
| 07 | MUT-A | protocol input robustness | 7 | 06 | blocked (textually stacked on 06) | !4604 (opposite on clamping), !5313 |
| 08 | MUT-D | HLG | 3 | 07 | blocked (stack) | none found |
| 09 | MUT-E | target colour volume and mastering metadata | 3 | 08 | blocked (stack) | !5068 |
| 10 | MUT-F | highlight mapping | 4 | 09 | blocked (stack) | !5068 |
| 11 | MUT-G | gamut compression and follow-ups | 12 | 10 | blocked (stack) | none found |
| 12 | MUT-H | CTA and base EDID target sources | 5 | 11 | blocked (stack) | Related #5001 |
| 13 | MUT-I | Night Light in linear light in BT.2100 | 11 | 12, 02 | **hold: needs design discussion / collides with !5177** | Related #3687 |
| 14 | MUT-J | per-monitor target overrides (D-Bus, monitors.xml, gdctl) | 7 | 13, 04 | **hold: needs design discussion / collides with !5177** | new D-Bus API |
| 15 | MUT-K | colour device, colord and store lifecycle | 11 | 06, 03 | **hold: needs design discussion / collides with !5177** (which removes this code) | test seam (below) |

Dependency chain (textual, verified by applying each slice on the minimal base): 01, 02, 03,
04 and 05 apply to `main` on their own; 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 is one
chain; 13 also needs 02, 14 also needs 04, and 15 needs 06 and 03. `units.tsv` records it and
`submit.sh` applies the units a unit is stacked on (skipping any already merged). MUT-A is a set
of bug fixes in substance, but it does not apply without MUT-C's changes to
`meta-wayland-color-management.c` and the tests; rebasing it onto `main` by hand is possible
follow-up work if upstream wants it first (the issue asks).

## What changed compared with `patches/mutter/`

The final tree of unit 14 equals `main` with the original patches 0001-0071, 0088 and 0089
applied, except for three intended edits (the copyright line of meta-color-target-override.h, the
0104 fix and the reworded 0035 comment), and unit 15's equals `main` with 0001-0012, 0017 and 0072-0087 applied,
except for the copyright lines (both checked with `git diff`). Changes:

- **Authorship and metadata** (every commit): author and committer Paul Junod; `Co-Authored-By`
  and `Claude-Session` trailers removed; process wording removed from messages ("Review
  corrections", "deferred regressions", "no unit execution", "source stage", "review decision",
  "acceptance point"); the Ubuntu 51.0 / "private real-panel probe" validation paragraph of 0001
  replaced by a neutral test description; the `nativehdr6` code comment of 0035 reworded.
- **Copyright holders**: `Copyright (C) 2026 Codex` (meta-color-target-override.h) and
  `Copyright (C) 2026 Sol Agent` (meta-color-lifecycle-test-private.h, color-lifecycle-tests.c)
  became `Copyright (C) 2026 Paul Junod`.
- **Messages**: lowercase subjects (0082-0087, 0090) capitalised and given upstream prefixes
  (`color-store:`, `backend:`, `seat/native:`, `tests/color:`, `frames/window-tracker:`); 17
  subjects over 72 characters shortened; the 16 empty bodies (0002-0007, 0078-0087) and the
  single-line bodies (0055-0060, 0088-0090) written from the diffs; long lines rewrapped.
- **URL line in every commit** (`doc/git-conventions.md`): MUT-B `Related: …/issues/4847`;
  MUT-C and MUT-H `Related: …/issues/5001`; MUT-I `Related: …/issues/3687`; every other commit
  `Link: TBD-MR` (see "Link lines").
- **Fixups squashed**: 0005 into 0004; 0021 split between 0019 and 0020 (the disconnect-warning
  expectation for each one's protocol-error cases); 0037 split into 0022 (code) and 0024 (tests),
  with both messages describing the Table 5 system gamma; 0064 and 0071 into 0058 (the D-Bus
  test's restore wait); 0065 into 0056 (truncated monitors.xml stays accepted); 0066 into 0061;
  0081 into 0080; 0082 into 0078; 0087 into 0083. Kept separate on purpose: 0007 (cannot move
  next to 0003 without conflicts; test-only), 0036, 0039, 0043 and 0046 (each a reasoned
  behaviour change with its own tests on top of 0028/0032).
- **Ubuntu-only fix ported**: `ubuntu-mutter/0104`'s `double peak = -1.0;` folded into 0027's
  test (unit 09), avoiding `-Wmaybe-uninitialized` in optimised `-Werror` builds.
- **Slices adjusted to what applies**: 0036 and 0038-0043, 0046 moved from MUT-E/MUT-G as listed
  in the inventory into one gamut slice (unit 11), because 0036 needs 0032-0035 and 0042 needs
  the gamut tests; MUT-E is 0025-0027; 0037 is in MUT-D; 0070 became its own unit (04) and
  0084/0085 unit 03; 0089 split: its stage-view test stays with 0088 (unit 02, applies to `main`)
  and its Night Light ramp check moved to the end of unit 13, which needs MUT-I's test.
- **0079 test seam** (unit 15): kept and flagged. It adds an optional hook, compiled only when
  tests are built (`HAVE_COLOR_LIFECYCLE_TESTS`), at the start of nine asynchronous colour
  callbacks so a test can park a GIO delivery and replay it after teardown. Mutter's existing
  test facilities (META_EXPORT_TEST, the dbusmock colord/gsd mocks, `meta_wait_for_*`) can
  delay D-Bus replies but cannot park an in-process `GAsyncReadyCallback` such as a file read
  or a GTask completion, so I found no way to express these 20 cases without a seam. Upstream
  may well object; since unit 15 is held for !5177 (which deletes this code), this does not
  block anything now. Distributions that build with `-Dtests=true` would ship the hook (inert
  without a test installing it).
- **0090 gtk4 bump** (unit 01): kept. `GTK_INTERFACE_COLOR_SCHEME_*` and the property exist only
  from GTK 4.20, so using them needs either the bump or a `GTK_CHECK_VERSION` branch; the
  description offers the branch as an alternative. GTK 4.20 shipped with GNOME 49.

## Link lines

Mutter wants an issue or MR URL in each commit, and its CI rules forbid a link to the MR's own
URL as a bare line and ask for no `Part-of:` (added at merge). Where no existing issue fits, the
commits carry `Link: TBD-MR`, and `submit.sh` refuses to run until `--link` says what replaces it:

- `--link https://gitlab.gnome.org/GNOME/mutter/-/issues/<N>`: the design-discussion issue from
  00-ISSUE.md once Paul opens it. Recommended for units 06-15.
- `--link mr`: the unit's own MR URL; the script opens the MR as a draft, rewrites the lines with
  its URL, force-pushes and then un-drafts it. Only allowed for units with nothing unmerged
  below them (01-05). Note the possible conflict: the commit-rules deny a bare own-MR URL line;
  a `Link: <url>` line does not match that regex, but maintainers may prefer the issue URL.
  This was the instruction I was given; Paul decides.

## Verification on lab5 (2026-10-27)

Environment: lab5, in a disposable Ubuntu 26.10 container (GCC 15.3, meson 1.10.1, GLib 2.90,
GTK 4.24.1, Mesa 26.2.4 llvmpipe), with libdisplay-info `main` + its units 01-06 installed in a
prefix (built with `-Dwerror=true`, 80/80 tests there too). Commands, in one shared build dir:

    PKG_CONFIG_PATH=<prefix>/lib/x86_64-linux-gnu/pkgconfig LDFLAGS=-Wl,-rpath,<prefix>/lib/x86_64-linux-gnu \
      meson setup b -Dremote_desktop=true -Dwerror=true
    git checkout <commit>; nice ninja -C b          # every commit of every unit, oldest first
    LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe LP_NUM_THREADS=2 META_DBUS_RUNNER_DISABLE_LOGIND_PASSTHROUGH=1 \
      meson test -C b --setup mutter:default --no-rebuild --num-processes 4 --timeout-multiplier 3 <tests>
    meson setup b-rel -Dremote_desktop=true -Dwerror=true -Dbuildtype=release; ninja -C b-rel   # each tip
    ./check-style.py --dry-run --sha <unit base>

| NN | Tip | -Werror build per commit | Release -Werror (tip) | Tests on the tip | check-style |
|---|---|---|---|---|---|
| 01 | `493eaec7cff4` | 1/1 | OK | none cover src/frames | clean |
| 02 | `584298d735b4` | 2/2 | OK | whole suite: 288 OK, 5 expected fail, 1 timeout (`input-capture` under the parallel run; rerun alone: OK, and OK alone on `main`) | clean |
| 03 | `678b96a1c695` | 2/2 | OK | unit, stage-views, monitor-config-tests, color-management: 4/4 | clean |
| 04 | `95b1396607df` | 1/1 | OK | unit, monitor-storage, monitor-config, monitor-dbus: 4/4 | clean |
| 05 | `227092f271f7` | 1/1 | OK | edid, native-hdr, monitor-color, monitor-config, color-management: 5/5 | clean |
| 06 | `2b45e9fd0fe0` | 11/11 | OK | colour set: 16/16 | chunk artefacts only |
| 07 | `0d5b92abd394` | 7/7 | OK | colour set: 18/18 | clean |
| 08 | `c12ecfcad68e` | 3/3 | OK | colour set + color-hdr: 19/19 | chunk artefacts only |
| 09 | `e53b42b27459` | 3/3 | OK | 19/19 | clean |
| 10 | `48e135c60ddd` | 4/4 | OK | 20/20 | chunk artefacts only |
| 11 | `8f1f532485be` | 12/12 | OK | 22/22 | chunk artefacts only |
| 12 | `3ec252ec9b9b` | 5/5 | OK | 24/24 | clean |
| 13 | `198a5e50255e` | 13/13 (incl. 02's 2) | OK | 27/27 (+ stage-views) | chunk artefacts only |
| 14 | `3bbe8f1681c6` | 8/8 (incl. 04's 1) | OK | 31/31 (+ unit, monitor-storage, monitor-dbus, monitor-gdctl) | suggestions not reviewed (hold) |
| 15 | `7e3ff6041788` | 13/13 (incl. 03's 2) | OK | 37/37 (colour set of 06 + color-lifecycle and its 20 cases) | real alignment slips in 0079's hook calls (hold) |

"Colour set": actor-color-state, color-pipeline, color-state-transform, monitor-color-tests,
monitor-config-tests, edid, color-management, color-management-profile-conflict, native-hdr,
wayland-color-management, wayland-color-representation, plus each separate
wayland-color-management case present at that unit (the exact list is in each DESCRIPTION.md).
In total 86 commit builds (81 commits plus the replayed dependency commits of 13-15), 0
failures. "Chunk artefacts": uncrustify re-indenting isolated chunks against the surrounding
upstream style (the CI job is allow-failure); not applied.

Not run: Mutter's own CI matrix (Fedora image, KVM/native KMS tests, the X11 and Xwayland jobs,
`build-intermediate-commits` on Fedora), and these exact branches on hardware. The hardware
results quoted in 00-ISSUE.md come from Mutter 51 builds of the same changes
(`docs/STATUS.md`). Unit 01 has no test because none exercises `src/frames`.

## Submitting

One command per unit, from this directory:

    ./submit.sh 01 --link mr          # standalone units 01-04
    ./submit.sh 06 --link https://gitlab.gnome.org/GNOME/mutter/-/issues/<N>
    ./submit.sh 05 --link mr --issue https://gitlab.gnome.org/GNOME/mutter/-/issues/<N>
    ./submit.sh all --link mr         # 01-04, stops at the first unit not marked ready
    ./submit.sh 01 --link mr --dry-run

Descriptions of units 05-15 point at the design-discussion issue: `--issue <URL>` fills it in
(an issue URL given to `--link` is used automatically); the script refuses without one.

It clones upstream into `~/.cache/upstream-submit/` (override with `UPSTREAM_SUBMIT_DIR`), puts
the unit and any unmerged units below it on a fresh branch of current `main` with
`git am --signoff`, stops with a clear message if they no longer apply, creates Paul's fork if
missing, pushes `hdr-NN-slug` and opens (or, on a rerun, updates) the MR with DESCRIPTION.md.
A unit marked blocked or hold is only submitted when asked for by number, with a warning.

Before the first run: put a personal access token with `api` and `write_repository` in
`~/.config/upstream/gitlab.gnome.org.token` (mode 600), open the issue from 00-ISSUE.md, and read
the descriptions; they are in Paul's voice and end with the AI-assistance statement, which is
his to make. Units 05-12 also need a libdisplay-info release with units 02-06 (see
`../libdisplay-info/README.md`) before Mutter's CI can build them.

`submit.sh` was tested with `--dry-run` (refusal without `--link`, `--link mr` refusal for a
stacked unit, `all`, and stacked unit 07 with an issue URL: the resulting tree equals the
verified branch and every commit has one `Signed-off-by: Paul Junod`). The real fork, push and
MR path has not been run.
