#!/usr/bin/env python3
"""Run an explicit affected-check batch and retain source-bound retry receipts."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid


ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SCHEMA = 1


class ValidationError(ValueError):
    """Invalid inputs or evidence; no implicit rerun is permitted."""


class TerminationRequested(KeyboardInterrupt):
    """A catchable termination, propagated only after child cleanup."""


@contextmanager
def termination_handler():
    # Imported batches must restore their caller's handler. After the first
    # request, coalesce further SIGTERMs so cleanup/receipt saving can finish.
    requested = False

    def terminate(signum, frame):
        nonlocal requested
        if not requested:
            requested = True
            raise TerminationRequested("SIGTERM")

    previous = signal.signal(signal.SIGTERM, terminate)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=unique_object)
    except (OSError, ValueError) as exc:
        raise ValidationError(f"Cannot read {path}: {exc}") from exc


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode("utf-8")).hexdigest()


def file_digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def text(value):
    return isinstance(value, str) and bool(value) and "\0" not in value


def fields(value, required, optional=()):
    if (not isinstance(value, dict) or not set(required) <= value.keys()
            or value.keys() - set(required) - set(optional)):
        raise ValidationError(f"Expected fields {required}, optional {optional}")


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValidationError(f"Invalid identifier: {value!r}")
    return value


def manifest(path):
    data = load_json(path)
    fields(data, ("schema", "sources", "checks"))
    if type(data["schema"]) is not int or data["schema"] != SCHEMA:
        raise ValidationError("Manifest schema must be integer 1")
    if not isinstance(data["sources"], dict) or not data["sources"]:
        raise ValidationError("sources must be a nonempty mapping of IDs to Git roots")
    sources = {}
    for name, root in data["sources"].items():
        identifier(name)
        if not text(root):
            raise ValidationError(f"Invalid source path: {name}")
        sources[name] = (path.parent / root).resolve()
    if not isinstance(data["checks"], list) or not data["checks"]:
        raise ValidationError("checks must be a nonempty list")
    checks = []
    seen = set()
    for check in data["checks"]:
        fields(check, ("id", "sources", "argv", "cwd", "env", "timeout_seconds"), ("paths",))
        name = identifier(check["id"])
        if name in seen:
            raise ValidationError(f"Duplicate check: {name}")
        seen.add(name)
        dependencies = check["sources"]
        if (not isinstance(dependencies, list) or not dependencies
                or not all(isinstance(item, str) and item in sources for item in dependencies)
                or len(set(dependencies)) != len(dependencies)):
            raise ValidationError(f"Invalid sources for {name}")
        if (not isinstance(check["argv"], list) or not check["argv"]
                or not all(isinstance(arg, str) and "\0" not in arg for arg in check["argv"])
                or not text(check["argv"][0])):
            raise ValidationError(f"argv for {name} must be a nonempty argument list")
        if not text(check["cwd"]):
            raise ValidationError(f"Invalid cwd for {name}")
        cwd = (path.parent / check["cwd"]).resolve()
        if not cwd.is_dir():
            raise ValidationError(f"Missing cwd for {name}: {cwd}")
        for source_id, root in sources.items():
            if cwd.is_relative_to(root) and source_id not in dependencies:
                raise ValidationError(f"{name} omits its cwd source: {source_id}")
        env = check["env"]
        if (not isinstance(env, dict)
                or not all(text(key) and "=" not in key and isinstance(value, str)
                           and "\0" not in value for key, value in env.items())):
            raise ValidationError(f"Invalid env for {name}")
        timeout = check["timeout_seconds"]
        if type(timeout) is not int or timeout <= 0:
            raise ValidationError(f"timeout_seconds for {name} must be a positive integer")
        paths = check.get("paths", {})
        if not isinstance(paths, dict) or paths.keys() - set(dependencies):
            raise ValidationError(f"Invalid paths mapping for {name}")
        for source_id, names in paths.items():
            if (not isinstance(names, list) or not names or not all(
                    text(item) and not PurePosixPath(item).is_absolute()
                    and str(PurePosixPath(item)) == item and item != "."
                    and ".." not in PurePosixPath(item).parts for item in names)
                    or len(set(names)) != len(names)):
                raise ValidationError(f"Invalid literal source paths for {name}: {source_id}")
        checks.append({**check, "cwd": str(cwd), "sources": sorted(dependencies),
                       "paths": {key: sorted(value) for key, value in paths.items()},
                       "env": {"PATH": os.defpath, "LC_ALL": "C", **env}})
    return sources, checks


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            env={"PATH": os.defpath, "LC_ALL": "C"}, timeout=30)
    if result.returncode:
        raise ValidationError(f"git {args[0]} failed for {root}: "
                              + result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def snapshot(sources):
    result = {}
    for name, root in sources.items():
        top = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
        if top != root:
            raise ValidationError(f"Source {name} must name the Git root: {top}")
        tree = git(root, "rev-parse", "HEAD^{tree}").decode().strip()
        if any(entry.startswith(b"160000 ") for entry in
               git(root, "ls-tree", "-r", "-z", "HEAD").split(b"\0")):
            raise ValidationError(f"Submodules unsupported in source {name}; declare plain Git roots")
        if git(root, "status", "--porcelain=v1", "--untracked-files=all"):
            raise ValidationError(f"Source {name} is dirty (including nonignored untracked files)")
        result[name] = {"path": str(root), "head": git(root, "rev-parse", "HEAD").decode().strip(),
                        "tree": tree}
    return result


def identities(state):
    # An identical exported tree at a different committer ID is the same code.
    return {name: {"path": item["path"], "tree": item["tree"]}
            for name, item in state.items()}


def check_state(sources, check, initial):
    state = {}
    for name in check["sources"]:
        item = dict(initial[name])
        paths = check["paths"].get(name)
        if paths is not None:
            entries = git(sources[name], "ls-tree", "-r", "-z", "HEAD").split(b"\0")
            selected = set()
            for path in paths:
                literal = path.encode("utf-8")
                matches = {entry for entry in entries if b"\t" in entry and
                           (entry.split(b"\t", 1)[1] == literal or
                            entry.split(b"\t", 1)[1].startswith(literal + b"/"))}
                if not matches:
                    raise ValidationError(f"{check['id']}: scoped path absent in {name}: {path}")
                selected.update(matches)
            item["paths"] = paths
            item["input_sha256"] = hashlib.sha256(b"\0".join(sorted(selected))).hexdigest()
        state[name] = item
    return state


def input_identities(state):
    return {name: {"path": item["path"], "paths": item.get("paths"),
                   "hash": item.get("input_sha256", item["tree"])}
            for name, item in state.items()}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, ledger):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(ledger, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep this inode: unlinking a flock file can admit a second lock holder.
    with path.with_name(path.name + ".lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValidationError("Ledger is already in use") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def read_ledger(path):
    if not path.exists():
        return {"schema": SCHEMA, "checks": {}}
    ledger = load_json(path)
    fields(ledger, ("schema", "checks"))
    if type(ledger["schema"]) is not int or ledger["schema"] != SCHEMA:
        raise ValidationError("Ledger schema must be integer 1")
    if not isinstance(ledger["checks"], dict):
        raise ValidationError("Invalid ledger checks")
    for name, attempts in ledger["checks"].items():
        identifier(name)
        if not isinstance(attempts, list) or not attempts:
            raise ValidationError(f"Invalid attempt history: {name}")
        for attempt in attempts:
            if (not isinstance(attempt, dict)
                    or attempt.get("status") not in ("running", "passed", "failed", "invalidated")
                    or not text(attempt.get("fingerprint"))):
                raise ValidationError(f"Invalid receipt: {name}")
            if attempt["status"] == "passed":
                if (type(attempt.get("returncode")) is not int or attempt["returncode"] != 0
                        or not text(attempt.get("log")) or not text(attempt.get("log_sha256"))):
                    raise ValidationError(f"Incomplete passing receipt: {name}")
    return ledger


def output_location(path, sources):
    # Receipts must not make the measured checkout dirty, or overwrite source.
    for root in sources.values():
        if path.is_relative_to(root):
            result = subprocess.run(["git", "-C", str(root), "check-ignore", "--quiet", "--",
                                     str(path)], env={"PATH": os.defpath, "LC_ALL": "C"})
            if result.returncode != 0:
                raise ValidationError(f"Ledger output inside source must be Git-ignored: {path}")


def execute(command, log):
    # No handler may unwind launch, cleanup or partial handler restoration.
    # Block only while changing handlers (never across Popen), so the child
    # inherits no blocked cancellation mask. Defer signals until after reap.
    numbers = (signal.SIGTERM, signal.SIGINT)
    pending = []
    previous = {}
    process = None

    def defer(signum, frame):
        if signum not in pending:
            pending.append(signum)

    mask = signal.pthread_sigmask(signal.SIG_BLOCK, numbers)
    try:
        try:
            for number in numbers:
                previous[number] = signal.signal(number, defer)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        try:
            process = subprocess.Popen(command["argv"], cwd=command["cwd"], env=command["env"],
                                       stdout=log, stderr=subprocess.STDOUT, shell=False,
                                       start_new_session=True)
            deadline = time.monotonic() + command["timeout_seconds"]
            while not pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command["argv"], command["timeout_seconds"])
                try:
                    return process.wait(timeout=min(0.1, remaining))
                except subprocess.TimeoutExpired:
                    pass
        finally:
            if process is not None and (pending or process.returncode is None):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
    finally:
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, numbers)
        try:
            for number, handler in previous.items():
                signal.signal(number, handler)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        # Replay through the caller-owned handler: termination_handler sets
        # its coalescing flag even for cancellation received during launch.
        for number in pending:
            signal.raise_signal(number)
        if pending:
            if signal.SIGTERM in pending:
                raise TerminationRequested("SIGTERM")
            raise KeyboardInterrupt


def run_batch(manifest_path, ledger_path, invalidate=(), reason=None):
    with termination_handler():
        return _run_batch(manifest_path, ledger_path, invalidate, reason)


def _run_batch(manifest_path, ledger_path, invalidate=(), reason=None):
    sources, checks = manifest(manifest_path)
    if len(set(invalidate)) != len(invalidate):
        raise ValidationError("Duplicate invalidation ID")
    invalidated = set(invalidate)
    if invalidated and (not isinstance(reason, str) or not reason.strip()):
        raise ValidationError("--invalidate requires a nonempty --reason")
    if reason is not None and not invalidated:
        raise ValidationError("--reason requires --invalidate")
    if invalidated - {check["id"] for check in checks}:
        raise ValidationError("Invalidation IDs must be checks in this manifest")
    log_dir = ledger_path.with_name(ledger_path.name + ".logs")
    for location in (ledger_path, ledger_path.parent,
                     ledger_path.with_name(ledger_path.name + ".lock"), log_dir):
        output_location(location, sources)
    initial = snapshot(sources)
    runner_sha256 = file_digest(Path(__file__))
    with locked(ledger_path):
        ledger = read_ledger(ledger_path)
        plans = []
        # Preflight the whole manifest before invalidating or executing anything.
        for check in checks:
            name = check["id"]
            state = check_state(sources, check, initial)
            command = {key: check[key] for key in ("argv", "cwd", "env", "timeout_seconds")}
            fingerprint = digest({"sources": input_identities(state), "command": command,
                                  "runner_sha256": runner_sha256})
            history = ledger["checks"].get(name, [])
            previous = history[-1] if history else None
            if name in invalidated and not previous:
                raise ValidationError(f"Cannot invalidate absent receipt: {name}")
            if (previous and previous["fingerprint"] != fingerprint
                    and name not in invalidated):
                raise ValidationError(f"{name}: source/command/runner changed; explicitly "
                                      "--invalidate this check with --reason")
            reuse = (previous is not None and previous["status"] == "passed"
                     and name not in invalidated)
            if reuse:
                try:
                    valid_log = file_digest(Path(previous["log"])) == previous["log_sha256"]
                except OSError:
                    valid_log = False
                if not valid_log:
                    raise ValidationError(f"{name}: successful log missing/changed; explicit "
                                          "invalidation required, not an automatic rerun")
            plans.append((check, state, command, fingerprint, bool(reuse)))
        for check, state, command, fingerprint, reuse in plans:
            name = check["id"]
            if name in invalidated:
                history = ledger["checks"][name]
                history.append({"status": "invalidated", "fingerprint": fingerprint,
                                "previous_fingerprint": history[-1]["fingerprint"],
                                "reason": reason, "at": timestamp()})
        if invalidated:
            save(ledger_path, ledger)
        failures = False
        for check, state, command, fingerprint, reuse in plans:
            name = check["id"]
            if identities(snapshot(sources)) != identities(initial):
                raise ValidationError("Sources changed during batch; stopped before next check")
            if file_digest(Path(__file__)) != runner_sha256:
                raise ValidationError("Runner changed during batch")
            if reuse:
                print(f"SKIP {name}: existing passing receipt", flush=True)
                continue
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{name}-{uuid.uuid4().hex}.log"
            attempt = {"status": "running", "fingerprint": fingerprint, "sources": state,
                       "command": command, "runner_sha256": runner_sha256,
                       "started_at": timestamp(), "log": str(log_path), "returncode": None}
            ledger["checks"].setdefault(name, []).append(attempt)
            save(ledger_path, ledger)
            print(f"RUN {name}: {json.dumps(command['argv'])}", flush=True)
            source_error = None
            try:
                with log_path.open("xb") as log:
                    try:
                        attempt["returncode"] = execute(command, log)
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        attempt["error"] = str(exc)
                        log.write(("\nRUNNER ERROR: " + str(exc) + "\n").encode("utf-8"))
                try:
                    if identities(snapshot(sources)) != identities(initial):
                        source_error = "Source identities changed during command"
                except ValidationError as exc:
                    source_error = str(exc)
                if source_error:
                    attempt["error"] = source_error
                if file_digest(Path(__file__)) != runner_sha256:
                    source_error = "Runner changed during command"
                    attempt["error"] = source_error
                attempt["log_sha256"] = file_digest(log_path)
                attempt["status"] = ("passed" if attempt["returncode"] == 0
                                     and "error" not in attempt else "failed")
            except KeyboardInterrupt as exc:
                attempt["error"] = f"cancelled: {type(exc).__name__}"
                raise
            finally:
                attempt["finished_at"] = timestamp()
                save(ledger_path, ledger)
            failures |= attempt["status"] != "passed"
            print(f"{attempt['status'].upper()} {name}: {log_path}", flush=True)
            if source_error:
                raise ValidationError(source_error + "; batch stopped")
        return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--invalidate", action="append", default=[], metavar="CHECK")
    parser.add_argument("--reason")
    args = parser.parse_args(argv)
    try:
        return run_batch(args.manifest.resolve(), args.ledger.resolve(), args.invalidate, args.reason)
    except (ValidationError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except TerminationRequested:
        print("ERROR: SIGTERM; nonpassing receipts will be retried", file=sys.stderr)
        return 128 + signal.SIGTERM
    except KeyboardInterrupt:
        print("ERROR: interrupted; running receipts will be retried", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
