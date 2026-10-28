# Draft proposal: an explicit optional-camera manifest setting

**Preparation hold:** contributor choice and a minimal manifest test are
still needed. This is a possible plugin feature, not a proven Expo defect.

A downstream app uses `expo-camera` for optional scanning and also works on
devices without a camera. It carries a config plugin that adds or updates
`android.hardware.camera` with `android:required="false"`.

The camera plugin in Expo
[`b79c79b3ac116d9224204e2d0998efd2e57c339c`](https://github.com/expo/expo/blob/b79c79b3ac116d9224204e2d0998efd2e57c339c/packages/expo-camera/plugin/src/withCamera.ts)
does not currently expose a `uses-feature` setting. Would a documented
option for an optional camera fit the plugin, or should applications keep
this as their own manifest policy?

A concrete proposal would need tests for a new feature entry, an existing
entry, preservation of unrelated features, repeated prebuilds, and an app
that intentionally requires camera hardware. It also needs the merged
manifest from the affected app; permissions alone do not establish what
the final hardware requirements are.

Prepared with AI coding assistants (OpenAI Codex; earlier inventory work
with Anthropic Claude through Claude Code). Human review and editing are
still pending.
