# Expo — evidence still needed before proposing changes

**Status:** splash fix prepared for a draft PR; optional camera held
· **Checked:** 2026-10-28.

Companion to the [submission ledger](../../docs/UPSTREAM_SUBMISSIONS.md).
This folder preserves the mobile items from Runner and Curator. The
original splash failure was recovered from Curator PR #10 and reproduced
with Android lint. The candidate includes a plugin regression and a
changeset. Full Expo package checks and prebuild/EAS validation remain.

Source checked: Expo `main` at
[`a66d72b9b679ae90b370a97136ad826f6254c2a9`](https://github.com/expo/expo/commit/a66d72b9b679ae90b370a97136ad826f6254c2a9).

| Item | Disposition | Material and next action |
|---|---|---|
| EX-1 | Ready for human review as a **draft PR** | [Splash API candidate](01-splash-api-guard/DESCRIPTION.md). Android lint fails before and passes after; three new Jest cases fail before and pass after. Full package checks/prebuild/EAS remain. |
| EX-2 | Superseded in Expo SDK 58 | Scene lifecycle is generated upstream; the handoff records Expo #46734. No new submission. Confirm compatibility when upgrading the downstream apps. |
| EX-3 (inventory E3) | Hold: optional feature proposal | [Optional camera draft](03-optional-camera/DESCRIPTION.md). Decide whether to request a plugin option, then test manifest merging. |
| E4 | No upstream change | Both apps pin `uuid`, but the inventory supplies no defect or reason for the override. Recover its rationale locally before treating it as an upstream issue. |

The current splash plugin emits `android:windowSplashScreenBehavior` without
`tools:targetApi`. Android lint rejects the generated item with minimum SDK
24. Adding the namespace and API-33 annotation resolves that diagnostic.
The current camera plugin configures permissions and barcode properties;
its source has no `uses-feature` handling.

A read-only GitHub issue search for `windowSplashScreenBehavior` returned
closed issues #44556, #38389 and #39771, and closed PRs #38700 and #23882.
None of those titles establishes the reported API-level problem. This is
a query result, not an exhaustive duplicate review.

No device, simulator, full Expo package build, prebuild or EAS Build was
used. No upstream issue or pull request has been opened. See the compact
[evidence receipt](evidence.json) for exact sources, commands and log hashes.

```bash
sh upstream/expo/submit.sh 01 --dry-run # Apply the unsigned candidate at its base.
sh upstream/expo/submit.sh 01           # Human: open a draft after reviewing it.
GRADLE_BIN=gradle sh upstream/expo/reproduce.sh # Run standalone Android lint A/B.
```

The live helper always opens 01 as a draft. Unit 03 remains held. The lint
reproducer needs Gradle 9.7.1, JDK 21 and `ANDROID_HOME` with SDK platform 36.
It creates an owned directory under `UPSTREAM_WORK_ROOT` (default
`~/.cache/upstream-prep`) and retains both logs. A failure for another reason
does not count as reproducing the API-level bug.

The isolated Jest harness is retained for the narrower test that ran here.
After applying 01 in an owned source checkout, set `EXPO_SOURCE` to it and
`EXPO_TEST_DEPS` to an owned dependency directory outside this repository:

```bash
npm install --prefix "$EXPO_TEST_DEPS" --ignore-scripts --no-audit --no-fund \
  jest@30.2.0 babel-jest@30.2.0 @babel/core@7.29.7 \
  @babel/preset-typescript@7.29.7 @babel/plugin-transform-modules-commonjs@7.29.7
NODE_PATH="$EXPO_TEST_DEPS/node_modules" node upstream/expo/test-harness.cjs "$EXPO_SOURCE"
```

Three passes mean the real styles callback produced the annotation,
preserved attributes, and remained idempotent. This harness mocks only mod
registration. It does not type-check the package, run other Expo tests, or
qualify prebuild and EAS Build.
