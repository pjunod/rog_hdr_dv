#!/bin/sh
# Run the Mutter colour fast lane headlessly (llvmpipe) against a build tree.
# Must start as root (it drops to TEST_UID for the run) inside a disposable
# container; no session, display or D-Bus variables leak in.
#
# Usage: test-mutter-colour.sh MUTTER_BUILD_DIR [extra meson test names...]
# Runs every mutter:wayland-color-management* invocation (including the
# separate cases) plus the fixed set below.
set -u
build=$(realpath "$1"); shift
uid=${TEST_UID:-1000}
fixed="mutter:actor-color-state mutter:color-hdr mutter:color-pipeline mutter:color-state-transform
mutter:monitor-color-tests mutter:monitor-config-tests mutter:color-management
mutter:color-management-profile-conflict mutter:native-hdr mutter:wayland-color-representation"
wayland=$(cd "$build" && meson test --list 2>/dev/null | grep -o 'mutter:wayland-color-management[^ ]*' | sort -u)
chown -R "$uid:$uid" "$build"
home=$(mktemp -d); chown "$uid" "$home"
exec setpriv --reuid="$uid" --regid="$uid" --clear-groups env -u DISPLAY -u WAYLAND_DISPLAY \
    -u DBUS_SESSION_BUS_ADDRESS -u DBUS_SYSTEM_BUS_ADDRESS -u XDG_RUNTIME_DIR HOME="$home" \
    LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe LP_NUM_THREADS=2 \
    META_DBUS_RUNNER_DISABLE_LOGIND_PASSTHROUGH=1 \
    timeout 3000 meson test -C "$build" --setup mutter:default --no-rebuild --num-processes 1 \
    --timeout-multiplier 2 --print-errorlogs $fixed $wayland "$@"
