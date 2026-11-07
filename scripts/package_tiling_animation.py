#!/usr/bin/env python3
"""Build the pinned Ubuntu extension source/package; never install or reload it."""
import argparse
from email.utils import formatdate
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = 'tiling-assistant@leleat-on-github'
PACKAGE = 'gnome-shell-ubuntu-extensions'
STOCK_VERSION = '51.26.10.6ubuntu'
VERSION = STOCK_VERSION + '+nativehdr3'
STOCK_DEB_SHA256 = '6784ab2e51c29e75efb94ac4de224141741d51fe388f95d48f70e32272f35df5'
UBUNTU_TOOLS = {
    'pkgbinarymangler_158_all.deb': '02d2a0038c4335e38c62b4ce1442eea403f8896b1deab5fb51d7d82d1af4d4c0',
    'lockfile-progs_0.2.0build1_amd64.deb': 'ca72b2d34b9cbd908f0bf3bd5fbd2b9d2435913465b5e4382ce3fd872bea36ed',
    'liblockfile1_1.17-2build2_amd64.deb': '70e8dd7d390a2b65b62cb59e4664729cb89a1196b241dd4e6bce1cb92f5eb735',
    'liblockfile-bin_1.17-2build2_amd64.deb': '0420cfd9502d22ca16bf4a2fa1374a7decd336de2d4fc56b3c0cd0c4bc701ea4',
    'advancecomp_2.5-1build2_amd64.deb': 'da38634c899442e7bee301e92fceda790536e002a81d96a062cfeb56a1024eab',
    'optipng_7.9.1+ds-2build1_amd64.deb': '805ce2239b864943f5ebd097d438644f60af5842ef80970a5752c172b560f52d',
}
PACKAGE_ADDITIONS = {
    '.meson-subproject-wrap-hash.txt', 'meson.build', 'translations/LINGUAS',
    'translations/POTFILES.in', 'translations/meson.build',
}


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_tools(inputs):
    for name, expected in UBUNTU_TOOLS.items():
        if not (inputs / name).is_file() or digest(inputs / name) != expected:
            raise ValueError('required Ubuntu packaging tool unavailable or SHA256 mismatch: ' + name)


def build_environment(inputs, output):
    """Use Ubuntu's unmodified dpkg-deb wrapper without host diversions/configuration."""
    verify_tools(inputs)
    if run('dpkg', '--print-architecture') != 'amd64':
        raise ValueError('pinned Ubuntu packaging tools require native amd64')
    # A configured Ubuntu buildd may already have the distribution diversion.
    real_dpkg_deb = Path(shutil.which('dpkg-deb.pkgbinarymangler') or
                         shutil.which('dpkg-deb') or '').resolve()
    if not real_dpkg_deb.is_file():
        raise ValueError('ordinary dpkg-deb is required')
    root = output / 'build-environment'
    prefix, bin_dir = root / 'prefix', root / 'bin'
    bin_dir.mkdir(parents=True)
    for name in UBUNTU_TOOLS:
        subprocess.run([str(real_dpkg_deb), '-x', str(inputs / name), str(prefix)], check=True)
    # Do not expose the package's optional dh_builddeb wrapper: it hardcodes /tmp.
    # Its dpkg-deb wrapper is independent; this package has exactly one binary.
    for path in (prefix / 'usr/bin').iterdir():
        if path.name != 'dh_builddeb':
            (bin_dir / path.name).symlink_to(path)
    (bin_dir / 'dpkg-deb.pkgbinarymangler').symlink_to(real_dpkg_deb)
    config = prefix / 'etc/pkgbinarymangler'
    strip_config = config / 'striptranslations.conf'
    text = strip_config.read_text()
    if text.count('enable: false') != 1:
        raise ValueError('unexpected official translation configuration')
    strip_config.write_text(text.replace('enable: false', 'enable: true'))
    build_info = root / 'CurrentlyBuilding'
    build_info.write_text(f'Package: {PACKAGE}\nComponent: main\nSuite: stonking\n')
    lock = root / 'binary-packages.lock'
    lock.write_text(PACKAGE + '\n')
    scratch = root / 'scratch'
    scratch.mkdir()
    env = dict(os.environ)
    # Caller environment must not silently bypass the declared build policy.
    for name in ('NO_PKG_MANGLE', 'PKG_IGNORE_CURRENTLY_BUILDING'):
        env.pop(name, None)
    env.update({
        'PATH': os.pathsep.join((str(bin_dir), env.get('PATH', ''))),
        'LD_LIBRARY_PATH': os.pathsep.join(filter(None, (
            str(prefix / 'usr/lib/x86_64-linux-gnu'), env.get('LD_LIBRARY_PATH', '')))),
        'PKGBINARYMANGLER_CONF_DIR': str(config),
        'PKGBINARYMANGLER_COMMON_PATH': str(prefix / 'usr/share/pkgbinarymangler'),
        'CURRENTLY_BUILDING_PATH': str(build_info),
        'PKGBINARYMANGLER_LOCKFILE': str(lock),
        'PKGBINARYMANGLER_PACKAGES': PACKAGE,
        'TMPDIR': str(scratch),
    })
    receipt = {
        'tool_deb_sha256': UBUNTU_TOOLS,
        'config': {p.name: p.read_text() for p in config.glob('*.conf')},
        'build_info': build_info.read_text(),
        'environment': {key: env[key] for key in (
            'PATH', 'LD_LIBRARY_PATH', 'PKGBINARYMANGLER_CONF_DIR',
            'PKGBINARYMANGLER_COMMON_PATH', 'CURRENTLY_BUILDING_PATH',
            'PKGBINARYMANGLER_LOCKFILE', 'PKGBINARYMANGLER_PACKAGES', 'TMPDIR')},
        'real_dpkg_deb': str(real_dpkg_deb),
        'tool_files': {str(p.relative_to(prefix)): digest(p)
                       for p in prefix.rglob('*') if p.is_file()},
        'host_installation_or_diversion': False,
    }
    (output / 'build-environment.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return env


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
             '  * Retain Ubuntu extensions and packaging; apply six synthetic tiling\n'
             '    animation ownership patches, including callback-only ease support.\n'
             '  * Build with Ubuntu pkgbinarymangler 158 translation policy; retain\n'
             '    raw translations separately, matching the stock payload class.\n'
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
    parser.add_argument('--ubuntu-packaging-inputs', type=Path,
                        help='required with --build: six authenticated pinned Ubuntu wrapper/dependency debs')
    args = parser.parse_args()
    inputs, candidate, output = map(durable, (args.inputs, args.candidate_repository, args.output))
    if any(output == p or p in output.parents or output in p.parents for p in (ROOT, inputs, candidate)):
        parser.error('output must be separate from delivery repository, inputs and candidate')
    tool_inputs = None
    if args.build:
        if not args.ubuntu_packaging_inputs:
            parser.error('--build requires --ubuntu-packaging-inputs (Ubuntu translation packaging policy)')
        tool_inputs = durable(args.ubuntu_packaging_inputs)
        verify_tools(tool_inputs)
    source = prepare(inputs, candidate, output, args.epoch)
    if args.build:
        command = ['dpkg-buildpackage', '-us', '-uc', '-Pnocheck']
        if args.build_admindir:
            command.append('--admindir=' + str(durable(args.build_admindir)))
        subprocess.run(command, cwd=source, env=build_environment(tool_inputs, output), check=True)
    print(source)


if __name__ == '__main__':
    main()
