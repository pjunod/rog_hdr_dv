#!/usr/bin/env python3
"""Prepare only our two kernel follow-ups; never send email from this helper."""
from __future__ import annotations
import argparse
from email.parser import Parser
from email.utils import parseaddr
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from urllib.request import urlopen

PROJECT = Path(__file__).resolve().parent
OWNER = "Paul Junod <donujp@gmail.com>"


def run(args, *, cwd=None, capture=False):
    result = subprocess.run(args, cwd=cwd, text=True, check=True,
                            stdout=subprocess.PIPE if capture else None,
                            env=os.environ | {"GIT_COMMITTER_NAME": "Paul Junod",
                                              "GIT_COMMITTER_EMAIL": "donujp@gmail.com"})
    return result.stdout.strip() if capture else ""


class ThreadParser(HTMLParser):
    message_id = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "msgid":
            self.message_id = attrs.get("value")


def message_id(value):
    value = value.strip().removeprefix("<").removesuffix(">")
    if not re.fullmatch(r"[^\s<>]+@[^\s<>]+", value):
        raise ValueError("thread must be a Message-ID without whitespace or headers")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("unit", nargs="?", default="02", choices=["01", "02", "03", "all"])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="apply and emit unsigned email files")
    mode.add_argument("--prepare", action="store_true",
                      help="human invocation: certify DCO for our two patches and emit email files")
    parser.add_argument("--thread", help="human-verified latest cover Message-ID; required for --prepare")
    parser.add_argument("--source", type=Path, help="read-only existing source cache containing the pinned base")
    parser.add_argument("--lookup-thread", action="store_true", help="read the original cover Message-ID from its public archive")
    args = parser.parse_args()
    thread_record = json.loads((PROJECT / "thread.json").read_text())
    if args.lookup_thread:
        with urlopen(thread_record["archive_url"], timeout=20) as response:
            page = response.read().decode("utf-8")
        reader = ThreadParser()
        reader.feed(page)
        print(message_id(reader.message_id or ""))
        print("Original cover only; verify whether a newer revision supersedes it before preparing mail.")
        return 0
    if not args.dry_run and not args.prepare:
        parser.error("choose --dry-run or --prepare; --prepare adds your personal DCO")
    if args.prepare and not args.thread:
        parser.error("--prepare requires --thread with the latest cover Message-ID you verified")
    thread = message_id(args.thread or thread_record["message_id"])
    manifest = json.loads((PROJECT / "manifest.json").read_text())
    units = [u for u in manifest["units"] if args.unit in (u["id"], "all")]
    for unit in units:
        if unit["id"] != "02":
            print(f"{unit['id']}: draft only; read {PROJECT / unit['slug'] / 'DESCRIPTION.md'}")
    if not any(u["id"] == "02" for u in units):
        return 0
    unit = next(u for u in units if u["id"] == "02")
    prerequisites = [PROJECT / p for p in unit["prerequisite_patches"]]
    outgoing = [PROJECT / p for p in unit["outgoing_patches"]]
    if len(prerequisites) != 2 or len(outgoing) != 2:
        raise ValueError("expected Cristian's two prerequisites and our two follow-ups")
    for path in prerequisites + outgoing:
        if PROJECT not in path.resolve().parents or not path.is_file():
            raise ValueError("missing or escaping patch")
    for path in outgoing:
        headers = Parser().parsestr("\n".join(path.read_text().splitlines()[1:]))
        if parseaddr(headers.get("From", "")) != ("Paul Junod", "donujp@gmail.com"):
            raise ValueError("outgoing patch is not authored by the owner; refusing to add DCO")
    work_root = Path(os.environ.get("UPSTREAM_WORK_ROOT", "~/work/upstream-prep/linux-mail")).expanduser()
    work_root.mkdir(parents=True, exist_ok=True)
    retained = Path(tempfile.mkdtemp(prefix="linux-mail-", dir=work_root))
    checkout = retained / "source"
    command = ["git", "clone", "--quiet", "--no-checkout"]
    if args.source:
        command += ["--shared", str(args.source.resolve()), str(checkout)]
    else:
        command += ["--depth=1", "--single-branch", "--branch", manifest["target_branch"], manifest["source_url"], str(checkout)]
    run(command)
    if not args.source:
        current = run(["git", "rev-parse", "HEAD"], cwd=checkout, capture=True)
        if current != manifest["base"]:
            raise ValueError(f"upstream moved to {current}; refresh and requalify before preparing mail")
    run(["git", "switch", "--quiet", "--detach", manifest["base"]], cwd=checkout)
    run(["git", "config", "user.name", "Paul Junod"], cwd=checkout)
    run(["git", "config", "user.email", "donujp@gmail.com"], cwd=checkout)
    run(["git", "-c", "commit.gpgsign=false", "am", *map(str, prerequisites)], cwd=checkout)
    command = ["git", "-c", "commit.gpgsign=false", "am"] + (["--signoff"] if args.prepare else [])
    run(command + list(map(str, outgoing)), cwd=checkout)
    tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout, capture=True)
    if tree != unit["candidate_tree"]:
        raise ValueError("prepared source differs from the qualified candidate tree")
    authors = run(["git", "log", "-2", "--format=%an <%ae>"], cwd=checkout, capture=True).splitlines()
    if authors != [OWNER, OWNER]:
        raise ValueError("outgoing range contains an author other than the owner; refusing third-party resubmission")
    output = retained / "outgoing"
    run(["git", "format-patch", "--cover-letter", "--no-signature", "--in-reply-to", thread,
         "--output-directory", str(output), "HEAD~2..HEAD"], cwd=checkout)
    covers = list(output.glob("0000-*.patch"))
    cover = covers[0]
    text = cover.read_text().replace("*** SUBJECT HERE ***", "drm: validate native DisplayID luminance")
    description = (PROJECT / unit["slug"] / "DESCRIPTION.md").read_text()
    text = text.replace("*** BLURB HERE ***", description)
    cover.write_text(text)
    files = sorted(output.glob("*.patch"))
    if len(files) != 3:
        raise ValueError("outgoing mail must contain one cover and only our two patches")
    maintainers = run([str(checkout / "scripts/get_maintainer.pl"), "--no-git", "--nogit-fallback",
                       *map(str, [p for p in files if p != cover])], cwd=checkout, capture=True)
    recipients = sorted(set(re.findall(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", maintainers)))
    if not recipients:
        raise ValueError("get_maintainer.pl returned no recipients")
    if args.prepare:
        send = ["git", "send-email", "--from", OWNER, "--to", "cristian.laspina@kernel.srl"]
        for recipient in recipients:
            if recipient != "cristian.laspina@kernel.srl":
                send += ["--cc", recipient]
        send += list(map(str, files))
        (output / "SEND_COMMAND.sh").write_text("#!/bin/sh\nset -eu\n" + shlex.join(send) + "\n")
    receipt = dict(base=manifest["base"], candidate_tree=tree, thread=thread,
                   dco_added_by_explicit_prepare=args.prepare, mail_sent=False, recipients=recipients,
                   patches={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Prepared " + ("owner-signed" if args.prepare else "unsigned") + " email files: " + str(output))
    print("Only our two follow-ups are exported. No email was sent; review the cover, recipients and files.")
    if args.prepare:
        print("After review and SMTP setup: sh " + shlex.quote(str(output / "SEND_COMMAND.sh")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print("kernel preparation failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)
