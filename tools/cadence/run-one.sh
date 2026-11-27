#!/bin/sh
# Run on the ROG as the session user: one player run with a flip trace.
# usage: run-one.sh LABEL SECONDS PLAYER_ARGV...
set -u
cd "$(dirname "$0")/.."
LABEL=$1; SECS=$2; shift 2
OUT=runs/$LABEL
[ -e "$OUT" ] && { echo "exists: $OUT"; exit 2; }
export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
sudo -n python3 tools/presentation_cadence.py capture "$OUT" --seconds $((SECS + 6)) > /dev/null 2>runs/.capture-$LABEL.err &
CAP=$!
sleep 2
START=$(date -u +%Y-%m-%dT%H:%M:%S)
WAYLAND_DEBUG=1 timeout -s INT $((SECS + 10)) "$@" > /dev/null 2> runs/.wl-$LABEL.log
RC=$?
wait $CAP
sudo -n chown -R "$(id -u):$(id -g)" "$OUT"
mv runs/.wl-$LABEL.log "$OUT/wayland-debug.log"; mv runs/.capture-$LABEL.err "$OUT/capture.err"
journalctl --user -b --since "$START" -o short-monotonic --no-pager 2>/dev/null | grep -i -E "page flip|atomic|drmModeAtomic" > "$OUT/journal-flip.txt"
journalctl -b --since "$START" --no-pager 2>/dev/null | grep -i -E "page flip|drmModeAtomic" >> "$OUT/journal-flip.txt"
printf '{"label":"%s","seconds":%s,"player_rc":%s,"argv":"%s"}\n' "$LABEL" "$SECS" "$RC" "$*" > "$OUT/run.json"
echo "$LABEL rc=$RC flips=$(grep -c intel_crtc_flip_done "$OUT/trace.txt") pageflip_errors=$(grep -c . "$OUT/journal-flip.txt")"
