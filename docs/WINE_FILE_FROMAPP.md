# Wine file API — desktop compatibility for processor investigation

**State:** source candidate compiled; adversarial review and runtime checks
pending. Companion to the historical [API diagnostic](WINE_API_CONTRACT.md).
This implements a missing Wine function; it does not qualify Dolby activation
or full Dolby Vision.

## Demonstrated cause and chosen correction

Stock Wine 11.0 resolves `api-ms-win-core-file-fromapp-l1-1-0.dll` but lacks its
`CreateFileFromAppW` export. The isolated diagnostic observed that failure.
The new [Wine patch](../patches/wine/0001-kernelbase-implement-CreateFileFromAppW.patch)
adds the normal `kernelbase` entry point and export. Its seven arguments are
passed unchanged to `CreateFileW`; it preserves the returned handle and
last-error behaviour. No replacement API-set DLL is introduced.

[Microsoft's API contract](https://learn.microsoft.com/en-us/windows/win32/api/fileapifromapp/nf-fileapifromapp-createfilefromappw)
includes UWP security semantics. Wine's existing
[token implementation](https://raw.githubusercontent.com/wine-mirror/wine/wine-11.0/dlls/ntdll/unix/security.c)
does not provide the complete Windows AppContainer boundary. The candidate is
therefore scoped to Wine's current desktop process model. It does not claim
AppContainer access brokerage, user-grant enforcement or native Windows
behavioural equivalence. Wine's existing
[CreateFileMappingFromApp implementation](https://raw.githubusercontent.com/wine-mirror/wine/wine-11.0/dlls/kernelbase/sync.c)
also delegates to the corresponding ordinary file-mapping API; this is a
compatibility implementation within that architecture.

## Source and compiler evidence

[sources.json](../sources.json) records the upstream tag, base and candidate
source trees. The source-only candidate is not installed on the host.

| Identity | Value |
|---|---|
| Base | Wine `wine-11.0`, `db11d0fe6a169c457e23d007e20404643d067aa8` |
| Candidate | `68c5cce867c8c5dc7e318eefc4c13f832d0471fa` |
| Candidate tree | `387cfcb18f0870100227fe059d804f2c16249c89` |
| Build | Native Linux amd64, GCC 13.3.0 and MinGW GCC 13 win32 |
| Configure | `--enable-win64 --enable-werror --without-x --without-wayland` |
| Targets | `make -j1 dlls/kernelbase/all dlls/kernelbase/tests/all` |

The unchanged baseline compiled before source edits. The exact committed
candidate then compiled with warnings as errors. The owned container runs with
one CPU, 2 GiB memory, no extra swap, no host mounts, no GPU and no privileged
mode. Builds run as an unprivileged user at reduced scheduling priority;
network access is disconnected after authenticated dependency installation.
Source archives carry no repository metadata or credentials.

The PE export set adds one name and removes none; no ordinal-stability claim
is made. Compiler and artifact hashes will accompany the final validation
receipt. Native Windows execution is unavailable and remains a distinct
qualification limit.

## Focused runtime and evidence limits

The dedicated `kernelbase_test.exe file_fromapp` entry resolves the function
through both kernelbase and the API-set. It checks synthetic Unicode filenames,
creation dispositions and defined last-error cases, truncation, read/write
contents, incompatible sharing, read-only handles, handle inheritance and
delete-on-close. Missing exports fail under Wine rather than silently skipping.
All temporary files belong to its own temporary directory.

Runtime preparation uses the authenticated, exact WineHQ 11.0 package set in
an owned container. A matching source-built kernelbase module is overlaid
inside that disposable environment after static import compatibility checks.
Preserve the stock and candidate hashes, prove which module was loaded, and
run with a fresh private prefix, no network or display access, an unprivileged
UID and a bounded deadline. This is a component test fixture, not a distributed
Wine runtime or host package installation.

Run the focused check only after final adversarial review. Passing file-API
behaviour would remove one demonstrated compatibility boundary; it would not
prove that the OEM component can activate or process frames. A subsequent
bounded [activation experiment](DOLBY_ACTIVATION_PROBE.md) must record its own
next boundary. Keep OEM components, raw logs and all proprietary tools private.
