"""Render the private APT endpoint into the packaged source stanza."""

import os
from pathlib import Path
import re
from urllib.parse import urlsplit


def main():
    uri = os.environ.get("ROG_APT_REPOSITORY_URL", "")
    parsed = urlsplit(uri)
    if (not re.fullmatch(r"https?://[A-Za-z0-9_.:/%~+\[\]-]+", uri)
            or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise SystemExit("set ROG_APT_REPOSITORY_URL to the credential-free APT repository URL")
    # Accessing port validates its syntax and range before APT sees the stanza.
    try:
        parsed.port
    except ValueError as error:
        raise SystemExit(str(error)) from error
    template = Path(__file__).with_name("rog-hdr.sources.in")
    output = template.with_suffix("")
    text = template.read_text(encoding="utf-8")
    output.write_text(text.replace("@REPOSITORY_URL@", uri.rstrip("/") + "/"), encoding="utf-8")


if __name__ == "__main__":
    main()
