#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Consumer pin re-releases: control rewriting, record validation and repacks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'packaging/gstreamer-gtk-dovi'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


repack = load('repack_consumers', FOLDER / 'repack-consumers.py')
managed = load('managed_for_repack', ROOT / 'packaging/ubuntu/managed.py')

PINS = {
    'libgstgtk-dovi-core0': '0.1.0+rogdv11',
    'gstreamer1.0-gtk-dovi': '0.1.0+rogdv11',
    'gstreamer1.0-plugins-bad': '1.28.6-1ubuntu1+rogdv11',
    'gstreamer1.0-gtk4': '0.15.2-1ubuntu2+rogdv5.8+depfix2',
}

SINK = '''Package: gstreamer1.0-gtk4
Source: rust-gst-plugin-gtk4
Version: 0.15.2-1ubuntu2+rogdv5.8
Architecture: amd64
Maintainer: Example <example@example.invalid>
Depends: libgstgtk-dovi-core0 (= 0.1.0+rogdv10), libc6 (>= 2.39),
 libgtk-4-1 (>= 4.24), gstreamer1.0-plugins-base | gstreamer1.0-plugins-bad (= 1.28.6-1ubuntu1+rogdv10)
Description: GTK sink
 Long text mentioning libgstgtk-dovi-core0 (= 0.1.0+rogdv10).
'''

SHOWTIME = '''Package: showtime
Version: 50.0-2+rogdv5.15
Architecture: all
Depends: gstreamer1.0-gtk4 (= 0.15.2-1ubuntu2+rogdv5.8), gstreamer1.0-gtk-dovi (= 0.1.0+rogdv10),
 gstreamer1.0-plugins-bad (= 1.28.6-1ubuntu1+rogdv10), python3
Pre-Depends: libgstgtk-dovi-core0 (= 0.1.0+rogdv10)
Description: video player
'''


class ReleaseControl(unittest.TestCase):
    def test_exact_managed_pins_and_version_are_rewritten(self):
        text = repack.release_control(SHOWTIME, '50.0-2+rogdv5.15+depfix3', PINS)
        fields = repack.parse_control(text)
        self.assertEqual(fields['Version'], '50.0-2+rogdv5.15+depfix3')
        self.assertEqual(fields['Depends'], (
            'gstreamer1.0-gtk4 (= 0.15.2-1ubuntu2+rogdv5.8+depfix2), '
            'gstreamer1.0-gtk-dovi (= 0.1.0+rogdv11), '
            'gstreamer1.0-plugins-bad (= 1.28.6-1ubuntu1+rogdv11), python3'))
        self.assertEqual(fields['Pre-Depends'], 'libgstgtk-dovi-core0 (= 0.1.0+rogdv11)')
        self.assertTrue(text.endswith('\n'))

    def test_other_relations_and_fields_are_unchanged(self):
        text = repack.release_control(SINK, '0.15.2-1ubuntu2+rogdv5.8+depfix2', PINS)
        self.assertIn('libc6 (>= 2.39),\n libgtk-4-1 (>= 4.24), ', text)
        self.assertIn('gstreamer1.0-plugins-base | gstreamer1.0-plugins-bad (= 1.28.6-1ubuntu1+rogdv10)', text)
        self.assertIn('libgstgtk-dovi-core0 (= 0.1.0+rogdv11), libc6', text)
        self.assertIn('Long text mentioning libgstgtk-dovi-core0 (= 0.1.0+rogdv10).', text)
        before = [l for l in SINK.splitlines() if l.startswith(('Source', 'Maintainer', 'Architecture'))]
        for line in before:
            self.assertIn(line, text.splitlines())

    def test_missing_fields_are_refused(self):
        for field in ('Depends', 'Version', 'Package'):
            stanza = '\n'.join(l for l in SINK.splitlines() if not l.startswith(field + ':'))
            with self.assertRaises(repack.PreparationError):
                repack.release_control(stanza, '1', PINS)


class RecordedReleases(unittest.TestCase):
    def test_real_file_is_accepted(self):
        releases = repack.consumer_releases()
        self.assertEqual(releases['showtime']['release']['version'], '50.0-2+rogdv5.15+depfix4')
        pins = repack.current_pins()
        self.assertEqual(pins['libgstgtk-dovi-core0'], repack.recipe.CORE_VERSION)
        self.assertEqual(pins['gstreamer1.0-gtk4'], '0.15.2-1ubuntu2+rogdv5.8+depfix3')

    def mutated(self, change):
        data = json.loads((FOLDER / 'package-inputs/consumer-releases.json').read_text())
        change(data['releases'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'consumer-releases.json'
            path.write_text(json.dumps(data))
            original, repack.RELEASES = repack.RELEASES, path
            try:
                return repack.consumer_releases()
            finally:
                repack.RELEASES = original

    def test_malformed_records_are_refused(self):
        def version(r): r['showtime']['release']['version'] = '50.0-2+rogdv5.15+fix3'
        def zero(r): r['showtime']['release']['version'] = '50.0-2+rogdv5.15+depfix0'
        def sha(r): r['showtime']['base']['deb_sha256'] = 'A' * 64
        def receipt(r): r['showtime']['release']['receipt'] = '../evidence/x.json'
        def missing(r): r['showtime']['release']['receipt'] = 'evidence/does-not-exist.json'
        def name(r): r['showtime']['package'] = 'other'
        for change in (version, zero, sha, receipt, missing, name):
            with self.subTest(change=change.__name__), self.assertRaises(repack.PreparationError):
                self.mutated(change)

    def test_publisher_uses_recorded_release_versions(self):
        self.assertEqual(managed.expected_version('rust-gst-plugin-gtk4', {}),
                         '0.15.2-1ubuntu2+rogdv5.8+depfix3')
        self.assertEqual(managed.expected_version('showtime', {}), '50.0-2+rogdv5.15+depfix4')


@unittest.skipUnless(shutil.which('dpkg-deb'), 'dpkg-deb is required')
class RepackRoundTrip(unittest.TestCase):
    def build(self, root, name, control, payload):
        tree = root / name
        (tree / 'DEBIAN').mkdir(parents=True)
        (tree / 'DEBIAN/control').write_text(control)
        (tree / 'usr/share/demo').mkdir(parents=True)
        (tree / 'usr/share/demo/file').write_text(payload)
        output = root / f'{name}.deb'
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(tree), str(output)],
                       check=True, capture_output=True)
        return output

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        control = SHOWTIME + 'Maintainer: Example <example@example.invalid>\n'
        self.base = self.build(self.root, 'base', control, 'payload\n')
        base_sha = hashlib.sha256(self.base.read_bytes()).hexdigest()
        releases = repack.consumer_releases()
        entry = dict(releases['showtime'])
        entry['base'] = dict(entry['base'], deb_sha256=base_sha)
        self.patcher = unittest.mock.patch.object(
            repack, 'consumer_releases', lambda: dict(releases, showtime=entry))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_repack_then_verify(self):
        output = repack.repack('showtime', self.base, self.root / 'out')
        self.assertEqual(output.name, 'showtime_50.0-2+rogdv5.15+depfix4_all.deb')
        fields = repack.parse_control(repack._dpkg_field_text(output))
        self.assertEqual(fields['Version'], '50.0-2+rogdv5.15+depfix4')
        repack.verify('showtime', self.base, output)
        with self.assertRaises(repack.PreparationError):
            repack.verify('showtime', self.base, output, recorded=True)

    def test_verify_refuses_different_payload_or_base(self):
        output = repack.repack('showtime', self.base, self.root / 'out')
        other = self.build(self.root, 'other', SHOWTIME, 'changed\n')
        with self.assertRaises(repack.PreparationError):
            repack.verify('showtime', other, output)
        tampered = self.build(self.root, 'tampered', repack.release_control(
            SHOWTIME, '50.0-2+rogdv5.15+depfix3', repack.current_pins()), 'changed\n')
        with self.assertRaises(repack.PreparationError):
            repack.verify('showtime', self.base, tampered)
        wrong_control = self.build(self.root, 'wrong', SHOWTIME, 'payload\n')
        with self.assertRaises(repack.PreparationError):
            repack.verify('showtime', self.base, wrong_control)


if __name__ == '__main__':
    unittest.main()
