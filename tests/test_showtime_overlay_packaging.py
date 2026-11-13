#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Showtime source/packaging boundary controls; requires SHOWTIME_PINNED_PLAY.

The fixture is the authentic upstream showtime/play.py named by the recorded
SHA256, not a reduced source snippet. Missing fixtures fail rather than skip.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'packaging/gstreamer-gtk-dovi'
spec = importlib.util.spec_from_file_location('showtime_packages', FOLDER / 'prepare-ubuntu-packages.py')
packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packages)


class ShowtimeOverlayPackaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = os.environ.get('SHOWTIME_PINNED_PLAY')
        if not fixture:
            raise AssertionError('SHOWTIME_PINNED_PLAY must name authenticated upstream Showtime 50.0 play.py')
        cls.upstream = Path(fixture).read_bytes()
        cls.series = json.loads((FOLDER / 'package-inputs/provenance.json').read_text())['showtime']['source_series']
        if hashlib.sha256(cls.upstream).hexdigest() != cls.series['upstream_play_sha256']:
            raise AssertionError('upstream Showtime fixture does not match the pinned source')

    def workspace(self, root):
        for label, name in [('gtk', 'source'), ('showtime', 'showtime-50.0')]:
            debian = root / name / 'debian'; debian.mkdir(parents=True)
            for field in packages.INPUT_FILES:
                shutil.copyfile(FOLDER / 'package-inputs' / label / field, debian / field)
        play = root / 'showtime-50.0/showtime/play.py'; play.parent.mkdir()
        play.write_bytes(self.upstream)
        return play

    def test_real_pinned_source_replays_all_consumer_patches_and_records_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); play = self.workspace(root)
            packages.prepare(root)
            receipt = json.loads((root / 'showtime-source-preparation.json').read_text())
            self.assertEqual(receipt['source_version'], '50.0-2+rogdv5.12')
            self.assertEqual(receipt['patches'], self.series['patches'])
            self.assertEqual(hashlib.sha256(play.read_bytes()).hexdigest(), self.series['patches'][-1]['result_play_sha256'])
            self.assertTrue((root / 'showtime-50.0/debian/changelog').read_text().startswith('showtime (50.0-2+rogdv5.12)'))
            self.assertIn('gstreamer1.0-plugins-base (= 1.28.7-1+rogdv3)',
                          (root / 'showtime-50.0/debian/control').read_text())
            inventory = json.loads((root / 'package-output-inventory.json').read_text())
            self.assertEqual(inventory['showtime_source']['output_play_sha256'], receipt['output_play_sha256'])
            before = play.read_bytes()
            packages.prepare(root)
            self.assertEqual(play.read_bytes(), before, 'prepared source rerun is idempotent')
            self.assertEqual(packages.CORE_VERSION, '0.1.0+rogdv10')
            self.assertEqual(packages.GTK_VERSION, '0.15.2-1ubuntu2+rogdv5.6')

    def test_showtime_only_preparation_preserves_unrelated_gtk_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.workspace(root)
            unrelated = root / 'source/debian/control'
            unrelated.write_text(unrelated.read_text() + '\n# caller-owned GTK work\n')
            before = {str(p.relative_to(root / 'source')): p.read_bytes()
                      for p in (root / 'source').rglob('*') if p.is_file()}
            packages.prepare(root, showtime_only=True)
            after = {str(p.relative_to(root / 'source')): p.read_bytes()
                     for p in (root / 'source').rglob('*') if p.is_file()}
            self.assertEqual(after, before)
            inventory = json.loads((root / 'package-output-inventory.json').read_text())
            self.assertEqual(set(inventory['outputs']), {'showtime'})

    def test_unrecognized_source_is_refused_without_metadata_or_source_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); play = self.workspace(root)
            play.write_bytes(play.read_bytes() + b'\n# unrecognized caller edit\n')
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaises(packages.PreparationError): packages.prepare(root)
            after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(after, before)


if __name__ == '__main__':
    unittest.main()
