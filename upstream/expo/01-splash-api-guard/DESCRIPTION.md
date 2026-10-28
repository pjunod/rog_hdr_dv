# [expo-splash-screen] Mark the splash behavior attribute with its API level

# Why

Android lint rejects the generated splash theme when the app's minimum SDK
is below 33. The plugin places `android:windowSplashScreenBehavior` in the
base resource directory without its API-level annotation.

A minimal Android app reproduces `NewApi` with minimum SDK 24 and compile
SDK 36. A downstream report is [Curator #10](https://github.com/pjunod/curator/pull/10).

# How

Add `tools:targetApi="33"` to the behavior item. Declare the tools namespace
on the resources element. Preserve existing namespaces. This matches the
downstream workaround and changes lint metadata only. It does not change
the splash behavior value or execute code on older devices.

The patch adds a regression for the registered Android styles action and
a patch changeset for `expo-splash-screen`. This is one independent change.

# Test Plan

Base: Expo `a66d72b9b679ae90b370a97136ad826f6254c2a9`.

- Android lint: Gradle 9.7.1, Android Gradle plugin 9.3.3, JDK 21.0.11,
  compile/target SDK 36 and minimum SDK 24. The unannotated resource fails
  `lintDebug` with the API-33 `NewApi` diagnostic. Adding only the tools
  namespace and the item annotation makes the same command pass.
- The three new Jest cases fail on unchanged upstream and pass with the fix.
  They execute the real styles action and check namespace preservation,
  the generated item's annotation and repeated application.
- The focused Jest run uses Jest 30.2.0 and Babel's TypeScript transform in
  an isolated harness on Node 24.22.1. The full monorepo package checks,
  TypeScript type-check, `npx expo prebuild`, and EAS Build have not run.
  Keep this PR as a draft until those checks and human review are complete.

The companion preparation kit includes a minimal runnable Android lint
reproduction and hashed test receipts. No device or simulator was used.

# Screenshots

No UI change.

# Checklist

- [x] Add a package changeset.
- [x] Add a regression that fails before the change.
- [ ] Run full package checks and prebuild/EAS validation.
- [ ] Contributor reviews the code and edits this description.

Prepared with AI coding assistants (OpenAI Codex; earlier downstream work
with Anthropic Claude through Claude Code). Human review is still pending.
