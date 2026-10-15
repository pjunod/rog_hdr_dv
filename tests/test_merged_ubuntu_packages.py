#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deferred, scoped merged-release packaging regressions (not upstream suites)."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load('release', ROOT / 'tools/merged-ubuntu-release.py')
isolation = load('isolation', ROOT / 'tools/isolated-ubuntu-apt.py')


class ReleaseRecipeTests(unittest.TestCase):
    def test_unique_version_and_distribution_recipe(self):
        self.assertIn(release.VERSION, release.CHANGELOG)
        self.assertIn('same-version', release.CHANGELOG)
        self.assertIn('nocheck', release.CHANGELOG)
        self.assertNotIn('certified', release.CHANGELOG)

    def test_durable_output_rejects_ephemeral_paths(self):
        for path in ['/tmp/package', '/private/tmp/package', '/var/tmp/package']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                release.durable_output(path)
            with self.assertRaises(ValueError):
                isolation.durable(path)

    def test_existing_output_preserves_work(self):
        with self.assertRaises(ValueError):
            release.durable_output(ROOT)

    def test_source_receipt_excludes_quilt_and_packaging(self):
        # Exercise real repository content, without creating throwaway roots.
        actual = release.files(ROOT / 'tools/native_player')
        self.assertIn('player.py', actual)
        self.assertFalse(any(p.startswith('debian/') for p in actual))
        self.assertEqual(actual['player.py'], hashlib.sha256((ROOT / 'tools/native_player/player.py').read_bytes()).hexdigest())

    def test_unprepared_isolation_is_refused(self):
        with self.assertRaises(ValueError):
            isolation.command(ROOT, ROOT / 'not-an-executable', ['dpkg', '--audit'])


class NativeArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Required fixtures fail, not skip: run only in the approved native batch.
        cls.artifacts = Path(os.environ['HDR_MERGED_ARTIFACT_ROOT'])
        cls.mutter = cls.artifacts / 'mutter'
        cls.launcher = cls.artifacts / 'launcher'
        cls.library = cls.artifacts / 'library'

    def control(self, path, field):
        return subprocess.check_output(['dpkg-deb', '-f', str(path), field], text=True).strip()

    def payload(self, path):
        data = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(path)])
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as packed:
            result = {}
            for member in packed.getmembers():
                stream = packed.extractfile(member) if member.isfile() else None
                result[member.name.removeprefix('./')] = (member, stream.read() if stream else None)
            return result

    def test_normal_source_and_binary_closures(self):
        for directory, component, count in [(self.mutter, 'mutter', 9), (self.launcher, 'hermes-hdr-experimental-player', 1)]:
            with self.subTest(component=component):
                self.assertEqual(len(list(directory.glob('*.deb'))), count)
                self.assertEqual(len(list(directory.glob('*.dsc'))), 1)
                self.assertTrue(list(directory.glob('*.changes')))
                self.assertTrue(list(directory.glob('*.buildinfo')))
                dsc, = directory.glob('*.dsc')
                self.assertIn('Source: ' + component, dsc.read_text())
                self.assertTrue(list(directory.glob('*.tar.xz')))
        receipt = json.loads((self.mutter / 'source-receipt.json').read_text())
        self.assertTrue(receipt['source_roundtrip_equal'])
        self.assertTrue(receipt['binary_build'])
        self.assertEqual(receipt['canonical_tree'], release.MUTTER_TREE)
        self.assertEqual(receipt['units_executed'], 0)
        for name, digest in receipt['artifacts'].items():
            self.assertEqual(hashlib.sha256((self.mutter / name).read_bytes()).hexdigest(), digest)

    def test_mutter_version_abi_and_dependencies(self):
        expected = {'mutter', 'mutter-common', 'mutter-common-bin', 'mutter-dev-bin',
                    'libmutter-51-0', 'libmutter-51-dev', 'gir1.2-mutter-51',
                    'libmutter-test-51', 'mutter-51-tests'}
        packages = {self.control(p, 'Package'): p for p in self.mutter.glob('*.deb')}
        self.assertEqual(set(packages), expected)
        for name, path in packages.items():
            self.assertEqual(self.control(path, 'Version'), release.VERSION)
            self.assertEqual(self.control(path, 'Architecture'), 'all' if name == 'mutter-common' else 'amd64')
        runtime = self.control(packages['libmutter-51-0'], 'Depends')
        self.assertIn('libdisplay-info3-native-hdr-api (>= 2)', runtime)
        self.assertIn('libdisplay-info3 (>= 0.3.0-1ubuntu1~hdr9)', runtime)
        self.assertIn('libmutter-51-0 (= ' + release.VERSION + ')', self.control(packages['libmutter-51-dev'], 'Depends'))
        self.assertIn('libgtk-4-1 (>= 4.22.0)', self.control(packages['mutter-common-bin'], 'Depends'))
        symbols = self.payload(packages['libmutter-51-0'])
        self.assertIn('usr/lib/x86_64-linux-gnu/libmutter-51.so.0.0.0', symbols)

    def test_payload_ownership_modes_and_no_manual_prefix(self):
        for path in sorted(self.mutter.glob('*.deb')) + sorted(self.launcher.glob('*.deb')):
            for name, (member, _) in self.payload(path).items():
                with self.subTest(package=path.name, file=name):
                    self.assertFalse(name.startswith(('usr/local/', 'home/', 'work/')))
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)
                    self.assertEqual(member.mode & 0o6000, 0)

    def test_launcher_exact_payload_and_declared_stock_dependencies(self):
        deb, = self.launcher.glob('*.deb')
        self.assertEqual(self.control(deb, 'Version'), '1.0~experimental3')
        self.assertEqual(self.control(deb, 'Architecture'), 'all')
        depends = self.control(deb, 'Depends')
        for dependency in ['python3 (>= 3.11)', 'mpv (>= 0.41.0)', 'libplacebo360 (>= 7.360.1)', 'libavcodec62 (>= 7:8.1.2)', 'libavutil60 (>= 7:8.1.2)']:
            self.assertIn(dependency, depends)
        payload = self.payload(deb)
        for source, target, mode in [('player.py', 'usr/bin/hermes-hdr-player', 0o755),
                                    ('player.desktop', 'usr/share/applications/hermes-hdr-player.desktop', 0o644),
                                    ('inputs.json', 'usr/share/doc/hermes-hdr-experimental-player/inputs.json', 0o644)]:
            self.assertEqual(payload[target][1], (ROOT / 'tools/native_player' / source).read_bytes())
            self.assertEqual(payload[target][0].mode, mode)
        control = subprocess.check_output(['dpkg-deb', '--ctrl-tarfile', str(deb)])
        with tarfile.open(fileobj=io.BytesIO(control), mode='r:') as packed:
            names = {p.name.removeprefix('./') for p in packed.getmembers()}
        self.assertFalse(names.intersection({'preinst', 'postinst', 'prerm', 'postrm'}))

    def test_hdr9_multiarch_original_identity_and_shared_files(self):
        manifest = json.loads((self.library / 'RETAINED.json').read_text())
        for filename, digest in manifest['binaries'].items():
            path = self.library / filename
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            self.assertEqual(self.control(path, 'Version'), '0.3.0-1ubuntu1~hdr9')
        for name in ['libdisplay-info3', 'libdisplay-info-dev']:
            payloads = []
            for arch in ['amd64', 'i386']:
                path = self.library / (name + '_0.3.0-1ubuntu1~hdr9_' + arch + '.deb')
                self.assertEqual(self.control(path, 'Multi-Arch'), 'same')
                payloads.append(self.payload(path))
            for shared in payloads[0].keys() & payloads[1].keys():
                self.assertEqual(payloads[0][shared][1], payloads[1][shared][1], shared)


if __name__ == '__main__':
    unittest.main()
