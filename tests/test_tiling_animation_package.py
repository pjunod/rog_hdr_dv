"""Bounded packaging guards; retained animation behavioral cases are not rerun."""
import importlib.util
import hashlib
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
