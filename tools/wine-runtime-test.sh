#!/bin/sh
# Run the Wine DisplayMonitor and display-configuration conformance tests
# with WineHQ wine-stable 11.0 and candidate modules overlaid, in a
# disposable Ubuntu 24.04 container (root). No GPU, display or host mounts
# besides MODULES are needed; Xvfb provides the X display.
#
# Usage: wine-runtime-test.sh MODULES_DIR
#   MODULES_DIR holds the candidate build's win32u.so, winex11.so,
#   winewayland.so, win32u.dll, winex11.drv, winewayland.drv, user32.dll,
#   setupapi.dll, cfgmgr32.dll, windows.devices.enumeration.dll,
#   windows.devices.display.dll and the windows.devices.display_test.exe and
#   user32_test.exe test binaries. Replace the whole GDI driver set together:
#   the DisplayMonitor work changes the driver ABI.
# Optional: HTTPS_PROXY / CA_BUNDLE as in container-setup.sh.
set -eu
mods=$(realpath "$1")
export DEBIAN_FRONTEND=noninteractive
if [ -n "${HTTPS_PROXY:-}" ]; then
    printf 'Acquire::https::Proxy "%s";\n' "$HTTPS_PROXY" > /etc/apt/apt.conf.d/90proxy
    [ -n "${CA_BUNDLE:-}" ] && printf 'Acquire::https::CaInfo "%s";\n' "$CA_BUNDLE" >> /etc/apt/apt.conf.d/90proxy
fi
if ! [ -x /opt/wine-stable/bin/wine ]; then
    sed -i 's#http://#https://#g' /etc/apt/sources.list.d/ubuntu.sources
    apt-get update -q >/dev/null
    apt-get install -y -q --no-install-recommends ca-certificates curl gnupg xvfb xauth >/dev/null
    mkdir -p /etc/apt/keyrings
    curl -fsSL ${CA_BUNDLE:+--cacert "$CA_BUNDLE"} https://dl.winehq.org/wine-builds/winehq.key -o /etc/apt/keyrings/winehq-archive.key
    curl -fsSL ${CA_BUNDLE:+--cacert "$CA_BUNDLE"} https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources -o /etc/apt/sources.list.d/winehq-noble.sources
    dpkg --add-architecture i386
    apt-get update -q >/dev/null
    apt-get install -y -q --install-recommends wine-stable >/dev/null
fi
W=/opt/wine-stable/lib/wine
for f in win32u.so winex11.so winewayland.so; do cp "$mods/$f" "$W/x86_64-unix/$f"; done
for f in win32u.dll winex11.drv winewayland.drv user32.dll setupapi.dll cfgmgr32.dll \
         windows.devices.enumeration.dll windows.devices.display.dll; do
    cp "$mods/$f" "$W/x86_64-windows/$f"
done
id tester >/dev/null 2>&1 || useradd -m tester
rm -rf /home/tester/pfx /home/tester/t
mkdir -p /home/tester/t
cp "$mods/windows.devices.display_test.exe" "$mods/user32_test.exe" /home/tester/t/
chown -R tester /home/tester
cat > /home/tester/go.sh <<'IN'
#!/bin/sh
set -u
# WINEDLLOVERRIDES keeps wineboot from waiting on Mono/Gecko installers.
export WINEDLLOVERRIDES="mscoree,mshtml=" WINEPREFIX=$HOME/pfx WINEDEBUG=-all WINEARCH=win64 PATH=/opt/wine-stable/bin:$PATH
xpid=
cleanup() {
    rc=$?
    trap - EXIT HUP INT TERM
    wineserver -k || printf 'Wine cleanup failed\n' >&2
    if [ -n "$xpid" ]; then
        kill "$xpid" 2>/dev/null || :
        wait "$xpid" 2>/dev/null || :
    fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
Xvfb :91 -screen 0 1920x1080x24 >/dev/null 2>&1 & xpid=$!
export DISPLAY=:91
sleep 1 || exit $?
cd "$HOME/t" || exit $?
init=0
timeout 300 wineboot --init > wineboot.log 2>&1 || init=$?
echo "wineboot exit=$init"
[ "$init" -eq 0 ] || exit "$init"
status=0
dm=0
timeout 300 wine windows.devices.display_test.exe displaymonitor > dm.log 2>&1 || dm=$?
echo "displaymonitor exit=$dm"; tail -1 dm.log
[ "$dm" -eq 0 ] || status=$dm
dc=0
timeout 300 wine user32_test.exe displayconfig > dc.log 2>&1 || dc=$?
echo "displayconfig exit=$dc"; tail -1 dc.log
if [ "$status" -eq 0 ]; then status=$dc; fi
exit "$status"
IN
chmod +x /home/tester/go.sh
su tester -c /home/tester/go.sh
