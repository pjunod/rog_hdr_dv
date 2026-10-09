#!/usr/bin/env python3
"""Validate repository integrity without building or touching a display."""

from pathlib import Path
import hashlib
import json
import re
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    errors = []
    manifest = {}
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if name in manifest:
            errors.append(f"Duplicate manifest entry: {name}")
        manifest[name] = digest
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"Missing or changed patch: {name}")
    patches = {str(p.relative_to(root)) for p in (root / "patches").rglob("*.patch")}
    if patches != set(manifest):
        errors.append("Patch manifest does not exactly cover the patch files")
    sources = json.loads((root / "sources.json").read_text())
    components = set()
    for component in sources["series"]:
        name = component["component"]
        components.add(name)
        directory = root / "patches" / name
        names = (directory / "series").read_text().splitlines()
        actual = {p.name for p in directory.glob("*.patch")}
        if len(names) != len(set(names)) or set(names) != actual:
            errors.append(f"Invalid series inventory: {name}")
        if len(names) != component["patch_count"]:
            errors.append(f"Wrong series length: {name}")
    if components != {p.name for p in (root / "patches").iterdir() if p.is_dir()}:
        errors.append("Source manifest does not cover every patch series")
    readme = (root / "README.md").read_text()
    for doc in sorted((root / "docs").glob("*.md")):
        if str(doc.relative_to(root)) not in readme:
            errors.append(f"Documentation absent from README: {doc.name}")
    for doc in [*root.glob("*.md"), *(root / "docs").glob("*.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
            if re.match(r"^(https?://|mailto:|#)", target):
                continue
            path = target.split("#", 1)[0]
            if path and not (doc.parent / path).exists():
                errors.append(f"Broken link in {doc.name}: {target}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"PASS: {len(patches)} patches, {len(components)} series, documentation links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
