#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Construct a normal source release from an exact committed Ubuntu candidate.

Native builder only. All writes are below a fresh durable output. No APT, host
installation or tests. Existing distribution quilt state is copied, never forged.
The generated source package is extracted again and is the actual binary input.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile

MUTTER_TREE = '08740f943fb2ddda60411fa4d72bb4ccc4238e5f'
LIBRARY_TREE = '96d65c11ed0f408792c41cd42c2866255b1089d0'
MUTTER_ORIG = '5d28f3ae225692428fcafb96500d673f34328b698b86960c9c1460d0b1d983b3'
VERSION = '51.0-1ubuntu3+nativehdr10.1'
CHANGELOG = '''mutter (51.0-1ubuntu3+nativehdr10.1) stonking; urgency=medium

  * Release merged nativehdr10, asynchronous lifetime/offscreen and GTK frames
    corrections as one coherent source/binary set with a unique version.
  * Preserve the SONAME, distribution packaging and qualified runtime source.
    Record the privately staged hdr9 dependency in normal shlibs metadata.
  * Supersede the provisional same-version common-bin artifacts. Construction
    uses nocheck; scoped qualification and physical installation are separate.

 -- HDR Engineering Agent <hdr-agent@users.noreply.github.com>  Thu, 15 Oct 2026 23:30:00 +0000

'''


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def text(command, cwd=None):
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def files(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and not p.is_symlink()
            and p.relative_to(root).parts[0] not in ('.pc', 'debian')}


def durable_output(path):
    path = Path(path).resolve()
    if any(path == Path(p) or Path(p) in path.parents
           for p in ('/tmp', '/private/tmp', '/var/tmp')):
        raise ValueError('output must be durable')
    if path.exists():
        raise ValueError('fresh output required; preserve previous work')
    return path


def verify_source(source, expected):
    if text(['git', '-C', str(source), 'rev-parse', 'HEAD^{tree}']) != expected:
        raise ValueError('canonical source tree mismatch')
    if text(['git', '-C', str(source), 'diff', '--name-only', 'HEAD']):
        raise ValueError('canonical tracked source is dirty')
    return text(['git', '-C', str(source), 'rev-parse', 'HEAD'])


def recipe(args):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or os.geteuid() == 0:
        raise ValueError('authorized unprivileged native x86_64 builder required')
    if not re.fullmatch('[0-9a-f]{40}', args.repository_commit):
        raise ValueError('full packaging repository commit required')
    expected = MUTTER_TREE if args.component == 'mutter' else LIBRARY_TREE
    source = args.source.resolve()
    head = verify_source(source, expected)
    out = durable_output(args.output)
    if source == out or source in out.parents or out in source.parents:
        raise ValueError('source and output must be disjoint')
    pc = args.quilt_state.resolve()
    if not (pc / 'applied-patches').is_file():
        raise ValueError('preserved actual quilt bookkeeping is required')
    applied = (pc / 'applied-patches').read_text().splitlines()
    series = (source / 'debian/patches/series').read_text().splitlines()
    if applied != [x for x in series if x and not x.startswith('#')]:
        raise ValueError('quilt bookkeeping differs from committed distribution series')
    if args.component == 'mutter' and sha(args.orig) != MUTTER_ORIG:
        raise ValueError('Mutter orig hash mismatch')
    if args.component == 'libdisplay-info' and sha(args.orig) != args.orig_sha256:
        raise ValueError('library orig hash mismatch')
    out.mkdir(parents=True)
    scratch = out / 'scratch'
    scratch.mkdir(mode=0o700)
    tree = out / 'prepared'
    tree.mkdir()
    archive = out / 'canonical-source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(source), 'archive', 'HEAD'], stdout=stream, check=True)
    with tarfile.open(archive) as packed:
        packed.extractall(tree, filter='data')
    shutil.copytree(pc, tree / '.pc')
    original = out / args.orig.name
    shutil.copyfile(args.orig, original)
    if args.component == 'mutter':
        with tarfile.open(original) as packed:
            for member in packed.getmembers():
                if member.name.startswith('mutter-51.0/subprojects/gvdb/'):
                    member.name = member.name.removeprefix('mutter-51.0/')
                    packed.extract(member, tree, filter='data')
        changelog = tree / 'debian/changelog'
        changelog.write_text(CHANGELOG + changelog.read_text())
        (tree / 'debian/shlibs.local').write_text('libdisplay-info 3 libdisplay-info3 (>= 0.3.0-1ubuntu1~hdr9)\n')
    canonical_payload = files(tree)
    env = dict(os.environ, TMPDIR=str(scratch), LC_ALL='C',
               DEB_BUILD_OPTIONS='nocheck parallel=2', DEB_BUILD_PROFILES='nocheck',
               EDITOR='true', VISUAL='true')
    commands = []

    def run(command, cwd=tree):
        commands.append(command)
        with (out / 'construction.log').open('a') as log:
            log.write('\nCOMMAND ' + repr(command) + '\n')
            log.flush()
            subprocess.run(command, cwd=cwd, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)

    run(['dpkg-source', '--commit', '.', 'merged-hdr-runtime.patch'])
    run(['dpkg-buildpackage', '-S', '-us', '-uc', '-d', '-nc'])
    dsc, = out.glob('*.dsc')
    extracted = out / 'source-from-dsc'
    run(['dpkg-source', '--no-check', '-x', str(dsc), str(extracted)], cwd=out)
    if files(extracted) != canonical_payload:
        raise ValueError('source package roundtrip changed canonical runtime inputs')
    receipt = {'schema': 1, 'component': args.component,
               'repository_commit': args.repository_commit,
               'canonical_commit': head, 'canonical_tree': expected,
               'canonical_archive_sha256': sha(archive), 'orig_sha256': sha(original),
               'actual_quilt_state': str(pc), 'quilt_applied': applied,
               'runtime_input_sha256': canonical_payload,
               'source_roundtrip_equal': True, 'commands': commands,
               'units_executed': 0, 'host_installs': 0, 'binary_build': False}
    if args.build:
        if args.component != 'mutter' or not args.library_dev or not args.library_runtime:
            raise ValueError('binary construction requires the Mutter and hdr9 inputs')
        spec = importlib.util.spec_from_file_location('offline', Path(__file__).with_name('package-ubuntu-offline.py'))
        assert spec is not None and spec.loader is not None
        offline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(offline)
        prefix = out / 'library-prefix'
        library_inputs = []
        for path, package, digest in [
                (args.library_dev, 'libdisplay-info-dev', args.dev_sha256),
                (args.library_runtime, 'libdisplay-info3', args.runtime_sha256)]:
            if sha(path) != digest or text(['dpkg-deb', '-f', str(path), 'Package']) != package:
                raise ValueError('hdr9 package name/hash mismatch')
            if text(['dpkg-deb', '-f', str(path), 'Architecture']) != 'amd64':
                raise ValueError('native dependency must be amd64')
            if text(['dpkg-deb', '-f', str(path), 'Version']) != '0.3.0-1ubuntu1~hdr9':
                raise ValueError('hdr9 dependency version mismatch')
            subprocess.run(['dpkg-deb', '-x', str(path), str(prefix)], check=True)
            library_inputs.append({'file': path.name, 'sha256': digest})
        if text(['dpkg-deb', '-f', str(args.library_runtime), 'Provides']) != 'libdisplay-info3-native-hdr-api (= 2)':
            raise ValueError('native HDR API virtual dependency missing')
        pcs = prefix / 'usr/lib/x86_64-linux-gnu/pkgconfig'
        for pc_file in pcs.glob('*.pc'):
            pc_file.write_text(pc_file.read_text().replace('prefix=/usr\n', 'prefix=' + str(prefix / 'usr') + '\n'))
        env.update(PKG_CONFIG_PATH=str(pcs), LD_LIBRARY_PATH=str(prefix / 'usr/lib/x86_64-linux-gnu'))
        for key in ('CFLAGS', 'LDFLAGS'):
            env.pop(key, None)
        audit = subprocess.run(['dpkg-checkbuilddeps', '-Pnocheck'], cwd=extracted,
                               env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / 'build-dependencies.log').write_text(audit.stdout)
        exception = offline.staged_dependency_exception(audit.returncode, audit.stdout, '0.3.0-1ubuntu1~hdr9')
        command = ['dpkg-buildpackage', '-F', '-us', '-uc']
        if exception:
            command.append('-d')
        run(command, cwd=extracted)
        receipt.update(binary_build=True, dependency_exception=exception, library_inputs=library_inputs)
    artifacts = [p for p in sorted(out.iterdir()) if p.is_file() and p.suffix
                 in ('.deb', '.ddeb', '.dsc', '.xz', '.bz2', '.changes', '.buildinfo')]
    receipt['artifacts'] = {p.name: sha(p) for p in artifacts}
    receipt['construction_log_sha256'] = sha(out / 'construction.log')
    (out / 'source-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'runtime_input_sha256'}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=['mutter', 'libdisplay-info'])
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--quilt-state', required=True, type=Path)
    parser.add_argument('--orig', required=True, type=Path)
    parser.add_argument('--orig-sha256', default='')
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--build', action='store_true', help='construct Mutter binaries from the extracted .dsc, nocheck')
    parser.add_argument('--library-dev', type=Path)
    parser.add_argument('--library-runtime', type=Path)
    parser.add_argument('--dev-sha256', default='')
    parser.add_argument('--runtime-sha256', default='')
    recipe(parser.parse_args())


if __name__ == '__main__':
    main()
