#!/usr/bin/env python3
"""Fetch the repository's public signing key into rog-apt-config/keyrings/.

    ROG_APT_READER_PASSWORD=... packaging/delivery/fetch-key.py [--url URL]

The key is public; the web server still asks every client for the reader
account, so the password comes from the environment (operator secret store
entry rog-apt-reader) and is never written anywhere. The URL defaults to the
URIs line of rog-apt-config/debian/rog-hdr.sources; pass --url when the
neutral host name does not resolve. The fetched key must carry the manifest's
fingerprint, or nothing is written. Commit the key file afterwards.
"""

import argparse
import base64
import os
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delivery  # noqa: E402

SOURCES = delivery.HERE / "rog-apt-config" / "debian" / "rog-hdr.sources"


def repository_url():
    for line in SOURCES.read_text(encoding="utf-8").splitlines():
        if line.startswith("URIs:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit(f"{SOURCES}: no URIs line")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=None, help="repository base URL")
    parser.add_argument("--user", default="rog-apt-reader")
    args = parser.parse_args()
    password = os.environ.get("ROG_APT_READER_PASSWORD")
    if not password:
        print("fetch-key.py: set ROG_APT_READER_PASSWORD", file=sys.stderr)
        return 2
    base = (args.url or repository_url()).rstrip("/")
    request = urllib.request.Request(f"{base}/rog-hdr-archive-keyring.asc")
    token = base64.b64encode(f"{args.user}:{password}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        armored = response.read().decode("ascii")
    expected = delivery.load_manifest()["repository"]["signing_key"]
    actual = delivery.openpgp_fingerprint(armored)
    if actual != expected:
        print(f"fetch-key.py: served key is {actual}, the manifest expects {expected}", file=sys.stderr)
        return 1
    delivery.KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    delivery.KEY_FILE.write_text(armored, encoding="ascii")
    print(f"wrote {delivery.KEY_FILE} ({actual})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
