#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Simulate an offline package change and its inverse against a dpkg status snapshot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def control_fields(paragraph):
    return dict(re.findall(r"^([A-Za-z0-9-]+): ([^\n]*)$", paragraph, re.M))


def package_key(fields):
    return fields["Package"], fields["Architecture"]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def packages(directory):
    result = {}
    for path in sorted(directory.resolve(strict=True).glob("*.deb")):
        paragraph = subprocess.check_output(["dpkg-deb", "--field", str(path)], text=True)
        fields = control_fields(paragraph)
        key = package_key(fields)
        if key in result:
            raise ValueError(f"multiple archives for {key} in {directory}")
        result[key] = (path, fields["Version"], paragraph.rstrip())
    return result


def apt_name(key, native):
    name, architecture = key
    return name if architecture in (native, "all") else f"{name}:{architecture}"


def simulate(output, phase, status, package_set, remove, native):
    args = ["apt-get", "--simulate", "--no-download", "--no-install-recommends",
            "-o", f"Dir::State::status={status}",
            "-o", f"Dir::State::Lists={output / 'lists'}",
            "-o", "Dir::Etc::sourcelist=/dev/null", "-o", "Dir::Etc::sourceparts=-",
            "-o", "Dir::Cache::pkgcache=", "-o", "Dir::Cache::srcpkgcache="]
    args += ["--allow-downgrades"] if phase == "rollback" else ["--no-remove"]
    args += ["install", *[str(pkg[0]) for pkg in package_set.values()],
             *[apt_name(key, native) + "-" for key in sorted(remove)]]
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          env={**os.environ, "LC_ALL": "C"})
    log = output / (phase + ".log")
    log.write_text(proc.stdout)
    if proc.returncode:
        raise ValueError(f"{phase} solver failed; see {log}")
    installs = {}
    removals = set()
    for line in proc.stdout.splitlines():
        if line.startswith("Inst "):
            match = re.match(r"Inst (\S+) (?:\[[^\]]+\] )?\((\S+)", line)
            if not match or match[1] in installs:
                raise ValueError(f"unexpected install action: {line}")
            installs[match[1]] = match[2]
        elif line.startswith("Remv "):
            removals.add(line.split()[1])
        elif line.startswith("Purg "):
            raise ValueError(f"unexpected purge: {line}")
    expected = {apt_name(key, native): pkg[1] for key, pkg in package_set.items()}
    if installs != expected or removals != {apt_name(key, native) for key in remove}:
        raise ValueError(f"{phase} actions differ from the proposed package set; see {log}")
    return {"install": installs, "remove": sorted(removals)}


def qualify(candidate_dir, rollback_dir, output, status_path=Path("/var/lib/dpkg/status")):
    candidate, rollback = packages(candidate_dir), packages(rollback_dir)
    if not candidate:
        raise ValueError("empty candidate package set")
    native = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    original = status_path.read_bytes()
    projected = {}
    for paragraph in original.decode().strip().split("\n\n"):
        fields = control_fields(paragraph)
        key = package_key(fields)
        if key in projected:
            raise ValueError(f"duplicate status for {key}")
        projected[key] = paragraph
    old = {}
    for key, (_, version, paragraph) in candidate.items():
        fields = control_fields(projected.get(key, ""))
        status = fields.get("Status", "").split()
        if len(status) == 3 and status[2] == "installed":
            if status != ["install", "ok", "installed"]:
                raise ValueError(f"ineligible installed state for {key}: {status}")
            old[key] = fields["Version"]
            if old[key] == version:
                raise ValueError(f"{key} already has candidate version {version}; omit it")
        elif status and status[1:] not in (["ok", "config-files"], ["ok", "not-installed"]):
            raise ValueError(f"partially installed package {key}: {status}")
        projected[key] = paragraph + "\nStatus: install ok installed"
    if {key: item[1] for key, item in rollback.items()} != old:
        raise ValueError("rollback directory must contain exactly the original installed versions")
    output = output.resolve()
    # The receipt includes the laptop's complete package database.
    if Path(__file__).resolve().parent.parent in (output, *output.parents):
        raise ValueError("choose a private receipt directory outside the source checkout")
    output.mkdir(mode=0o700, exist_ok=False)
    (output / "lists/partial").mkdir(parents=True)
    start, end = output / "starting-status", output / "projected-status"
    start.write_bytes(original)
    end.write_text("\n\n".join(projected.values()) + "\n")
    new = set(candidate) - set(old)
    report = {"scope": "APT simulations; installed package versions and dependencies only",
              "starting_status_sha256": digest(start),
              "candidate": {v[0].name: digest(v[0]) for v in candidate.values()},
              "rollback": {v[0].name: digest(v[0]) for v in rollback.values()}}
    report["forward_actions"] = simulate(output, "forward", start, candidate, set(), native)
    report["rollback_actions"] = simulate(output, "rollback", end, rollback, new, native)
    if status_path.read_bytes() != original:
        raise ValueError("installed package state changed during qualification")
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Qualified {len(candidate)} forward changes, {len(old)} restores, {len(new)} removals.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("rollback", type=Path)
    parser.add_argument("private_output", type=Path, help="fresh private receipt directory")
    args = parser.parse_args()
    qualify(args.candidate, args.rollback, args.private_output)
