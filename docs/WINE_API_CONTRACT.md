# Wine API contract — separate module resolution from function support

**Status:** reviewed and executed; Wine 11.0 export absence confirmed · **Written:** 2026-10-09 UTC.

Companion to [the Dolby activation probe](DOLBY_ACTIVATION_PROBE.md): this
diagnostic answers whether stock Wine resolves the one API-set import that
blocked that experiment. Read [status](STATUS.md) for the wider display
acceptance boundary. Its [source](../probes/wine_api_contract/probe.cpp) loads
no OEM DLL, calls no discovered export and changes no live display state.

## The exact contract and what a result proves

The executable accepts no arguments. It loads the fixed name
`api-ms-win-core-file-fromapp-l1-1-0.dll` with
`LoadLibraryExW(..., LOAD_LIBRARY_SEARCH_SYSTEM32)`, resolves the exact named
export `CreateFileFromAppW` with `GetProcAddress`, and releases the module.
There is no arbitrary DLL path, fallback search, registration, function-pointer
cast, function invocation, package identity override or compatibility shim.

Read-only inspection established that this is the OEM processor's sole import
from that API-set. Wine 9.0 lacks the mapping and the preceding activation
experiment stopped during DLL loading. Upstream Wine 11.0 maps this API-set to
`kernelbase.dll`, but its export specification does not include
`CreateFileFromAppW`. These are source observations, not a new runtime receipt:
[Wine 9.0 schema](https://raw.githubusercontent.com/wine-mirror/wine/wine-9.0/dlls/apisetschema/apisetschema.spec),
[Wine 11.0 schema](https://raw.githubusercontent.com/wine-mirror/wine/wine-11.0/dlls/apisetschema/apisetschema.spec),
[Wine 11.0 exports](https://raw.githubusercontent.com/wine-mirror/wine/wine-11.0/dlls/kernelbase/kernelbase.spec).

**Acceptance for this diagnostic:** Record the module-load and export-resolution
results separately on the pinned runtime. A non-null address proves an export
exists; it does not prove the export is callable, implemented, policy-correct
or used by the OEM processor. A missing export identifies the next contract
to implement or investigate. Neither outcome qualifies Dolby activation,
processing, metadata, display management or playback.

Microsoft specifies [UWP security semantics for CreateFileFromAppW](https://learn.microsoft.com/en-us/windows/win32/api/fileapifromapp/nf-fileapifromapp-createfilefromappw).
Forwarding it to ordinary `CreateFileW` would require its own compatibility
design and evidence. This batch does not make that substitution.

## Compiler receipt and official package pins

Before editing C++, a new agent-owned `rog-wine-api-contract` container was
created from the cached image below. A minimal C hello executable compiled
with `-std=c11 -Wall -Wextra -Werror`; `objdump -f` identified `pei-x86-64`.
It was not run. The diagnostic then compiled with C++17, optimization,
warnings-as-errors, static runtime libraries and no PE timestamp using the
[build script](../probes/wine_api_contract/build.sh). Its only import modules
are `KERNEL32.dll` and `msvcrt.dll`. Compilation completed with exit 0 and no
compiler diagnostics. No runtime was executed before review; the subsequent receipt is below.

| Dependency | Exact prepared environment |
|---|---|
| Base image | `ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3` |
| Compiler package | `g++-mingw-w64-x86-64-posix` `13.2.0-6ubuntu1+26.1` |
| Header package | `mingw-w64-x86-64-dev` `11.0.1-3build1` |
| Binutils package | `binutils-mingw-w64-x86-64` `2.41.90.20240122-1ubuntu1+11.4` |
| WineHQ packages | `winehq-stable`, `wine-stable`, `wine-stable-amd64`, `wine-stable-i386:i386`, all `11.0.0.0~noble-1` |
| Package source | Official signed WineHQ Ubuntu `noble/main` repository |
| Runtime loader | `/opt/wine-stable/bin/wine`, verified from installed package inventory |

WineHQ's package dependency chain includes i386 packages even though this
diagnostic is x64. Those dependencies were installed normally inside the
disposable container; none were bypassed. Ubuntu supplies the distro library
dependencies. Their complete installed manifest remains inside the container
at `/probe/package-manifest.txt`; its SHA-256 is
`f3482c31556121cfdbe91c0c4d8abb62a672baba1bf02b269d1a64b2e3c3211d`.
The script pins the principal package versions; the base image and principal
pins alone do not freeze future transitive Ubuntu dependency versions.

The fetched signing key contains primary fingerprint
`D43F640145369C51D786DDEA76F1A20FF987672F` and subkey fingerprint
`9CDD4BB7ED8C37C95FFF34F1DDB25B3BE89767D6`. APT verified repository signatures.
The setup script also pins the fetched key and repository descriptor bytes.

| Artifact | SHA-256 |
|---|---|
| WineHQ key file | `d965d646defe94b3dfba6d5b4406900ac6c81065428bf9d9303ad7a72ee8d1b8` |
| WineHQ Noble source descriptor | `b5962429ece1f831c9f713c13f9f0d26bb367117ef56706648ff385f004779fb` |
| `winehq-stable` package | `86c6eb4d27028630a9d4db64f9d2e5c3d97b5b6eff71039f61f1bc20d887b4b9` |
| `wine-stable` package | `04e7b4b995262c734019099d93277d8f219f7d180ebb65b5ccb3df7f97be1078` |
| `wine-stable-amd64` package | `6cb835e2171b5572b17f1c06729735c2c7e40178239d7fa6c29ef14bd9b40d16` |
| `wine-stable-i386` package | `b322b50f9e8bd59687840d9a7bad10d70b12ef9bdb873298e858ff93a6205e56` |
| Diagnostic `probe.cpp` | `fc13b56f603380bbb06285ee27b8ace3f2333ddb9ab2e74e69223ad9f9b6cdd0` |
| Diagnostic `build.sh` | `a0afc8c06db9e6f30ef39144172a73e05e9c12ea9ba8092ee47839a5de51d452` |
| Diagnostic executable | `86441da0ac1526aac683b071740abb9cafe632567065c5ad36abf30950992d98` |

The package hashes come from authenticated APT metadata; executable/source
hashes describe `/probe/build/wine-api-contract.exe` and
`/probe/probes/wine_api_contract/` in this own container.

## Reproduce preparation without executing Wine

The [setup script](../probes/wine_api_contract/setup-container.sh) creates only
a new container with the fixed name and ownership label. Docker rejects a
name collision; it never reuses or deletes an existing container. It installs
the pinned compiler/Wine packages, compiles hello without running it, records
the package manifest, disconnects its setup bridge and asserts zero network
attachments. Network/package/signature failures stop preparation without a
fallback version or shim. Review such a blocker instead of bypassing it.

From the own repository clone on the machine with Docker:

```bash
set -eu
sh probes/wine_api_contract/setup-container.sh  # New disposable container only.
COPYFILE_DISABLE=1 tar --no-xattrs -cf - probes/wine_api_contract | \
  docker exec -i rog-wine-api-contract tar -xf - -C /probe
docker exec rog-wine-api-contract sh \
  /probe/probes/wine_api_contract/build.sh /probe/build  # Compile only.
```

The prepared container has no host mounts, credentials, Docker socket, GPU
devices, display sockets or privileged mode. Only this new container was
changed; the preceding OEM probe container was not restarted or modified.
Its network was disconnected after package installation, before any Wine
execution. The completed container was removed after recovering the private
receipts below. No OEM binary/profile belongs in this diagnostic environment.

## One bounded run after final adversarial review

The following is the reviewed execution recipe. Run the whole
block in its own shell only after the final review and required fast lane.
It requires the prepared container to be running with zero network
attachments, rejects changed isolation, creates private output/prefix
directories, and invokes Wine once as container UID/GID 65534. It does not
reattach a network or create host/display mounts. Do not alter the container
concurrently or remove a failed assertion to make the run proceed.

```bash
set -eu
probe_container=rog-wine-api-contract
[ "$(docker inspect -f '{{.Name}}' "$probe_container")" = /rog-wine-api-contract ]
[ "$(docker inspect -f '{{index .Config.Labels "purpose"}}' "$probe_container")" = rog-wine-api-contract ]
[ "$(docker inspect -f '{{.State.Running}}' "$probe_container")" = true ]
[ "$(docker inspect -f '{{len .Mounts}}' "$probe_container")" = 0 ]
[ "$(docker inspect -f '{{.HostConfig.Privileged}}' "$probe_container")" = false ]
[ "$(docker inspect -f '{{len .HostConfig.Devices}}' "$probe_container")" = 0 ]
[ "$(docker inspect -f '{{len .HostConfig.DeviceRequests}}' "$probe_container")" = 0 ]
[ "$(docker inspect -f '{{len .HostConfig.CapAdd}}' "$probe_container")" = 0 ]
[ "$(docker inspect -f '{{len .NetworkSettings.Networks}}' "$probe_container")" = 0 ]
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
  timeout --signal=TERM --kill-after=5s 30s /opt/wine-stable/bin/wine \
    /probe/build/wine-api-contract.exe \
    >/probe/results/api-contract.jsonl 2>/probe/results/wine.stderr
'; then
  probe_exit=0
else
  probe_exit=$?
fi
printf 'probe_exit=%s\n' "$probe_exit"
exit "$probe_exit"  # EXIT trap stops remaining Wine processes too.
```

Root is used only inside the disposable container to prepare directory
ownership. Wine runs unprivileged; results/prefix are mode 0700 and files
are created under `umask 077`. The EXIT trap stops this container on success
and runtime error. Recover private results using `docker cp`, including after
it stops. Keep stderr private: runtime diagnostics can include paths. Publish
only sanitized output, artifact/runtime pins and the supervisor exit status.

The 30-second deadline includes first Wine-prefix setup. An absent `scope`
event does not identify a diagnostic API failure. Timeout exit 124 or a
forced-kill exit 137 identifies the supervisor boundary, not a Win32 error.

Remove only this owned container after saving results:

```bash
docker rm -f rog-wine-api-contract  # Removes packages, prefix and private logs.
```

## Runtime receipt — API-set resolves, required export does not

After adversarial review and the affected fast lane, the complete recipe ran
on the pinned stock Wine 11.0 package set. Source/executable hashes were
rechecked; zero network attachments and zero mounts were verified. No OEM
component or discovered function was invoked.

| Call | Result |
|---|---|
| `LoadLibraryExW` for the fixed API-set | Success; Win32 `0` / `0x00000000` |
| `GetProcAddress(CreateFileFromAppW)` | Failure; Win32 `127` (`ERROR_PROC_NOT_FOUND`) / `0x8007007F` |
| `FreeLibrary` | Success; Win32 `0` / `0x00000000` |

The executable returned `3`, its documented missing-export outcome, before
the supervisor deadline. Module mapping has progressed beyond Wine 9.0's
missing-module result, but the required function is still absent. This
runtime confirms the pinned source finding; a stock runtime upgrade alone
does not supply that contract. It says nothing about other activation or
processing prerequisites.

The next compatibility implementation must supply and validate the actual
file API contract in Wine, including its security semantics; an export alias
is not evidence of equivalence. The independent native reference-tool route
remains in [the quality plan](DOLBY_VISION_AND_QUALITY.md#41-use-an-official-linux-reference-for-display-management-validation).
Raw logs, executable and package manifest were retained privately with mode
`0600`. The agent-owned container, prefix and package installation were
removed. No host package or display configuration changed.

## Read the JSONL and exit code

Schema 1 emits `scope`, flushed `begin`/`result` pairs and `summary` objects.
Each API result records success, its exact numeric Win32 error and a derived
HRESULT. Successful results record zero; a failing API that supplies no error
retains Win32 zero and derives `E_FAIL`. `export_exists` is `null` when lookup
was not attempted, `false` on lookup failure, or `true` for a non-null address.
The summary always records `export_called: false`,
`behavior_qualified: false` and `full_dv_qualified: false`.

| Exit | Meaning |
|---|---|
| 0 | Module loaded, named export exists and module release succeeded; behavior remains untested |
| 1 | Unexpected arguments; no module load attempted |
| 2 | System32-only API-set load failed; export existence is unknown |
| 3 | Module loaded but named-export lookup failed; inspect its exact Win32 code |
| 4 | Export found but module release failed |

If lookup and release both fail, exit 3 preserves the earlier lookup boundary
and the release error remains separately recorded. An unmatched final `begin`
can locate a stalled API; a crash/loader failure may instead require private
stderr and the external exit status. No result authorizes a DLL shim or means
that Wine/full Dolby processing is impossible.

[Microsoft GetProcAddress](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress)
defines named-export lookup and extended error retrieval;
[LoadLibraryExW](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryexw)
defines system-directory search.
[The official Wine 11.0 release](https://list.winehq.org/hyperkitty/list/wine-releases%40list.winehq.org/message/UL6L2GJ55VYUJ5KUMBZ3TZSXRFJ52QG6/)
identifies the stable source release and its single `wine` loader. The prepared
packages were obtained from the official WineHQ Noble repository named in the
setup script, rather than from a third-party runtime bundle.
