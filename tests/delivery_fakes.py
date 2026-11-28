#!/usr/bin/env python3
"""Test doubles for the package publisher: an ssh that runs locally and an
aptly that keeps the subset of state the publisher uses in a JSON file.

    delivery_fakes.py ssh HOST COMMAND      run COMMAND with sh in $FAKE_HOME
    delivery_fakes.py aptly -config=FILE …  repo/snapshot/publish/db subset
    delivery_fakes.py sha256sum -- FILE…

The aptly double rejects queries in any form other than the one the
publisher sends, and refuses what real aptly refuses: a conflicting file for
an existing package key, a duplicate snapshot, and dropping the published
snapshot.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packaging" / "delivery"))
import delivery  # noqa: E402

HERE = Path(__file__).resolve()


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def ssh(args):
    host, command = args[0], args[1]
    home = os.environ["FAKE_HOME"]
    environment = dict(os.environ, HOME=home)
    log = Path(home) / "ssh.log"
    with log.open("a") as stream:
        stream.write(f"{host} {command}\n")
    # sha256sum is the only coreutils program the publisher needs that macOS lacks.
    shim = Path(home) / ".fake-bin"
    shim.mkdir(exist_ok=True)
    script = shim / "sha256sum"
    if not script.exists():
        script.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(HERE))} sha256sum \"$@\"\n")
        script.chmod(0o755)
    environment["PATH"] = f"{shim}:{environment['PATH']}"
    return subprocess.run(["sh", "-c", command], cwd=home, env=environment).returncode


def sha256sum(args):
    for name in args:
        if name == "--":
            continue
        print(f"{hashlib.sha256(Path(name).read_bytes()).hexdigest()}  {name}")
    return 0


PACKAGE_REF = re.compile(r"[^_]+_[^_]+_[^_]+\Z")


def aptly(args):
    config = None
    while args and args[0].startswith("-config="):
        config = args.pop(0).split("=", 1)[1]
    if config is None:
        fail("fake aptly needs -config=")
    root = Path(json.loads(Path(config).read_text())["rootDir"])
    state_file = root / "state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {
        "repos": {}, "pool": {}, "snapshots": [], "published": {}}

    def save():
        root.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=1, sort_keys=True))

    def repo(name):
        return state["repos"].setdefault(name, [])

    command = args[:2]
    if command == ["repo", "create"]:
        name, base = args[2], args[5]
        refs = next(s["refs"] for s in state["snapshots"] if s["name"] == base)
        state["repos"][name] = list(refs)
        save()
    elif command == ["repo", "drop"]:
        if args[2] != "-force":
            fail("fake aptly: dropping a snapshot's source repo requires -force")
        del state["repos"][args[3]]
        save()
    elif command == ["repo", "add"]:
        refs = repo(args[2])
        for path in args[3:]:
            deb = delivery.Deb(path)
            key = f"{deb.name}_{deb.version}_{deb.architecture}"
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if state["pool"].get(key, digest) != digest:
                fail(f"ERROR: conflict in package {key}")
            state["pool"][key] = digest
            if key not in refs:
                refs.append(key)
            print(f"Added {key}")
        save()
    elif command == ["repo", "show"]:
        if args[2] != "-with-packages":
            fail("fake aptly: expected -with-packages")
        refs = repo(args[3])
        print(f"Name: {args[3]}\nComment: \nNumber of packages: {len(refs)}\nPackages:")
        for key in sorted(refs):
            print(f"  {key}")
    elif command == ["repo", "remove"]:
        key = args[3]
        if not PACKAGE_REF.fullmatch(key):
            fail(f"fake aptly: unsupported package reference {key!r}")
        refs = repo(args[2])
        if key in refs:
            refs.remove(key)
            print(f"Removing {key}...")
        save()
    elif command == ["snapshot", "create"]:
        name = args[2]
        if args[3:5] != ["from", "repo"]:
            fail("fake aptly: only snapshots from a repo")
        if any(s["name"] == name for s in state["snapshots"]):
            fail(f"ERROR: snapshot {name} already exists")
        state["snapshots"].append({"name": name, "refs": sorted(repo(args[5]))})
        save()
        print(f"Snapshot {name} successfully created.")
    elif command == ["snapshot", "list"]:
        for snapshot in state["snapshots"]:
            print(snapshot["name"])
    elif command == ["snapshot", "drop"]:
        name = args[2]
        if name in state["published"].values():
            fail(f"ERROR: unable to drop: snapshot is published")
        state["snapshots"] = [s for s in state["snapshots"] if s["name"] != name]
        save()
    elif command == ["publish", "switch"]:
        if not args[2].startswith("-gpg-key="):
            fail("fake aptly: publish switch must name the signing key")
        distribution, name = args[3], args[4]
        if os.environ.get("FAKE_SWITCH_FAIL"):
            fail("fake aptly: switch failed")
        if not any(s["name"] == name for s in state["snapshots"]):
            fail(f"ERROR: snapshot {name} not found")
        state["published"][distribution] = name
        state["signing_key"] = args[2].split("=", 1)[1]
        save()
    elif command == ["publish", "show"]:
        name = state["published"].get(args[2])
        if name is None:
            fail("ERROR: published repo not found")
        print(f"Prefix: .\nDistribution: {args[2]}\nArchitectures: amd64 i386\nSources:\n  main: {name} [snapshot]")
    elif command == ["db", "cleanup"]:
        used = {k for refs in state["repos"].values() for k in refs}
        used |= {k for s in state["snapshots"] for k in s["refs"]}
        state["pool"] = {k: v for k, v in state["pool"].items() if k in used}
        save()
    else:
        fail(f"fake aptly: unsupported command {args}")
    return 0


if __name__ == "__main__":
    tool, rest = sys.argv[1], sys.argv[2:]
    raise SystemExit({"ssh": ssh, "aptly": aptly, "sha256sum": sha256sum}[tool](rest))
