#!/usr/bin/env python3
"""Build the pinned Ubuntu extension source/package; never install or reload it."""
import argparse
from email.utils import formatdate
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = 'tiling-assistant@leleat-on-github'
PACKAGE = 'gnome-shell-ubuntu-extensions'
STOCK_VERSION = '51.26.10.6ubuntu'
VERSION = STOCK_VERSION + '+nativehdr1'
STOCK_DEB_SHA256 = '6784ab2e51c29e75efb94ac4de224141741d51fe388f95d48f70e32272f35df5'
PACKAGE_ADDITIONS = {
    '.meson-subproject-wrap-hash.txt', 'meson.build', 'translations/LINGUAS',
    'translations/POTFILES.in', 'translations/meson.build',
}


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable(path):
    path = path.resolve()
    for root in (Path('/tmp'), Path('/private/tmp'), Path('/var/tmp'), Path.home() / 'code'):
        if path == root or root in path.parents:
            raise ValueError('use durable owned paths, not temporary or owner repositories')
    return path


def git_files(repository, ref):
    entries = subprocess.check_output(['git', 'ls-tree', '-rz', ref], cwd=repository)
    result = {}
    for item in entries.split(b'\0'):
        if not item:
            continue
        fields, raw_name = item.split(b'\t', 1)
        mode, kind, oid = fields.decode().split()
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('unsupported upstream Git entry')
        name = raw_name.decode()
        data = subprocess.check_output(['git', 'cat-file', 'blob', oid], cwd=repository)
        result[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'executable': mode == '100755'}
    return result


def verify_subproject(source, expected):
    actual = {str(p.relative_to(source)): p for p in source.rglob('*') if p.is_file()}
    missing = set(expected) - actual.keys()
    extra = actual.keys() - expected.keys()
    if missing != {'.gitignore'} or extra != PACKAGE_ADDITIONS:
        raise ValueError(f'upstream/package inventory mismatch: missing={missing}, extra={extra}')
    for name in expected.keys() & actual.keys():
        path = actual[name]
        if path.is_symlink() or digest(path) != expected[name]['sha256']:
            raise ValueError('upstream/package bytes differ: ' + name)
        if bool(path.stat().st_mode & 0o111) != expected[name]['executable']:
            raise ValueError('upstream/package mode differs: ' + name)
    return {name: digest(actual[name]) for name in sorted(extra)}


def prepare(inputs, candidate, output, epoch):
    component = next(c for c in json.loads((ROOT / 'sources.json').read_text())['series']
                     if c['component'] == 'ubuntu-tiling-assistant')
    if run('git', 'rev-parse', 'HEAD^{tree}', cwd=candidate) != component['candidate_tree']:
        raise ValueError('candidate Git tree is not the qualified source')
    if run('git', 'rev-parse', component['base_tree'] + '^{tree}', cwd=candidate) != component['base_tree']:
        raise ValueError('candidate repository lacks the exact base tree')
    artifacts = {a['file']: a['sha256'] for a in component['source_origin']['artifacts']}
    artifacts[f'{PACKAGE}_{STOCK_VERSION}_all.deb'] = STOCK_DEB_SHA256
    for name, expected in artifacts.items():
        if digest(inputs / name) != expected:
            raise ValueError('input SHA256 mismatch: ' + name)
    patches = ROOT / 'patches/ubuntu-tiling-assistant'
    sums = dict(line.split('  ', 1)[::-1] for line in (ROOT / 'SHA256SUMS').read_text().splitlines())
    for name in component['patch_order']:
        if digest(patches / name) != sums['patches/ubuntu-tiling-assistant/' + name]:
            raise ValueError('patch SHA256 mismatch: ' + name)
    output.mkdir(parents=True, exist_ok=False)
    source = output / f'{PACKAGE}-{VERSION}'
    subprocess.run(['dpkg-source', '-x', str(inputs / f'{PACKAGE}_{STOCK_VERSION}.dsc'), str(source)], check=True)
    subproject = source / 'subprojects/tiling-assistant'
    base_files = git_files(candidate, component['base_tree'])
    additions = verify_subproject(subproject, base_files)
    before = {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}
    for name in component['patch_order']:
        subprocess.run(['git', 'apply', '--whitespace=error', str(patches / name)], cwd=subproject, check=True)
    candidate_files = git_files(candidate, 'HEAD')
    if verify_subproject(subproject, candidate_files) != additions:
        raise ValueError('packaging-only files changed')
    # The exact replay was syntax-qualified by prepare_tiling_animation.py.
    # Packaging verifies every source byte; Ubuntu's binary build needs no Node.
    changelog = source / 'debian/changelog'
    entry = (f'{PACKAGE} ({VERSION}) stonking; urgency=medium\n\n'
             '  * Retain Ubuntu extensions and packaging; apply the five reviewed\n'
             '    synthetic tiling animation ownership patches from rog_hdr_dv.\n'
             f'  * Qualified upstream source tree: {component["candidate_tree"]}.\n\n'
             f' -- HDR Builder <hdr-builder@users.noreply.github.com>  {formatdate(epoch)}\n\n')
    changelog.write_text(entry + changelog.read_text())
    copyright_file = source / 'debian/copyright'
    copyright_file.write_text(copyright_file.read_text() + '\n'
        'Files: subprojects/tiling-assistant/tiling-assistant@leleat-on-github/src/extension/windowAnimation.js\n'
        'Copyright: 2026 HDR contributors\n'
        'License: GPL-2\n')
    after = {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    expected_changes = sorted(['debian/changelog', 'debian/copyright'] + [
        'subprojects/tiling-assistant/' + EXTENSION + '/src/extension/' + name
        for name in ('windowAnimation.js', 'tilingWindowManager.js', 'keybindingHandler.js')])
    if changed != expected_changes:
        raise ValueError('unexpected enclosing source changes: ' + repr(changed))
    receipt = {
        'schema': 1, 'package': PACKAGE, 'version': VERSION,
        'input_sha256': artifacts, 'base_commit': component['base_commit'],
        'base_tree': component['base_tree'], 'candidate_tree': component['candidate_tree'],
        'base_files': base_files, 'candidate_files': candidate_files,
        'packaging_only_files': additions, 'enclosing_source_changes': changed,
        'source_files': after, 'behavioral_units_executed': 0,
        'installation_performed': False, 'live_qualification': False,
    }
    (output / 'source-manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True, help='authenticated pinned dsc, tar and stock deb')
    parser.add_argument('--candidate-repository', type=Path, required=True, help='exact replay made by prepare_tiling_animation.py')
    parser.add_argument('--output', type=Path, required=True, help='absent durable owned directory outside the repository')
    parser.add_argument('--epoch', type=int, required=True, help='fixed changelog/source date epoch')
    parser.add_argument('--build', action='store_true', help='run ordinary unsigned dpkg-buildpackage; no installation')
    parser.add_argument('--build-admindir', type=Path, help='optional isolated native dpkg build-dependency inventory')
    args = parser.parse_args()
    inputs, candidate, output = map(durable, (args.inputs, args.candidate_repository, args.output))
    if any(output == p or p in output.parents or output in p.parents for p in (ROOT, inputs, candidate)):
        parser.error('output must be separate from delivery repository, inputs and candidate')
    source = prepare(inputs, candidate, output, args.epoch)
    if args.build:
        command = ['dpkg-buildpackage', '-us', '-uc', '-Pnocheck']
        if args.build_admindir:
            command.append('--admindir=' + str(durable(args.build_admindir)))
        subprocess.run(command, cwd=source, check=True)
    print(source)


if __name__ == '__main__':
    main()
