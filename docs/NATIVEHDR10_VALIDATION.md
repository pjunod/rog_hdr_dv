# nativehdr10 single-batch validation receipts

## Implementation status and ownership

This runner and its regression coverage are integrated in the owned
`codex/team-hdr-nativehdr10-20261011` candidate. Both adversarial reviews and
focused reviews are delivered and signal-handler findings addressed. Runner
bytes were frozen at `e4f981d` before execution; all **29 individual Linux
regression methods passed**. The first full affected batch returned 69 passes
and two native failures, not candidate acceptance. See the
[original receipts](../evidence/nativehdr10-validation-attempt1.json).
Do not edit the frozen runner or repeat successful methods for another reviewer.
The first restricted retry passed colour channel bounds and the target-overrides
D-Bus case, but failed the later has-external-monitor case on colord lookup.
Latest receipts are 70 passed, one failed; see the
[retry evidence](../evidence/nativehdr10-validation-attempt2.json).
The next [required-check gate](../evidence/nativehdr10-validation-attempt3.json)
passed color-management but monitor-dbus exited 245; 15 genuinely invalidated
checks did not run. Raw 70 passing histories are not 70 valid current-candidate
receipts: 55 valid passes, one failure, 15 pending. All 75 logs are preserved.

The existing [colour harness](../tools/test-mutter-colour.sh) selects tests and
sets up their environment, but does not keep per-check retry receipts. Existing
[evidence](../evidence/nativehdr10-sol-stage.json) is a source/compiler handoff,
not a unit pass ledger. The small standard-library
[runner](../scripts/nativehdr10_validation.py) adds only the missing execution
and receipt layer; it does not replace reconstruction, compilation, Meson,
unittest or the owned native transport. See [development](DEVELOPMENT.md) and
the [source contract](NIGHT_LIGHT_AND_OVERRIDES.md).

## Manifest format

Python 3.9+ and Git on Linux/macOS are required. The manifest is trusted
executable input: review its commands and dependency scopes along with the
candidate. It is not safe to run an arbitrary downloaded manifest.

A manifest has exactly `schema`, `sources`, and `checks`. Paths for source
roots and working directories are relative to the manifest's directory (or
absolute); no environment-variable expansion occurs. Use actual owned paths,
not the illustrative `/owned` paths below. Every source must be a clean Git
root with a committed HEAD. Staged/unstaged edits and nonignored untracked
files are rejected; submodules are deliberately unsupported.

```json
{
  "schema": 1,
  "sources": {
    "repository": "/owned/hdr",
    "mutter": "/owned/native/src/mutter",
    "library": "/owned/native/src/libdisplay-info"
  },
  "checks": [
    {
      "id": "repository-integrity",
      "sources": ["repository"],
      "argv": ["/usr/bin/python3", "scripts/check_repository.py"],
      "cwd": "/owned/hdr",
      "env": {},
      "timeout_seconds": 120
    },
    {
      "id": "validation-runner-regressions",
      "sources": ["repository"],
      "paths": {
        "repository": [
          "scripts/nativehdr10_validation.py",
          "tests/test_nativehdr10_validation.py"
        ]
      },
      "argv": [
        "/usr/bin/python3", "-m", "unittest", "-v",
        "test_nativehdr10_validation"
      ],
      "cwd": "/owned/hdr",
      "env": {"PYTHONPATH": "tests"},
      "timeout_seconds": 120
    }
  ]
}
```

This is a **format example, not the complete nativehdr10 acceptance manifest**.
The integration/validation owner supplies the agreed affected native tests,
configuration/API cases and repository checks, after source review. IDs are
unique lowercase words/digits separated by hyphens. Checks run sequentially in
manifest order, with one explicit argument-vector command per check. Duplicate
keys/IDs, string shell commands, unknown fields, missing dependencies, invalid
paths/environments and nonpositive timeouts are rejected.

Each check requires:

- `id`: stable receipt key; do not rename successful checks to force execution.
- `sources`: nonempty list of source IDs covering **all** code dependencies,
  including the source containing `cwd` when applicable. For native Mutter
  tests include the library source and any repository-owned helpers used.
- `argv`: argument vector passed directly to the process, with `shell=False`.
  No word splitting, shell substitution or glob expansion. Use one exact Meson
  test name or unittest target per entry if those checks need separate retries.
- `cwd`: existing working directory.
- `env`: complete explicit additions/overrides to `PATH=os.defpath` and
  `LC_ALL=C`. No parent environment is inherited. Include required `HOME`,
  runtime-directory, renderer, library-path and test-setup values explicitly.
  Do not put credentials in this map: it is written verbatim to the receipt.
- `timeout_seconds`: positive integer for that invocation. Timeout, SIGINT or
  SIGTERM kills the child process group and reaps the check, not just a wrapper
  process.
  Catchable cancellation during launch is deferred until its process handle
  exists, and throughout execution/reaping. Bounded wait slices limit cancellation
  latency to about 0.1 seconds. Signal-handler installation/restoration is masked
  atomically; the child inherits no newly blocked signals. After reap, deferred
  cancellation is replayed through the restored caller-owned handler, including
  the batch's coalescing SIGTERM handler. Imported batches restore the caller's
  signal handlers. `TerminationRequested` subclasses `KeyboardInterrupt`, so an
  importer's `except KeyboardInterrupt` also catches SIGTERM. Batches must run
  on the main thread. SIGHUP is deliberately unhandled. SIGHUP, SIGKILL, host
  loss and descendants that deliberately escape the process group cannot be
  cleaned up by the runner; reconcile those
  externally before retrying a nonpassing receipt.
- Optional `paths`: mapping from a listed source ID to nonempty lists of
  literal tracked file/directory paths relative to that source. No globs,
  traversal, absolute names or missing paths. A missing mapping entry means
  the **whole source tree** is affected. For a scoped source the SHA-256 is over
  sorted Git file-mode/blob-ID/path entries for the selected files, including
  directory descendants. Additions/removals/mode changes within scope alter
  it. The full HEAD and Git tree are still recorded as execution provenance.

Scopes are a reviewed dependency declaration, not a dependency inference
engine. Include common production code, fixtures, test harnesses and build
metadata where they can affect a result. Prefer whole-tree scope unless the
reviewers can justify a narrower dependency set. An unrelated documentation
edit can retain a correctly scoped success; a common colour-code edit cannot
be hidden by listing only its test file. Build outputs, ignored files,
toolchain/library versions and system state are not independently attested by
Git: the validation owner must ensure the compiled candidate matches these
trees, keep its compiler receipts, and explicitly invalidate affected checks
when external inputs change. No ignored/untracked implementation may be used.

## Execute once, then retry only what needs it

After both complete-batch reviews and fixes, commit/freeze source, verify the
export replay and build receipts, and execute the reviewed manifest:

```sh
python3 scripts/nativehdr10_validation.py /owned/state/affected-checks.json \
  --ledger /owned/state/nativehdr10-receipts.json
```

Use the **same ledger and stable IDs** on subsequent invocations. The ledger,
lock and log directory must live outside measured source roots or in an
already-created Git-ignored directory. Keep the manifest outside measured
source roots or committed/ignored there too. Successful receipts are not
imported from the old handoff. An empty ledger really executes every explicit
check; preserve it rather than starting a new one for another reviewer.

On unchanged inputs, a successful check with its intact hash-verified log is
skipped. A failed or interrupted check is executed again by the next invocation;
there is no in-process retry loop. Ordinary failures do not prevent other
explicit affected checks from running. No test discovery, default full suite,
reconstruction, installation or display action is added by the runner.

A changed source input hash, command, cwd, environment, timeout, scope or
runner bytes causes the **whole manifest to fail preflight**, before any
command executes or any receipt is invalidated. Declare exactly the checks
invalidated by the fix, with a durable reason:

```sh
python3 scripts/nativehdr10_validation.py /owned/state/affected-checks.json \
  --ledger /owned/state/nativehdr10-receipts.json \
  --invalidate monitor-dbus --invalidate monitor-gdctl \
  --reason 'ApplyMonitorsConfig validation correction changes both API checks'
```

The IDs here are illustrative and must exist in the actual manifest/ledger.
Invalidation also handles changed external build/test inputs or lost logs on
otherwise unchanged source. It appends a reasoned invalidation event before
the new attempt, preserving the old receipt/log reference. Missing or modified
successful logs produce an error, **not** an automatic successful-suite rerun.
An identical Git tree with a different committer ID does not require a rerun.
A scoped success from an older full tree is retained only when its declared
input hash matches; its original execution tree remains in the old receipt,
never rewritten as a fictional pass on the new tree.

Do not shrink scopes, remove required checks, substitute no-op commands,
rename IDs, hand-edit passes or delete the ledger to bypass evidence. The
runner cannot prove semantic coverage or authenticate against a malicious
local editor; reviewers own manifest completeness and receipt interpretation.

A reviewer-approved retry manifest may restrict the check list to the exact IDs
being retried against the same ledger, with their unchanged command objects and
original source declarations. Retained receipts keep their recorded executing
trees; final evidence must list every required ID, its executing tree and the
reviewer's retention rationale. This does not grant automatic whole-tree reuse
or permission to silently drop required checks.

For corrections 0069–0071, Fable `t_bedcc81f` approved exactly `mutter-color-hdr`
and `mutter-monitor-dbus-tests` for retry on `9111578e` using a two-check manifest
and the existing ledger/runner. The 40 prior native passes remain executed on
`ac02a18f`: 0069/0071 preserve their executables and loaded libraries exactly;
0070 changes libmutter-51, so retention instead rests on source reachability.
Its only changed idle callback runs on pending persistent D-Bus rejection,
which no retained test/fixture invokes. The hash inventories and focused
decision are retained with the retry archive; this is a reviewer attestation,
not a new pass or runner-inferred dependency proof. Further production changes
need a new invalidation computation. The failed retry stops execution pending
focused diagnosis/review; no bounds widening or extra invalidation is authorized.

For production corrections 0072–0074, Fable `t_6b592492` approved 17 checks
whose mocked-colord traffic changes and retention of 25 native receipts plus
29 scoped runner receipts. Tier A: native-hdr/monitor-utils never construct a
colour manager, so the changed code cannot execute. Tier B: HEADLESS checks
use only virtual monitors, where unregister has no colord call and the same
observable effect in either version. This is reviewer-attested reachability /
observable equivalence, not exact shared-library identity or runner inference.
The decision and before/after binary inventories are in the attempt-3 archive;
all retained receipts keep their actual executing trees. Because the frozen
runner continues ordinary failures, the exact 17-check retry manifest was
split into required-two and dependent-fifteen subsets with unchanged objects,
sources, ledger and runner. The required gate failed, so the latter did not run
and its older passes are marked pending-invalidated in public evidence, not
claimed as current acceptance. No further retry before focused correction /
scope review (`t_ef832f3b`, `t_c88207c7`).

## Receipts, errors and retained evidence

The JSON ledger stores ordered attempt histories per check. Each execution
records full source paths/HEAD/tree, optional scoped input hashes, exact argv,
cwd and child environment, timeout, runner SHA-256, start/end UTC times,
result/exit code or error, and an absolute combined stdout/stderr log path
with SHA-256. `passed` is produced only by an actual zero exit followed by
unchanged clean source/runner verification. A zero exit on mutated source is
failed and stops the batch; source changes detected before the next check
also stop execution. Freeze checkouts during validation; before/after checks
are not a sandbox against mutations that are reverted mid-command.

A `running` record is atomically saved before launch. Interruption leaves it
nonpassing and eligible for retry. Results are saved after each command, not
only at batch completion. A Unix advisory lock rejects another concurrent
runner using that ledger; the `.lock` file stays in place, and the OS releases
the lock if the runner exits. Keep separate source/build ownership as well;
the ledger lock does not protect the checkouts from other tools.

Exit codes: `0` means all manifest checks passed or reused valid successes;
`1` means one or more executed checks failed; `2` means invalid input,
receipt/source error or unavailable prerequisite; `130` means interrupted by
SIGINT and `143` means terminated by SIGTERM after child cleanup.
No exit code establishes display, optical, package or Dolby qualification.

## Integration and native execution

1. Cherry-pick Sol's delivered commits with authorship into the owned
   integration clone; do not copy into another active worker's checkout.
   Add the README topic-index link and canonical status entry there.
2. Both adversarial reviewers inspect this runner, coverage and the complete
   compositor candidate. This document is not a review approval or test pass.
3. Build/fix/export the complete candidate as documented by the integration
   owner. Prepare the explicit affected manifest using existing Meson names
   and the unprivileged test environment from the owned builder. Do not wrap
   the entire colour harness in a single receipt if failed constituent tests
   must be retried individually. The root-dropping colour harness is not
   directly suitable for the already-unprivileged native builder.
4. Native Linux execution uses the owned `.peer-linux/run.py` wrapper only.
   Inside that command, invoke the snapshot's runner on a manifest and ledger
   under the persistent `$PEER_WORK` with actual reconstructed Git roots.
   `$PEER_SOURCE` is a read-only transport snapshot, **not** a Git source root;
   repository checks need a committed owned Git checkout in the container or
   a separate local manifest. Use the wrapper's documented regular-file export
   route for receipts/logs; do not bypass it with SSH or access credentials.
5. Give every required Python runner regression method its own stable check
   ID and exact unittest target in the single post-review Linux batch:
   `PYTHONPATH=tests python3 -B -m unittest -v
   test_nativehdr10_validation.ValidationTests.test_method` (one shell line,
   substituting the actual method). Scope these checks to the runner and test
   files; retain one receipt per method and retry only nonpassing or genuinely
   invalidated checks. No command-narrowing retry is needed.
6. Retain ledger, manifest, logs and compiler/replay receipts in owned ignored
   evidence storage; sanitize any public summary separately. Reuse successful
   evidence for the second reviewer; do not execute the successful suites again.

PR16 remains held unmerged. No source-stage runner invocation authorizes a
push, merge, package installation, native deployment or physical display change.
