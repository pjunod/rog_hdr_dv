"""Managed public package families: completeness, immutability and stale pins.

The companion APT integration cases use the real apt-get solver and dpkg's
version comparison; they never modify the host package database.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('managed_ubuntu', ROOT / 'packaging/ubuntu/managed.py')
managed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(managed)


def fixture():
    data = {'webkit2gtk': {'expected_package_version': '2.52.6-1ubuntu1+rogdv7', 'derivative': '+rogdv', 'packages': {'amd64': ['libwebkitgtk-6.0-4', 'libjavascriptcoregtk-6.0-1']}}}
    rows = [{'Package': name, 'Source': 'webkit2gtk', 'Version': '2.52.6-1ubuntu1+rogdv7',
             'Architecture': 'amd64', 'SHA256': 'a' * 64}
            for name in data['webkit2gtk']['packages']['amd64']]
    return data, rows


class ManagedPolicyTests(unittest.TestCase):
    def test_every_managed_family_has_an_authoritative_full_version(self):
        for source, spec in managed.families().items():
            if not spec.get('policy_only'):
                self.assertIn(spec['derivative'], managed.expected_version(source, spec))

    def test_old_and_arbitrarily_new_derivative_versions_are_not_release_candidates(self):
        data, rows = fixture()
        installed = [{'Package': rows[0]['Package'], 'Architecture': 'amd64'}]
        for version in ('2.52.6-1ubuntu1+rogdv6', '2.52.6-1ubuntu1+rogdv999'):
            wrong = [dict(row, Version=version) for row in rows]
            with self.assertRaisesRegex(ValueError, 'intended full candidate'):
                managed.validate_bundle(wrong, data)
            with self.assertRaisesRegex(ValueError, 'intended'):
                managed.preflight(installed, wrong, data)
            with self.assertRaisesRegex(ValueError, 'no complete published'):
                managed.publication_freshness(data, wrong, {'webkit2gtk': '2.52.6-1ubuntu1'})

    def test_existing_partial_target_hash_conflict_is_refused(self):
        _, rows = fixture()
        with self.assertRaisesRegex(ValueError, 'immutable version conflict'):
            managed.preflight_existing(rows, [dict(rows[1], SHA256='b' * 64)])
        managed.preflight_existing(rows, rows[:1])

    def test_simulation_requires_exact_authenticated_source_version_architecture(self):
        data, rows = fixture()
        name = rows[0]['Package']
        version = rows[0]['Version']
        managed.validate_simulation(f'Inst {name} ({version} project [amd64])', rows, data)
        for line in (f'Inst {name} (2.52.6-1ubuntu1.1 Ubuntu [amd64])',
                     f'Inst {name}:i386 ({version} project [i386])',
                     f'Inst unknown ({version} project [amd64])', f'Remv {name} [{version}]'):
            with self.subTest(line=line), self.assertRaises(ValueError):
                managed.validate_simulation(line, rows, data)
        with self.assertRaisesRegex(ValueError, 'source/version/architecture'):
            managed.validate_simulation(f'Inst {name} ({version} project [amd64])',
                                       [dict(r, Source='foreign-source') for r in rows], data)

    def test_complete_family_and_exact_index_hash(self):
        data, rows = fixture()
        managed.validate_bundle(rows, data)
        managed.verify_index(rows, rows)
        corrupt = copy.deepcopy(rows)
        corrupt[1]['SHA256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            managed.verify_index(rows, corrupt)

    def test_missing_mixed_duplicate_and_foreign_refused(self):
        data, rows = fixture()
        for bad in (rows[:1], rows + [rows[0]], [dict(rows[0], Version='stock'), rows[1]],
                    [dict(rows[0], Source='private-provider'), rows[1]],
                    [dict(rows[0], Version='2.52.6-1ubuntu1+rogdv8'), rows[1]]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                managed.validate_bundle(bad, data)

    def test_preflight_refuses_missing_companion_before_targets(self):
        data, rows = fixture()
        installed = [{'Package': rows[0]['Package'], 'Architecture': 'amd64'}]
        with self.assertRaisesRegex(ValueError, 'no complete family'):
            managed.preflight(installed, rows[:1], data)
        self.assertEqual(managed.preflight(installed, rows, data),
                         ['libwebkitgtk-6.0-4:amd64=2.52.6-1ubuntu1+rogdv7'])

    @unittest.skipUnless(shutil.which('dpkg'), 'requires Debian comparator')
    def test_preflight_refuses_newer_installed_patchset_downgrade(self):
        data, rows = fixture()
        installed = [{'Package': rows[0]['Package'], 'Architecture': 'amd64',
                      'InstalledVersion': '2.52.6-1ubuntu1+rogdv15'}]
        with self.assertRaisesRegex(ValueError, 'automatic downgrade refused'):
            managed.preflight(installed, rows, data)

    def test_preferences_are_scoped_and_cover_companions(self):
        data, rows = fixture()
        result = managed.preferences(data, 'forge.lan')
        self.assertNotIn('Package: *', result)
        self.assertIn('Pin-Priority: 999', result)
        self.assertIn('libwebkitgtk-6.0-4:amd64', result)
        self.assertIn('Pin: version *+rogdv*', result)
        for row in rows:
            self.assertIn(row['Package'], result)

    @unittest.skipUnless(shutil.which('dpkg'), 'requires Debian comparator')
    def test_source_monitor_fails_for_newer_authenticated_revision(self):
        data, _ = fixture()
        with patch.object(managed, 'reviewed_version', return_value='2.52.6-1ubuntu1'), patch.object(
                managed, 'run', return_value='Package: webkit2gtk\nVersion: 2.52.6-1ubuntu1.1\n\n'):
            with self.assertRaisesRegex(ValueError, 'Ubuntu fixes are waiting'):
                managed.freshness(data)

    def test_source_monitor_refuses_empty_metadata(self):
        data, _ = fixture()
        with patch.object(managed, 'reviewed_version', return_value='2.52.6-1ubuntu1'), patch.object(
                managed, 'run', return_value=''):
            with self.assertRaisesRegex(ValueError, 'source index is missing'):
                managed.freshness(data)

    def test_separate_playback_releases_get_scoped_fallback_without_origin(self):
        data = {s: f for s, f in managed.families().items() if f.get('policy_only')}
        self.assertEqual(set(data), {'mpv', 'ffmpeg', 'mesa', 'gnome-shell-ubuntu-extensions', 'network-manager'})
        policy = managed.preferences(data, 'forge.lan')
        self.assertNotIn('Pin: origin', policy)
        self.assertIn('Pin: version *+rogwsi*', policy)
        self.assertIn('Pin: version *+nativehdr*', policy)
        self.assertIn('Pin: version *+rogsleep*', policy)
        for name in ('mpv', 'libavcodec62', 'libavdevice62', 'libavformat62', 'libavfilter11', 'mesa-vulkan-drivers', 'gnome-shell-ubuntu-extensions', 'network-manager'):
            self.assertIn(name, policy)
        self.assertEqual(managed.preflight([{'Package': 'mpv', 'Architecture': 'amd64'}], [], data), [])
        with self.assertRaisesRegex(ValueError, 'preference/monitor only'):
            managed.validate_bundle([{'Package': 'mpv', 'Source': 'mpv'}], data)
        self.assertEqual(managed.reviewed_version('mpv', data['mpv']), '0.41.0-2ubuntu5')
        self.assertEqual(managed.reviewed_version('gnome-shell-ubuntu-extensions', data['gnome-shell-ubuntu-extensions']), '51.26.10.6ubuntu')
        self.assertEqual(managed.reviewed_version('network-manager', data['network-manager']), '1.58.1-1ubuntu3')

    @unittest.skipUnless(shutil.which('dpkg'), 'requires Debian comparator')
    def test_separate_playback_source_drift_is_actionable(self):
        data = {'mpv': managed.families()['mpv']}
        with patch.object(managed, 'run', return_value='Package: mpv\nVersion: 0.41.0-2ubuntu6\n\n'):
            with self.assertRaisesRegex(ValueError, 'separate project release') as error:
                managed.freshness(data)
        self.assertIn('Ubuntu packaging base only', str(error.exception))

    def test_current_source_requires_complete_current_published_family(self):
        data, rows = fixture()
        current = {'webkit2gtk': '2.52.6-1ubuntu1'}
        managed.publication_freshness(data, rows, current)
        old = [dict(row, Version='2.52.6-1ubuntu0.1+rogdv7') for row in rows]
        with self.assertRaisesRegex(ValueError, 'waiting for publication'):
            managed.publication_freshness(data, old, current)
        with self.assertRaisesRegex(ValueError, 'every required binary'):
            managed.publication_freshness(data, rows[:1], current)
        with self.assertRaisesRegex(ValueError, 'no authenticated current Ubuntu source'):
            managed.publication_freshness(data, rows, {})

    def test_webkit_publication_requires_exact_reviewed_package_version(self):
        spec = managed.families()['webkit2gtk']
        pin = json.loads((ROOT / spec['pin']).read_text())
        rows = [{'Package': name, 'Source': 'webkit2gtk', 'Version': pin['package_version'],
                 'Architecture': arch, 'SHA256': 'a' * 64} for name, arch in managed.expected(spec)]
        data = {'webkit2gtk': spec}
        current = {'webkit2gtk': pin['source_version']}
        managed.publication_freshness(data, rows, current)
        rows[0]['Version'] = pin['package_version'] + '.older-review'
        with self.assertRaisesRegex(ValueError, 'no complete published'):
            managed.publication_freshness(data, rows, current)

    def test_policy_only_families_need_no_registry_publication(self):
        data = {s: f for s, f in managed.families().items() if f.get('policy_only')}
        managed.publication_freshness(data, [], {})

    def test_missing_authenticated_project_index_is_distinct(self):
        with patch.object(managed, 'run', return_value=''):
            with self.assertRaisesRegex(ValueError, 'index unavailable'):
                managed.authenticated_project_index('http://forge.lan:3000/api/packages/operator/debian')

    def test_webkit_inventory_is_exact_recipe_inventory(self):
        data = managed.families()
        pin = json.loads((ROOT / data['webkit2gtk']['pin']).read_text())
        self.assertEqual(set(pin['binary_packages']), set(data['webkit2gtk']['packages']['amd64']))
        for source, spec in data.items():
            if not spec.get('project'):
                self.assertTrue(managed.reviewed_version(source, spec))


@unittest.skipUnless(shutil.which('apt-get') and shutil.which('dpkg'), 'requires Ubuntu APT/dpkg')
class RealAptPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ('state/lists/partial', 'cache/archives/partial', 'etc/preferences.d', 'etc/sources.list.d', 'repo'):
            (self.root / folder).mkdir(parents=True)
        self.data, self.rows = fixture()
        self.name = self.rows[0]['Package']
        (self.root / 'etc/preferences').write_text(managed.preferences(self.data, 'project.invalid'))
        (self.root / 'etc/sources.list').write_text(f'deb [trusted=yes] file:{self.root}/repo ./\n')
        # Trusted local fixture indexes contain no network source or system key.
        # Production setup uses signed APT metadata and has no trusted override.
        self.options = [f'-oDir={self.root}', '-oDir::State=state', '-oDir::State::status=state/status',
                        '-oDir::Cache=cache', '-oDir::Etc=etc', '-oAPT::Architecture=amd64',
                        '-oAPT::Architectures::=amd64', '-oDebug::NoLocking=1', '-oAPT::Sandbox::User=root',
                        '-oAcquire::AllowInsecureRepositories=true']
        self.installed = '2.52.6-1ubuntu1+rogdv7'
        (self.root / 'state/status').write_text(f'Package: {self.name}\nStatus: install ok installed\nArchitecture: amd64\nVersion: {self.installed}\nDescription: isolated fixture\n\n')

    def solve(self, versions):
        entries = []
        for version in versions:
            entries.append(f'Package: {self.name}\nVersion: {version}\nArchitecture: amd64\nFilename: fixture.deb\nSize: 1\nSHA256: {"a" * 64}\nDescription: isolated fixture\n\n')
        (self.root / 'repo/Packages').write_text(''.join(entries))
        subprocess.run(['apt-get', *self.options, 'update'], check=True, capture_output=True, text=True)
        return subprocess.check_output(['apt-get', *self.options, '-s', 'install', self.name], text=True)

    def test_absent_registry_keeps_installed_derivative_over_newer_stock(self):
        result = self.solve(['2.52.6-1ubuntu1.1'])
        self.assertNotIn('Inst ' + self.name, result)

    def test_present_registry_keeps_derivative_over_newer_stock(self):
        result = self.solve([self.installed, '2.52.6-1ubuntu1.1'])
        self.assertNotIn('Inst ' + self.name, result)

    def test_newer_derivative_is_automatically_selected(self):
        version = '2.52.6-1ubuntu1.1+rogdv8'
        result = self.solve(['2.52.6-1ubuntu1.1', version])
        self.assertIn('Inst ' + self.name, result)
        self.assertIn(version, result)

    def test_older_project_origin_keeps_newer_installed_derivative(self):
        # file repositories have an empty origin hostname. Exercise the real
        # origin record as well as fallback with equal priorities.
        policy = managed.preferences(self.data, 'project.invalid').replace('origin "project.invalid"', 'origin ""')
        (self.root / 'etc/preferences').write_text(policy)
        version = '2.52.6-1ubuntu1+rogdv6'
        result = self.solve([version, '2.52.6-1ubuntu1.1'])
        self.assertNotIn('Inst ' + self.name, result)

    def test_foreign_i386_derivative_is_protected(self):
        self.name = 'libavcodec62'
        self.data = {'ffmpeg': {'policy_only': True, 'derivative': '+rogdv',
                               'packages': {'amd64': [self.name], 'i386': [self.name]}}}
        self.options.append('-oAPT::Architectures::=i386')
        installed = '7:8.1.2-2ubuntu2+rogdv4.2'
        (self.root / 'state/status').write_text(
            f'Package: {self.name}\nStatus: install ok installed\nArchitecture: i386\n'
            f'Version: {installed}\nMulti-Arch: same\nDescription: foreign fixture\n\n')
        (self.root / 'etc/preferences').write_text(managed.preferences(self.data, 'project.invalid'))
        self.assertIn(self.name + ':i386', managed.preferences(self.data, 'project.invalid'))
        (self.root / 'repo/Packages').write_text(
            f'Package: {self.name}\nVersion: 7:8.1.2-2ubuntu3\nArchitecture: i386\nMulti-Arch: same\n'
            f'Filename: fixture.deb\nSize: 1\nSHA256: {"a" * 64}\nDescription: foreign fixture\n\n')
        subprocess.run(['apt-get', *self.options, 'update'], check=True, capture_output=True, text=True)
        result = subprocess.check_output(['apt-get', *self.options, '-s', 'install', self.name + ':i386'], text=True)
        self.assertNotIn('Inst ' + self.name, result)

    def test_derivative_priority_beats_target_release_990(self):
        import hashlib
        self.solve([self.installed, '2.52.6-1ubuntu1.1'])
        payload = (self.root / 'repo/Packages').read_bytes()
        (self.root / 'repo/Release').write_text(
            'Suite: fixture\nCodename: fixture\nOrigin: Ubuntu\nLabel: Ubuntu\nArchitectures: amd64\n'
            'SHA256:\n ' + hashlib.sha256(payload).hexdigest() + f' {len(payload)} Packages\n')
        subprocess.run(['apt-get', *self.options, 'update'], check=True, capture_output=True, text=True)
        result = subprocess.check_output(['apt-get', *self.options, '-oAPT::Default-Release=fixture', '-s', 'install', self.name], text=True)
        self.assertNotIn('Inst ' + self.name, result)

    def test_separate_architecture_all_index_is_acquired_and_solved(self):
        import hashlib
        repo = self.root / 'repo'
        package = ('Package: mutter-common\nVersion: 51.0-1ubuntu3+nativehdr17\n'
                   'Architecture: all\nFilename: fixture.deb\nSize: 1\nSHA256: ' + 'a' * 64 +
                   '\nDescription: separate all-index fixture\n\n')
        entries = []
        for arch, content in (('amd64', ''), ('all', package)):
            relative = f'main/binary-{arch}/Packages'
            target = repo / 'dists/fixture' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            entries.append(f' {hashlib.sha256(content.encode()).hexdigest()} {len(content.encode())} {relative}\n')
        (repo / 'dists/fixture/Release').write_text(
            'Suite: fixture\nCodename: fixture\nArchitectures: amd64 all\nComponents: main\nSHA256:\n' + ''.join(entries))
        (self.root / 'etc/sources.list').write_text('')
        (self.root / 'etc/sources.list.d/project.sources').write_text(
            f'Types: deb\nURIs: file:{repo}\nSuites: fixture\nComponents: main\n'
            'Architectures-Add: all\nTrusted: yes\n')
        subprocess.run(['apt-get', *self.options, 'update'], check=True, capture_output=True, text=True)
        targets = subprocess.check_output(['apt-get', *self.options, 'indextargets', '--format', '$(URI)'], text=True)
        self.assertIn('binary-all/Packages', targets)
        result = subprocess.check_output(['apt-get', *self.options, '-s', 'install', 'mutter-common'], text=True)
        self.assertIn('Inst mutter-common', result)
        self.assertIn('51.0-1ubuntu3+nativehdr17', result)

    def test_debian_epoch_and_revision_ordering(self):
        self.assertEqual(subprocess.run(['dpkg', '--compare-versions', '1:2.0-1', 'gt', '9.0-1']).returncode, 0)
        self.assertEqual(subprocess.run(['dpkg', '--compare-versions', '2.52.6-1ubuntu1.1', 'gt', '2.52.6-1ubuntu1+rogdv7']).returncode, 0)


@unittest.skipUnless(shutil.which('apt-get'), 'requires the supported Ubuntu shell environment')
class SetupShellRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.recipe = self.root / 'packaging/ubuntu'
        self.recipe.mkdir(parents=True)
        for name in ('managed.py', 'managed-families.json'):
            shutil.copy2(ROOT / 'packaging/ubuntu' / name, self.recipe / name)
        self.etc = self.root / 'etc'
        for path in ('apt/keyrings', 'apt/sources.list.d', 'apt/preferences.d'):
            (self.etc / path).mkdir(parents=True)
        (self.etc / 'os-release').write_text('VERSION_CODENAME=fixture\n')
        text = (ROOT / 'packaging/ubuntu/setup-apt.sh').read_text().replace('/etc/', str(self.etc) + '/')
        (self.recipe / 'setup-apt.sh').write_text(text)
        fake = '''#!/usr/bin/env python3
import os, sys
from pathlib import Path
name, args = Path(sys.argv[0]).name, sys.argv[1:]
with open(os.environ['CALL_LOG'], 'a') as stream:
    stream.write(name + ' ' + ' '.join(args) + '\\n')
if name == 'id':
    print('0')
elif name == 'dpkg-query':
    if os.environ.get('POLICY_ONLY') == 'yes':
        print('mpv amd64 0.42.0-0ubuntu0+rogdv5.5 ii ')
elif name == 'curl':
    Path(args[args.index('-o') + 1]).write_text('new fixture key')
elif name == 'apt-get' and args[0] == 'update' and os.environ.get('FAIL_UPDATE') == 'yes':
    sys.exit(23)
'''
        for name in ('id', 'dpkg-query', 'curl', 'apt-get', 'apt-mark'):
            path = self.bin / name
            path.write_text(fake)
            path.chmod(0o755)
        (self.root / 'tmp').mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        TMPDIR=str(self.root / 'tmp'), CALL_LOG=str(self.root / 'calls'))

    def setup(self, **env):
        return subprocess.run(['bash', str(self.recipe / 'setup-apt.sh'), 'http://project.invalid', 'operator'],
                              env=dict(self.env, **env), capture_output=True, text=True)

    def test_empty_or_policy_only_host_does_not_attempt_empty_install(self):
        for policy in ('no', 'yes'):
            with self.subTest(policy=policy):
                (self.root / 'calls').write_text('')
                result = self.setup(POLICY_ONLY=policy)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('configured intentionally', result.stdout)
                calls = (self.root / 'calls').read_text()
                self.assertNotIn('apt-get install', calls)
                self.assertNotIn('apt-get -s', calls)
                self.assertNotIn('apt-mark unhold', calls)

    def test_failed_authenticated_update_restores_bytes_modes_links_and_absence(self):
        source = self.etc / 'apt/sources.list.d/rog-hdr-dv.sources'
        source.write_bytes(b'original source bytes\n')
        source.chmod(0o640)
        target = self.etc / 'original-policy'
        target.write_bytes(b'original protected policy\n')
        target.chmod(0o600)
        preferences = self.etc / 'apt/preferences.d/rog-hdr-dv'
        preferences.symlink_to(target)
        key = self.etc / 'apt/keyrings/rog-hdr-dv.asc'
        result = self.setup(FAIL_UPDATE='yes')
        self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
        self.assertEqual(source.read_bytes(), b'original source bytes\n')
        self.assertEqual(source.stat().st_mode & 0o777, 0o640)
        self.assertTrue(preferences.is_symlink())
        self.assertEqual(preferences.readlink(), target)
        self.assertEqual(target.read_bytes(), b'original protected policy\n')
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertFalse(key.exists())


@unittest.skipUnless(shutil.which('apt-get'), 'requires the supported Ubuntu shell environment')
class PublisherShellRegressionTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.recipe = self.root / 'packaging/ubuntu'
        self.recipe.mkdir(parents=True)
        for name in ('managed.py', 'registry.sh', 'publish.sh'):
            shutil.copy2(ROOT / 'packaging/ubuntu' / name, self.recipe / name)
        data = {'fixture-source': {'derivative': '+rogdv', 'expected_package_version': '1-1+rogdv2',
                                  'packages': {'amd64': ['fixture-first', 'fixture-second']}}}
        (self.recipe / 'managed-families.json').write_text(json.dumps({'families': data}))
        self.outputs = self.root / 'outputs'
        self.outputs.mkdir()
        self.rows = []
        for name in ('fixture-first', 'fixture-second'):
            row = dict(Package=name, Source='fixture-source', Version='1-1+rogdv2', Architecture='amd64')
            payload = json.dumps(row).encode()
            (self.outputs / f'{name}_1-1+rogdv2_amd64.deb').write_bytes(payload)
            self.rows.append(dict(row, SHA256=hashlib.sha256(payload).hexdigest()))
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        (self.root / 'pool').mkdir()
        (self.root / 'index').write_text('')
        (self.root / 'tmp').mkdir()
        fake = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name, args = Path(sys.argv[0]).name, sys.argv[1:]
root = Path(os.environ['FAKE_REGISTRY'])
if name == 'docker':
    print('fixture')
elif name == 'dpkg-deb':
    row = json.loads(Path(args[1]).read_text())
    print(''.join(f'{key}: {value}\\n' for key, value in row.items()))
elif name == 'curl':
    if '-X' in args:
        with (root / 'mutations').open('a') as stream:
            stream.write(args[args.index('-X') + 1] + '\\n')
        print('201', end='')
    elif args[-1].endswith('/Packages'):
        print((root / 'index').read_text(), end='')
        print('\\n200', end='')
    else:
        payload = root / 'pool' / args[-1].rsplit('/', 1)[-1]
        destination = Path(args[args.index('-o') + 1])
        destination.write_bytes(payload.read_bytes() if payload.exists() else b'not found')
        print('200' if payload.exists() else '404', end='')
'''
        for name in ('docker', 'dpkg-deb', 'curl'):
            path = self.bin / name
            path.write_text(fake)
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        TMPDIR=str(self.root / 'tmp'), FAKE_REGISTRY=str(self.root), FORGEJO_TOKEN='fixture-only')

    def test_later_unindexed_partial_target_conflict_prevents_first_put(self):
        (self.root / 'pool/fixture-second_1-1+rogdv2_amd64.deb').write_bytes(b'preserve earlier different payload')
        result = subprocess.run(['bash', str(self.recipe / 'publish.sh'), str(self.outputs)],
                                env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('immutable version conflict before mutation', result.stderr)
        self.assertFalse((self.root / 'mutations').exists())

    def test_missing_publication_prerequisite_refuses_preflight(self):
        env = self.env.copy()
        env.pop('TMPDIR')
        result = subprocess.run(['bash', str(self.recipe / 'publish.sh'), '--preflight-only', str(self.outputs)],
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('TMPDIR', result.stderr)
        self.assertFalse((self.root / 'mutations').exists())
