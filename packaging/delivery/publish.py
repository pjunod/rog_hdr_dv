#!/usr/bin/env python3
"""The single publisher for the rog-hdr APT repository.

    ROG_APT_HOST=aptly@<repository host> \\
      packaging/delivery/publish.py --project rog_hdr_dv DIR [--dry-run]

Every .deb in DIR is checked against packaging/delivery/manifest.json:

- its name is listed, by an entry owned by the claimed project;
- its Source is that entry's source, and its architecture is listed;
- each `multiarch_same` name is present on every listed architecture, and
  any Multi-Arch: same package present on two architectures ships
  byte-identical shared files;
- no name or architecture appears twice;
- it has no exact (= ...) dependency on a binary of another manifest entry.
  `--allow-baseline-exact-deps` accepts those for `imported` entries only,
  for the baseline import of the bytes already installed; never for `built`.

Only when every check passes does it change the repository, over ssh to
ROG_APT_HOST as the aptly account:

1. upload the files into a fresh staging directory and verify their hashes;
2. initialize a temporary local repo from the published snapshot and add the files;
3. remove every other version of each published (name, architecture),
   except kernel entries, and nothing of any other name;
4. snapshot the repository as <prefix>-<UTC timestamp>-<project>;
5. `aptly publish switch` to it, signed with the manifest's key;
6. drop all but the newest keep_snapshots publisher snapshots (never the
   published one) and clean the package pool.

A remote lock directory serializes publishers. With a verified release.json,
versions must advance according to dpkg or match the published SHA-256. An exact
replay leaves the published snapshot in place. --dry-run checks the local
inputs and prints the plan without contacting the host. ROG_APT_SSH (default
`ssh -o BatchMode=yes`) and ROG_APT_APTLY (default `aptly`) override the
transport and the aptly command, for testing against a scratch rootDir.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delivery  # noqa: E402

LOCK = ".rog-apt-publish.lock"


class Rejected(Exception):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(manifest, project, debs, allow_baseline_exact=False):
    """Return (errors, notes) for the candidate .debs."""
    errors, notes = [], []
    if project not in manifest["projects"]:
        return [f"unknown project {project!r}; the manifest lists {manifest['projects']}"], notes
    index = delivery.binary_index(manifest)
    unpublished = delivery.unpublished_reasons(manifest)
    seen = {}
    accepted = []
    for deb in debs:
        label = deb.path.name
        entry = index.get(deb.name)
        if entry is None:
            reason = unpublished.get(deb.name, "not in the manifest")
            errors.append(f"{label}: {deb.name} is not published ({reason})")
            continue
        if entry["project"] != project:
            errors.append(f"{label}: {deb.name} belongs to project {entry['project']}, not {project}")
            continue
        if deb.source != entry["source"]:
            errors.append(f"{label}: Source {deb.source} is not the manifest's {entry['source']}")
        architectures = delivery.binary_architectures(entry, deb.name)
        if deb.architecture not in architectures:
            errors.append(f"{label}: architecture {deb.architecture} is not listed for {entry['source']} "
                          f"({', '.join(architectures)}; binary {deb.name})")
        key = (deb.name, deb.architecture)
        if key in seen:
            errors.append(f"{label}: {deb.name} {deb.architecture} is also in {seen[key].path.name}")
            continue
        seen[key] = deb
        accepted.append((deb, entry))

    # A built source is published as one release because its binaries can
    # depend on sibling binaries at exactly the same version.
    built = {}
    for deb, entry in accepted:
        if entry["class"] == "built":
            built.setdefault(entry["source"], []).append((deb, entry))
    for source, items in sorted(built.items()):
        entry = items[0][1]
        expected = {(name, arch) for name in entry["binaries"]
                    for arch in delivery.binary_architectures(entry, name)}
        present = {(deb.name, deb.architecture) for deb, _ in items}
        if missing := sorted(expected - present):
            errors.append(f"{source}: incomplete built release, missing "
                          + ", ".join(f"{name}:{arch}" for name, arch in missing))
        if len({deb.version for deb, _ in items}) != 1:
            errors.append(f"{source}: built release has mixed versions")

    # Multi-Arch: same completeness and shared-file identity.
    by_name = {}
    for deb, entry in accepted:
        by_name.setdefault(deb.name, []).append((deb, entry))
    for name, items in sorted(by_name.items()):
        entry = items[0][1]
        arches = {deb.architecture for deb, _ in items}
        if name in entry.get("multiarch_same", []):
            wanted = set(delivery.binary_architectures(entry, name)) - {"all"}
            missing = sorted(wanted - arches)
            if missing:
                errors.append(f"{name}: Multi-Arch: same pair is incomplete, missing {', '.join(missing)}")
        same = [deb for deb, _ in items if deb.multiarch == "same"]
        if name in entry.get("multiarch_same", []) and len(same) != len(items):
            errors.append(f"{name}: listed in multiarch_same but not every architecture is Multi-Arch: same")
        if len(same) > 1:
            versions = {deb.version for deb in same}
            if len(versions) > 1:
                errors.append(f"{name}: Multi-Arch: same architectures differ in version: {sorted(versions)}")
            first, *rest = same
            for other in rest:
                a, b = first.files(), other.files()
                for path in sorted(set(a) & set(b)):
                    if a[path] != b[path]:
                        errors.append(f"{name}: {path} differs between {first.architecture} and {other.architecture}")

    # Exact dependencies across sources.
    for deb, entry in accepted:
        for field in ("Pre-Depends", "Depends"):
            for target, operator, version in delivery.relations(deb.control.get(field)):
                if operator != "=":
                    continue
                owner = index.get(target)
                if owner is None:
                    if target not in entry["binaries"]:
                        notes.append(f"{deb.path.name}: {field} {target} (= {version}) names an unlisted "
                                     "package (an Ubuntu binary or a virtual ABI name)")
                    continue
                if owner is entry:
                    continue
                message = (f"{deb.path.name}: {field} {target} (= {version}) pins a binary of "
                           f"{owner['source']}, another source")
                if allow_baseline_exact and entry["class"] == "imported":
                    notes.append(message + "; accepted for the baseline import")
                else:
                    errors.append(message)
    return errors, notes


class Remote:
    def __init__(self, host, ssh=None, aptly=None, dry_run=False):
        self.host = host
        self.ssh = shlex.split(ssh or os.environ.get("ROG_APT_SSH", "ssh -o BatchMode=yes"))
        self.aptly_command = shlex.split(aptly or os.environ.get("ROG_APT_APTLY", "aptly"))
        self.dry_run = dry_run

    def run(self, argv, stdin=None, capture=True):
        command = shlex.join(argv)
        if self.dry_run:
            print(f"would run: {command}")
            return ""
        result = subprocess.run(self.ssh + [self.host, command], stdin=stdin,
                                capture_output=capture, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"remote command failed ({result.returncode}): {command}\n"
                               f"{(result.stderr or '').strip()}")
        return result.stdout or ""

    def aptly(self, *args):
        return self.run(self.aptly_command + list(args))

    def upload(self, path, destination):
        if self.dry_run:
            print(f"would upload: {path.name} -> {destination}")
            return
        with open(path, "rb") as stream:
            result = subprocess.run(self.ssh + [self.host, "cat > " + shlex.quote(destination)],
                                    stdin=stream, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"upload of {path.name} failed: {result.stderr.strip()}")


def repository_packages(remote, local_repo):
    """{(name, arch): {versions}} from `aptly repo show -with-packages`."""
    output = remote.aptly("repo", "show", "-with-packages", local_repo)
    packages, listing = {}, False
    for line in output.splitlines():
        if line.startswith("Packages:"):
            listing = True
            continue
        if not listing or not line.strip():
            continue
        parts = line.strip().split("_")
        if len(parts) != 3:
            raise RuntimeError(f"unexpected package reference from aptly: {line.strip()}")
        name, version, arch = parts
        packages.setdefault((name, arch), set()).add(version)
    return packages


def published_snapshot(remote, distribution, component):
    if remote.dry_run:
        remote.aptly("publish", "show", distribution)
        return "<published-snapshot>"
    pattern = rf"\s+{re.escape(component)}: (\S+) \[snapshot\]"
    for line in remote.aptly("publish", "show", distribution).splitlines():
        if match := re.fullmatch(pattern, line):
            return match.group(1)
    raise RuntimeError(f"{distribution}/{component} is not published from a snapshot")


def release_already_published(remote, local_repo, base, debs, release_hashes):
    """Check the entire receipt against the current snapshot under the writer lock."""
    present = repository_packages(remote, local_repo)
    unchanged = True
    for deb in debs:
        versions = present.get((deb.name, deb.architecture), ())
        if deb.version not in versions:
            unchanged = False
        for version in sorted(versions):
            if deb.version != version:
                result = remote.run([
                    "sh", "-c",
                    'dpkg --compare-versions "$1" gt "$2"; rc=$?; '
                    'case "$rc" in 0|1) echo "$rc";; *) exit "$rc";; esac',
                    "compare-versions", deb.version, version,
                ]).strip()
                if result not in {"0", "1"}:
                    raise RuntimeError("unexpected response from dpkg version comparison")
                if result == "1":
                    raise RuntimeError(f"{deb.name}:{deb.architecture} {deb.version} is not newer "
                                       f"than published version {version}")
                continue
            query = (f"Name (= {deb.name}), Architecture (= {deb.architecture}), "
                     f"Version (= {version})")
            hashes = remote.aptly("snapshot", "search", "-format={{.SHA256}}", base, query).split()
            if len(hashes) != 1 or not re.fullmatch(r"[a-f0-9]{64}", hashes[0]):
                raise RuntimeError(f"cannot verify the published hash of {deb.name}:{deb.architecture}")
            if hashes[0] != release_hashes[deb.path.name]:
                raise RuntimeError(f"{deb.name}:{deb.architecture} {version} differs from the published bytes")
    return unchanged


def publish(manifest, project, debs, remote, now=None, release_hashes=None):
    repo = manifest["repository"]
    distribution, component = repo["distribution"], repo["component"]
    prefix, keep = repo["snapshot_prefix"], repo["keep_snapshots"]
    index = delivery.binary_index(manifest)
    stamp = (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y%m%dT%H%M%S%fZ")
    snapshot = f"{prefix}-{stamp}-{project}"
    local_repo = f"{repo['local_repo']}-incoming-{stamp}"

    remote.run(["mkdir", LOCK])
    try:
        base = published_snapshot(remote, distribution, component)
        remote.aptly("repo", "create", local_repo, "from", "snapshot", base)
        try:
            if release_hashes is not None:
                if remote.dry_run:
                    print("would verify the release is newer than the active snapshot or an exact replay")
                elif release_already_published(remote, local_repo, base, debs, release_hashes):
                    print(f"release already matches {base}")
                    return base
            prepare_snapshot(remote, local_repo, snapshot, debs, index, release_hashes)
        finally:
            remote.aptly("repo", "drop", "-force", local_repo)

        switch_options = ["-batch", f"-gpg-key={repo['signing_key']}"]
        try:
            remote.aptly("publish", "switch", *switch_options, distribution, snapshot)
        except RuntimeError as switch_error:
            try:
                active = published_snapshot(remote, distribution, component)
            except RuntimeError as status_error:
                raise RuntimeError(f"publication outcome unknown for {snapshot}; "
                                   f"verify the active snapshot before retrying: {status_error}") from switch_error
            if active != snapshot:
                raise
            print(f"warning: {snapshot} is live but aptly reported an error: {switch_error}",
                  file=sys.stderr)
        print(f"{'would publish' if remote.dry_run else 'published'} {snapshot}")

        if remote.dry_run:
            print(f"would keep the newest {keep} {prefix}-<timestamp>-<project> snapshots and clean the pool")
        else:
            try:
                prune_snapshots(remote, prefix, keep, snapshot)
            except RuntimeError as exc:
                print(f"warning: {snapshot} is live; retention cleanup failed: {exc}", file=sys.stderr)
    finally:
        remote.run(["rmdir", LOCK])
    return snapshot


def prune_snapshots(remote, prefix, keep, active):
    pattern = re.compile(re.escape(prefix) + r"-(\d{8}T\d{6}(?:\d{6})?)Z-[a-z0-9_-]+\Z")
    ours = sorted((match.group(1).ljust(21, "0"), name)
                  for name in remote.aptly("snapshot", "list", "-raw").split()
                  if (match := pattern.fullmatch(name)))
    for _, name in ours[:-keep]:
        if name != active:
            remote.aptly("snapshot", "drop", name)
            print(f"dropped snapshot {name}")
    remote.aptly("db", "cleanup")


def prepare_snapshot(remote, local_repo, snapshot, debs, index, release_hashes=None):
    staging = remote.run(["mktemp", "-d", "rog-apt-incoming.XXXXXXXX"]).strip() or "rog-apt-incoming.DRYRUN"
    try:
        remote_paths = []
        for deb in debs:
            destination = f"{staging}/{deb.path.name}"
            remote.upload(deb.path, destination)
            remote_paths.append(destination)
        if not remote.dry_run:
            sums = remote.run(["sha256sum", "--"] + remote_paths)
            actual = {line.split()[1]: line.split()[0] for line in sums.splitlines() if line.strip()}
            for deb, destination in zip(debs, remote_paths):
                expected = (sha256(deb.path) if release_hashes is None
                            else release_hashes[deb.path.name])
                if actual.get(destination) != expected:
                    raise RuntimeError(f"uploaded {deb.path.name} does not match its expected hash")
        remote.aptly("repo", "add", local_repo, *remote_paths)
    finally:
        remote.run(["rm", "-rf", "--", staging])

    if not remote.dry_run:
        present = repository_packages(remote, local_repo)
        for deb in debs:
            if index[deb.name].get("kernel"):
                continue
            for version in sorted(present.get((deb.name, deb.architecture), set()) - {deb.version}):
                remote.aptly("repo", "remove", local_repo,
                             f"{deb.name}_{version}_{deb.architecture}")
                print(f"removed {deb.name} {version} {deb.architecture}")
    else:
        print("would remove: every other version of each published (name, architecture), kernels excepted")

    remote.aptly("snapshot", "create", snapshot, "from", "repo", local_repo)


def verify_release_receipt(directory, paths, manifest, project, required=False):
    receipt = directory / "release.json"
    if not receipt.is_file():
        if required:
            raise ValueError("release.json is required for project CI publication")
        return
    meta = json.loads(receipt.read_text(encoding="utf-8"), object_pairs_hook=delivery.unique_object)
    channel = manifest.get("release_channels", {}).get(project)
    if channel is None or meta.get("forgejo_repository") != channel["repository"]:
        raise ValueError("release receipt does not identify the selected project")
    if (not isinstance(meta.get("tag"), str) or not meta["tag"].startswith(channel["tag_prefix"])
            or not isinstance(meta.get("source_commit"), str)
            or not re.fullmatch(r"[a-f0-9]{40}", meta["source_commit"])):
        raise ValueError("release receipt must identify a matching tag and source commit")
    current = {path.name: sha256(path) for path in paths}
    if current != meta.get("package_sha256"):
        raise ValueError("package files differ from the verified release receipt")
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory")
    parser.add_argument("--project", required=True)
    parser.add_argument("--manifest", default=str(delivery.MANIFEST))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-baseline-exact-deps", action="store_true")
    parser.add_argument("--require-release-receipt", action="store_true")
    args = parser.parse_args()

    manifest = delivery.load_manifest(args.manifest)
    errors = delivery.validate(manifest)
    if errors:
        print("manifest is invalid:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    directory = Path(args.directory)
    paths = sorted(directory.glob("*.deb"))
    if not paths:
        print(f"publish.py: no .deb in {args.directory}", file=sys.stderr)
        return 1
    try:
        release_hashes = verify_release_receipt(directory, paths, manifest, args.project,
                                               args.require_release_receipt)
    except (OSError, ValueError) as error:
        print(f"publish.py: {error}", file=sys.stderr)
        return 1
    debs, errors = [], []
    for path in paths:
        try:
            debs.append(delivery.Deb(path))
        except (delivery.DebError, OSError, ValueError, EOFError) as exc:
            errors.append(f"{path.name}: unreadable: {exc}")
    more, notes = verify(manifest, args.project, debs, args.allow_baseline_exact_deps)
    errors += more
    for note in notes:
        print(f"note: {note}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        print(f"publish.py: rejected {len(paths)} package(s); nothing was published", file=sys.stderr)
        return 1
    print(f"verified {len(debs)} package(s) for {args.project}")

    host = os.environ.get("ROG_APT_HOST")
    if not host and not args.dry_run:
        print("publish.py: set ROG_APT_HOST to the aptly account on the repository host", file=sys.stderr)
        return 2
    remote = Remote(host or "<ROG_APT_HOST>", dry_run=args.dry_run)
    try:
        publish(manifest, args.project, debs, remote,
                release_hashes=release_hashes)
    except RuntimeError as exc:
        print(f"publish.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
