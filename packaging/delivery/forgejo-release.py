#!/usr/bin/env python3
"""Transfer verified Debian bundles through a project's Forgejo release."""

import argparse
import hashlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

import delivery
import publish


class RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def project_release_api(manifest, project, server, token):
    channel = manifest.get("release_channels", {}).get(project)
    if channel is None:
        raise ValueError(f"{project} has no configured Forgejo release source")
    origin = urlsplit(server)
    if (origin.scheme not in ("http", "https") or not origin.hostname or origin.username
            or origin.password or origin.path.rstrip("/") or origin.query or origin.fragment):
        raise ValueError("ROG_APT_FORGEJO_URL must name the Forgejo server")
    if origin.scheme != "https" and origin.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Forgejo access requires HTTPS or a local endpoint on an authenticated tunnel")
    opener = build_opener(RefuseRedirects())

    def request(url, method="GET", payload=None, mime="application/json"):
        actual = urlsplit(url)
        if (actual.scheme, actual.netloc) != (origin.scheme, origin.netloc):
            raise ValueError("release asset left the configured Forgejo origin")
        headers = {"Authorization": f"token {token}", "Content-Type": mime}
        return opener.open(Request(url, payload, headers, method=method), timeout=60)

    api = f"{server.rstrip('/')}/api/v1/repos/{channel['repository']}"
    return channel, api, request, server.rstrip("/")


def release_commit(api, request, tag, missing_ok=False):
    try:
        with request(f"{api}/tags/{quote(tag, safe='')}") as response:
            commit = json.load(response)["commit"]["sha"]
    except HTTPError as error:
        if error.code == 404 and missing_ok:
            return None
        raise
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("release tag did not resolve to a Git commit")
    return commit


def read_assets(release, base, repository, tag):
    assets = {}
    for asset in release["assets"]:
        name = asset["name"]
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.+:~%-]+", name) or name in assets:
            raise ValueError(f"invalid or repeated asset: {name!r}")
        if asset["type"] != "attachment":
            raise ValueError(f"{name} is not an uploaded Forgejo asset")
        assets[name] = f"{base}/{repository}/releases/download/{tag}/{quote(name, safe='')}"
    return assets


def checksum_records(sums):
    expected = {}
    for line in sums.splitlines():
        digest, name = line.split(maxsplit=1)
        if (not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.+:~%-]+", name)
                or not re.fullmatch(r"[a-f0-9]{64}", digest) or name in expected):
            raise ValueError(f"invalid release checksum record: {line!r}")
        expected[name] = digest
    return expected


def package_tag(manifest, project, channel, debs):
    errors, notes = publish.verify(manifest, project, debs)
    for note in notes:
        print(f"note: {note}")
    if errors:
        raise ValueError("\n".join(errors))
    if len({(deb.source, deb.version) for deb in debs}) != 1:
        raise ValueError("one source release must carry one Debian source and version")
    version = debs[0].version.replace("_", "_u").replace(":", "_c").replace("~", "_t")
    return channel["tag_prefix"] + version


def retrieve(manifest, project, tag, output, server, token):
    channel, api, request, base = project_release_api(manifest, project, server, token)
    if not tag.startswith(channel["tag_prefix"]) or not re.fullmatch(r"[a-zA-Z0-9.+_-]+", tag):
        raise ValueError(f"{tag!r} is outside the release tag namespace for {project}")
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists: {output}")
    with request(f"{api}/releases/tags/{quote(tag, safe='')}") as response:
        release = json.load(response)
    if release["tag_name"] != tag or release["draft"]:
        raise ValueError("expected a published release at the exact tag")
    commit = release_commit(api, request, tag)
    receipt = re.search(r"Source commit `([a-f0-9]{40})`[.]", release.get("body") or "")
    if receipt is None or receipt[1] != commit:
        raise ValueError("release source receipt does not match the repository tag")
    assets = read_assets(release, base, channel["repository"], tag)
    with request(assets["SHA256SUMS"]) as response:
        sums = response.read(65537).decode("ascii")
    if len(sums) > 65536:
        raise ValueError("release checksum list is too large")
    expected = {name: digest for name, digest in checksum_records(sums).items() if name.endswith(".deb")}
    if not expected or set(expected) != {name for name in assets if name.endswith(".deb")}:
        raise ValueError("release package list and checksums differ")

    with tempfile.TemporaryDirectory(prefix=".rog-release-", dir=output.parent) as temporary:
        staging = Path(temporary) / "release"
        staging.mkdir(mode=0o700)
        for name, digest in sorted(expected.items()):
            path = staging / name
            with request(assets[name]) as response, path.open("wb") as stream:
                shutil.copyfileobj(response, stream)
            if publish.sha256(path) != digest:
                raise ValueError(f"{name} differs from the released digest")
        debs = [delivery.Deb(staging / name) for name in expected]
        if tag != package_tag(manifest, project, channel, debs):
            raise ValueError("Debian package version differs from the release tag")
        (staging / "release.json").write_text(json.dumps({
            "forgejo_repository": channel["repository"], "tag": tag, "source_commit": commit,
            "package_sha256": expected,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        staging.rename(output)
    print(f"verified {len(expected)} package(s) from {channel['repository']}@{commit} ({tag})")


def attach(manifest, project, directory, revision, server, token):
    channel, api, request, base = project_release_api(manifest, project, server, token)
    if revision != os.environ["FORGEJO_SHA"] or os.environ["FORGEJO_REPOSITORY"] != channel["repository"]:
        raise ValueError("release must run from the configured Forgejo project and checkout")
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("release checkout must name a full Git commit")
    checksums = directory / "SHA256SUMS"
    if checksums.is_symlink() or not checksums.is_file():
        raise ValueError("release needs a local SHA256SUMS file")
    files = checksum_records(checksums.read_text(encoding="ascii"))
    if checksums.name in files:
        raise ValueError("SHA256SUMS cannot list itself")
    for name, digest in files.items():
        path = directory / name
        if not path.is_file() or path.is_symlink() or publish.sha256(path) != digest:
            raise ValueError(f"{name} differs from the build receipt")
    debs = [delivery.Deb(directory / name) for name in files if name.endswith(".deb")]
    tag = package_tag(manifest, project, channel, debs)
    if not re.fullmatch(r"[a-zA-Z0-9.+_-]+", tag):
        raise ValueError("package version cannot be represented as a release tag")

    with request(api) as response:
        if json.load(response)["private"] is not True:
            raise ValueError("package staging requires a private project repository")
    if release_commit(api, request, tag, missing_ok=True) not in (None, revision):
        raise ValueError(f"{tag} points to a different Git commit")
    body = f"CI-verified APT package release. Source commit `{revision}`."
    try:
        with request(f"{api}/releases/tags/{tag}") as response:
            release = json.load(response)
    except HTTPError as error:
        if error.code != 404:
            raise
        data = {"tag_name": tag, "target_commitish": revision, "name": tag, "body": body,
                "draft": True, "prerelease": True}
        with request(f"{api}/releases", "POST", json.dumps(data).encode()) as response:
            release = json.load(response)
    if release["body"] != body or (release["draft"] and release["target_commitish"] != revision):
        raise ValueError(f"{tag} belongs to a different build")
    assets = read_assets(release, base, channel["repository"], tag)
    files["SHA256SUMS"] = publish.sha256(checksums)
    if assets.keys() - files.keys() or (not release["draft"] and assets.keys() != files.keys()):
        raise ValueError(f"{tag} has an unexpected asset list")
    url = f"{api}/releases/{release['id']}"
    for name, digest in files.items():
        if name in assets:
            with request(assets[name]) as response:
                if hashlib.file_digest(response, "sha256").hexdigest() != digest:
                    raise ValueError(f"{tag}/{name} differs from the retained release")
            continue
        boundary = uuid4().hex
        header = (f"--{boundary}\r\nContent-Disposition: form-data; "
                  f'name="attachment"; filename="{name}"\r\n'
                  "Content-Type: application/octet-stream\r\n\r\n")
        payload = header.encode("ascii") + (directory / name).read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        with request(f"{url}/assets?{urlencode({'name': name})}", "POST", payload,
                     f"multipart/form-data; boundary={boundary}"):
            pass
    if release["draft"]:
        with request(url, "PATCH", b'{"draft":false}'):
            pass
    if release_commit(api, request, tag) != revision:
        raise ValueError(f"published tag {tag} does not point to the build")
    print(f"attached verified package assets to {tag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--attach", action="store_true", help="attach a CI release instead of retrieving one")
    parser.add_argument("ref", help="release tag for retrieval or checkout commit for attachment")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        manifest = delivery.load_manifest()
        if errors := delivery.validate(manifest):
            raise ValueError("\n".join(errors))
        server, token = os.environ["ROG_APT_FORGEJO_URL"], os.environ["ROG_APT_FORGEJO_TOKEN"]
        if args.attach:
            attach(manifest, args.project, args.directory, args.ref, server, token)
        else:
            retrieve(manifest, args.project, args.ref, args.directory, server, token)
    except (KeyError, OSError, ValueError) as error:
        sys.exit(f"forgejo-release: {error}")


if __name__ == "__main__":
    main()
