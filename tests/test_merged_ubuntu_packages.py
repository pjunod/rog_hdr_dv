#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deferred, scoped merged-release packaging regressions (not upstream suites).

NativeArtifactTests inspect the actual constructed kit named by
HDR_MERGED_ARTIFACT_ROOT (mutter/, launcher/, library/, library-source/).
Missing fixtures fail; nothing here skips, builds, installs or runs a player.
"""
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = 'hermes-hdr-experimental-player'
LAUNCHER_VERSION = '1.0~experimental4'
LIBRARY_VERSION = '0.3.0-1ubuntu1~hdr9'
TRIPLET = {'amd64': 'x86_64-linux-gnu', 'i386': 'i386-linux-gnu'}
ELF_IDENTITY = {'amd64': ('ELF64', 'Advanced Micro Devices X86-64'),
                'i386': ('ELF32', 'Intel 80386')}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load('release', ROOT / 'tools/merged-ubuntu-release.py')
isolation = load('isolation', ROOT / 'tools/isolated-ubuntu-apt.py')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def tar_manifest(stream, strip_top=False):
    """Typed manifest of tar members, comparable with release.manifest()."""
    result = {}
    tops = set()
    with tarfile.open(fileobj=stream, mode='r:*') as packed:
        for member in packed.getmembers():
            name = member.name.removeprefix('./')
            if not name or name == '.':
                continue
            parts = name.split('/')
            tops.add(parts[0])
            if strip_top:
                parts = parts[1:]
                if not parts:
                    continue
            key = '/'.join(parts)
            if member.issym():
                result[key] = {'type': 'symlink', 'target': member.linkname}
            elif member.isfile():
                data = packed.extractfile(member).read()
                result[key] = {'type': 'file', 'sha256': sha256(data),
                               'executable': bool(member.mode & 0o111)}
            elif member.isdir():
                continue
            else:
                raise AssertionError('unsupported archive member type: ' + name)
    if strip_top and len(tops) != 1:
        raise AssertionError('archive must have exactly one top directory: ' + repr(sorted(tops)))
    return result


def checksums(document):
    """Checksums-Sha256 references of a .dsc/.changes/.buildinfo: name -> (size, sha256).

    Also returns the Files: section names so the two listings can be compared.
    """
    references, files, section = {}, set(), None
    for line in Path(document).read_text().splitlines():
        if not line.startswith(' '):
            section = line.split(':')[0] if line.endswith(':') else None
            continue
        if section == 'Checksums-Sha256':
            digest, size, name = line.split()
            references[name] = (int(size), digest)
        elif section == 'Files':
            files.add(line.split()[-1])
    return references, files


def field(document, name):
    match = re.search('^' + re.escape(name) + r': (.*)$', Path(document).read_text(), re.MULTILINE)
    return match[1] if match else None


class ReleaseRecipeTests(unittest.TestCase):
    def test_unique_version_and_distribution_recipe(self):
        self.assertIn(release.VERSION, release.CHANGELOG)
        self.assertIn('same-version', release.CHANGELOG)
        self.assertIn('nocheck', release.CHANGELOG)
        self.assertNotIn('certified', release.CHANGELOG)
        self.assertNotIn('reproducib', release.CHANGELOG)
        for component in ('mutter', 'libdisplay-info'):
            allowed = release.ALLOWED_PACKAGING_DELTAS[component]
            self.assertIn('debian/patches/' + release.AGGREGATE_PATCH, allowed)
            self.assertTrue(all(key.startswith('debian/') for key in allowed))
        self.assertEqual(set(release.MANIFEST_POLICY), {'file', 'symlink', 'directory', 'other'})

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
        actual = release.manifest(ROOT / 'tools/native_player')
        self.assertFalse(any(p.startswith('debian/') or p.startswith('.pc/') for p in actual))
        player = actual['player.py']
        self.assertEqual(player['type'], 'file')
        self.assertEqual(player['sha256'], sha256((ROOT / 'tools/native_player/player.py').read_bytes()))
        self.assertIn('executable', player)
        self.assertEqual(release.files(ROOT / 'tools/native_player')['player.py'], player['sha256'])
        packaging = release.packaging_inventory(ROOT / 'tools/native_player')
        self.assertIn('debian/rules', packaging)
        self.assertTrue(packaging['debian/rules']['executable'])
        self.assertEqual(packaging['debian/control']['sha256'],
                         sha256((ROOT / 'tools/native_player/debian/control').read_bytes()))

    def test_source_manifest_detects_mode_and_symlink_drift(self):
        # Content-identical trees that differ only by an execute bit, a link
        # target or a link-versus-file entry must not compare equal.
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as temporary:
            base = Path(temporary)
            canonical, candidate = base / 'canonical', base / 'candidate'
            for tree in (canonical, candidate):
                (tree / 'src').mkdir(parents=True)
                (tree / 'src/run.sh').write_bytes(b'#!/bin/sh\n')
                (tree / 'src/run.sh').chmod(0o755)
                (tree / 'src/data.txt').write_bytes(b'same\n')
                (tree / 'src/alias').symlink_to('data.txt')
                (tree / 'debian').mkdir()
                (tree / 'debian/control').write_bytes(b'Source: x\n')
                (tree / '.pc').mkdir()
                (tree / '.pc/applied-patches').write_text('a.patch\n')
            # An outward-pointing link is inventoried by its literal target, never followed.
            (canonical / 'src/outside').symlink_to('../../../../etc/hostname')
            (candidate / 'src/outside').symlink_to('../../../../etc/hostname')
            equal = release.manifest(canonical)
            self.assertEqual(equal, release.manifest(candidate))
            self.assertEqual(equal['src/outside'], {'type': 'symlink', 'target': '../../../../etc/hostname'})
            self.assertTrue(equal['src/run.sh']['executable'])
            self.assertNotIn('debian/control', equal)
            self.assertNotIn('.pc/applied-patches', equal)
            self.assertEqual(release.quilt_state(candidate), ['a.patch'])
            # Lost execute bit, same bytes.
            (candidate / 'src/run.sh').chmod(0o644)
            deltas, _ = release.compare_manifests(equal, release.manifest(candidate))
            self.assertEqual(list(deltas), ['src/run.sh'])
            self.assertEqual(release.files(canonical), release.files(candidate))
            (candidate / 'src/run.sh').chmod(0o755)
            # Retargeted link, still a link.
            (candidate / 'src/alias').unlink()
            (candidate / 'src/alias').symlink_to('run.sh')
            deltas, _ = release.compare_manifests(equal, release.manifest(candidate))
            self.assertEqual(list(deltas), ['src/alias'])
            # Link replaced by a regular file with the link target's content.
            (candidate / 'src/alias').unlink()
            (candidate / 'src/alias').write_bytes(b'same\n')
            deltas, _ = release.compare_manifests(equal, release.manifest(candidate))
            self.assertEqual(list(deltas), ['src/alias'])
            self.assertEqual(deltas['src/alias']['candidate']['type'], 'file')
            comparison = release.source_comparison('libdisplay-info', canonical, candidate)
            self.assertFalse(comparison['runtime_equal'])
            self.assertIn('runtime delta: src/alias', comparison['problems'])
            (candidate / 'src/alias').unlink()
            (candidate / 'src/alias').symlink_to('data.txt')
            # Packaging deltas are inventoried separately and must be explained.
            (candidate / 'debian/rules').write_bytes(b'#!/usr/bin/make -f\n')
            comparison = release.source_comparison('libdisplay-info', canonical, candidate)
            self.assertTrue(comparison['runtime_equal'])
            self.assertIn('unexplained packaging delta: debian/rules', comparison['problems'])
            self.assertIn('expected packaging delta absent: debian/patches/series', comparison['problems'])
            os.mkfifo(candidate / 'src/fifo')
            with self.assertRaises(ValueError):
                release.manifest(candidate)

    def test_source_closure_rejects_missing_or_wrong_hash(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as temporary:
            base = Path(temporary)
            archive = base / 'x_1.0.tar.xz'
            archive.write_bytes(b'archive bytes\n')
            digest = sha256(archive.read_bytes())
            dsc = base / 'x_1.0.dsc'

            def write(size, sha):
                dsc.write_text('Format: 3.0 (native)\nSource: x\nVersion: 1.0\n'
                               'Checksums-Sha256:\n ' + sha + ' ' + str(size) + ' x_1.0.tar.xz\n'
                               'Files:\n 0 ' + str(size) + ' x_1.0.tar.xz\n')

            write(archive.stat().st_size, digest)
            bound = release.bind_source_package(dsc)
            self.assertEqual(bound['archives']['x_1.0.tar.xz']['sha256'], digest)
            self.assertEqual(bound['dsc_sha256'], sha256(dsc.read_bytes()))
            self.assertEqual(release.dsc_references(dsc), {'x_1.0.tar.xz': (archive.stat().st_size, digest)})
            write(archive.stat().st_size, 'f' * 64)
            with self.assertRaises(ValueError):
                release.bind_source_package(dsc)
            write(archive.stat().st_size + 1, digest)
            with self.assertRaises(ValueError):
                release.bind_source_package(dsc)
            write(archive.stat().st_size, digest)
            archive.unlink()
            with self.assertRaises(ValueError):
                release.bind_source_package(dsc)
            # The test-side closure helper used on real kits must agree.
            self.assertEqual(checksums(dsc), ({'x_1.0.tar.xz': (14, digest)}, {'x_1.0.tar.xz'}))

    def test_unprepared_isolation_is_refused(self):
        with self.assertRaises(ValueError):
            isolation.command(ROOT, ROOT / 'not-an-executable', ['dpkg', '--audit'])


class NativeArtifactTests(unittest.TestCase):
    MUTTER_PACKAGES = {'mutter': 'amd64', 'mutter-common': 'all', 'mutter-common-bin': 'amd64',
                       'mutter-dev-bin': 'amd64', 'libmutter-51-0': 'amd64', 'libmutter-51-dev': 'amd64',
                       'gir1.2-mutter-51': 'amd64', 'libmutter-test-51': 'amd64', 'mutter-51-tests': 'amd64'}
    MUTTER_DEBUG = {'mutter', 'libmutter-51-0', 'libmutter-51-dev', 'libmutter-test-51',
                    'mutter-51-tests', 'mutter-common-bin', 'mutter-dev-bin'}
    MUTTER_MULTIARCH = {'libmutter-51-0': 'same', 'libmutter-51-dev': 'same', 'gir1.2-mutter-51': 'same',
                        'mutter-common': 'foreign', 'mutter-common-bin': 'foreign', 'mutter-dev-bin': 'foreign',
                        'mutter': None, 'libmutter-test-51': None, 'mutter-51-tests': None}
    # SONAME -> installed path; the symbols contract packages exactly these four.
    MUTTER_DSOS = {'libmutter-51.so.0': 'usr/lib/x86_64-linux-gnu/libmutter-51.so.0.0.0',
                   'libmutter-clutter-51.so.0': 'usr/lib/x86_64-linux-gnu/mutter-51/libmutter-clutter-51.so.0.0.0',
                   'libmutter-cogl-51.so.0': 'usr/lib/x86_64-linux-gnu/mutter-51/libmutter-cogl-51.so.0.0.0',
                   'libmutter-mtk-51.so.0': 'usr/lib/x86_64-linux-gnu/mutter-51/libmutter-mtk-51.so.0.0.0'}
    # Symbols introduced by the merged series, with their packaged minimum versions.
    MUTTER_SYMBOLS = {'libmutter-51.so.0': ['meta_color_device_get_target_luminance@Base 51.0-1ubuntu3+nativehdr3~',
                                            'meta_monitor_get_target_override@Base 51.0-1ubuntu3+nativehdr10~'],
                      'libmutter-clutter-51.so.0': ['clutter_color_state_params_get_adapted_white@Base 51.0-1ubuntu3+nativehdr10~']}
    LIBRARY_SYMBOLS = ['di_displayid2_data_block_get_luminance@Base 0.3.0-1ubuntu1~hdr7~',
                       'di_displayid2_data_block_get_native_chromaticities@Base 0.3.0-1ubuntu1~hdr8~']
    LIBRARY_PACKAGES = {'libdisplay-info3': 'same', 'libdisplay-info-dev': 'same', 'libdisplay-info-bin': 'foreign'}

    @classmethod
    def setUpClass(cls):
        # Required fixtures fail, not skip: run only in the approved native batch.
        cls.artifacts = Path(os.environ['HDR_MERGED_ARTIFACT_ROOT'])
        cls.mutter = cls.artifacts / 'mutter'
        cls.launcher = cls.artifacts / 'launcher'
        cls.library = cls.artifacts / 'library'
        cls.library_source = cls.artifacts / 'library-source'
        for directory in (cls.mutter, cls.launcher, cls.library, cls.library_source):
            if not directory.is_dir():
                raise AssertionError('required fixture directory missing: ' + str(directory))
        cls.scratch = cls.artifacts / 'validation-scratch'
        cls.scratch.mkdir(exist_ok=True)

    def control(self, path, name):
        return subprocess.check_output(['dpkg-deb', '-f', str(path), name], text=True).strip()

    def control_members(self, path):
        data = subprocess.check_output(['dpkg-deb', '--ctrl-tarfile', str(path)])
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as packed:
            return {m.name.removeprefix('./'): packed.extractfile(m).read()
                    for m in packed.getmembers() if m.isfile()}

    def payload(self, path):
        data = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(path)])
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as packed:
            result = {}
            for member in packed.getmembers():
                stream = packed.extractfile(member) if member.isfile() else None
                result[member.name.removeprefix('./')] = (member, stream.read() if stream else None)
            return result

    def readelf(self, data, *flags):
        with tempfile.TemporaryDirectory(dir=self.scratch) as temporary:
            target = Path(temporary) / 'payload.elf'
            target.write_bytes(data)
            return subprocess.check_output(['readelf', '-W', *flags, str(target)], text=True)

    def build_id(self, data):
        match = re.search(r'Build ID: ([0-9a-f]{40})', self.readelf(data, '-n'))
        return match[1] if match else None

    def elf_members(self, payload):
        return {name: data for name, (member, data) in payload.items()
                if member.isfile() and data and data.startswith(b'\x7fELF')}

    def closure(self, directory, document, partial=()):
        """Every referenced file must exist with its size and SHA256.

        Only suffixes in ``partial`` may be absent: that is an explicitly
        labelled partial closure, never a silent pass. Returns the absent names.
        """
        references, files = checksums(document)
        self.assertTrue(references, document.name)
        if document.suffix != '.buildinfo':
            self.assertEqual(files, set(references), 'Files and Checksums-Sha256 disagree in ' + document.name)
        missing = []
        for name, (size, digest) in references.items():
            path = directory / name
            if not path.is_file():
                self.assertTrue(name.endswith(partial), 'missing referenced artifact ' + name + ' in ' + document.name)
                missing.append(name)
                continue
            self.assertEqual(path.stat().st_size, size, name)
            self.assertEqual(sha256(path.read_bytes()), digest, name)
        return missing

    def single(self, directory, pattern):
        matches = sorted(directory.glob(pattern))
        self.assertEqual(len(matches), 1, pattern + ' in ' + str(directory))
        return matches[0]

    def receipt(self, path):
        self.assertTrue(path.is_file(), 'required receipt missing: ' + str(path))
        return json.loads(path.read_text())

    def audit(self, directory, component, tree, dsc):
        """The supplemental typed-manifest audit of an existing source package."""
        audit = self.receipt(directory / 'source-audit.json')
        self.assertEqual(audit['kind'], 'source-audit')
        self.assertEqual(audit['component'], component)
        self.assertEqual(audit['canonical_tree'], tree)
        self.assertFalse(audit['constructed'])
        self.assertFalse(audit['binary_build'])
        self.assertEqual(audit['units_executed'], 0)
        self.assertTrue(audit['runtime_equal'], audit['problems'])
        self.assertEqual(audit['problems'], [])
        self.assertEqual(audit['runtime_deltas'], {})
        self.assertEqual(audit['manifest_policy'], release.MANIFEST_POLICY)
        self.assertEqual(audit['source_package']['dsc_sha256'], sha256(dsc.read_bytes()))
        self.assertEqual(audit['source_package']['dsc'], dsc.name)
        self.assertEqual(set(audit['packaging_deltas']), set(release.ALLOWED_PACKAGING_DELTAS[component]))
        self.assertGreater(audit['runtime_entry_counts']['file'], 0)
        self.assertGreaterEqual(audit['runtime_entry_counts']['symlink'], 0)
        return audit

    def test_normal_source_and_binary_closures(self):
        version = release.VERSION
        with self.subTest(component='mutter'):
            expected = {name + '_' + version + '_' + arch + '.deb' for name, arch in self.MUTTER_PACKAGES.items()}
            self.assertEqual({p.name for p in self.mutter.glob('*.deb')}, expected)
            self.assertEqual({p.name for p in self.mutter.glob('*.ddeb')},
                             {name + '-dbgsym_' + version + '_amd64.ddeb' for name in self.MUTTER_DEBUG})
            dsc = self.single(self.mutter, '*.dsc')
            self.assertEqual(dsc.name, 'mutter_' + version + '.dsc')
            self.assertEqual(field(dsc, 'Source'), 'mutter')
            self.assertEqual(field(dsc, 'Version'), version)
            self.assertEqual(field(dsc, 'Format'), '3.0 (quilt)')
            self.assertEqual(set(checksums(dsc)[0]),
                             {'mutter_51.0.orig.tar.xz', 'mutter_' + version + '.debian.tar.xz'})
            self.assertEqual(self.closure(self.mutter, dsc), [])
            self.assertEqual(sha256((self.mutter / 'mutter_51.0.orig.tar.xz').read_bytes()), release.MUTTER_ORIG)
            for name in ('_amd64.changes', '_amd64.buildinfo'):
                document = self.single(self.mutter, 'mutter_' + version + name)
                self.assertEqual(field(document, 'Source'), 'mutter')
                self.assertEqual(self.closure(self.mutter, document), [], name)
            final = checksums(self.mutter / ('mutter_' + version + '_amd64.changes'))[0]
            self.assertEqual({n for n in final if n.endswith(('.deb', '.ddeb'))},
                             expected | {p.name for p in self.mutter.glob('*.ddeb')})
            self.assertEqual(final[dsc.name], (dsc.stat().st_size, sha256(dsc.read_bytes())))
            # The -S stage wrote _source.changes/_source.buildinfo before the -F
            # build regenerated the .dsc and debian archive. Their closure is
            # therefore allowed to be superseded ONLY on those two source
            # artifacts, and that is recorded here as a labelled partial
            # closure, not hidden: every other reference must match exactly.
            for name in ('_source.changes', '_source.buildinfo'):
                document = self.single(self.mutter, 'mutter_' + version + name)
                references = checksums(document)[0]
                superseded = []
                for referenced, (size, digest) in references.items():
                    path = self.mutter / referenced
                    self.assertTrue(path.is_file(), referenced)
                    if (path.stat().st_size, sha256(path.read_bytes())) != (size, digest):
                        self.assertTrue(referenced.endswith(('.dsc', '.debian.tar.xz')),
                                        'source-stage reference drifted beyond the regenerated source: ' + referenced)
                        superseded.append(referenced)
                self.assertIn(len(superseded), (0, 2), 'partial source-stage closure: ' + repr(superseded))
            receipt = self.receipt(self.mutter / 'source-receipt.json')
            self.assertTrue(receipt['source_roundtrip_equal'])
            self.assertTrue(receipt['binary_build'])
            self.assertEqual(receipt['canonical_tree'], release.MUTTER_TREE)
            self.assertEqual(receipt['units_executed'], 0)
            self.assertEqual(receipt['host_installs'], 0)
            self.assertEqual(receipt['quilt_applied'][-1], 'ubuntu/xwayland-dnd-Fix-atom-name-mismatch.patch')
            self.assertEqual(set(receipt['artifacts']),
                             {p.name for p in self.mutter.iterdir() if p.suffix in
                              ('.deb', '.ddeb', '.dsc', '.xz', '.changes', '.buildinfo')})
            for name, digest in receipt['artifacts'].items():
                self.assertEqual(sha256((self.mutter / name).read_bytes()), digest, name)
            self.assertEqual(sha256((self.mutter / 'construction.log').read_bytes()), receipt['construction_log_sha256'])
            audit = self.audit(self.mutter, 'mutter', release.MUTTER_TREE, dsc)
            self.assertEqual(audit['quilt_applied'], receipt['quilt_applied'] + [release.AGGREGATE_PATCH])
            self.assertEqual(set(audit['source_package']['archives']), set(checksums(dsc)[0]))
        with self.subTest(component=LAUNCHER):
            deb = self.single(self.launcher, '*.deb')
            self.assertEqual(deb.name, LAUNCHER + '_' + LAUNCHER_VERSION + '_all.deb')
            dsc = self.single(self.launcher, '*.dsc')
            self.assertEqual(dsc.name, LAUNCHER + '_' + LAUNCHER_VERSION + '.dsc')
            self.assertEqual(field(dsc, 'Source'), LAUNCHER)
            self.assertEqual(field(dsc, 'Version'), LAUNCHER_VERSION)
            self.assertEqual(field(dsc, 'Format'), '3.0 (native)')
            self.assertEqual(set(checksums(dsc)[0]), {LAUNCHER + '_' + LAUNCHER_VERSION + '.tar.xz'})
            self.assertEqual(self.closure(self.launcher, dsc), [])
            for name in ('_amd64.changes', '_amd64.buildinfo'):
                document = self.single(self.launcher, LAUNCHER + '_' + LAUNCHER_VERSION + name)
                self.assertEqual(field(document, 'Source'), LAUNCHER)
                self.assertEqual(self.closure(self.launcher, document), [], name)
            changes = checksums(self.launcher / (LAUNCHER + '_' + LAUNCHER_VERSION + '_amd64.changes'))[0]
            self.assertEqual(set(changes), {deb.name, dsc.name, LAUNCHER + '_' + LAUNCHER_VERSION + '.tar.xz',
                                            LAUNCHER + '_' + LAUNCHER_VERSION + '_amd64.buildinfo'})
            receipt = self.receipt(self.launcher / 'build-receipt.json')
            self.assertEqual(receipt['status'], 'constructed-not-installed-not-unit-validated')
            self.assertRegex(receipt['source_commit'], '^[0-9a-f]{40}$')
            self.assertEqual(receipt['native_architecture'], 'x86_64')
            self.assertEqual((receipt['units_run'], receipt['installs'], receipt['physical_trials_run']), (0, 0, 0))
            self.assertEqual(set(receipt['artifacts']), set(changes) | {LAUNCHER + '_' + LAUNCHER_VERSION + '_amd64.changes'})
            for name, digest in receipt['artifacts'].items():
                self.assertEqual(sha256((self.launcher / name).read_bytes()), digest, name)
            self.assertEqual(sha256((self.launcher / 'build.log').read_bytes()), receipt['build_log_sha256'])
            self.assertEqual(sha256((self.launcher / 'committed-source.tar').read_bytes()),
                             receipt['source_archive_sha256'])
            sums = dict(line.split('  ', 1)[::-1] for line in
                        (self.launcher / 'SHA256SUMS').read_text().splitlines())
            self.assertEqual(sums, receipt['artifacts'])
        with self.subTest(component='libdisplay-info-source'):
            dsc = self.single(self.library_source, '*.dsc')
            self.assertEqual(dsc.name, 'libdisplay-info_' + LIBRARY_VERSION + '.dsc')
            self.assertEqual(field(dsc, 'Format'), '3.0 (quilt)')
            self.assertEqual(set(checksums(dsc)[0]), {'libdisplay-info_0.3.0.orig.tar.bz2',
                                                      'libdisplay-info_' + LIBRARY_VERSION + '.debian.tar.xz'})
            self.assertEqual(self.closure(self.library_source, dsc), [])
            for name in ('_source.changes', '_source.buildinfo'):
                document = self.single(self.library_source, 'libdisplay-info_' + LIBRARY_VERSION + name)
                self.assertEqual(self.closure(self.library_source, document), [], name)
            receipt = self.receipt(self.library_source / 'source-receipt.json')
            self.assertFalse(receipt['binary_build'])
            self.assertEqual(receipt['canonical_tree'], release.LIBRARY_TREE)
            self.assertEqual(receipt['quilt_applied'], ['test-Disable-decode-tests.patch'])
            self.assertEqual(receipt['units_executed'], 0)
            for name, digest in receipt['artifacts'].items():
                self.assertEqual(sha256((self.library_source / name).read_bytes()), digest, name)
            audit = self.audit(self.library_source, 'libdisplay-info', release.LIBRARY_TREE, dsc)
            self.assertEqual(audit['quilt_applied'], ['test-Disable-decode-tests.patch', release.AGGREGATE_PATCH])
            # Reconstructed source only: it is NOT the build source of the retained binaries.
            self.assertEqual(list(self.library.glob('*.dsc')), [])
            self.assertEqual(list(self.library_source.glob('*.deb')), [])
        with self.subTest(component='libdisplay-info-binaries'):
            retained = self.receipt(self.library / 'RETAINED.json')
            self.assertEqual(retained['disposition'], 'original bytes, no new build')
            self.assertEqual(retained['source_tree'], release.LIBRARY_TREE)
            for arch in ('amd64', 'i386'):
                # Historical binary-construction closure: every .deb and
                # .buildinfo it names must be the retained bytes; only debug
                # or source files it names may be absent, and that absence is
                # the labelled partial historical closure.
                for suffix in ('.changes', '.buildinfo'):
                    document = self.single(self.library, 'libdisplay-info_' + LIBRARY_VERSION + '_' + arch + suffix)
                    self.assertEqual(field(document, 'Source'), 'libdisplay-info')
                    self.assertEqual(field(document, 'Version'), LIBRARY_VERSION)
                    missing = self.closure(self.library, document, partial=('.ddeb', '.dsc', '.tar.xz', '.tar.bz2'))
                    referenced = set(checksums(document)[0])
                    self.assertEqual({n for n in referenced if n.endswith('.deb')},
                                     {name + '_' + LIBRARY_VERSION + '_' + arch + '.deb' for name in self.LIBRARY_PACKAGES})
                    with self.subTest(closure=arch + suffix, partial_historical_closure=sorted(missing)):
                        self.assertTrue(all(n.endswith('.ddeb') or n.startswith('libdisplay-info_') for n in missing))

    def test_mutter_version_abi_and_dependencies(self):
        version = release.VERSION
        packages = {self.control(p, 'Package'): p for p in self.mutter.glob('*.deb')}
        self.assertEqual(set(packages), set(self.MUTTER_PACKAGES))
        for name, path in packages.items():
            with self.subTest(package=name):
                self.assertEqual(self.control(path, 'Version'), version)
                self.assertEqual(self.control(path, 'Architecture'), self.MUTTER_PACKAGES[name])
                self.assertEqual(self.control(path, 'Source'), '' if name == 'mutter' else 'mutter')
                self.assertEqual(path.name, name + '_' + version + '_' + self.MUTTER_PACKAGES[name] + '.deb')
                multiarch = self.control(path, 'Multi-Arch')
                if self.MUTTER_MULTIARCH[name] is None:
                    self.assertIn(multiarch, ('', 'no'))
                else:
                    self.assertEqual(multiarch, self.MUTTER_MULTIARCH[name])
        depends = {name: self.control(path, 'Depends') for name, path in packages.items()}
        exact = '(= ' + version + ')'
        # Strict closure: dev, GIR, test and test-suite packages bind the exact
        # runtime build; the runtime binds the staged hdr9 API and library.
        for package, requirements in {
                'libmutter-51-0': ['libdisplay-info3-native-hdr-api (>= 2)',
                                   'libdisplay-info3 (>= ' + LIBRARY_VERSION + ')',
                                   'mutter-common (>= 50~beta)', 'mutter-common-bin (>= 49.0)'],
                'libmutter-51-dev': ['libmutter-51-0 ' + exact, 'gir1.2-mutter-51 ' + exact,
                                     'libdisplay-info-dev (>= 0.3.0-1ubuntu1~hdr8~)'],
                'gir1.2-mutter-51': ['libmutter-51-0 ' + exact],
                'libmutter-test-51': ['libmutter-51-0 ' + exact, 'mutter ' + exact, 'gir1.2-mutter-51 ' + exact],
                'mutter-51-tests': ['libmutter-51-0 ' + exact, 'libmutter-test-51 ' + exact, 'mutter ' + exact],
                'mutter': ['mutter-common (>= 49.0)', 'libmutter-51-0 ('],
                'mutter-common-bin': ['libgtk-4-1 (>= 4.22.0)', 'python3-gi', 'gir1.2-glib-2.0'],
                'mutter-dev-bin': ['libgtk-4-1 (>= 4.22.0)']}.items():
            for requirement in requirements:
                with self.subTest(package=package, requirement=requirement):
                    self.assertIn(requirement, depends[package])
        for package in packages:
            self.assertNotIn('nativehdr10)', depends[package].replace(version + ')', ''),
                             package + ' still binds the superseded nativehdr10 version')
        # Packaged symbol/shlibs contract of the runtime library.
        members = self.control_members(packages['libmutter-51-0'])
        self.assertIn('symbols', members)
        self.assertIn('shlibs', members)
        symbols = members['symbols'].decode()
        for soname, entries in self.MUTTER_SYMBOLS.items():
            self.assertIn(soname + ' libmutter-51-0 #MINVER#', symbols)
            for entry in entries:
                self.assertIn(' ' + entry + '\n', symbols)
        for soname in self.MUTTER_DSOS:
            self.assertIn(soname + ' libmutter-51-0 #MINVER#', symbols)
            self.assertIn(soname.replace('.so.', ' ') + ' libmutter-51-0', members['shlibs'].decode())
        self.assertNotIn('MISSING', symbols)
        test_members = self.control_members(packages['libmutter-test-51'])
        self.assertIn('libmutter-test-51.so libmutter-test-51 #MINVER#', test_members['symbols'].decode())
        payload = self.payload(packages['libmutter-51-0'])
        for soname, path in self.MUTTER_DSOS.items():
            self.assertIn(path, payload)
            link = path.rsplit('/', 1)[0] + '/' + soname
            self.assertTrue(payload[link][0].issym(), link)
            self.assertEqual(payload[link][0].linkname, path.rsplit('/', 1)[1])
        self.assertIn('usr/share/doc/libmutter-51-0/README.native-displayid', payload)

    def test_payload_ownership_modes_and_no_manual_prefix(self):
        artifacts = (sorted(self.mutter.glob('*.deb')) + sorted(self.mutter.glob('*.ddeb'))
                     + sorted(self.launcher.glob('*.deb')) + sorted(self.library.glob('*.deb')))
        self.assertEqual(len(artifacts), 9 + 7 + 1 + 6)
        for path in artifacts:
            for name, (member, _) in self.payload(path).items():
                with self.subTest(package=path.name, file=name):
                    self.assertFalse(name.startswith(('usr/local/', 'home/', 'work/', 'tmp/', 'opt/')))
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)
                    self.assertEqual(member.mode & 0o6000, 0)
                    self.assertEqual(member.mode & 0o022, 0, 'group/other writable')
                    self.assertFalse(member.ischr() or member.isblk() or member.isfifo())

    def inspect_elf(self, package, name, data, arch):
        identity, machine = ELF_IDENTITY[arch]
        header = self.readelf(data, '-h')
        self.assertRegex(header, r'Class:\s+' + re.escape(identity) + r'\n', name)
        self.assertRegex(header, r'Machine:\s+' + re.escape(machine) + r'\n', name)
        dynamic = self.readelf(data, '-d')
        for line in dynamic.splitlines():
            if '(RPATH)' in line or '(RUNPATH)' in line:
                value = line.split('[', 1)[1].rstrip(']')
                for entry in value.split(':'):
                    self.assertTrue(entry.startswith('/usr/lib/' + TRIPLET[arch] + '/'),
                                    package + ' ' + name + ' private runtime path ' + entry)
        return header, dynamic

    def test_elf_sonames_architectures_and_runtime_paths(self):
        version = release.VERSION
        mutter = {self.control(p, 'Package'): p for p in self.mutter.glob('*.deb')}
        debug = {self.control(p, 'Package'): p for p in self.mutter.glob('*.ddeb')}
        self.assertEqual(set(debug), {name + '-dbgsym' for name in self.MUTTER_DEBUG})
        # Required ELF inventory: package -> paths that must be ELF regular files.
        required = {'libmutter-51-0': list(self.MUTTER_DSOS.values()),
                    'libmutter-test-51': ['usr/lib/x86_64-linux-gnu/libmutter-test-51.so'],
                    'mutter': ['usr/bin/mutter', 'usr/lib/x86_64-linux-gnu/mutter-51/plugins/libdefault.so'],
                    'mutter-common-bin': ['usr/libexec/mutter-x11-frames', 'usr/libexec/mutter-backlight-helper'],
                    'mutter-dev-bin': ['usr/libexec/mutter-devkit'],
                    'libmutter-51-dev': ['usr/lib/x86_64-linux-gnu/mutter-51/libasan-preloader.so'],
                    'mutter-51-tests': ['usr/libexec/installed-tests/mutter-51/mutter-native-hdr',
                                        'usr/libexec/installed-tests/mutter-51/mutter-color-lifecycle']}
        needed = {'usr/lib/x86_64-linux-gnu/libmutter-51.so.0.0.0':
                  ['libdisplay-info.so.3', 'libmutter-clutter-51.so.0', 'libmutter-cogl-51.so.0', 'libmutter-mtk-51.so.0'],
                  'usr/bin/mutter': ['libmutter-51.so.0'],
                  'usr/libexec/mutter-x11-frames': ['libgtk-4.so.1'],
                  'usr/lib/x86_64-linux-gnu/mutter-51/plugins/libdefault.so': ['libmutter-clutter-51.so.0']}
        sonames = {path: soname for soname, path in self.MUTTER_DSOS.items()}
        sonames['usr/lib/x86_64-linux-gnu/libmutter-test-51.so'] = 'libmutter-test-51.so'
        exports = {'usr/lib/x86_64-linux-gnu/libmutter-51.so.0.0.0': ['meta_color_device_get_target_luminance',
                                                                       'meta_monitor_get_target_override'],
                   'usr/lib/x86_64-linux-gnu/mutter-51/libmutter-clutter-51.so.0.0.0':
                       ['clutter_color_state_params_get_adapted_white']}
        total = 0
        for package, path in sorted(mutter.items()):
            payload = self.payload(path)
            elves = self.elf_members(payload)
            for name in required.get(package, []):
                self.assertIn(name, elves, package + ' must ship ELF ' + name)
            if package in ('mutter-common', 'gir1.2-mutter-51'):
                self.assertEqual(elves, {}, package + ' is not expected to ship ELF objects')
            build_ids = {}
            for name, data in elves.items():
                with self.subTest(package=package, file=name):
                    total += 1
                    _, dynamic = self.inspect_elf(package, name, data, 'amd64')
                    if name in sonames:
                        self.assertIn('Library soname: [' + sonames[name] + ']', dynamic)
                    for library in needed.get(name, []):
                        self.assertIn('Shared library: [' + library + ']', dynamic)
                    if name in exports:
                        table = self.readelf(data, '--dyn-syms')
                        for symbol in exports[name]:
                            self.assertRegex(table, r'FUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+' + symbol + r'\n')
                    if not re.search(r'Type:\s+REL \(', self.readelf(data, '-h')):
                        identity = self.build_id(data)
                        self.assertIsNotNone(identity, 'build-id missing in ' + name)
                        build_ids[identity] = name
            # Matched debug symbols: every shipped ELF build-id has its debug
            # file in the package's .ddeb and every debug file belongs to a
            # shipped ELF; the Build-Ids control field agrees with both.
            if package in self.MUTTER_DEBUG:
                ddeb = debug[package + '-dbgsym']
                self.assertEqual(self.control(ddeb, 'Version'), version)
                self.assertEqual(self.control(ddeb, 'Architecture'), 'amd64')
                self.assertEqual(self.control(ddeb, 'Depends'), package + ' (= ' + version + ')')
                debug_files = {}
                for name, (member, data) in self.payload(ddeb).items():
                    if member.isfile():
                        match = re.fullmatch(r'usr/lib/debug/\.build-id/([0-9a-f]{2})/([0-9a-f]{38})\.debug', name)
                        self.assertIsNotNone(match, package + '-dbgsym unexpected member ' + name)
                        self.assertTrue(data.startswith(b'\x7fELF'), name)
                        self.assertEqual(self.build_id(data), match[1] + match[2], name)
                        debug_files[match[1] + match[2]] = name
                self.assertEqual(set(debug_files), set(build_ids),
                                 package + ' debug symbols do not match its shipped ELF build-ids')
                self.assertEqual(set(self.control(ddeb, 'Build-Ids').split()), set(build_ids), package)
            else:
                self.assertEqual(build_ids, {}, package + ' ships ELF objects without matched debug symbols')
        self.assertGreater(total, 0)
        # hdr9 library binaries: native class and machine for each architecture.
        for arch in ('amd64', 'i386'):
            library = 'usr/lib/' + TRIPLET[arch] + '/libdisplay-info.so.0.3.0'
            payload = self.payload(self.library / ('libdisplay-info3_' + LIBRARY_VERSION + '_' + arch + '.deb'))
            elves = self.elf_members(payload)
            self.assertEqual(set(elves), {library})
            _, dynamic = self.inspect_elf('libdisplay-info3', library, elves[library], arch)
            self.assertIn('Library soname: [libdisplay-info.so.3]', dynamic)
            self.assertIn('Shared library: [libc.so.6]', dynamic)
            table = self.readelf(elves[library], '--dyn-syms')
            for entry in self.LIBRARY_SYMBOLS:
                self.assertRegex(table, r'FUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+' + entry.split('@')[0] + r'\n')
            self.assertIsNotNone(self.build_id(elves[library]))
            link = payload['usr/lib/' + TRIPLET[arch] + '/libdisplay-info.so.3'][0]
            self.assertTrue(link.issym())
            self.assertEqual(link.linkname, 'libdisplay-info.so.0.3.0')
            decoder = self.elf_members(self.payload(self.library / ('libdisplay-info-bin_' + LIBRARY_VERSION + '_' + arch + '.deb')))
            self.assertEqual(set(decoder), {'usr/bin/di-edid-decode'})
            _, dynamic = self.inspect_elf('libdisplay-info-bin', 'usr/bin/di-edid-decode', decoder['usr/bin/di-edid-decode'], arch)
            self.assertIn('Shared library: [libdisplay-info.so.3]', dynamic)
            dev = self.payload(self.library / ('libdisplay-info-dev_' + LIBRARY_VERSION + '_' + arch + '.deb'))
            self.assertEqual(self.elf_members(dev), {})
            link = dev['usr/lib/' + TRIPLET[arch] + '/libdisplay-info.so'][0]
            self.assertTrue(link.issym())
            self.assertEqual(link.linkname, 'libdisplay-info.so.3')

    def test_launcher_exact_payload_and_declared_stock_dependencies(self):
        deb = self.single(self.launcher, '*.deb')
        source = ROOT / 'tools/native_player'
        self.assertEqual(self.control(deb, 'Package'), LAUNCHER)
        self.assertEqual(self.control(deb, 'Version'), LAUNCHER_VERSION)
        self.assertEqual(self.control(deb, 'Architecture'), 'all')
        self.assertIn('hermes-hdr-experimental-player (' + LAUNCHER_VERSION + ')', (source / 'debian/changelog').read_text())
        depends = self.control(deb, 'Depends')
        for dependency in ['python3 (>= 3.11)', 'mpv (>= 0.41.0)', 'libplacebo360 (>= 7.360.1)',
                           'libavcodec62 (>= 7:8.1.2)', 'libavutil60 (>= 7:8.1.2)']:
            self.assertIn(dependency, depends)
        self.assertNotIn('libdisplay-info', depends)
        self.assertNotIn('mutter', depends)
        payload = self.payload(deb)
        files = {name: (member, data) for name, (member, data) in payload.items() if member.isfile()}
        doc = 'usr/share/doc/' + LAUNCHER + '/'
        expected = {'usr/bin/hermes-hdr-player': ('player.py', 0o755),
                    'usr/share/applications/hermes-hdr-player.desktop': ('player.desktop', 0o644),
                    doc + 'USAGE.txt': ('USAGE.txt', 0o644),
                    doc + 'inputs.json': ('inputs.json', 0o644),
                    doc + 'copyright': ('debian/copyright', 0o644)}
        # Exact payload accounting: generated files plus the compressed native changelog.
        self.assertEqual(set(files), set(expected) | {doc + 'changelog.gz'})
        for target, (origin, mode) in expected.items():
            with self.subTest(file=target):
                self.assertEqual(files[target][1], (source / origin).read_bytes())
                self.assertEqual(files[target][0].mode, mode)
        self.assertEqual(gzip.decompress(files[doc + 'changelog.gz'][1]), (source / 'debian/changelog').read_bytes())
        self.assertEqual(files[doc + 'changelog.gz'][0].mode, 0o644)
        for name, (member, _) in payload.items():
            self.assertFalse(member.issym(), name)
        usage = files[doc + 'USAGE.txt'][1].decode()
        self.assertNotRegex(usage, r'1\.0~experimental[0-9]')
        self.assertIn('SHA256SUMS', usage)
        self.assertIn('dpkg-query -W', usage)
        self.assertIn('"autoremove"', usage)
        control = self.control_members(deb)
        self.assertFalse(set(control).intersection({'preinst', 'postinst', 'prerm', 'postrm', 'triggers', 'conffiles'}))
        self.assertIn('md5sums', control)
        md5sums = {line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in control['md5sums'].decode().splitlines()}
        self.assertEqual(set(md5sums), set(files))
        for name, digest in md5sums.items():
            self.assertEqual(hashlib.md5(files[name][1]).hexdigest(), digest, name)
        # Source archive members are the committed source: both the committed
        # archive the builder consumed and the transferred repository copy.
        receipt = self.receipt(self.launcher / 'build-receipt.json')
        committed = self.launcher / 'committed-source.tar'
        self.assertEqual(sha256(committed.read_bytes()), receipt['source_archive_sha256'])
        with committed.open('rb') as stream:
            committed_manifest = tar_manifest(stream)
        repository = {key: value for key, value in release.manifest(source, excluded=()).items()
                      if '__pycache__' not in key and not key.endswith('.pyc')}
        self.assertEqual(committed_manifest, repository)
        archive = self.single(self.launcher, LAUNCHER + '_' + LAUNCHER_VERSION + '.tar.xz')
        with archive.open('rb') as stream:
            packaged = tar_manifest(stream, strip_top=True)
        self.assertEqual(packaged, repository)
        for name in ('player.py', 'player.desktop', 'USAGE.txt', 'inputs.json', 'debian/control',
                     'debian/changelog', 'debian/rules', 'debian/copyright', 'debian/source/format'):
            self.assertIn(name, packaged)
        self.assertTrue(packaged['debian/rules']['executable'])
        self.assertEqual(release.dsc_references(self.single(self.launcher, '*.dsc'))[archive.name],
                         (archive.stat().st_size, sha256(archive.read_bytes())))
        self.assertEqual(receipt['artifacts'][archive.name], sha256(archive.read_bytes()))

    def test_hdr9_multiarch_original_identity_and_shared_files(self):
        manifest = self.receipt(self.library / 'RETAINED.json')
        expected = {name + '_' + LIBRARY_VERSION + '_' + arch + '.deb'
                    for name in self.LIBRARY_PACKAGES for arch in ('amd64', 'i386')}
        self.assertEqual(set(manifest['binaries']), expected)
        self.assertEqual({p.name for p in self.library.glob('*.deb')}, expected)
        for filename, digest in manifest['binaries'].items():
            path = self.library / filename
            self.assertEqual(sha256(path.read_bytes()), digest, filename)
            name, version, arch = filename.removesuffix('.deb').split('_')
            self.assertEqual(self.control(path, 'Package'), name)
            self.assertEqual(self.control(path, 'Version'), LIBRARY_VERSION)
            self.assertEqual(self.control(path, 'Architecture'), arch)
            self.assertEqual(self.control(path, 'Multi-Arch'), self.LIBRARY_PACKAGES[name])
            if name == 'libdisplay-info3':
                self.assertEqual(self.control(path, 'Provides'), 'libdisplay-info3-native-hdr-api (= 2)')
                symbols = self.control_members(path)['symbols'].decode()
                self.assertIn('libdisplay-info.so.3 libdisplay-info3 #MINVER#', symbols)
                for entry in self.LIBRARY_SYMBOLS:
                    self.assertIn(' ' + entry + '\n', symbols)
            if name == 'libdisplay-info-dev':
                self.assertEqual(self.control(path, 'Depends'), 'libdisplay-info3 (= ' + LIBRARY_VERSION + ')')
            if name == 'libdisplay-info-bin':
                self.assertIn('libdisplay-info3 (>= ', self.control(path, 'Depends'))
        shared_required = {
            'libdisplay-info3': ['usr/share/doc/libdisplay-info3/copyright',
                                 'usr/share/doc/libdisplay-info3/changelog.Debian.gz',
                                 'usr/share/doc/libdisplay-info3/README.native-displayid.gz'],
            'libdisplay-info-dev': ['usr/include/libdisplay-info/' + header + '.h' for header in
                                    ('cta', 'cvt', 'displayid', 'displayid2', 'dmt', 'edid', 'gtf', 'info')]
                                   + ['usr/share/doc/libdisplay-info-dev/copyright']}
        arch_specific = {'libdisplay-info3': ['usr/lib/{}/libdisplay-info.so.0.3.0', 'usr/lib/{}/libdisplay-info.so.3'],
                         'libdisplay-info-dev': ['usr/lib/{}/libdisplay-info.so', 'usr/lib/{}/pkgconfig/libdisplay-info.pc']}
        for name in ['libdisplay-info3', 'libdisplay-info-dev']:
            payloads = {}
            for arch in ['amd64', 'i386']:
                payloads[arch] = self.payload(self.library / (name + '_' + LIBRARY_VERSION + '_' + arch + '.deb'))
                for pattern in arch_specific[name]:
                    self.assertIn(pattern.format(TRIPLET[arch]), payloads[arch])
            shared = payloads['amd64'].keys() & payloads['i386'].keys()
            for required in shared_required[name]:
                self.assertIn(required, shared, name + ' must share ' + required)
            for member in sorted(shared):
                with self.subTest(package=name, file=member):
                    a, b = payloads['amd64'][member][0], payloads['i386'][member][0]
                    self.assertEqual(a.type, b.type)
                    self.assertEqual(a.mode, b.mode)
                    self.assertEqual(a.linkname, b.linkname)
                    self.assertEqual(payloads['amd64'][member][1], payloads['i386'][member][1])
                    if a.isfile():
                        self.assertFalse(member.startswith('usr/lib/'), 'architecture payload shared: ' + member)
            self.assertFalse(any(m.startswith('usr/lib/' + TRIPLET['i386']) for m in payloads['amd64']))
            self.assertFalse(any(m.startswith('usr/lib/' + TRIPLET['amd64']) for m in payloads['i386']))


if __name__ == '__main__':
    unittest.main()
