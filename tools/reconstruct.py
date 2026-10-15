#!/usr/bin/env python3
"""Rebuild a pinned source tree from sources.json and patches/, and prove it.

For an upstream series (libdisplay-info, mutter, wine) this clones the
recorded upstream, checks out base_commit, applies the series with git am and
requires the resulting tree to equal candidate_tree. For an Ubuntu series it
downloads the recorded source-package artifacts, verifies every SHA-256,
extracts them with dpkg-source -x, requires the import tree to equal
base_tree, applies the series and requires candidate_tree.

Commit IDs differ from the original preparation (committer metadata); trees
must not. Exit status is 0 only when every requested tree matches.
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDENTITY = {"GIT_COMMITTER_NAME": "reconstruct", "GIT_COMMITTER_EMAIL": "reconstruct@invalid",
            "GIT_AUTHOR_NAME": "reconstruct", "GIT_AUTHOR_EMAIL": "reconstruct@invalid"}
UPSTREAM_FALLBACK = {"libdisplay-info": "https://gitlab.freedesktop.org/emersion/libdisplay-info.git"}


def run(args, cwd=None, env=None):
    full = dict(os.environ, **IDENTITY, **(env or {}))
    return subprocess.run(args, cwd=cwd, env=full, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


def series(component):
    for entry in json.loads((ROOT / "sources.json").read_text())["series"]:
        if entry["component"] == component:
            return entry
    raise SystemExit(f"unknown component {component}")


def apply_series(component, tree_dir):
    pdir = ROOT / "patches" / component
    names = (pdir / "series").read_text().split()
    for name in names:
        run(["git", "am", "--quiet", "--keep-cr", str(pdir / name)], cwd=tree_dir)
    return len(names)


def check(label, got, want):
    ok = got == want
    print(f"{label}: {got} {'OK' if ok else 'MISMATCH, expected ' + want}")
    return ok


def upstream(component, entry, work):
    url = entry.get("upstream") or UPSTREAM_FALLBACK[component]
    tree_dir = work / component
    if not tree_dir.exists():
        run(["git", "clone", "--quiet", "--filter=blob:none", url, str(tree_dir)])
    run(["git", "checkout", "--quiet", "--detach", entry["base_commit"]], cwd=tree_dir)
    ok = True
    if "base_tree" in entry:
        ok &= check("base tree", run(["git", "rev-parse", "HEAD^{tree}"], cwd=tree_dir), entry["base_tree"])
    count = apply_series(component, tree_dir)
    print(f"applied {count} patches")
    return ok & check("candidate tree", run(["git", "rev-parse", "HEAD^{tree}"], cwd=tree_dir),
                      entry["candidate_tree"])


def ubuntu(component, entry, work):
    origin = entry["source_origin"]
    dl = work / f"{component}-artifacts"
    dl.mkdir(parents=True, exist_ok=True)
    dsc = None
    for artifact in origin["artifacts"]:
        target = dl / artifact["file"]
        if not target.exists():
            with urllib.request.urlopen(artifact["url"]) as response:
                target.write_bytes(response.read())
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != artifact["sha256"]:
            raise SystemExit(f"{artifact['file']}: sha256 {digest} does not match the pin")
        if artifact["file"].endswith(".dsc"):
            dsc = target
    tree_dir = work / component
    if tree_dir.exists():
        raise SystemExit(f"{tree_dir} exists; use an empty work directory")
    run(["dpkg-source", "--no-check", "-x", str(dsc), str(tree_dir)])
    run(["git", "init", "--quiet"], cwd=tree_dir)
    # The recorded imports honour the package's own .gitignore (which keeps
    # subprojects/gvdb and debian/tests/build out) and exclude quilt's .pc/.
    run(["git", "add", "--", ".", ":(exclude).pc"], cwd=tree_dir)
    ok = check("base tree", run(["git", "write-tree"], cwd=tree_dir), entry["base_tree"])
    if not ok:
        return False
    run(["git", "commit", "--quiet", "-m", f"Import {origin['package']} {origin['version']}"], cwd=tree_dir)
    count = apply_series(component, tree_dir)
    print(f"applied {count} patches")
    return check("candidate tree", run(["git", "rev-parse", "HEAD^{tree}"], cwd=tree_dir),
                 entry["candidate_tree"])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("component", choices=["libdisplay-info", "mutter", "wine",
                                              "ubuntu-libdisplay-info", "ubuntu-mutter"])
    parser.add_argument("workdir", type=pathlib.Path, help="Disposable directory outside this repository")
    args = parser.parse_args()
    work = args.workdir.resolve()
    if ROOT in work.parents or work == ROOT:
        raise SystemExit("the work directory must be outside the repository")
    work.mkdir(parents=True, exist_ok=True)
    entry = series(args.component)
    ok = ubuntu(args.component, entry, work) if args.component.startswith("ubuntu-") \
        else upstream(args.component, entry, work)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
