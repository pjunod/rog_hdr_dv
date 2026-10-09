#!/usr/bin/env python3
"""Validate recorded source integrity, without building or touching a display."""

from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import sys
from urllib.parse import unquote, urlsplit


COMPONENT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def patch_name(value):
    return (isinstance(value, str) and value.endswith(".patch")
            and value not in (".patch", "..patch")
            and not any(c.isspace() or c in "/\\" or ord(c) < 32 for c in value))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


class Checker:
    def __init__(self, root):
        self.root = root.resolve()
        self.errors = []

    def label(self, path):
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def safe_path(self, path, kind="file"):
        try:
            if not path.resolve().is_relative_to(self.root):
                self.errors.append(f"Unsafe path escapes repository: {self.label(path)}")
                return False
            exists = (path.is_file() if kind == "file" else
                      path.is_dir() if kind == "directory" else path.exists())
            if not exists:
                self.errors.append(f"Missing {kind}: {self.label(path)}")
                return False
            return True
        except (OSError, RuntimeError, ValueError) as exc:
            self.errors.append(f"Cannot resolve {self.label(path)}: {exc}")
            return False

    def read(self, path, binary=False):
        if not self.safe_path(path):
            return None
        try:
            return path.read_bytes() if binary else path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self.errors.append(f"Cannot read {self.label(path)}: {exc}")
            return None

    def files_under(self, directory, suffix):
        """Walk recursively without following directory symlinks or reading escapes."""
        files = set()
        if not self.safe_path(directory, "directory"):
            return files
        if directory.is_symlink():
            self.errors.append(f"Directory symlink is unsupported: {self.label(directory)}")
            return files
        try:
            children = sorted(directory.iterdir())
        except OSError as exc:
            self.errors.append(f"Cannot list {self.label(directory)}: {exc}")
            return files
        for child in children:
            if child.is_dir():
                files.update(self.files_under(child, suffix))
            elif child.is_symlink() and not self.safe_path(child):
                continue
            elif child.suffix == suffix and self.safe_path(child):
                files.add(child)
        return files

    def manifest(self, patches):
        content = self.read(self.root / "SHA256SUMS")
        entries = {}
        if content is None:
            return
        for number, line in enumerate(content.splitlines(), 1):
            parts = line.split("  ", 1)
            if len(parts) != 2 or not DIGEST.fullmatch(parts[0]):
                self.errors.append(f"Malformed SHA256SUMS line {number}: expected lowercase SHA256, two spaces, patch path")
                continue
            digest, name = parts
            parts = PurePosixPath(name).parts
            if (len(parts) != 3 or parts[0] != "patches"
                    or not COMPONENT.fullmatch(parts[1]) or not patch_name(parts[2])
                    or str(PurePosixPath(name)) != name):
                self.errors.append(f"Unsafe or invalid patch path in SHA256SUMS line {number}: {name}")
                continue
            if name in entries:
                self.errors.append(f"Duplicate manifest entry: {name}")
            entries[name] = digest
            data = self.read(self.root / name, binary=True)
            if data is not None and hashlib.sha256(data).hexdigest() != digest:
                self.errors.append(f"SHA256 mismatch: {name}")
        actual = {self.label(path) for path in patches}
        for name in sorted(actual - entries.keys()):
            self.errors.append(f"Patch missing from SHA256SUMS: {name}")
        for name in sorted(entries.keys() - actual):
            self.errors.append(f"SHA256SUMS entry is not a repository patch: {name}")

    def sources(self, patches):
        content = self.read(self.root / "sources.json")
        components = set()
        if content is None:
            return components
        try:
            sources = json.loads(content, object_pairs_hook=unique_object)
        except (ValueError, RecursionError) as exc:
            self.errors.append(f"Malformed sources.json: {exc}")
            return components
        if not isinstance(sources, dict):
            self.errors.append("sources.json must be an object")
            return components
        if type(sources.get("schema")) is not int or sources["schema"] != 1:
            self.errors.append("sources.json schema must be integer 1")
        series = sources.get("series")
        if not isinstance(series, list) or not series:
            self.errors.append("sources.json series must be a nonempty list")
            return components
        for number, component in enumerate(series, 1):
            if not isinstance(component, dict):
                self.errors.append(f"sources.json series entry {number} must be an object")
                continue
            name = component.get("component")
            if not isinstance(name, str) or not COMPONENT.fullmatch(name):
                self.errors.append(f"Invalid component ID in sources.json series entry {number}: {name!r}")
                continue
            if name in components:
                self.errors.append(f"Duplicate component ID: {name}")
            components.add(name)
            for field in ("base_commit", "candidate_commit", "base_tree", "candidate_tree"):
                if field.endswith("tree") and field not in component:
                    continue
                value = component.get(field)
                if not isinstance(value, str) or not OBJECT_ID.fullmatch(value):
                    self.errors.append(f"Invalid or missing source pin {name}.{field}: expected full lowercase Git object ID")
            count = component.get("patch_count")
            if type(count) is not int or count < 1:
                self.errors.append(f"Invalid patch_count for {name}: expected positive integer")
            order = component.get("patch_order")
            if not isinstance(order, list) or not order or not all(patch_name(p) for p in order):
                self.errors.append(f"Invalid or missing patch_order for {name}: expected ordered patch basenames")
                order = None
            elif len(order) != len(set(order)):
                self.errors.append(f"Duplicate patch_order entry for {name}")
            directory = self.root / "patches" / name
            content = self.read(directory / "series")
            if content is None:
                continue
            names = content.splitlines()
            if not all(patch_name(p) for p in names) or len(names) != len(set(names)):
                self.errors.append(f"Invalid series inventory: {name}")
            actual = {path.name for path in patches if path.parent == directory}
            if set(names) != actual:
                self.errors.append(f"Series inventory does not exactly cover patch files: {name}")
            if order is not None and names != order:
                self.errors.append(f"Series order differs from sources.json patch_order: {name}")
            if type(count) is int and (len(names) != count or (order is not None and len(order) != count)):
                self.errors.append(f"Wrong series length: {name}")
        patch_root = self.root / "patches"
        if self.safe_path(patch_root, "directory"):
            try:
                directories = {p.name for p in patch_root.iterdir() if p.is_dir()}
                for name in sorted(directories - components):
                    self.errors.append(f"Missing component in sources.json: {name}")
                for name in sorted(components - directories):
                    self.errors.append(f"Missing patch directory for component: {name}")
            except OSError as exc:
                self.errors.append(f"Cannot list patches: {exc}")
        return components

    @staticmethod
    def links(content):
        # Inline links and reference definitions; optional Markdown link titles.
        targets = re.findall(r"\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", content)
        targets += re.findall(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", content, re.MULTILINE)
        return [target[1:-1] if target.startswith("<") else target for target in targets]

    @staticmethod
    def anchors(content):
        anchors, counts = set(), {}
        fenced = False
        for line in content.splitlines():
            if re.match(r"^\s*(```|~~~)", line):
                fenced = not fenced
            if fenced:
                continue
            heading = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
            if heading:
                title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading[1])
                slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
                count = counts.get(slug, 0)
                counts[slug] = count + 1
                anchors.add(f"{slug}-{count}" if count else slug)
        anchors.update(re.findall(r"\b(?:id|name)=[\"']([^\"']+)[\"']", content))
        return anchors

    def documentation(self):
        docs = self.files_under(self.root / "docs", ".md")
        contents = {}
        for doc in sorted(docs | set(self.root.glob("*.md")) | {self.root / "README.md"}):
            content = self.read(doc)
            if content is not None:
                contents[doc] = content
        indexed = set()
        for doc, content in contents.items():
            for target in self.links(content):
                try:
                    parsed = urlsplit(target)
                except ValueError as exc:
                    self.errors.append(f"Malformed link in {self.label(doc)}: {target}: {exc}")
                    continue
                if parsed.scheme or parsed.netloc:
                    continue
                path = unquote(parsed.path)
                linked = doc.parent / path if path else doc
                if doc == self.root / "README.md":
                    indexed.add(linked)
                if not self.safe_path(linked, "path"):
                    self.errors.append(f"Broken or unsafe link in {self.label(doc)}: {target}")
                    continue
                if parsed.fragment and linked.suffix == ".md":
                    text = contents.get(linked)
                    if text is None:
                        text = self.read(linked)
                    if text is not None and unquote(parsed.fragment) not in self.anchors(text):
                        self.errors.append(f"Broken anchor in {self.label(doc)}: {target}")
        for doc in sorted(docs - indexed):
            self.errors.append(f"Documentation absent from README: {self.label(doc)}")


def main():
    checker = Checker(Path(__file__).resolve().parents[1])
    patches = checker.files_under(checker.root / "patches", ".patch")
    checker.manifest(patches)
    components = checker.sources(patches)
    checker.documentation()
    if checker.errors:
        print("\n".join(checker.errors), file=sys.stderr)
        return 1
    print(f"PASS: {len(patches)} patches, {len(components)} series, documentation links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
