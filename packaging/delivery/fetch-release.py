#!/usr/bin/env python3
"""Fetch a verified Debian bundle from a configured project's Forgejo release."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import delivery
import publish


class RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def retrieve(manifest, project, tag, output, server, token):
    channel = manifest.get("release_channels", {}).get(project)
    if channel is None:
        raise ValueError(f"{project} has no configured Forgejo release source")
    if not tag.startswith(channel["tag_prefix"]) or not re.fullmatch(r"[a-zA-Z0-9.+_-]+", tag):
        raise ValueError(f"{tag!r} is outside the release tag namespace for {project}")
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists: {output}")
    origin = urlsplit(server)
    if origin.scheme not in ("http", "https") or not origin.hostname or origin.username or origin.password:
        raise ValueError("ROG_APT_FORGEJO_URL must name the Forgejo server")
    opener = build_opener(RefuseRedirects())
    token_header = {"Authorization": f"token {token}"}
    repository = channel["repository"]
    base = server.rstrip("/")
    api = f"{base}/api/v1/repos/{repository}"

    def request(url):
        actual = urlsplit(url)
        if (actual.scheme, actual.netloc) != (origin.scheme, origin.netloc):
            raise ValueError("release asset left the configured Forgejo origin")
        return opener.open(Request(url, headers=token_header), timeout=60)

    with request(f"{api}/releases/tags/{quote(tag, safe='')}") as response:
        release = json.load(response)
    if release["tag_name"] != tag or release["draft"]:
        raise ValueError("expected a published release at the exact tag")
    with request(f"{api}/tags/{quote(tag, safe='')}") as response:
        commit = json.load(response)["commit"]["sha"]
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("release tag did not resolve to a Git commit")
    assets = {}
    for asset in release["assets"]:
        name = asset["name"]
        if "/" in name or name in assets or name in (".", ".."):
            raise ValueError(f"invalid or repeated asset: {name!r}")
        assets[name] = asset["browser_download_url"]

    with request(assets["SHA256SUMS"]) as response:
        sums = response.read(65537).decode("ascii")
    if len(sums) > 65536:
        raise ValueError("release checksum list is too large")
    expected = {}
    for line in sums.splitlines():
        digest, name = line.split(maxsplit=1)
        if not name.endswith(".deb"):
            continue
        if (not re.fullmatch(r"[a-z0-9][a-zA-Z0-9_.+:~%-]+[.]deb", name)
                or not re.fullmatch(r"[a-f0-9]{64}", digest) or name in expected):
            raise ValueError(f"invalid Debian package checksum record: {line!r}")
        expected[name] = digest
    if not expected or set(expected) != {name for name in assets if name.endswith(".deb")}:
        raise ValueError("release package list and checksums differ")

    with tempfile.TemporaryDirectory(prefix=".rog-release-", dir=output.parent) as temporary:
        staging = Path(temporary) / "release"
        staging.mkdir()
        for name, digest in sorted(expected.items()):
            path = staging / name
            with request(assets[name]) as response, path.open("wb") as stream:
                shutil.copyfileobj(response, stream)
            if publish.sha256(path) != digest:
                raise ValueError(f"{name} differs from the released digest")
        debs = [delivery.Deb(staging / name) for name in expected]
        errors, notes = publish.verify(manifest, project, debs)
        for note in notes:
            print(f"note: {note}")
        if errors:
            raise ValueError("\n".join(errors))
        versions = {deb.version for deb in debs}
        if len(versions) != 1:
            raise ValueError("one source release must carry one Debian version")
        version = versions.pop().replace("_", "_u").replace(":", "_c").replace("~", "_t")
        if tag != channel["tag_prefix"] + version:
            raise ValueError("Debian package version differs from the release tag")
        (staging / "release.json").write_text(json.dumps({
            "forgejo_repository": repository, "tag": tag, "source_commit": commit,
            "package_sha256": expected,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        staging.rename(output)
    print(f"verified {len(expected)} package(s) from {repository}@{commit} ({tag})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("tag")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        manifest = delivery.load_manifest()
        if errors := delivery.validate(manifest):
            raise ValueError("\n".join(errors))
        retrieve(manifest, args.project, args.tag, args.output,
                 os.environ["ROG_APT_FORGEJO_URL"], os.environ["ROG_APT_FORGEJO_TOKEN"])
    except (KeyError, OSError, ValueError) as error:
        sys.exit(f"fetch-release: {error}")


if __name__ == "__main__":
    main()
