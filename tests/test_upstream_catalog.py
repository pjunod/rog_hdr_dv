"""Catch missing preparation, mutated patches and unsafe submission paths."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "check_upstream", Path(__file__).resolve().parents[1] / "scripts/check_upstream.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        owned = Path(__file__).resolve().parents[1] / "work" / "test-upstream-catalog"
        owned.mkdir(parents=True, exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(dir=owned)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.kit = self.root / "upstream"
        (self.kit / "example/01-fix").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.patch = self.kit / "example/01-fix/fix.patch"
        self.patch.write_text(
            "From " + "a" * 40 + " Mon Sep 17 00:00:00 2001\n"
            "From: Paul Junod <donujp@gmail.com>\n"
            "Date: Wed, 28 Oct 2026 10:00:00 -0400\n"
            "Subject: [PATCH] example: fix parsing\n\nBound the read.\n\n---\n")
        self.manifest = self.kit / "example/manifest.json"
        self.manifest.write_text(json.dumps({
            "base": "a" * 40, "units": [{"id": "01", "status": "held",
            "patches": ["01-fix/fix.patch"]}]}))
        (self.root / "docs/UPSTREAM_SUBMISSIONS.md").write_text(
            "| Unit | Change |\n|---|---|\n| EXAMPLE | A fix |\n")
        self.catalog = self.kit / "catalog.json"
        self.catalog.write_text(json.dumps({"items": [{"id": "EXAMPLE",
            "disposition": "held", "artifacts": ["upstream/example/manifest.json"]}]}))
        self.lock()

    def lock(self):
        (self.kit / "SHA256SUMS").write_text(module.checksum_text(self.kit))

    def test_complete_held_item_is_valid_without_claiming_test_success(self):
        self.assertEqual(module.check(self.root), [])

    def test_patch_mutation_requires_deliberate_new_checksum(self):
        self.patch.write_text(self.patch.read_text() + "changed\n")
        self.assertTrue(any("bytes changed" in e for e in module.check(self.root)))

    def test_signoff_cannot_be_smuggled_by_refreshing_checksums(self):
        self.patch.write_text(self.patch.read_text().replace(
            "\n---\n", "\nSigned-off-by: Paul Junod <donujp@gmail.com>\n\n---\n"))
        self.lock()
        self.assertTrue(any("sign-off" in e for e in module.check(self.root)))

    def test_empty_commit_body_cannot_be_hidden_by_refreshing_checksums(self):
        self.patch.write_text(self.patch.read_text().replace("Bound the read.\n", ""))
        self.lock()
        self.assertTrue(any("missing explanatory" in e for e in module.check(self.root)))

    def test_missing_inventory_row_is_reported(self):
        (self.root / "docs/UPSTREAM_SUBMISSIONS.md").write_text("# Inventory\n")
        self.assertTrue(any("Inventory differs" in e for e in module.check(self.root)))

    def test_manifest_cannot_reference_a_file_outside_its_project(self):
        self.manifest.write_text(json.dumps({"base": "a" * 40, "units": [
            {"id": "01", "status": "held", "patches": ["../../docs/UPSTREAM_SUBMISSIONS.md"]}]}))
        self.lock()
        self.assertTrue(any("noncanonical" in e for e in module.check(self.root)))

    def test_symlink_artifact_is_rejected_even_within_the_kit(self):
        (self.kit / "alias.patch").symlink_to(self.patch)
        with self.assertRaisesRegex(ValueError, "symlink"):
            module.checksum_text(self.kit)

    def test_directory_symlink_cannot_hide_unhashed_submission_material(self):
        external = self.root / "external"
        external.mkdir()
        (external / "submit.sh").write_text("#!/bin/sh\nexit 1\n")
        (self.kit / "hidden-project").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            module.checksum_text(self.kit)

    def test_duplicate_catalog_ids_are_rejected(self):
        content = json.loads(self.catalog.read_text())
        content["items"] *= 2
        self.catalog.write_text(json.dumps(content))
        self.lock()
        self.assertTrue(any("duplicate inventory" in e for e in module.check(self.root)))

    def test_ready_item_needs_local_material_and_evidence(self):
        content = json.loads(self.catalog.read_text())
        content["items"][0].update(disposition="ready-for-human-review", artifacts=[
            "https://github.com/pjunod/example/blob/main/DESCRIPTION.md"])
        self.catalog.write_text(json.dumps(content))
        self.lock()
        self.assertTrue(any("needs local material" in e for e in module.check(self.root)))

    def test_unknown_disposition_is_rejected(self):
        content = json.loads(self.catalog.read_text())
        content["items"][0]["disposition"] = "everything-is-fine"
        self.catalog.write_text(json.dumps(content))
        self.lock()
        self.assertTrue(any("lacks disposition" in e for e in module.check(self.root)))


if __name__ == "__main__":
    unittest.main()
