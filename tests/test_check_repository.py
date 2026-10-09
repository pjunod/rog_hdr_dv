"""Mutation regressions for the offline repository integrity checker."""

import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]


class RepositoryIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        for directory in ("patches", "docs", "evidence"):
            shutil.copytree(REPOSITORY / directory, self.root / directory, symlinks=True)
        for path in REPOSITORY.glob("*.md"):
            shutil.copy2(path, self.root / path.name)
        for name in ("sources.json", "SHA256SUMS"):
            shutil.copy2(REPOSITORY / name, self.root / name)
        (self.root / "scripts").mkdir()
        shutil.copy2(REPOSITORY / "scripts/check_repository.py",
                     self.root / "scripts/check_repository.py")
        self.sources = json.loads((self.root / "sources.json").read_text())
        self.library = next(item for item in self.sources["series"]
                            if item["component"] == "libdisplay-info")
        self.patch = self.root / "patches/libdisplay-info" / self.library["patch_order"][0]

    def write_sources(self, sources=None):
        (self.root / "sources.json").write_text(json.dumps(self.sources if sources is None else sources))

    def check(self, root=None):
        root = root or self.root
        return subprocess.run([sys.executable, str(root / "scripts/check_repository.py")],
                              cwd=root, capture_output=True, text=True, timeout=30)

    def rejected(self, message):
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("PASS:", result.stdout)

    def test_clean_clone_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS:", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_optional_metadata_and_subset_without_tree_remain_valid(self):
        self.library["source_origin"] = {"kind": "upstream", "note": "documented metadata"}
        kernel = next(item for item in self.sources["series"] if item["component"] == "linux")
        kernel.pop("candidate_tree", None)
        self.write_sources()
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reordering_dependent_series_is_rejected(self):
        path = self.root / "patches/libdisplay-info/series"
        path.write_text("\n".join(reversed(path.read_text().splitlines())) + "\n")
        self.rejected("Series order differs from sources.json patch_order: libdisplay-info")

    def test_changed_patch_bytes_are_rejected(self):
        self.patch.write_bytes(self.patch.read_bytes() + b"\nmutation\n")
        self.rejected("SHA256 mismatch:")

    def test_wrong_digest_is_rejected(self):
        path = self.root / "SHA256SUMS"
        path.write_text("0" * 64 + path.read_text()[64:])
        self.rejected("SHA256 mismatch:")

    def test_malformed_checksum_lines_are_controlled_errors(self):
        path = self.root / "SHA256SUMS"
        original = path.read_text()
        for line in ("garbage", "z" * 64 + "  patches/linux/file.patch", "", "a" * 64 + " file.patch"):
            with self.subTest(line=line):
                path.write_text(line + "\n" + original)
                self.rejected("Malformed SHA256SUMS line 1")

    def test_missing_and_duplicate_checksum_entries_are_rejected(self):
        path = self.root / "SHA256SUMS"
        original = path.read_text()
        first, remaining = original.split("\n", 1)
        path.write_text(remaining)
        self.rejected("Patch missing from SHA256SUMS:")
        path.write_text(first + "\n" + original)
        self.rejected("Duplicate manifest entry:")

    def test_malformed_json_is_a_controlled_error(self):
        (self.root / "sources.json").write_text('{"series": [')
        self.rejected("Malformed sources.json:")

    def test_duplicate_json_keys_are_rejected(self):
        (self.root / "sources.json").write_text('{"schema": 1, "schema": 1, "series": []}')
        self.rejected("duplicate JSON key: schema")

    def test_wrong_top_level_shapes_and_schema_are_rejected(self):
        for sources, message in (([], "must be an object"),
                                 ({"schema": True, "series": []}, "schema must be integer 1"),
                                 ({"schema": 2, "series": self.sources["series"]}, "schema must be integer 1"),
                                 ({"schema": 1, "series": {}}, "series must be a nonempty list"),
                                 ({"schema": 1, "series": [None]}, "must be an object")):
            with self.subTest(sources=sources):
                self.write_sources(sources)
                self.rejected(message)

    def test_duplicate_component_is_rejected(self):
        self.sources["series"].append(copy.deepcopy(self.library))
        self.write_sources()
        self.rejected("Duplicate component ID: libdisplay-info")

    def test_missing_component_is_rejected(self):
        self.sources["series"].remove(self.library)
        self.write_sources()
        self.rejected("Missing component in sources.json: libdisplay-info")

    def test_invalid_component_ids_are_rejected(self):
        for value in ("../outside", "/outside", {}, "lib/display-info", ""):
            with self.subTest(value=value):
                self.library["component"] = value
                self.write_sources()
                self.rejected("Invalid component ID")

    def test_missing_source_pins_are_rejected(self):
        original = copy.deepcopy(self.sources)
        for field in ("base_commit", "candidate_commit"):
            with self.subTest(field=field):
                sources = copy.deepcopy(original)
                del sources["series"][0][field]
                self.write_sources(sources)
                self.rejected(f".{field}: expected full lowercase Git object ID")

    def test_malformed_commit_and_tree_ids_are_rejected(self):
        for field in ("base_commit", "candidate_commit", "base_tree", "candidate_tree"):
            for value in ("abc123", "z" * 40, "A" * 40, None, 123):
                with self.subTest(field=field, value=value):
                    sources = copy.deepcopy(self.sources)
                    sources["series"][0][field] = value
                    self.write_sources(sources)
                    self.rejected(f".{field}: expected full lowercase Git object ID")

    def test_bad_patch_count_is_rejected(self):
        for value in (True, "4", 0, -1, None):
            with self.subTest(value=value):
                self.library["patch_count"] = value
                self.write_sources()
                self.rejected("Invalid patch_count for libdisplay-info")
        self.library["patch_count"] = 100
        self.write_sources()
        self.rejected("Wrong series length: libdisplay-info")

    def test_missing_or_unsafe_patch_order_is_rejected(self):
        del self.library["patch_order"]
        self.write_sources()
        self.rejected("Invalid or missing patch_order for libdisplay-info")
        for value in ([], {}, [None], ["../outside.patch"], ["/outside.patch"], [["nested.patch"]]):
            with self.subTest(value=value):
                self.library["patch_order"] = value
                self.write_sources()
                self.rejected("Invalid or missing patch_order for libdisplay-info")

    def test_duplicate_patch_order_is_rejected(self):
        self.library["patch_order"].append(self.library["patch_order"][0])
        self.write_sources()
        self.rejected("Duplicate patch_order entry for libdisplay-info")

    def test_missing_repository_files_are_controlled_errors(self):
        for relative in ("SHA256SUMS", "sources.json", "patches/libdisplay-info/series", "README.md"):
            with self.subTest(relative=relative):
                path = self.root / relative
                data = path.read_bytes()
                path.unlink()
                self.rejected(f"Missing file: {relative}")
                path.write_bytes(data)
        self.patch.unlink()
        self.rejected("Missing file: patches/libdisplay-info/")

    def test_checksum_path_traversal_is_rejected(self):
        path = self.root / "SHA256SUMS"
        original = path.read_text()
        for target in ("../outside.patch", "/tmp/outside.patch", "patches/../outside.patch",
                       "patches/libdisplay-info/../../outside.patch", "patches//linux/file.patch"):
            with self.subTest(target=target):
                path.write_text("a" * 64 + "  " + target + "\n" + original)
                self.rejected("Unsafe or invalid patch path in SHA256SUMS line 1")

    def test_patch_symlink_escape_is_rejected_even_with_matching_hash(self):
        outside = Path(self.temporary.name) / "outside.patch"
        outside.write_bytes(self.patch.read_bytes())
        self.patch.unlink()
        self.patch.symlink_to(outside)
        self.rejected("Unsafe path escapes repository: patches/libdisplay-info/")

    def test_directory_symlink_escape_is_rejected(self):
        directory = self.root / "patches/libdisplay-info"
        outside = Path(self.temporary.name) / "outside-series"
        directory.rename(outside)
        directory.symlink_to(outside, target_is_directory=True)
        self.rejected("Unsafe path escapes repository: patches/libdisplay-info")

    def test_missing_document_link_is_rejected_recursively(self):
        path = self.root / "docs/nested/TEST.md"
        path.parent.mkdir()
        path.write_text("# Nested\n\n[missing](missing.md)\n")
        with (self.root / "README.md").open("a") as readme:
            readme.write("\n[nested](docs/nested/TEST.md)\n")
        self.rejected("Broken or unsafe link in docs/nested/TEST.md: missing.md")

    def test_document_absent_from_readme_is_rejected_recursively(self):
        path = self.root / "docs/nested/TEST.md"
        path.parent.mkdir()
        path.write_text("# Nested\n")
        self.rejected("Documentation absent from README: docs/nested/TEST.md")

    def test_document_symlink_and_absolute_link_escapes_are_rejected(self):
        outside = Path(self.temporary.name) / "outside.md"
        outside.write_text("# Outside\n")
        with (self.root / "README.md").open("a") as readme:
            readme.write(f"\n[outside]({outside})\n")
        self.rejected("Unsafe path escapes repository:")
        (self.root / "docs/ESCAPE.md").symlink_to(outside)
        self.rejected("Unsafe path escapes repository: docs/ESCAPE.md")

    def test_missing_anchor_is_rejected(self):
        with (self.root / "README.md").open("a") as readme:
            readme.write("\n[bad anchor](docs/STATUS.md#does-not-exist)\n")
        self.rejected("Broken anchor in README.md: docs/STATUS.md#does-not-exist")

    def test_undecodable_source_manifest_is_a_controlled_error(self):
        (self.root / "sources.json").write_bytes(b"\xff")
        self.rejected("Cannot read sources.json:")


if __name__ == "__main__":
    unittest.main()
