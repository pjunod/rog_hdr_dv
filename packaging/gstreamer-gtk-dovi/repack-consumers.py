#!/usr/bin/python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Record and verify metadata-only re-releases of the GTK sink and Showtime.

Both packages carry exact dependency pins on coupled libraries. When one of
those is re-released the consumers are repacked with the same payload, a new
Version and updated pins; package-inputs/consumer-releases.json records them.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[1]
RELEASES = FOLDER / "package-inputs/consumer-releases.json"
PACKAGES = {"rust-gst-plugin-gtk4": "gstreamer1.0-gtk4", "showtime": "showtime"}
SHA = re.compile(r"[0-9a-f]{64}")

_spec = importlib.util.spec_from_file_location("prepare_ubuntu_packages", FOLDER / "prepare-ubuntu-packages.py")
recipe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(recipe)
PreparationError = recipe.PreparationError


def _checked_sha(value, label):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise PreparationError(f"{label}: expected a lowercase 64-hex sha256")
    return value


def consumer_releases():
    """Load and validate the recorded consumer re-releases."""
    data = json.loads(RELEASES.read_text())
    if data.get("schema") != 1 or set(data) != {"schema", "releases"}:
        raise PreparationError("consumer-releases.json: unsupported schema")
    releases = data["releases"]
    if set(releases) != set(PACKAGES):
        raise PreparationError("consumer-releases.json: unexpected source set")
    for source, entry in releases.items():
        if entry.get("package") != PACKAGES[source]:
            raise PreparationError(f"{source}: unexpected package name")
        if not entry.get("architecture"):
            raise PreparationError(f"{source}: missing architecture")
        base, release = entry["base"], entry["release"]
        _checked_sha(base.get("deb_sha256"), f"{source} base")
        _checked_sha(release.get("deb_sha256"), f"{source} release")
        match = re.fullmatch(r"\+depfix([1-9][0-9]*)", release["version"][len(base["version"]):]) \
            if release["version"].startswith(base["version"]) else None
        if not base["version"] or not match:
            raise PreparationError(f"{source}: release version must be base version + '+depfixN'")
        receipt = Path(release.get("receipt", ""))
        if receipt.is_absolute() or ".." in receipt.parts or receipt.parts[:1] != ("evidence",) \
                or not (ROOT / receipt).is_file():
            raise PreparationError(f"{source}: receipt must be an existing relative path under evidence/")
    return releases


def current_pins():
    """Exact versions the consumers must pin to for the current library set."""
    pins = dict(recipe.qualified_pipeline())
    pins["libgstgtk-dovi-core0"] = recipe.CORE_VERSION
    pins["gstreamer1.0-gtk-dovi"] = recipe.CORE_VERSION
    pins["libgtk-4-1"] = recipe.FIXED_GTK
    pins["gstreamer1.0-gtk4"] = consumer_releases()["rust-gst-plugin-gtk4"]["release"]["version"]
    return pins


def _rewrite_relations(value, pins):
    def one(match):
        relation = match.group(0)
        exact = re.fullmatch(r"(\s*)([A-Za-z0-9][A-Za-z0-9.+-]*) \(= ([^)\s]+)\)(\s*)", relation)
        if not exact or exact.group(2) not in pins:
            return relation
        lead, name, _, trail = exact.groups()
        return f"{lead}{name} (= {pins[name]}){trail}"
    return re.sub(r"[^,]+", one, value)


def release_control(base_control_text, release_version, pins):
    """Return the binary control stanza for the re-release."""
    text = base_control_text.rstrip("\n")
    for field in ("Package", "Version", "Depends"):
        if not re.search(rf"^{field}:", text, re.M):
            raise PreparationError(f"control lacks {field}")
    text = re.sub(r"^Version:.*$", lambda _: f"Version: {release_version}", text, count=1, flags=re.M)
    text = re.sub(
        r"^((?:Pre-)?Depends:)(.*(?:\n[ \t].*)*)",
        lambda m: m.group(1) + _rewrite_relations(m.group(2), pins), text, flags=re.M)
    return text + "\n"


def parse_control(text):
    """Parse a control stanza into fields with folded whitespace."""
    fields, name = {}, None
    for line in text.splitlines():
        if line[:1] in " \t" and name:
            fields[name] += " " + line
        elif ":" in line:
            name, value = line.split(":", 1)
            fields[name] = value
    return {key: " ".join(value.split()) for key, value in fields.items()}


def _sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _recorded(source):
    releases = consumer_releases()
    if source not in releases:
        raise PreparationError(f"unknown consumer source {source}")
    return releases[source]


def _require_base(entry, base_deb):
    if _sha256_file(base_deb) != entry["base"]["deb_sha256"]:
        raise PreparationError("base package sha256 does not match the recorded base")


def _dpkg_field_text(deb):
    return subprocess.run(["dpkg-deb", "-f", str(deb)], check=True, capture_output=True, text=True).stdout


def _expected_control(entry, base_deb):
    return release_control(_dpkg_field_text(base_deb), entry["release"]["version"], current_pins())


def repack(source, base_deb, out_dir):
    """Build the recorded re-release from the recorded base package."""
    entry = _recorded(source)
    _require_base(entry, base_deb)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        tree = Path(work) / "tree"
        subprocess.run(["dpkg-deb", "-R", str(base_deb), str(tree)], check=True)
        (tree / "DEBIAN/control").write_text(_expected_control(entry, base_deb))
        output = out_dir / f"{entry['package']}_{entry['release']['version']}_{entry['architecture']}.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(tree), str(output)], check=True)
    print(output)
    print(_sha256_file(output))
    return output


def payload_listing(deb):
    """Return payload members with ownership, mode, link target and content hash."""
    with tempfile.TemporaryDirectory() as work:
        archive = Path(work) / "payload.tar"
        with archive.open("wb") as handle:
            subprocess.run(["dpkg-deb", "--fsys-tarfile", str(deb)], check=True, stdout=handle)
        listing = {}
        with tarfile.open(archive) as tar:
            for member in tar:
                digest = ""
                if member.isreg():
                    digest = hashlib.sha256(tar.extractfile(member).read()).hexdigest()
                listing[member.name] = (
                    member.type, member.mode, member.uid, member.gid, member.uname, member.gname,
                    member.size, member.linkname, digest)
        return listing


def verify(source, base_deb, candidate_deb, recorded=False):
    """Prove the candidate is the base payload with only the generated control."""
    entry = _recorded(source)
    _require_base(entry, base_deb)
    expected = parse_control(_expected_control(entry, base_deb))
    actual = parse_control(_dpkg_field_text(candidate_deb))
    if actual != expected:
        changed = sorted(key for key in set(actual) | set(expected) if actual.get(key) != expected.get(key))
        raise PreparationError(f"candidate control differs from the generated control: {', '.join(changed)}")
    if payload_listing(base_deb) != payload_listing(candidate_deb):
        raise PreparationError("candidate payload differs from the base payload")
    digest = _sha256_file(candidate_deb)
    matches = digest == entry["release"]["deb_sha256"]
    print(f"candidate sha256 {digest} "
          f"{'equals' if matches else 'differs from'} the recorded release sha256")
    if recorded and not matches:
        raise PreparationError("candidate is not the recorded release")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("repack")
    build.add_argument("source")
    build.add_argument("base_deb")
    build.add_argument("out_dir")
    check = commands.add_parser("verify")
    check.add_argument("source")
    check.add_argument("base_deb")
    check.add_argument("candidate_deb")
    check.add_argument("--recorded", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "repack":
            repack(args.source, args.base_deb, args.out_dir)
        else:
            verify(args.source, args.base_deb, args.candidate_deb, args.recorded)
    except (PreparationError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"repack refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
