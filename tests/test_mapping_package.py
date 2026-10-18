"""Deferred package-wrapper control regressions; no vendor/render fixtures."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('abi368_package_run', ROOT / 'packaging/rog-hdr-dm-experimental/run.py')
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class PackageWrapperTests(unittest.TestCase):
    def test_environment_does_not_inherit_loader_display_or_driver_overrides(self):
        stage = Path('/work/task-owned-package-control')
        with patch.dict(os.environ, {'LD_PRELOAD': '/wrong', 'LD_LIBRARY_PATH': '/wrong',
                                     'DISPLAY': ':0', 'WAYLAND_DISPLAY': 'wrong',
                                     'VK_DRIVER_FILES': '/wrong', 'HOME': '/wrong'}):
            env = runner.environment(stage)
        self.assertNotIn('LD_PRELOAD', env)
        self.assertNotIn('LD_LIBRARY_PATH', env)
        self.assertNotIn('DISPLAY', env)
        self.assertNotIn('WAYLAND_DISPLAY', env)
        self.assertEqual(env['VK_DRIVER_FILES'], str(runner.ICD))
        self.assertEqual(env['TMPDIR'], str(stage))
        self.assertEqual(env['HOME'], str(stage))
        self.assertEqual(env['VK_LOADER_LAYERS_DISABLE'], '~all~')

    def test_duplicate_fields_and_changed_package_schema_fail_closed(self):
        with self.assertRaises(ValueError):
            runner.unique([('abi', 368), ('abi', 368)])
        # Malformed package-control metadata only. No passing native/vendor data.
        with patch.object(runner.platform, 'system', return_value='Linux'), \
             patch.object(runner.platform, 'machine', return_value='x86_64'), \
             patch.object(Path, 'exists', return_value=False), \
             patch.object(runner, 'read_json', return_value={'schema': 'hdr.open-dm-compile.v1'}):
            with self.assertRaisesRegex(ValueError, 'package identity/schema'):
                runner.installed(Path('/work/not-a-package'), {})

    def test_system_temporary_and_existing_stages_rejected_without_changes(self):
        for path in ('/tmp/abi368-must-not-create', '/private/tmp/abi368-must-not-create',
                     '/var/tmp/abi368-must-not-create'):
            with self.assertRaisesRegex(ValueError, 'durable'):
                runner.durable_stage(Path(path))
        # TMPDIR is explicitly the task-owned durable directory in the batch.
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as directory:
            with self.assertRaises(FileExistsError):
                runner.durable_stage(Path(directory))
            new = runner.durable_stage(Path(directory) / 'new')
            self.assertTrue(new.is_dir())

    def test_dependency_resolution_rejects_missing_or_empty_closure(self):
        for output, reason in (('libplacebo.so.368 => not found\n', 'unresolved'),
                               ('statically linked\n', 'empty')):
            completed = type('Completed', (), {'stdout': output})()
            with patch.object(runner.subprocess, 'run', return_value=completed):
                with self.assertRaisesRegex(ValueError, reason):
                    runner.dependencies(Path('/work/control-only'), {})
