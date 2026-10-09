"""Focused socket fixtures. Run only after review, using explicitly built binaries.

WAYLAND_COLOR_INFO_BUILD must name an external build directory. Each invocation
creates a private runtime directory and a synthetic server; no real desktop is used.
"""
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time
import unittest


class ProtocolTests(unittest.TestCase):
    def capture(self, scenario, version=2):
        build = Path(os.environ['WAYLAND_COLOR_INFO_BUILD']).resolve()
        with tempfile.TemporaryDirectory(prefix='color-info-fixture-') as runtime:
            os.chmod(runtime, 0o700)
            env = dict(os.environ, XDG_RUNTIME_DIR=runtime, WAYLAND_DISPLAY='fixture')
            env.pop('WAYLAND_SOCKET', None)
            env.pop('WAYLAND_DEBUG', None)
            server = subprocess.Popen([str(build / 'color-info-fixture'), scenario, str(version)],
                                      env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertTrue(select.select([server.stdout], [], [], 2)[0], 'fixture startup timeout')
                self.assertEqual(server.stdout.readline().strip(), 'READY')
                started = time.monotonic()
                probe = subprocess.run([str(build / 'wayland-color-info')], env=dict(env, WAYLAND_DEBUG='1'),
                                       capture_output=True, text=True, timeout=7)
                elapsed = time.monotonic() - started
                data = json.loads(probe.stdout)
                self.assertLess(len(probe.stdout), 65536)
                for private in ('PRIVATE-MAKE', 'PRIVATE-MODEL', 'PRIVATE-SERVER-ERROR', runtime):
                    self.assertNotIn(private, probe.stdout + probe.stderr)
                if scenario == 'icc-hang':
                    self.assertTrue(select.select([server.stdout], [], [], 1)[0])
                    self.assertEqual(server.stdout.readline().strip(), 'ICC_READ_END_CLOSED')
                return probe.returncode, data, elapsed
            finally:
                server.terminate()
                try:
                    server.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.communicate()

    def test_rejected_build_path_creates_nothing(self):
        source = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(prefix='color-info-build-guard-') as tmp:
            root = Path(tmp) / 'checkout'
            probe = root / 'probes' / 'wayland_color_info'
            probe.mkdir(parents=True)
            (root / 'AGENTS.md').write_text('Synthetic checkout marker')
            shutil.copyfile(source / 'build.sh', probe / 'build.sh')
            output = root / 'not-created' / 'build'
            result = subprocess.run(['sh', str(probe / 'build.sh'), str(output)],
                                    capture_output=True, text=True, timeout=2)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.parent.exists())
            alias = Path(tmp) / 'alias'
            alias.symlink_to(root, target_is_directory=True)
            result = subprocess.run(['sh', str(probe / 'build.sh'), str(alias / 'not-created')],
                                    capture_output=True, text=True, timeout=2)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'not-created').exists())

    def test_versions_and_global_order(self):
        for version in (1, 2):
            for scenario in ('normal', 'manager-first', 'output-v1'):
                with self.subTest(version=version, scenario=scenario):
                    code, data, _ = self.capture(scenario, version)
                    self.assertEqual(code, 0)
                    self.assertEqual(data['status'], 'complete')
                    self.assertEqual(data['manager_version'], version)
                    o = data['outputs'][0]
                    self.assertEqual(o['description_identity']['hi'], 0 if version == 1 else 1)
                    self.assertEqual(o['luminances']['raw'], [500, 1000, 203])
                    self.assertEqual(o['target_luminance']['raw'], [100, 616])
                    self.assertNotEqual(o['primaries']['raw'], o['target_primaries']['raw'])
                    self.assertTrue(o['tf_power']['present'] and o['tf_named']['present'])
                    self.assertEqual(o['tf_named']['raw'], [2])
                    self.assertEqual(o['tf_pair_consistency'], 'consistent')
                    self.assertEqual(o['target_max_cll']['raw'], [600])
                    self.assertEqual(o['target_max_fall']['raw'], [300])

    def test_non_success_protocol_cases(self):
        for scenario in ('absent', 'duplicate', 'incomplete', 'remove', 'changed', 'failed', 'overflow', 'disconnect', 'contradictory-tf', 'manager-remove'):
            with self.subTest(scenario=scenario):
                code, data, _ = self.capture(scenario)
                self.assertNotEqual(code, 0)
                self.assertEqual(data['status'], 'incomplete')
                self.assertLessEqual(len(data['outputs']), 32)
                if scenario == 'remove':
                    self.assertEqual(data['outputs'][0]['status'], 'removed')
                if scenario == 'changed':
                    self.assertEqual(data['snapshot_consistency'], 'unstable')

    def test_deadline_and_missing_completion(self):
        for scenario in ('hang', 'missing-done', 'icc-hang'):
            with self.subTest(scenario=scenario):
                code, data, elapsed = self.capture(scenario)
                self.assertNotEqual(code, 0)
                self.assertEqual(data['reason'], 'deadline')
                self.assertGreater(elapsed, 4)
                self.assertLess(elapsed, 6.5)

    def test_icc_presence_without_contents(self):
        code, data, _ = self.capture('icc')
        self.assertEqual(code, 0)
        o = data['outputs'][0]
        self.assertEqual(o['icc_size'], {'present': True, 'raw': [123]})
        self.assertFalse(o['primaries']['present'])
        self.assertEqual(o['primaries']['raw'], [])


if __name__ == '__main__':
    unittest.main()
