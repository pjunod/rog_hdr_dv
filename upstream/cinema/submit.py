#!/usr/bin/env python3
"""Prepare a recorded upstream unit; publishing is reserved for its human owner."""
from __future__ import annotations
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile


def run(args: list[str], *, cwd: Path | None = None, capture: bool = False, env_overrides: dict | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, check=True,
                            stdout=subprocess.PIPE if capture else None,
                            env=os.environ | {"GIT_COMMITTER_NAME": "Paul Junod",
                                              "GIT_COMMITTER_EMAIL": "donujp@gmail.com"} | (env_overrides or {}))
    return result.stdout.strip() if capture else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("unit", help="unit number, inventory ID, or all")
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and apply only; no sign-off, fork, push, or PR")
    args = parser.parse_args()
    project = args.project.resolve()
    manifest = json.loads((project / "manifest.json").read_text())
    units = [u for u in manifest["units"] if args.unit == "all" or args.unit in
             [u["id"], u["slug"], *u.get("inventory_ids", [])]]
    if not units:
        parser.error("unknown unit")
    sparse_paths = manifest.get("sparse_paths", [])
    if not isinstance(sparse_paths, list) or any(
        not isinstance(p, str) or not p or Path(p).is_absolute()
        or ".." in Path(p).parts or p in (".", "..")
        or Path(p).as_posix() != p or p.startswith("-") or "\\" in p
        for p in sparse_paths
    ):
        sys.exit("invalid sparse source paths")
    repository = manifest["repository"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        sys.exit("invalid repository identity")
    for unit in units:
        slug = unit["slug"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", slug):
            sys.exit("invalid unit slug")
        patches = [(project / p).resolve() for p in unit.get("patches", [])]
        if any(project not in p.parents or not p.is_file() for p in patches):
            sys.exit("patch escapes project or is missing")
        if patches:
            body = (project / slug / "DESCRIPTION.md").resolve()
            if project not in body.parents or not body.is_file():
                sys.exit("missing description")
    service = None
    venue = manifest.get("venue", "github")
    if not args.dry_run:
        blocked = [u["id"] for u in units if u["status"] != "ready-for-human-review"]
        if any(not u.get("patches") for u in units):
            sys.exit("No-patch units require their documented manual submission route.")
        if blocked:
            sys.exit("Refusing publication of held units: " + ", ".join(blocked))
        if venue == "github":
            login = run(["gh", "api", "user", "--jq", ".login"], capture=True)
        elif venue == "forgejo":
            import importlib.util
            transport = importlib.util.spec_from_file_location("upstream_forgejo", Path(__file__).with_name("forgejo.py"))
            module = importlib.util.module_from_spec(transport)
            transport.loader.exec_module(module)
            service = module.Forgejo(manifest.get("api_host", "code.ffmpeg.org"))
            login = service.login()
        else:
            sys.exit("This venue is held pending its documented submission route.")
        if login != "pjunod":
            sys.exit("Submit using the pjunod account; found " + login)
    work_root = Path(os.environ.get("UPSTREAM_WORK_ROOT", "~/.cache/upstream-prep")).expanduser()
    work_root.mkdir(parents=True, exist_ok=True)
    repository = manifest["repository"]
    url = manifest.get("source_url", "https://github.com/" + repository + ".git")
    target = manifest["target_branch"]
    prepared = []
    for unit in units:
        patches = [(project / p).resolve() for p in unit.get("patches", [])]
        if not patches:
            print(f"{unit['id']}: {unit['status']}: no patch unit; read its DESCRIPTION.md")
            continue
        if any(project not in p.parents or not p.is_file() for p in patches):
            sys.exit("patch escapes project or is missing")
        checkout = Path(tempfile.mkdtemp(prefix=project.name + "-" + unit["id"] + "-", dir=work_root))
        print(f"{unit['id']}: retained preparation checkout {checkout}", flush=True)
        clone = ["git", "clone", "--quiet", "--depth=1", "--single-branch", "--branch", target]
        if sparse_paths:
            clone += ["--filter=blob:none", "--sparse", "--no-checkout"]
        run(clone + [url, str(checkout)])
        if sparse_paths:
            run(["git", "sparse-checkout", "set", "--", *sparse_paths], cwd=checkout)
            run(["git", "checkout", "--quiet", "HEAD"], cwd=checkout)
        current = run(["git", "rev-parse", "HEAD"], cwd=checkout, capture=True)
        base = unit.get("base", manifest["base"])
        if current != base:
            sys.exit(f"Upstream moved from tested base {base} to {current}; refresh and revalidate first.")
        branch = "upstream/" + project.name + "-" + unit["slug"]
        run(["git", "switch", "--quiet", "-c", branch], cwd=checkout)
        run(["git", "config", "user.name", "Paul Junod"], cwd=checkout)
        run(["git", "config", "user.email", "donujp@gmail.com"], cwd=checkout)
        command = ["git", "-c", "commit.gpgsign=false", "am", "--keep-non-patch", "--committer-date-is-author-date"]
        if not args.dry_run:
            command.append("--signoff")
        run(command + [str(p) for p in patches], cwd=checkout)
        print(f"{unit['id']}: patches applied; status={unit['status']}", flush=True)
        prepared.append((unit, checkout, branch))
    if args.dry_run:
        return 0
    for unit, checkout, branch in prepared:
        fork = "pjunod/" + repository.rsplit("/", 1)[1]
        if service:
            fork_url = service.ensure_fork(repository)
            prs = service.pull_requests(repository, branch)
        else:
            run(["gh", "repo", "fork", repository, "--clone=false", "--remote=false"], cwd=checkout)
            metadata = json.loads(run(["gh", "api", "repos/" + fork], capture=True))
            if not metadata.get("fork") or metadata.get("parent", {}).get("full_name", "").lower() != repository.lower():
                sys.exit("The destination repository is not a fork of the recorded upstream.")
            fork_url = "https://github.com/" + fork + ".git"
            prs = json.loads(run(["gh", "pr", "list", "--repo", repository, "--head", "pjunod:" + branch,
                                  "--state", "all", "--json", "number,state,url,baseRefName"], capture=True))
        if any(pr["baseRefName"] != target for pr in prs):
            sys.exit("An existing PR targets another base; resolve it manually.")
        if any(pr["state"] in ("CLOSED", "MERGED") for pr in prs):
            for pr in prs:
                print(pr["state"] + " " + pr["url"])
            continue
        remote_ref = "refs/heads/" + branch
        fork_env = service.git_environment(checkout) if service else None
        def fork_git(arguments, capture=False):
            if service:
                return run(["git", "-c", "credential.helper=", "-c", "http.followRedirects=false", *arguments], cwd=checkout,
                           capture=capture, env_overrides=fork_env)
            return run(["git", *arguments], cwd=checkout, capture=capture)
        existing = fork_git(["ls-remote", fork_url, remote_ref], capture=True)
        if existing:
            fork_git(["fetch", "--quiet", fork_url, remote_ref])
            existing_head = run(["git", "rev-parse", "FETCH_HEAD"], cwd=checkout, capture=True)
            candidate_head = run(["git", "rev-parse", "HEAD"], cwd=checkout, capture=True)
            if existing_head != candidate_head:
                sys.exit("Existing submission branch differs in content or commit metadata; refusing to overwrite it.")
        elif prs:
            sys.exit("An open PR has no source branch; inspect it before resubmission.")
        else:
            fork_git(["push", fork_url, "HEAD:" + remote_ref])
        if prs:
            for pr in prs:
                print(pr["state"] + " " + pr["url"])
            continue
        body = (project / unit["slug"] / "DESCRIPTION.md").resolve()
        draft = manifest.get("draft", False) or unit.get("draft", False)
        if service:
            service.create(repository, branch, target, unit["title"], body, draft)
        else:
            command = ["gh", "pr", "create", "--repo", repository, "--base", target,
                       "--head", "pjunod:" + branch, "--title", unit["title"], "--body-file", str(body)]
            if draft:
                command.append("--draft")
            run(command)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print("submission preparation failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)
