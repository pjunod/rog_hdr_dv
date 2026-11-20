#!/usr/bin/env python3
"""Public Ubuntu derivative families: publication, preference and update policy.

Run freshness only after a successful authenticated Ubuntu apt-get update. It
reads that APT cache, never scrapes a website or accepts new source identities.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def families():
    return json.loads((HERE / 'managed-families.json').read_text())['families']


def records(body):
    result = []
    for paragraph in re.split(r'\n\s*\n', body.strip()):
        row = {}
        for line in paragraph.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                key, value = line.split(': ', 1)
                row[key] = value
        if row:
            result.append(row)
    return result


def run(*args):
    return subprocess.check_output(args, text=True)


def package_map(data):
    return {name: (source, spec) for source, spec in data.items()
            for key in ('packages', 'optional_packages')
            for names in spec.get(key, {}).values() for name in names}


def expected(spec, optional=False):
    return {(name, arch) for key in (('packages', 'optional_packages') if optional else ('packages',))
            for arch, names in spec.get(key, {}).items() for name in names}


def source_name(row):
    return row.get('Source', row['Package']).split(' ', 1)[0]


def validate_bundle(rows, data):
    """Reject unknown, duplicate, mixed or incomplete source-family uploads."""
    groups = {}
    seen = set()
    for row in rows:
        source = source_name(row)
        if source not in data:
            raise ValueError(f'unmanaged source {source}')
        spec = data[source]
        if spec.get('policy_only'):
            raise ValueError(f'{source}: separately released public binaries are preference/monitor only, not managed publication')
        name, arch, version = row['Package'], row['Architecture'], row['Version']
        base = name.removesuffix('-dbgsym')
        if (base, arch) not in expected(spec, optional=True):
            raise ValueError(f'unmanaged binary/architecture {name}:{arch} in {source}')
        if spec['derivative'] not in version:
            raise ValueError(f'{source}: version {version} lacks reviewed derivative suffix')
        identity = name, arch
        if identity in seen:
            raise ValueError(f'duplicate binary {name}:{arch}')
        seen.add(identity)
        groups.setdefault(source, []).append(row)
    for source, members in groups.items():
        if len({row['Version'] for row in members}) != 1:
            raise ValueError(f'{source}: mixed versions')
        missing = expected(data[source]) - {(row['Package'], row['Architecture']) for row in members}
        if missing:
            raise ValueError(f'{source}: incomplete family, missing {sorted(missing)}')
    if not groups:
        raise ValueError('empty package bundle')
    return groups


def verify_index(rows, index):
    """Require the exact published version, architecture and payload hash."""
    by_id = {(r['Package'], r['Version'], r['Architecture']): r for r in index}
    for row in rows:
        identity = row['Package'], row['Version'], row['Architecture']
        actual = by_id.get(identity)
        if actual is None or actual.get('SHA256') != row['SHA256']:
            raise ValueError(f'published index missing or hash differs: {identity}')


def local_rows(directories):
    rows = []
    for directory in directories:
        for path in sorted(Path(directory).glob('*.deb')):
            if any(c in str(path) for c in ('\t', '\n', '\r')):
                raise ValueError('package paths cannot contain tabs or newlines')
            if path.is_symlink() or not path.is_file():
                raise ValueError(f'not a regular package: {path}')
            row = records(run('dpkg-deb', '-f', str(path)))[0]
            row['Path'] = str(path.resolve())
            with path.open('rb') as stream:
                row['SHA256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            rows.append(row)
    return rows


def preferences(data, host):
    if not re.fullmatch(r'[A-Za-z0-9.-]+', host):
        raise ValueError('invalid registry host')
    sections = ['# Generated from managed-families.json. No permanent dpkg holds.']
    for source, spec in data.items():
        names = ' '.join(sorted({name for name, _ in expected(spec, optional=True)}))
        # The version pin also protects an installed derivative when its registry
        # entry disappears. Source monitoring must keep this safety wait visible.
        sections.append(f'# {source}' + (' (separate release: installed derivative protection only)' if spec.get('policy_only') else ''))
        if not spec.get('policy_only'):
            sections.append(f'Package: {names}\nPin: origin "{host}"\nPin-Priority: 1001\n')
        sections.append(f'Package: {names}\nPin: version *{spec["derivative"]}*\nPin-Priority: 1001\n')
    return '\n'.join(sections)


def preflight(installed, index, data):
    """Resolve one complete project version per installed family/architecture.

    Return exact installed-package targets only after every companion binary is
    available in the project index. Never infer project availability from stock
    apt-cache candidates or the installed dpkg status record.
    """
    mapping = package_map(data)
    selected = []
    for source, spec in data.items():
        if spec.get('policy_only'):
            continue
        installed_rows = [r for r in installed if r['Package'] in mapping
                          and mapping[r['Package']][0] == source]
        if not installed_rows:
            continue
        arches = {r['Architecture'] for r in installed_rows} - {'all'}
        if not arches:
            arches = {'amd64'}
        wanted = {(n, a) for n, a in expected(spec) if a in arches or a == 'all'}
        wanted.update((r['Package'], r['Architecture']) for r in installed_rows)
        candidates = {}
        for row in index:
            if (source_name(row) == source and spec['derivative'] in row['Version']
                    and re.fullmatch('[0-9a-f]{64}', row.get('SHA256', ''))):
                candidates.setdefault(row['Version'], set()).add((row['Package'], row['Architecture']))
        versions = [v for v, members in candidates.items() if wanted <= members]
        if not versions:
            raise ValueError(f'{source}: project registry has no complete family for {sorted(arches)}; holds and installed packages unchanged')
        version = versions[0]
        for other in versions[1:]:
            if subprocess.run(['dpkg', '--compare-versions', other, 'gt', version]).returncode == 0:
                version = other
        for row in installed_rows:
            installed_version = row.get('InstalledVersion')
            if installed_version and subprocess.run(
                    ['dpkg', '--compare-versions', version, 'lt', installed_version]).returncode == 0:
                raise ValueError(f'{source}: registry {version} is older than installed {installed_version}; automatic downgrade refused; review an exact manual transaction separately')
            selected.append(f'{row["Package"]}:{row["Architecture"]}={version}')
    return selected


def reviewed_version(source, spec):
    if 'pin' in spec:
        return json.loads((ROOT / spec['pin']).read_text())['source_version']
    if 'component' in spec:
        entries = json.loads((ROOT / 'sources.json').read_text())['series']
        return next(e['source_origin']['version'] for e in entries if e['component'] == spec['component'])
    if 'provenance' in spec:
        provenance = ROOT / 'packaging/gstreamer-gtk-dovi/package-inputs/provenance.json'
        return json.loads(provenance.read_text())[spec['provenance']]['package_version']
    raise ValueError(f'{source}: missing reviewed Ubuntu source identity')


def freshness(data):
    stale = []
    for source, spec in data.items():
        if spec.get('project'):
            continue  # Project-owned source has no Ubuntu counterpart.
        reviewed = reviewed_version(source, spec)
        versions = [r['Version'] for r in records(run('apt-cache', 'showsrc', source)) if 'Version' in r]
        if not versions:
            raise ValueError(f'{source}: authenticated Ubuntu source index is missing')
        newest = versions[0]
        for version in versions[1:]:
            if subprocess.run(['dpkg', '--compare-versions', version, 'gt', newest]).returncode == 0:
                newest = version
        if subprocess.run(['dpkg', '--compare-versions', newest, 'gt', reviewed]).returncode == 0:
            action = ('Refresh authenticated source/patch review and qualify a separate project release; generic family publication does not manage this subset.'
                      if spec.get('policy_only') else
                      'Refresh authenticated source pin/patch replay, build and qualify the complete family, then publish.')
            scope = spec.get('monitor_scope', '')
            stale.append(f'{source}: Ubuntu {newest} > reviewed {reviewed}. {action} {scope} Existing derivative protection remains active; Ubuntu fixes are waiting.')
    if stale:
        raise ValueError('\n'.join(stale))
    print('All managed Ubuntu source families match or precede their reviewed source pins.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('names')
    sub.add_parser('preferences').add_argument('host')
    sub.add_parser('freshness')
    complete = sub.add_parser('complete-index')
    complete.add_argument('source')
    complete.add_argument('version')
    complete.add_argument('architectures', nargs='+')
    sub.add_parser('simulation')
    bundle = sub.add_parser('bundle')
    bundle.add_argument('directories', nargs='+')
    check = sub.add_parser('verify-index')
    check.add_argument('bundle')
    check.add_argument('indices', nargs='+')
    before = sub.add_parser('preflight')
    before.add_argument('installed')
    before.add_argument('indices', nargs='+')
    args = parser.parse_args()
    data = families()
    if args.command == 'names':
        print('\n'.join(sorted(package_map({s: f for s, f in data.items() if not f.get('policy_only')}))))
    elif args.command == 'preferences':
        print(preferences(data, args.host))
    elif args.command == 'complete-index':
        spec = data[args.source]
        wanted = {(n, a) for n, a in expected(spec) if a in args.architectures or a == 'all'}
        available = {(r['Package'], r['Architecture']) for r in records(sys.stdin.read())
                     if source_name(r) == args.source and r['Version'] == args.version
                     and re.fullmatch('[0-9a-f]{64}', r.get('SHA256', ''))}
        if not wanted <= available:
            sys.exit(1)
    elif args.command == 'simulation':
        mapping = package_map({s: f for s, f in data.items() if not f.get('policy_only')})
        for line in sys.stdin:
            if line.startswith('Remv '):
                raise ValueError('simulation removes a package: ' + line.strip())
            if line.startswith('Inst ') and line.split()[1].split(':')[0] not in mapping:
                raise ValueError('simulation changes an unmanaged dependency; review it separately: ' + line.strip())
    elif args.command == 'freshness':
        freshness(data)
    elif args.command == 'bundle':
        rows = local_rows(args.directories)
        validate_bundle(rows, data)
        print(json.dumps(rows))
    elif args.command == 'verify-index':
        rows = json.loads(Path(args.bundle).read_text())
        index = [r for p in args.indices for r in records(Path(p).read_text())]
        verify_index(rows, index)
    elif args.command == 'preflight':
        installed = [dict(zip(('Package', 'Architecture', 'InstalledVersion'), line.split()))
                     for line in Path(args.installed).read_text().splitlines() if line.strip()]
        index = [r for p in args.indices for r in records(Path(p).read_text())]
        print('\n'.join(preflight(installed, index, data)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, StopIteration, OSError, subprocess.CalledProcessError) as error:
        print(f'managed.py: {error}', file=sys.stderr)
        sys.exit(1)
