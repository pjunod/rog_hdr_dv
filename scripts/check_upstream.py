#!/usr/bin/env python3
"""Check submission-kit integrity and inventory coverage without contacting upstream."""

from __future__ import annotations

import argparse
from email.parser import Parser
from email.utils import parseaddr
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlsplit


OID = re.compile(r"[0-9a-f]{40}\Z")
DISPOSITIONS = {"ready-for-human-review", "held", "discussion-draft",
                "superseded", "excluded", "third-party"}
BAD_TRAILER = re.compile(
    r"^(?:Co-Authored-By:|Claude-Session:)|claude\.ai/code/session_", re.I | re.M
)


def inside(root: Path, relative: str) -> Path:
    """Require a canonical, relative file path without traversing symlinks."""
    parts = PurePosixPath(relative)
    if (not relative or parts.is_absolute() or ".." in parts.parts
            or str(parts) != relative or "\\" in relative):
        raise ValueError(f"noncanonical path: {relative!r}")
    candidate = root.joinpath(*parts.parts)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"path escapes submission kit: {relative}")
    if any(p.is_symlink() for p in [candidate, *candidate.parents]
           if p != root.parent and p.is_relative_to(root)):
        raise ValueError(f"symlink in submission path: {relative}")
    if not candidate.is_file():
        raise ValueError(f"missing submission file: {relative}")
    return candidate


def artifact_files(directory: Path) -> list[Path]:
    paths = list(directory.rglob("*"))
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"symlink in submission material: {path.relative_to(directory)}")
    return sorted(p for p in paths
                  if p.is_file() and p != directory / "SHA256SUMS"
                  and p.name != ".DS_Store"
                  and "__pycache__" not in p.parts and p.suffix != ".pyc")


def checksum_text(directory: Path) -> str:
    rows = []
    for path in artifact_files(directory):
        relative = path.relative_to(directory).as_posix()
        inside(directory, relative)
        rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n")
    return "".join(rows)


def check(root: Path) -> list[str]:
    directory = root / "upstream"
    errors: list[str] = []
    try:
        expected = checksum_text(directory)
        recorded = inside(directory, "SHA256SUMS").read_text()
        if recorded != expected:
            errors.append("Submission bytes changed: review, then run scripts/check_upstream.py --write-checksums")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    for patch in sorted(directory.rglob("*.patch")):
        try:
            inside(directory, patch.relative_to(directory).as_posix())
            preamble = patch.read_text().split("\n---\n", 1)[0]
            headers = Parser().parsestr("\n".join(preamble.splitlines()[1:]))
            name, address = parseaddr(headers.get("From", ""))
            if not name or not address or re.search(r"agent|codex|claude|invalid", name + address, re.I):
                errors.append(f"{patch.relative_to(root)}: missing or placeholder patch author")
            if not headers.get("Subject"):
                errors.append(f"{patch.relative_to(root)}: missing patch subject")
            if not str(headers.get_payload()).strip():
                errors.append(f"{patch.relative_to(root)}: missing explanatory commit body")
            if BAD_TRAILER.search(preamble):
                errors.append(f"{patch.relative_to(root)}: assistant trailer/session link in exported metadata")
            if re.search(r"^Signed-off-by:.*(?:Paul Junod|donujp@gmail\.com)", preamble, re.M | re.I):
                errors.append(f"{patch.relative_to(root)}: Paul's sign-off must be added by Paul at submission")
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(str(exc))

    for manifest_path in sorted(directory.glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text())
            if not OID.fullmatch(manifest.get("base", "")):
                raise ValueError(f"{manifest_path.relative_to(root)}: missing full base SHA")
            seen = set()
            for unit in manifest["units"]:
                if unit["id"] in seen:
                    raise ValueError(f"duplicate unit in {manifest_path.relative_to(root)}: {unit['id']}")
                seen.add(unit["id"])
                if not unit.get("status"):
                    raise ValueError(f"missing unit status: {manifest_path.relative_to(root)} {unit['id']}")
                if "base" in unit and not OID.fullmatch(unit["base"]):
                    raise ValueError(f"invalid unit base: {manifest_path.relative_to(root)} {unit['id']}")
                for patch in unit.get("patches", []):
                    inside(manifest_path.parent, patch)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))

    try:
        catalog = json.loads(inside(directory, "catalog.json").read_text())
        ids = set()
        for item in catalog["items"]:
            if item["id"] in ids:
                raise ValueError(f"duplicate inventory ID: {item['id']}")
            ids.add(item["id"])
            if item.get("disposition") not in DISPOSITIONS or not item.get("artifacts"):
                raise ValueError(f"inventory item lacks disposition/material: {item['id']}")
            local_material = False
            for artifact in item["artifacts"]:
                if artifact.startswith("https://"):
                    url = urlsplit(artifact)
                    if url.hostname != "github.com" or not url.path.startswith("/pjunod/"):
                        raise ValueError(f"external kit artifact must identify the owner's repository: {artifact}")
                    continue  # Remote material is not execution evidence.
                inside(root, artifact)
                local_material = True
            if item["disposition"] == "ready-for-human-review":
                if not local_material or not item.get("evidence"):
                    raise ValueError(f"ready item needs local material and an evidence receipt: {item['id']}")
                for evidence in item["evidence"]:
                    inside(root, evidence)
        text = (root / "docs" / "UPSTREAM_SUBMISSIONS.md").read_text()
        documented = {line.split("|")[1].strip() for line in text.splitlines()
                      if line.startswith("| ") and not line.startswith("| Unit")}
        if ids != documented:
            errors.append(f"Inventory differs from ledger: undocumented={sorted(ids - documented)}, uncatalogued={sorted(documented - ids)}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-checksums", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.write_checksums:
        (root / "upstream" / "SHA256SUMS").write_text(checksum_text(root / "upstream"))
    errors = check(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("PASS: submission checksums, patch metadata, bases, paths and inventory coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
