# Dolby activation probe — find the first compatibility boundary

**Status:** cross-compiled and probed; Wine API-set load boundary identified ·
**Written:** 2026-10-08.

Companion to [Dolby Vision and quality](DOLBY_VISION_AND_QUALITY.md): this
document answers how to inspect the recovered Windows processor's activation
contract without registering it or changing the live Linux display. Read
[status](STATUS.md) for the full project acceptance boundary. The source is
[probe.cpp](../probes/dolby_activation/probe.cpp); the
[build script](../probes/dolby_activation/build.sh) only compiles it.

## What this executable establishes

The x64 Windows console executable takes one absolute Windows DLL path. It
initializes COM in MTA, WinRT in MTA and Media Foundation with
`MFSTARTUP_NOSOCKET`, loads that exact file, resolves `DllGetActivationFactory`,
requests `DolbyVisionPlugin.RendererEffect`, calls `ActivateInstance`, and
queries `IMFTransform`. Successful calls then permit bounded stream and
unconfigured input/output media-type enumeration.

The recovered manifest advertises P010
(`30313050-0000-0010-8000-00aa00389b71`) and NV12
(`3231564e-0000-0010-8000-00aa00389b71`), for registered profiles 4, 5, 8 and 9.
Those are source findings; this probe does not assert support based on them
and does not guess a transform CLSID from `DllGetClassObject`.

**Limits:** It does not register a COM server, modify a licence, bypass DRM,
spoof hardware, install OEM profiles, create a D3D device, negotiate types,
feed frames/metadata, invoke processing, or qualify playback. The DLL itself
runs native code during loading/activation; execute only in the isolated
container or another explicitly approved disposable environment. Factory
activation and an `IMFTransform` interface do not establish metadata transport,
display management, creative trims, panel configuration or output semantics.
Every summary therefore says `full_dv_qualified: false`.

## Compiler receipt and disposable environment

The compiler loop was established before writing the probe by compiling a
minimal C hello executable with `-std=c11 -Wall -Wextra -Werror`, then inspecting
its `pei-x86-64` header. That executable was not run. The probe was subsequently
compiled with the script's C++17, optimization, warnings-as-errors and static
runtime flags. `objdump -p` shows only `KERNEL32.dll`, `msvcrt.dll` and
`ole32.dll` imports; WinRT/MF entry points are resolved at runtime so a missing
export can produce a step receipt. A failure in the OS loader before `wmain`
still requires the external supervisor's exit/stderr receipt.

| Dependency | Exact compile environment |
|---|---|
| Base image | `ubuntu:24.04`, digest `sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3` |
| Compiler package | `g++-mingw-w64-x86-64-posix` `13.2.0-6ubuntu1+26.1` |
| Header package | `mingw-w64-x86-64-dev` `11.0.1-3build1` |
| Binutils package | `binutils-mingw-w64-x86-64` `2.41.90.20240122-1ubuntu1+11.4` |
| Wine packages | `wine64` and `libwine:amd64` `9.0~repack-4build3` |

The final compile completed with exit 0 and no compiler diagnostics. The
container's source, build script and executable hashes were recorded:

| Artifact | SHA-256 |
|---|---|
| `probe.cpp` | `69208536e1551c733065e20bf37b5a27ef7ce7d4123407bb1d73719e14775277` |
| `build.sh` | `23f9e97c11d66cebff2e38c0f318f96f5fce5791ca7db785877cdbc8da004c02` |
| `dolby-activation-probe.exe` | `06975793c115c3bceab8acecb33c791355d719a98ab078feb2a0e5fdbe78e8cd` |

The receipt describes the container build at `/probe/build/`; it is
compiler evidence; the separate runtime receipt follows below.

Only the agent-owned `rog-dv-agent-probe` container was created. It has no
host filesystem mounts, Docker socket, credentials, GPU devices, display
sockets, or privileged mode. Compiler/Wine packages were installed inside
that container from Ubuntu repositories; no host packages were installed.
Source arrived by a tar stream containing this probe directory only. The
exact recovered DLL was later copied privately for the bounded experiment
below. An installed Wine package alone is not compatibility evidence.

Reproduce compilation after installing the listed tools in a disposable
environment:

```bash
sh probes/dolby_activation/build.sh build/dolby-activation  # Compile only.
x86_64-w64-mingw32-objdump -p build/dolby-activation/dolby-activation-probe.exe
sha256sum build/dolby-activation/dolby-activation-probe.exe  # Bind the receipt.
```

The build does not distribute OEM binaries or profiles. Keep generated
executables and runtime logs in ignored storage. The executable has its PE
timestamp disabled to avoid a changing timestamp in compiler receipts.

## Run after review — keep the execution private and bounded

The commands below document the reviewed experiment. For a new execution,
first recheck the source and compilation, then supply the DLL from the
private recovered inventory. Copy the exact approved DLL into
`/private/oem/DolbyVisionPlugin.dll` inside this own container, without mounting
its host directory. Record its SHA-256 and executable SHA-256 separately.
The recovered source hash is
`ecb3d9024e53defcdfaa0ae6bd3fdc87165f2a845efc71d83456d59add4d9936`.
Any adjacent OEM dependencies need their own reviewed inventory; a load error
does not authorize installing them silently.

The probe's default search includes only the supplied DLL's directory and
Windows system32 for dependencies. It never adds the current directory or
registers the package. For the first experiment, keep network and graphics
access absent, and use a prefix inside the container:

```bash
# Run on the laptop only after review. No X11/Wayland/GPU access is supplied.
set -eu
probe_container=rog-dv-agent-probe
# Fail before native code if the owned container or isolation has changed.
[ "$(docker inspect -f '{{.Name}}' "$probe_container")" = /rog-dv-agent-probe ]
[ "$(docker inspect -f '{{index .Config.Labels "purpose"}}' "$probe_container")" = rog-dv-activation-probe ]
[ "$(docker inspect -f '{{.State.Running}}' "$probe_container")" = true ]
[ "$(docker inspect -f '{{len .Mounts}}' "$probe_container")" = 0 ]
[ "$(docker inspect -f '{{.HostConfig.Privileged}}' "$probe_container")" = false ]
[ "$(docker inspect -f '{{len .HostConfig.Devices}}' "$probe_container")" = 0 ]
[ "$(docker inspect -f '{{len .HostConfig.DeviceRequests}}' "$probe_container")" = 0 ]
[ "$(docker inspect -f '{{len .HostConfig.CapAdd}}' "$probe_container")" = 0 ]
# Require exactly the setup bridge; an unexpected attachment stops this recipe.
[ "$(docker inspect -f '{{len .NetworkSettings.Networks}}' "$probe_container")" = 1 ]
[ -n "$(docker inspect -f '{{with index .NetworkSettings.Networks "bridge"}}{{.EndpointID}}{{end}}' "$probe_container")" ]
docker network disconnect bridge "$probe_container"  # Must succeed.
[ "$(docker inspect -f '{{len .NetworkSettings.Networks}}' "$probe_container")" = 0 ]
# Stop the entire owned container on every subsequent exit, including errors.
trap 'docker stop "$probe_container" >/dev/null' EXIT
docker exec "$probe_container" install -d -m 0700 -o 65534 -g 65534 \
  /probe/results /probe/wine-prefix
[ "$(docker inspect -f '{{len .NetworkSettings.Networks}}' "$probe_container")" = 0 ]
probe_exit=0
if docker exec --user 65534:65534 "$probe_container" sh -c '
  set -eu
  umask 077
  export WINEPREFIX=/probe/wine-prefix WINEARCH=win64
  unset DISPLAY WAYLAND_DISPLAY
  timeout --signal=TERM --kill-after=5s 30s /usr/lib/wine/wine64 \
    /probe/build/dolby-activation-probe.exe \
    "Z:\\private\\oem\\DolbyVisionPlugin.dll" \
    >/probe/results/activation.jsonl 2>/probe/results/wine.stderr
'; then
  probe_exit=0
else
  probe_exit=$?
fi
printf 'probe_exit=%s\n' "$probe_exit"  # Preserve supervisor/runtime exit status.
# Copy private results out with docker cp, including after the EXIT trap stops it.
exit "$probe_exit"
```

Run the complete block in its own shell. Any failed assertion, inspection or
disconnect terminates setup before the DLL is invoked; the recipe also rejects
unexpected additional networks rather than disconnecting them and continuing.
After a failed or already-completed disconnect, inspect the state and prepare
a reviewed replacement recipe instead of deleting the assertions. No other
operator should alter the container's network while this block runs.

Wine and the DLL run as container UID/GID 65534, with private writable result
and prefix directories and files created under `umask 077`. The executable
and supplied DLL must be readable by that user. Root is used only inside the
container to prepare those directories; the recipe does not install anything
on the host or run the DLL as host/container root. The exit trap stops this
owned container to terminate lingering Wine processes; `docker cp` can recover
its private results after it stops.

The supervisor bounds hangs/crashes in DLL entry points; stream/type counts
alone cannot bound a foreign function's duration. Exit 124 from GNU `timeout`
means its deadline expired; a forced-kill case can report 137. Wine startup
may consume the deadline before the probe begins, which must be distinguished
from an activation stall using the JSONL trace. Do not interpret absent JSON
as an activation HRESULT. Keep stderr private: Wine/DLL diagnostics can
contain paths and environment details the probe itself omits. Publish only
reviewed, sanitized JSONL plus hashes, versions, command shape and exit status.

Remove only this own container when finished:

```bash
docker rm -f rog-dv-agent-probe  # Deletes its compiler, prefix and OEM copy.
```

## Runtime receipt — a missing Wine API-set stops DLL loading

On 2026-10-09 UTC, after adversarial review and the 45-test fast lane, the
exact compiled executable and recovered DLL hashes above were checked and
the complete isolated recipe was executed. No network attachments, host
mounts, display sockets or GPU access were provided; Wine ran as UID/GID
65534. The supervisor returned exit 2 before its deadline. The exit trap
stopped the container; private results were recovered with mode `0600`.
The agent-owned container was then removed, deleting its Wine prefix and OEM
copy. The compiled executable was retained with the private receipts.

| Step | Result |
|---|---|
| COM MTA initialization | `S_OK` |
| WinRT MTA initialization | `S_FALSE` (successful existing initialization) |
| Media Foundation startup | `S_OK` |
| Exact OEM DLL load | `0x8007007E` (`ERROR_MOD_NOT_FOUND`) |
| Media Foundation shutdown | `S_OK` |

Private loader diagnostics identify the missing import as
`api-ms-win-core-file-fromapp-l1-1-0.dll`. This is a concrete Wine 9.0 API-set
compatibility boundary. The class factory and `ActivateInstance` were never
reached. It does not establish that a newer Wine can activate the processor,
nor that rendering, licensing, panel configuration or full DV are supported.

The next experiment must establish which imported functions are needed and
whether an official newer Wine implements this contract, then repeat bounded
activation in a fresh isolated environment. Do not substitute a guessed DLL
or claim processor activation based on Media Foundation startup alone. Raw
Wine logs, OEM files and the runtime prefix remain outside the repository.

## Read the JSONL — an HRESULT belongs to one call

The probe writes one JSON object per line to stdout and flushes before each
external call. It never prints the DLL argument, host name, user directory,
file contents, runtime class metadata or arbitrary string attributes.
Schema 1 records:

| Event | Meaning |
|---|---|
| `scope` | Fixed runtime class, bounded discovery scope, no DV qualification |
| `begin` | Next call is about to run; a final unmatched line locates a possible stall |
| `result` | Named step, hexadecimal HRESULT, optional known HRESULT name, disposition |
| `stream_count` | Reported input/output stream counts before allocation |
| `media_type` | Direction, stream ID, index, major GUID and subtype GUID only |
| `summary` | Discovery reached the end, cleanup outcome, no DV qualification |

Exit 0 means bounded unconfigured enumeration, MF shutdown and plugin unload
completed. Interfaces are released before MF shutdown; the plugin remains
loaded until after that shutdown in case pending MF work uses its code.
Exit 2 means this probe stopped at a missing contract/limit or shutdown error.
The first unsuccessful call's `result` is the useful boundary; cleanup may
add later `MFShutdown`/`unload_plugin` results. Unknown HRESULTs retain their
exact value and use `unmapped_hresult`, so a source lookup remains possible.

| Result boundary | Interpretation and next investigation |
|---|---|
| `load_exact_plugin` | DLL or dependency load failed; use private loader diagnostics to distinguish dependency/API/architecture failures. It does not identify the missing dependency by itself. |
| `DllGetActivationFactory_class` | Class factory lookup was rejected in this runtime/package context; it says nothing about other activation routes. |
| `ActivateInstance` | Activation prerequisite failed; inspect that HRESULT and runtime diagnostics before designing a host. |
| `QueryInterface_IMFTransform` / `E_NOINTERFACE` | The activated object does not expose this interface directly; the renderer-effect hosting contract remains to investigate. This does not prove Wine or Dolby processing impossible. |
| Available type / `MF_E_TRANSFORM_TYPE_NOT_SET` | Unconfigured enumeration requires the opposite type first; stop rather than guessing formats, display configuration or a GPU manager. |
| Available type / `E_NOTIMPL` | No enumerated type list is provided for this call; it is not a statement that no supported type exists. |
| Available type / `MF_E_NO_MORE_TYPES` | Normal list termination, including an empty list; not a negotiated or processing capability. |
| `GetStreamIDs` / `E_NOTIMPL` | Microsoft's documented fixed consecutive-ID convention is used, beginning at zero. |
| `stop_stream_limit` / `stop_type_limit` | Bounds were reached: at most 16 streams per direction and 64 returned types per stream. The result is intentionally incomplete. |

Stop at the first missing contract. The executable never retries activation
under a forged identity, silently installs an API implementation, selects an
HDR10 fallback, or changes the live display to make the experiment pass.

## Primary API references

[Microsoft's activation factory contract](https://learn.microsoft.com/en-us/windows/win32/api/activation/nn-activation-iactivationfactory)
defines `DllGetActivationFactory` and `ActivateInstance`.
[RoInitialize](https://learn.microsoft.com/en-us/windows/win32/api/roapi/nf-roapi-roinitialize)
requires balancing successful initialization, including `S_FALSE`, with
`RoUninitialize`.
[MFStartup](https://learn.microsoft.com/en-us/windows/win32/api/mfapi/nf-mfapi-mfstartup)
defines `MFSTARTUP_NOSOCKET` and the matching shutdown requirement.
[LoadLibraryExW](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryexw)
defines the full-path and dependency search flags used here.
[GetStreamIDs](https://learn.microsoft.com/en-us/windows/win32/api/mftransform/nf-mftransform-imftransform-getstreamids)
documents the consecutive-ID fallback.
[GetInputAvailableType](https://learn.microsoft.com/en-us/windows/win32/api/mftransform/nf-mftransform-imftransform-getinputavailabletype)
documents enumeration termination and output-type prerequisites. These are
Windows contracts; they do not assert the installed Wine implements them.
