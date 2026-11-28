"""Shared logic for the package-delivery manifest, pins and publisher.

Standard library only: the publisher runs on the repository's runner and the
repository check runs anywhere Python 3 does. Reading .deb files needs no
dpkg; zstd-compressed members need Python 3.14 or newer.
"""

import base64
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.json"
PIN_FILE = HERE / "rog-apt-config" / "preferences.d" / "rog-hdr"
KEY_FILE = HERE / "rog-apt-config" / "keyrings" / "rog-hdr-archive-keyring.asc"

CLASSES = ("built", "imported")
ARCHITECTURES = ("amd64", "i386", "all")
NAME = re.compile(r"[a-z0-9][a-z0-9+.-]+\Z")
PROJECT = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")
FINGERPRINT = re.compile(r"[0-9A-F]{40}\Z")
SERIES = re.compile(r"(?:patches|packaging)/[A-Za-z0-9._/-]+\Z")
SNAPSHOT_STAMP = re.compile(r"\d{8}T\d{6}Z\Z")

ENTRY_FIELDS = {"source", "project", "class", "binaries", "architectures",
                "shadows_ubuntu", "version", "series", "reconcile_with",
                "multiarch_same", "binary_architectures", "binary_versions", "kernel", "note"}
REQUIRED_ENTRY_FIELDS = {"source", "project", "class", "binaries",
                         "architectures", "shadows_ubuntu", "version"}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_manifest(path=MANIFEST):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object)


def _string_list(value, pattern=NAME):
    return (isinstance(value, list) and bool(value)
            and all(isinstance(v, str) and pattern.fullmatch(v) for v in value))


def validate(manifest, root=None):
    """Return a list of schema errors; an empty list means valid.

    root, when given, is the repository root used to check that each
    `series` path exists.
    """
    errors = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    if type(manifest.get("schema")) is not int or manifest.get("schema") != 1:
        errors.append("manifest schema must be integer 1")
    if manifest.get("origin") != "rog-hdr":
        errors.append("manifest origin must be rog-hdr")
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        errors.append("manifest repository must be an object")
        repository = {}
    for field in ("local_repo", "distribution", "component", "snapshot_prefix"):
        if not isinstance(repository.get(field), str) or not NAME.fullmatch(repository.get(field, "")):
            errors.append(f"repository.{field} must be a package-style name")
    if not isinstance(repository.get("signing_key"), str) or not FINGERPRINT.fullmatch(repository["signing_key"]):
        errors.append("repository.signing_key must be a 40-digit uppercase fingerprint")
    keep = repository.get("keep_snapshots")
    if type(keep) is not int or keep < 2:
        errors.append("repository.keep_snapshots must be an integer of at least 2")
    if not _string_list(repository.get("architectures")) or not set(repository.get("architectures", [])) <= {"amd64", "i386"}:
        errors.append("repository.architectures must list amd64 and/or i386")
    projects = manifest.get("projects")
    if not _string_list(projects, PROJECT) or len(set(projects)) != len(projects):
        errors.append("projects must be a nonempty list of unique project names")
        projects = []
    channels = manifest.get("release_channels", {})
    if not isinstance(channels, dict):
        errors.append("release_channels must be an object")
    else:
        for project, channel in channels.items():
            if (project not in projects or not isinstance(channel, dict)
                    or not isinstance(channel.get("repository"), str)
                    or not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", channel["repository"])
                    or not isinstance(channel.get("tag_prefix"), str)
                    or not re.fullmatch(r"[a-z0-9-]+-", channel["tag_prefix"])):
                errors.append(f"invalid release channel for project {project!r}")
    packages = manifest.get("packages")
    if not isinstance(packages, list) or not packages:
        return errors + ["packages must be a nonempty list"]
    sources = set()
    for number, entry in enumerate(packages, 1):
        where = f"packages[{number}]"
        if not isinstance(entry, dict):
            errors.append(f"{where} must be an object")
            continue
        source = entry.get("source")
        if isinstance(source, str):
            where = f"package {source}"
        unknown = set(entry) - ENTRY_FIELDS
        missing = REQUIRED_ENTRY_FIELDS - set(entry)
        if unknown:
            errors.append(f"{where}: unknown fields {sorted(unknown)}")
        if missing:
            errors.append(f"{where}: missing fields {sorted(missing)}")
            continue
        if not isinstance(source, str) or not NAME.fullmatch(source):
            errors.append(f"{where}: invalid source name")
        elif source in sources:
            errors.append(f"duplicate source entry: {source}")
        sources.add(source)
        if entry["project"] not in projects:
            errors.append(f"{where}: project {entry['project']!r} is not in projects")
        if entry["class"] not in CLASSES:
            errors.append(f"{where}: class must be one of {CLASSES}")
        if not _string_list(entry["binaries"]) or len(set(entry["binaries"])) != len(entry["binaries"]):
            errors.append(f"{where}: binaries must be a nonempty list of unique package names")
        arches = entry["architectures"]
        if (not isinstance(arches, list) or not arches or len(set(arches)) != len(arches)
                or not set(arches) <= set(ARCHITECTURES)):
            errors.append(f"{where}: architectures must be unique values from {ARCHITECTURES}")
            arches = []
        if type(entry["shadows_ubuntu"]) is not bool:
            errors.append(f"{where}: shadows_ubuntu must be a boolean")
        if entry["version"] is not None and not (isinstance(entry["version"], str) and entry["version"]):
            errors.append(f"{where}: version must be the installed version string or null")
        if entry["class"] == "built":
            series = entry.get("series")
            if not isinstance(series, str) or not SERIES.fullmatch(series) or ".." in series:
                errors.append(f"{where}: a built entry needs a series path under patches/ or packaging/")
            elif root is not None and not (Path(root) / series).exists():
                errors.append(f"{where}: series {series} does not exist")
        elif "series" in entry:
            errors.append(f"{where}: only built entries have a series; use reconcile_with")
        if "reconcile_with" in entry:
            value = entry["reconcile_with"]
            if not isinstance(value, str) or not SERIES.fullmatch(value) or ".." in value:
                errors.append(f"{where}: reconcile_with must be a path under patches/ or packaging/")
            elif root is not None and not (Path(root) / value).exists():
                errors.append(f"{where}: reconcile_with {value} does not exist")
        if "binary_architectures" in entry:
            by_binary = entry["binary_architectures"]
            if (not isinstance(by_binary, dict) or not by_binary
                    or not set(by_binary) <= set(entry["binaries"])
                    or not all(_string_list(values) and len(set(values)) == len(values)
                               and set(values) <= set(arches) for values in by_binary.values())):
                errors.append(f"{where}: binary_architectures must map listed binaries to listed architectures")
        if "multiarch_same" in entry:
            pairs = entry["multiarch_same"]
            if (not _string_list(pairs) or not set(pairs) <= set(entry["binaries"])
                    or len([a for a in arches if a != "all"]) < 2):
                errors.append(f"{where}: multiarch_same must name listed binaries of an entry with two architectures")
        if "binary_versions" in entry:
            versions = entry["binary_versions"]
            if (not isinstance(versions, dict) or not versions
                    or not set(versions) <= set(entry["binaries"])
                    or not all(isinstance(v, str) and v for v in versions.values())):
                errors.append(f"{where}: binary_versions must map listed binaries to versions")
        if "kernel" in entry:
            if entry["kernel"] is not True or entry["class"] != "imported" or entry["shadows_ubuntu"]:
                errors.append(f"{where}: kernel entries are imported, do not shadow Ubuntu, and set kernel true")
        if "note" in entry and not isinstance(entry["note"], str):
            errors.append(f"{where}: note must be a string")
    owners = {}
    for entry in packages:
        if isinstance(entry, dict) and isinstance(entry.get("binaries"), list):
            for name in entry["binaries"]:
                owners.setdefault(name, []).append(entry.get("source"))
    for name, owner in sorted(owners.items()):
        if len(owner) > 1:
            errors.append(f"binary {name} is listed by more than one source: {owner}")
    for list_name in ("unconfirmed", "excluded"):
        items = manifest.get(list_name, [])
        if not isinstance(items, list):
            errors.append(f"{list_name} must be a list")
            continue
        for number, item in enumerate(items, 1):
            if (not isinstance(item, dict) or not _string_list(item.get("binaries"))
                    or not isinstance(item.get("reason"), str) or not item["reason"]):
                errors.append(f"{list_name}[{number}] needs binaries and a reason")
                continue
            for name in item["binaries"]:
                if name in owners:
                    errors.append(f"binary {name} is both published and {list_name}")
    return errors


def binary_index(manifest):
    return {name: entry for entry in manifest["packages"] for name in entry["binaries"]}


def binary_architectures(entry, name):
    return entry.get("binary_architectures", {}).get(name, entry["architectures"])


def unpublished_reasons(manifest):
    reasons = {}
    for list_name in ("unconfirmed", "excluded"):
        for item in manifest.get(list_name, []):
            for name in item["binaries"]:
                reasons[name] = f"{list_name}: {item['reason']}"
    return reasons


# --- apt preferences ---------------------------------------------------------

def generate_pins(manifest):
    """The apt preferences file for this origin, deterministic for a manifest."""
    origin = manifest["origin"]
    packages = {True: set(), False: set()}
    for entry in manifest["packages"]:
        for name in entry["binaries"]:
            for arch in binary_architectures(entry, name):
                qualifier = "any" if arch == "all" else arch
                packages[entry["shadows_ubuntu"]].add(f"{name}:{qualifier}")
    shadow, normal = sorted(packages[True]), sorted(packages[False])
    lines = [
        "# Generated by packaging/delivery/pins.py from packaging/delivery/manifest.json.",
        "# Do not edit; change the manifest and regenerate.",
        "",
    ]

    def stanza(explanation, names, priority):
        lines.append(f"Explanation: {explanation}")
        lines.append(f"Package: {' '.join(names)}")
        lines.append(f"Pin: release o={origin}")
        lines.append(f"Pin-Priority: {priority}")
        lines.append("")

    if shadow:
        stanza("listed binaries that replace Ubuntu packages: always ours", shadow, 1001)
    if normal:
        stanza("other listed binaries: normal priority", normal, 500)
    stanza("any other name from this origin: never installed", ["*"], -1)
    return "\n".join(lines)


# --- .deb reading --------------------------------------------------------------

class DebError(ValueError):
    pass


class _Window(io.RawIOBase):
    """A read-only view of [start, start+size) of an open file."""

    def __init__(self, stream, start, size):
        self.stream, self.start, self.size, self.position = stream, start, size, 0

    def readable(self):
        return True

    def readinto(self, buffer):
        remaining = self.size - self.position
        if remaining <= 0:
            return 0
        self.stream.seek(self.start + self.position)
        data = self.stream.read(min(len(buffer), remaining))
        buffer[:len(data)] = data
        self.position += len(data)
        return len(data)


def _members(stream):
    if stream.read(8) != b"!<arch>\n":
        raise DebError("not an ar archive")
    while True:
        header = stream.read(60)
        if not header:
            return
        if len(header) != 60 or header[58:60] != b"`\n":
            raise DebError("truncated ar member header")
        name = header[:16].decode("ascii").strip().rstrip("/")
        size = int(header[48:58].decode("ascii").strip())
        start = stream.tell()
        yield name, start, size
        stream.seek(start + size + (size & 1))


def _tar_mode(name):
    for suffix, mode in ((".gz", "r|gz"), (".xz", "r|xz"), (".zst", "r|zst"), (".bz2", "r|bz2")):
        if name.endswith(suffix):
            return mode
    if name.endswith(".tar"):
        return "r|"
    raise DebError(f"unsupported member compression: {name}")


def parse_control(text):
    fields, current = {}, None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line[0] in " \t":
            if current is None:
                raise DebError("control continuation before any field")
            fields[current] += "\n" + line
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise DebError(f"malformed control line: {line!r}")
        current = key.strip()
        fields[current] = value.strip()
    return fields


class Deb:
    def __init__(self, path):
        self.path = Path(path)
        self._files = None
        self.control = None
        with self.path.open("rb") as stream:
            for name, start, size in _members(stream):
                if name.startswith("control.tar"):
                    with tarfile.open(fileobj=io.BufferedReader(_Window(stream, start, size)),
                                      mode=_tar_mode(name)) as archive:
                        for member in archive:
                            if member.isfile() and member.name.lstrip("./") == "control":
                                self.control = parse_control(archive.extractfile(member).read().decode("utf-8"))
                                break
                    break
        if self.control is None:
            raise DebError(f"{self.path.name}: no control file")
        for field in ("Package", "Version", "Architecture"):
            if not self.control.get(field):
                raise DebError(f"{self.path.name}: control has no {field}")

    @property
    def name(self):
        return self.control["Package"]

    @property
    def version(self):
        return self.control["Version"]

    @property
    def architecture(self):
        return self.control["Architecture"]

    @property
    def source(self):
        return self.control.get("Source", self.name).split(" ")[0]

    @property
    def multiarch(self):
        return self.control.get("Multi-Arch", "no")

    def files(self):
        """{path: sha256 or 'link:target'} for every regular file and symlink."""
        if self._files is None:
            files = {}
            with self.path.open("rb") as stream:
                for name, start, size in _members(stream):
                    if not name.startswith("data.tar"):
                        continue
                    with tarfile.open(fileobj=io.BufferedReader(_Window(stream, start, size)),
                                      mode=_tar_mode(name)) as archive:
                        for member in archive:
                            path = "/" + member.name.lstrip("./")
                            if member.issym():
                                files[path] = "link:" + member.linkname
                            elif member.isfile():
                                digest = hashlib.sha256()
                                handle = archive.extractfile(member)
                                for block in iter(lambda: handle.read(1 << 20), b""):
                                    digest.update(block)
                                files[path] = digest.hexdigest()
            self._files = files
        return self._files


RELATION = re.compile(r"\s*([a-z0-9][a-z0-9+.-]*)(?::[a-z0-9-]+)?\s*(?:\(\s*(<<|<=|=|>=|>>)\s*([^)\s]+)\s*\))?")


def relations(text):
    """Yield (name, operator, version) for every alternative of a relation field."""
    for group in (text or "").split(","):
        for alternative in group.split("|"):
            if not alternative.strip():
                continue
            match = RELATION.match(alternative)
            if match:
                yield match.group(1), match.group(2), match.group(3)


# --- OpenPGP ----------------------------------------------------------------

def openpgp_fingerprint(armored):
    """Fingerprint of the first (primary) v4 public key in an armored block."""
    lines = armored.strip().splitlines()
    try:
        start = lines.index("-----BEGIN PGP PUBLIC KEY BLOCK-----")
    except ValueError:
        raise ValueError("not an armored public key block") from None
    body = []
    for line in lines[start + 1:]:
        if line.startswith("-----END"):
            break
        if not line.strip() or ":" in line and not body:
            continue
        if line.startswith("="):
            break
        body.append(line.strip())
    data = base64.b64decode("".join(body))
    tag_byte = data[0]
    if not tag_byte & 0x80:
        raise ValueError("invalid OpenPGP packet")
    if tag_byte & 0x40:
        tag = tag_byte & 0x3F
        first = data[1]
        if first < 192:
            length, offset = first, 2
        elif first < 224:
            length, offset = ((first - 192) << 8) + data[2] + 192, 3
        else:
            length, offset = int.from_bytes(data[2:6], "big"), 6
    else:
        tag = (tag_byte >> 2) & 0x0F
        size = {0: 1, 1: 2, 2: 4}[tag_byte & 3]
        length, offset = int.from_bytes(data[1:1 + size], "big"), 1 + size
    if tag != 6:
        raise ValueError("first packet is not a public key")
    packet = data[offset:offset + length]
    if packet[0] != 4:
        raise ValueError("only v4 keys are supported")
    return hashlib.sha1(b"\x99" + len(packet).to_bytes(2, "big") + packet).hexdigest().upper()
