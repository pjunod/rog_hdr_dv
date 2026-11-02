#!/usr/bin/env python3
"""Private, append-only run allocation and completed build-output inventories.

An inventory describes retained bytes, not an independent build attestation.
No operation removes outputs, copies archives or uploads records.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile


def reserve(root):
    root = Path(root).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=root))


def inventory(directory):
    directory = Path(directory)
    records = []
    for path in sorted(directory.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"not a regular output file: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        records.append({"path": path.relative_to(directory).as_posix(),
                        "size": path.stat().st_size, "sha256": digest.hexdigest()})
    if not records:
        raise ValueError(f"empty output directory: {directory}")
    return records


def verify(directory, manifest):
    record = json.loads(Path(manifest).read_text())
    if record.get("schema") != 1 or record.get("files") != inventory(directory):
        raise ValueError(f"output inventory differs: {directory}")


def seal(directory, manifest, source, ubuntu_version, version, architecture):
    directory, manifest = Path(directory).resolve(), Path(manifest).resolve()
    if manifest.is_relative_to(directory):
        raise ValueError("inventory must live outside the inventoried directory")
    record = {"schema": 1, "source": source, "ubuntu_version": ubuntu_version,
              "version": version, "architecture": architecture,
              "files": inventory(directory)}
    # Never overwrite a previous inventory. A failed write remains evidence too.
    with manifest.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    verify(directory, manifest)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("reserve")
    create.add_argument("root")
    for command in ("seal", "verify"):
        sub = commands.add_parser(command)
        sub.add_argument("directory")
        sub.add_argument("manifest")
        if command == "seal":
            sub.add_argument("source")
            sub.add_argument("ubuntu_version")
            sub.add_argument("version")
            sub.add_argument("architecture")
    args = vars(parser.parse_args())
    command = args.pop("command")
    try:
        if command == "reserve":
            print(reserve(**args))
        elif command == "seal":
            seal(**args)
        else:
            verify(**args)
    except (OSError, ValueError) as error:
        parser.exit(1, f"outputs.py: {error}\n")


if __name__ == "__main__":
    main()
