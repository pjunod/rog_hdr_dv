#!/usr/bin/env python3
"""Fetch the repository's public signing key into rog-apt-config/keyrings/.

    packaging/delivery/fetch-key.py --url URL

The key is public; the web server still asks every client for the reader
account, so the password comes from the environment (operator secret store
entry rog-apt-reader) and is never written anywhere. Set the endpoint with
--url or ROG_APT_REPOSITORY_URL. The fetched key must carry the manifest's
fingerprint before it is written. Commit the updated public key afterwards.
"""

import argparse
import base64
import os
import re
import sys
import urllib.request
from urllib.parse import urlsplit

import delivery


class RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("ROG_APT_REPOSITORY_URL"), help="repository base URL")
    parser.add_argument("--user", default="rog-apt-reader")
    args = parser.parse_args()
    password = os.environ.get("ROG_APT_READER_PASSWORD")
    if not password:
        print("fetch-key.py: set ROG_APT_READER_PASSWORD", file=sys.stderr)
        return 2
    uri = args.url or ""
    parsed = urlsplit(uri)
    if (not re.fullmatch(r"https?://[A-Za-z0-9_.:/%~+\[\]-]+", uri)
            or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        parser.error("provide a credential-free APT repository URL with --url or ROG_APT_REPOSITORY_URL")
    try:
        parsed.port
    except ValueError as error:
        parser.error(str(error))
    base = uri.rstrip("/")
    request = urllib.request.Request(f"{base}/rog-hdr-archive-keyring.asc")
    token = base64.b64encode(f"{args.user}:{password}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")
    opener = urllib.request.build_opener(RejectRedirect, urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=30) as response:
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
