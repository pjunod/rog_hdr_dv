"""Bounded packaging guards; retained animation behavioral cases are not rerun."""
import importlib.util
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tiling_package', ROOT / 'scripts/package_tiling_animation.py')
assert spec is not None and spec.loader is not None
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class TilingPackageTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work/tiling-package-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)
        self.name = package.EXTENSION + '/src/extension/utility.js'
        p = self.source / self.name
        p.parent.mkdir(parents=True)
        p.write_text('unchanged runtime dependency\n')
        self.expected = {
            '.gitignore': {'sha256': '0' * 64, 'executable': False},
            self.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'executable': False},
        }
        for name in package.PACKAGE_ADDITIONS:
            p = self.source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('Ubuntu packaging\n')

    def test_full_inventory_accepts_only_documented_package_differences(self):
        additions = package.verify_subproject(self.source, self.expected)
        self.assertEqual(set(additions), package.PACKAGE_ADDITIONS)

    def test_unchanged_runtime_dependency_byte_drift_is_rejected(self):
        (self.source / self.name).write_text('mutated dependency\n')
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            package.verify_subproject(self.source, self.expected)

    def test_runtime_executable_mode_drift_is_rejected(self):
        (self.source / self.name).chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'mode differs'):
            package.verify_subproject(self.source, self.expected)

    def test_missing_runtime_dependency_is_rejected(self):
        (self.source / self.name).unlink()
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            package.verify_subproject(self.source, self.expected)

    def test_unexpected_runtime_file_is_rejected(self):
        (self.source / 'unexpected.js').write_text('unowned\n')
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            package.verify_subproject(self.source, self.expected)

    def test_runtime_symlink_is_rejected_even_with_equal_bytes(self):
        p = self.source / self.name
        p.unlink()
        target = self.source / 'meson.build'
        p.symlink_to(target)
        self.expected[self.name]['sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            package.verify_subproject(self.source, self.expected)

    def test_wrong_candidate_stops_before_output_creation(self):
        output = self.source / 'new-output'
        with mock.patch.object(package, 'run', return_value='0' * 40):
            with self.assertRaisesRegex(ValueError, 'not the qualified source'):
                package.prepare(self.source, self.source, output, 1793646237)
        self.assertFalse(output.exists())

    def test_system_temporary_and_owner_paths_are_rejected(self):
        for path in (Path('/tmp/source'), Path('/private/tmp/output'),
                     Path('/var/tmp/receipt'), Path.home() / 'code/owner'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'durable owned'):
                package.durable(path)

    def test_missing_pinned_packaging_tool_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'packaging tool unavailable'):
            package.verify_tools(self.source)

    def test_pinned_packaging_tool_bytes_are_required(self):
        tool = self.source / 'tool.deb'
        tool.write_bytes(b'authenticated tool bytes')
        with mock.patch.object(package, 'UBUNTU_TOOLS', {'tool.deb': package.digest(tool)}):
            package.verify_tools(self.source)
            tool.write_bytes(b'different tool')
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                package.verify_tools(self.source)

    def test_build_without_declared_ubuntu_policy_stops_before_source_preparation(self):
        args = ['package', '--inputs', str(self.source), '--candidate-repository', str(self.source),
                '--output', str(ROOT.parent / 'unused-test-output'), '--epoch', '1793646237', '--build']
        with mock.patch.object(sys, 'argv', args), mock.patch.object(package, 'prepare') as prepare:
            with self.assertRaises(SystemExit) as error:
                package.main()
            self.assertEqual(error.exception.code, 2)
            prepare.assert_not_called()

    def test_build_environment_uses_official_wrapper_and_durable_local_policy(self):
        real = self.source / 'ordinary-dpkg-deb'
        real.write_text('ordinary tool fixture')

        def extract(command, check):
            self.assertTrue(check)
            prefix = Path(command[-1])
            config = prefix / 'etc/pkgbinarymangler'
            config.mkdir(parents=True, exist_ok=True)
            (config / 'striptranslations.conf').write_text('enable: false\ncomponents: main\n')
            bin_dir = prefix / 'usr/bin'
            bin_dir.mkdir(parents=True, exist_ok=True)
            for name in ('dpkg-deb', 'dh_builddeb', 'pkgstriptranslations', 'lockfile-create'):
                (bin_dir / name).write_text('unchanged official fixture\n')

        output = self.source / 'output'
        with mock.patch.object(package, 'verify_tools'), \
                mock.patch.object(package, 'run', return_value='amd64'), \
                mock.patch.object(package.shutil, 'which', return_value=str(real)), \
                mock.patch.object(package.subprocess, 'run', side_effect=extract), \
                mock.patch.dict(os.environ, {'NO_PKG_MANGLE': '1', 'PKG_IGNORE_CURRENTLY_BUILDING': '1'}):
            env = package.build_environment(self.source, output)
        root = output / 'build-environment'
        self.assertEqual(env['PATH'].split(os.pathsep)[0], str(root / 'bin'))
        self.assertNotIn('NO_PKG_MANGLE', env)
        self.assertNotIn('PKG_IGNORE_CURRENTLY_BUILDING', env)
        self.assertEqual(Path(env['TMPDIR']), root / 'scratch')
        self.assertEqual((root / 'bin/dpkg-deb').read_text(), 'unchanged official fixture\n')
        self.assertEqual((root / 'bin/dpkg-deb.pkgbinarymangler').resolve(), real)
        self.assertFalse((root / 'bin/dh_builddeb').exists())
        self.assertTrue((root / 'prefix/usr/bin/dh_builddeb').exists())
        self.assertIn('enable: true', (Path(env['PKGBINARYMANGLER_CONF_DIR']) / 'striptranslations.conf').read_text())
        self.assertIn('Component: main', Path(env['CURRENTLY_BUILDING_PATH']).read_text())
        self.assertTrue((output / 'build-environment.json').is_file())


if __name__ == '__main__':
    unittest.main()
