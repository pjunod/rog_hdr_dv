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

    def assert_success(self, scenario, version):
        code, data, _ = self.capture(scenario, version)
        self.assertEqual(code, 0)
        self.assertEqual(data['status'], 'complete')
        self.assertEqual(data['manager_version'], version)
        self.assertEqual(len(data['outputs']), 32 if scenario == 'max' else 1)
        o = data['outputs'][0]
        self.assertEqual(o['description_identity']['hi'], 0 if version == 1 else 1)
        self.assertEqual(o['luminances']['raw'], [500, 1000, 203])
        self.assertEqual(o['target_luminance']['raw'], [100, 616])
        # Exact values pin which event fills which field, not just that they differ.
        self.assertEqual(o['primaries']['raw'],
                         [640000, 330000, 300000, 600000, 150000, 60000, 312700, 329000])
        self.assertEqual(o['target_primaries']['raw'],
                         [680000, 320000, 265000, 690000, 150000, 60000, 312700, 329000])
        self.assertTrue(o['tf_power']['present'] and o['tf_named']['present'])
        self.assertEqual(o['tf_named']['raw'], [2])
        self.assertEqual(o['tf_pair_consistency'], 'consistent')
        self.assertEqual(o['target_max_cll']['raw'], [600])
        self.assertEqual(o['target_max_fall']['raw'], [300])

    def assert_non_success(self, scenario):
        code, data, _ = self.capture(scenario)
        self.assertNotEqual(code, 0)
        self.assertEqual(data['status'], 'incomplete')
        self.assertLessEqual(len(data['outputs']), 32)
        expected_reason = {'absent': 'unsupported_protocol', 'overflow': 'output_cap',
                           'disconnect': 'disconnect', 'manager-remove': 'manager_removed'}
        if scenario in expected_reason:
            self.assertEqual(data['reason'], expected_reason[scenario])
        if scenario == 'remove':
            self.assertEqual(data['outputs'][0]['status'], 'removed')
        if scenario == 'changed':
            self.assertEqual(data['snapshot_consistency'], 'unstable')
        if scenario == 'contradictory-tf':
            self.assertEqual(data['outputs'][0]['tf_pair_consistency'], 'contradictory')
        if scenario == 'manager-remove':
            self.assertTrue(data['manager_removed'])

    def assert_deadline(self, scenario):
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


# Each case has an exact unittest selector; retries never repeat passing scenarios.
def success_case(scenario, version):
    def test(self):
        self.assert_success(scenario, version)
    return test


def failure_case(scenario):
    def test(self):
        self.assert_non_success(scenario)
    return test


def deadline_case(scenario):
    def test(self):
        self.assert_deadline(scenario)
    return test


for protocol_version in (1, 2):
    for fixture_scenario in ('normal', 'manager-first', 'output-v1', 'max'):
        setattr(ProtocolTests, f'test_v{protocol_version}_{fixture_scenario.replace("-", "_")}',
                success_case(fixture_scenario, protocol_version))
for fixture_scenario in ('absent', 'duplicate', 'incomplete', 'remove', 'changed',
                         'failed', 'overflow', 'disconnect', 'contradictory-tf', 'manager-remove'):
    setattr(ProtocolTests, f'test_failure_{fixture_scenario.replace("-", "_")}',
            failure_case(fixture_scenario))
for fixture_scenario in ('hang', 'missing-done', 'icc-hang'):
    setattr(ProtocolTests, f'test_deadline_{fixture_scenario.replace("-", "_")}',
            deadline_case(fixture_scenario))


if __name__ == '__main__':
    unittest.main()
