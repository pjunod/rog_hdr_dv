#!/bin/sh
# Reproduce the Android lint failure without an Expo app or a device.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
gradle_bin=${GRADLE_BIN:-gradle}
command -v "$gradle_bin" >/dev/null || { echo 'Set GRADLE_BIN to Gradle 9.7.1.' >&2; exit 1; }
[ -n "${ANDROID_HOME:-}" ] || { echo 'Set ANDROID_HOME to an SDK with platform 36.' >&2; exit 1; }
root=${UPSTREAM_WORK_ROOT:-$HOME/.cache/upstream-prep}
mkdir -p "$root"
work=$(mktemp -d "$root/expo-splash-lint.XXXXXX")
cp -R "$here/repro" "$work/project"
mkdir "$work/tmp"
printf 'Retained reproduction: %s\n' "$work"
if "$gradle_bin" --no-daemon -Djava.io.tmpdir="$work/tmp" -p "$work/project" lintDebug > "$work/before.txt" 2>&1; then
    echo 'Unexpected baseline pass: inspect before.txt; no failure reproduced.' >&2
    exit 1
fi
grep -F 'android:windowSplashScreenBehavior requires API level 33 (current min is 24) [NewApi]' "$work/before.txt" >/dev/null || {
    echo 'Baseline failed for another reason; inspect before.txt.' >&2
    exit 1
}
python3 - "$work/project/src/main/res/values/styles.xml" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
path.write_text(path.read_text().replace(
    '<resources>', '<resources xmlns:tools="http://schemas.android.com/tools">'
).replace(
    'name="android:windowSplashScreenBehavior"',
    'name="android:windowSplashScreenBehavior" tools:targetApi="33"'
))
PY
if ! "$gradle_bin" --no-daemon -Djava.io.tmpdir="$work/tmp" -p "$work/project" lintDebug > "$work/after.txt" 2>&1; then
    echo 'Annotated resource still fails: inspect after.txt.' >&2
    exit 1
fi
printf 'PASS: baseline NewApi failure; annotation-only lint success. Logs: %s\n' "$work"
