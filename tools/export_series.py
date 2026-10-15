#!/usr/bin/env python3
"""Export a work branch's commits into patches/<component> and refresh pins.

Replaces the series from --start onward with `git format-patch BASE..HEAD`
of REPO (zero commit IDs, no signature), rewrites the series file, updates
candidate_commit, candidate_tree, patch_count, patch_order and
candidate_status for the component in sources.json, and regenerates
SHA256SUMS in its existing order. Regenerate SHA256SUMS deliberately: only
when patch bytes change, and say why in the commit message.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def export(component, repo, base, start, status):
    pdir = ROOT / "patches" / component
    names = (pdir / "series").read_text().split()
    keep = names[:start - 1]
    for name in names[start - 1:]:
        (pdir / name).unlink()
    out = subprocess.check_output(
        ["git", "-C", str(repo), "format-patch", "--zero-commit", "--no-signature",
         "--no-numbered", f"--start-number={start}", "-o", str(pdir), f"{base}..HEAD"],
        text=True).split()
    names = keep + [pathlib.Path(p).name for p in out]
    (pdir / "series").write_text("\n".join(names) + "\n")
    data = json.loads((ROOT / "sources.json").read_text())
    for entry in data["series"]:
        if entry["component"] == component:
            entry["candidate_commit"] = git(repo, "rev-parse", "HEAD")
            entry["candidate_tree"] = git(repo, "rev-parse", "HEAD^{tree}")
            entry["patch_count"] = len(names)
            entry["patch_order"] = names
            entry["candidate_status"] = status
            break
    else:
        raise SystemExit(f"unknown component {component}")
    (ROOT / "sources.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return names


def sums():
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}"
             for p in sorted((ROOT / "patches").rglob("*.patch"))]
    old = (ROOT / "SHA256SUMS").read_text().splitlines()
    order = {line.split("  ", 1)[1]: i for i, line in enumerate(old)}
    lines.sort(key=lambda line: (order.get(line.split("  ", 1)[1], 10 ** 6), line.split("  ", 1)[1]))
    (ROOT / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("component", help="Directory name under patches/")
    parser.add_argument("repo", type=pathlib.Path, help="Work clone; HEAD is exported")
    parser.add_argument("base", help="Commit the exported range starts after")
    parser.add_argument("--start", type=int, required=True, help="Number of the first exported patch")
    parser.add_argument("--status", required=True, help="candidate_status text for sources.json")
    args = parser.parse_args()
    names = export(args.component, args.repo, args.base, args.start, args.status)
    sums()
    print(f"{args.component}: {len(names)} patches")


if __name__ == "__main__":
    main()
