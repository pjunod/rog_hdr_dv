#!/usr/bin/env python3
"""Public Ubuntu derivative families: publication, preference and update policy.

Run freshness only after a successful authenticated Ubuntu apt-get update. It
reads that APT cache, never scrapes a website or accepts new source identities.
"""
import argparse
import ast
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




def source_matches(row, source, version):
    field = row.get('Source', row['Package'])
    match = re.fullmatch(r'([^\s(]+)(?: \(([^)]+)\))?', field)
    return bool(match and match.group(1) == source and (match.group(2) is None or match.group(2) == version))


def expected_version(source, spec):
    """Resolve the reviewed full derivative version, never just a suffix."""
    if spec.get('policy_only'):
        raise ValueError(f'{source}: policy-only release has no managed publication version')
    if 'expected_package_version' in spec:
        return spec['expected_package_version']  # Explicit small offline fixture/release metadata.
    if spec.get('automatic'):
        return reviewed_version(source, spec) + '+nativehdr' + (HERE / 'REVISION').read_text().strip()
    if 'pin' in spec:
        return json.loads((ROOT / spec['pin']).read_text())['package_version']
    if source in ('gst-plugins-base1.0', 'gst-plugins-bad1.0', 'gst-plugins-good1.0', 'gst-libav1.0'):
        pipeline = json.loads((ROOT / 'packaging/gstreamer-gtk-dovi/package-inputs/qualified-pipeline.json').read_text())
        return pipeline['source_families'][source]['source_version']
    if source == 'gtk4':
        entries = json.loads((ROOT / 'sources.json').read_text())['series']
        return next(e['candidate_package_version'] for e in entries if e['component'] == spec['component'])
    if source in ('rust-gst-plugin-gtk4', 'showtime'):
        constant = 'GTK_VERSION' if source == 'rust-gst-plugin-gtk4' else 'SHOWTIME_VERSION'
        recipe = ast.parse((ROOT / 'packaging/gstreamer-gtk-dovi/prepare-ubuntu-packages.py').read_text())
        for node in recipe.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == constant for t in node.targets):
                version = ast.literal_eval(node.value)
                if isinstance(version, str):
                    return version
        raise ValueError(f'{source}: missing literal public recipe version {constant}')
    if source == 'gst-gtk-dovi-map':
        changelog = (ROOT / 'packaging/gstreamer-gtk-dovi/debian/changelog').read_text()
        match = re.match(r'gst-gtk-dovi-map \(([^)]+)\)', changelog)
        if match:
            return match.group(1)
    raise ValueError(f'{source}: missing authoritative full candidate version')


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
        intended = expected_version(source, spec)
        if version != intended:
            raise ValueError(f'{source}: version {version} differs from intended full candidate {intended}')
        source_field = row.get('Source', '')
        if '(' in source_field and source_field.split('(', 1)[1].rstrip(')') != intended:
            raise ValueError(f'{source}: Source version differs from intended full candidate {intended}')
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
        if (actual is None or actual.get('SHA256') != row['SHA256']
                or not source_matches(actual, source_name(row), row['Version'])):
            raise ValueError(f'published index missing or hash differs: {identity}')



def preflight_existing(rows, index):
    """Check every existing target before ANY deletion or upload, including partial releases."""
    targets = {(r['Package'], r['Version'], r['Architecture']): r for r in rows}
    for actual in index:
        identity = actual['Package'], actual['Version'], actual['Architecture']
        target = targets.get(identity)
        if target is not None and (not source_matches(actual, source_name(target), target['Version'])
                                   or actual.get('SHA256') != target['SHA256']):
            raise ValueError(f'immutable version conflict before publication: {identity}; retain the existing bytes and use a new reviewed revision')


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
        names = ' '.join(sorted({f'{name}:{arch if arch != "all" else "any"}'
                                 for name, arch in expected(spec, optional=True)}))
        # The version pin also protects an installed derivative when its registry
        # entry disappears. Source monitoring must keep this safety wait visible.
        sections.append(f'# {source}' + (' (separate release: installed derivative protection only)' if spec.get('policy_only') else ''))
        if not spec.get('policy_only'):
            sections.append(f'Package: {names}\nPin: origin "{host}"\nPin-Priority: 999\n')
        # APT treats a final glob star as a prefix matcher; *+suffix*
        # therefore does not match derivative versions. Use its explicit regex
        # form, with a literal plus, so absent registry versions stay protected.
        derivative_pattern = re.escape(spec['derivative']).replace(r'\+', '[+]')
        sections.append(f'Package: {names}\nPin: version /.*{derivative_pattern}.*/\nPin-Priority: 999\n')
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
        intended = expected_version(source, spec)
        candidates = {}
        for row in index:
            if (source_matches(row, source, intended) and row['Version'] == intended
                    and re.fullmatch('[0-9a-f]{64}', row.get('SHA256', ''))):
                candidates.setdefault(row['Version'], set()).add((row['Package'], row['Architecture']))
        versions = [v for v, members in candidates.items() if wanted <= members]
        if not versions:
            raise ValueError(f'{source}: project registry has no complete family at intended {intended} for {sorted(arches)}; holds and installed packages unchanged')
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
    current = {}
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
        current[source] = newest
        if subprocess.run(['dpkg', '--compare-versions', newest, 'gt', reviewed]).returncode == 0:
            action = ('Refresh authenticated source/patch review and qualify a separate project release; generic family publication does not manage this subset.'
                      if spec.get('policy_only') else
                      'Refresh authenticated source pin/patch replay, build and qualify the complete family, then publish.')
            scope = spec.get('monitor_scope', '')
            stale.append(f'{source}: Ubuntu {newest} > reviewed {reviewed}. {action} {scope} Existing derivative protection remains active; Ubuntu fixes are waiting.')
    if stale:
        raise ValueError('\n'.join(stale))
    print('All managed Ubuntu source families match or precede their reviewed source pins.')
    return current



def authenticated_project_index(registry):
    """Read only indexes authenticated by the immediately preceding APT update."""
    registry = registry.rstrip('/')
    targets = run('apt-get', 'indextargets', '--format', '$(IDENTIFIER) $(URI) $(FILENAME)')
    paths = []
    for line in targets.splitlines():
        fields = line.split(' ', 2)
        if len(fields) == 3 and fields[0] == 'Packages' and fields[1].startswith(registry + '/'):
            paths.append(fields[2])
    if not paths:
        raise ValueError('authenticated project Packages index unavailable; check the registry, suite and architectures (not an empty published family)')
    return [row for path in paths for row in records(run('/usr/lib/apt/apt-helper', 'cat-file', path))]


def publication_freshness(data, index, current):
    """A reviewed pin alone is insufficient: the current source must be shipped."""
    failures = []
    for source, spec in data.items():
        if spec.get('policy_only'):
            continue
        pinned_package = expected_version(source, spec)
        versions = {}
        for row in index:
            version = row['Version']
            if (not source_matches(row, source, pinned_package) or spec['derivative'] not in version
                    or not re.fullmatch('[0-9a-f]{64}', row.get('SHA256', ''))):
                continue
            if pinned_package is not None and version != pinned_package:
                continue
            if not spec.get('project'):
                if source not in current:
                    raise ValueError(f'{source}: no authenticated current Ubuntu source identity')
                # Derivative revision ordering need not preserve Ubuntu's
                # version prefix; the reviewed source identity is independent.
                if reviewed_version(source, spec) != current[source]:
                    continue
            versions.setdefault(version, set()).add((row['Package'], row['Architecture']))
        if not any(expected(spec) <= members for members in versions.values()):
            target = pinned_package if spec.get('project') else current.get(source, 'unknown')
            failures.append(f'{source}: no complete published project family for current source {target}; reviewed source alone is insufficient. Build, qualify and publish every required binary/architecture; Ubuntu fixes are waiting for publication.')
    if failures:
        raise ValueError('\n'.join(failures))
    print('Complete current-source public project families verified in authenticated APT indexes.')



def validate_simulation(body, index, data):
    """Every simulated install must belong to an exact authenticated candidate closure."""
    approved = {s: f for s, f in data.items() if not f.get('policy_only')}
    mapping = package_map(approved)
    indexed = {}
    for row in index:
        indexed.setdefault((row['Package'], row['Version'], row['Architecture']), []).append(row)
    for line in body.splitlines():
        if line.startswith('Remv '):
            raise ValueError('simulation removes a package: ' + line)
        if not line.startswith('Inst '):
            continue
        match = re.fullmatch(r'Inst (\S+)(?: \[[^\]]+\])? \((\S+).* \[([^\]]+)\]\)(?: \[[^\]]*\])?', line)
        if not match:
            raise ValueError('cannot validate simulated install identity: ' + line)
        binary, version, arch = match.groups()
        name, _, named_arch = binary.partition(':')
        if named_arch and named_arch != arch:
            raise ValueError('simulation architecture mismatch: ' + line)
        if name not in mapping:
            raise ValueError('simulation changes an unmanaged dependency; review it separately: ' + line)
        source, spec = mapping[name]
        intended = expected_version(source, spec)
        candidates = indexed.get((name, version, arch), [])
        if version != intended or not any(source_matches(r, source, intended) and re.fullmatch('[0-9a-f]{64}', r.get('SHA256', '')) for r in candidates):
            raise ValueError('simulation install lacks exact intended authenticated source/version/architecture: ' + line)
        wanted = {(n, a) for n, a in expected(spec) if a == arch or a == 'all'}
        available = {(r['Package'], r['Architecture']) for r in index
                     if source_matches(r, source, intended) and r['Version'] == intended
                     and re.fullmatch('[0-9a-f]{64}', r.get('SHA256', ''))}
        if not wanted <= available:
            raise ValueError('simulation dependency family is incomplete: ' + line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('names')
    reviewed = sub.add_parser('require-reviewed')
    reviewed.add_argument('sources', nargs='+', help='SOURCE=UBUNTU-VERSION discovered from authenticated APT')
    sub.add_parser('preferences').add_argument('host')
    sub.add_parser('freshness').add_argument('--registry', help='also require complete current-source publication from authenticated APT cache')
    complete = sub.add_parser('complete-index')
    complete.add_argument('source')
    complete.add_argument('version')
    complete.add_argument('architectures', nargs='+')
    simulation = sub.add_parser('simulation')
    simulation.add_argument('index')
    bundle = sub.add_parser('bundle')
    bundle.add_argument('directories', nargs='+')
    collision = sub.add_parser('preflight-existing')
    collision.add_argument('bundle')
    collision.add_argument('indices', nargs='+')
    check = sub.add_parser('verify-index')
    check.add_argument('bundle')
    check.add_argument('indices', nargs='+')
    before = sub.add_parser('preflight')
    before.add_argument('installed')
    before.add_argument('indices', nargs='+')
    args = parser.parse_args()
    data = families()
    if args.command == 'require-reviewed':
        for item in args.sources:
            source, version = item.split('=', 1)
            reviewed = reviewed_version(source, data[source])
            if version != reviewed:
                raise ValueError(f'{source}: discovered Ubuntu {version} differs from reviewed {reviewed}; refresh authenticated source review before any build/prune/publication')
    elif args.command == 'names':
        print('\n'.join(sorted(package_map({s: f for s, f in data.items() if not f.get('policy_only')}))))
    elif args.command == 'preferences':
        print(preferences(data, args.host))
    elif args.command == 'complete-index':
        spec = data[args.source]
        wanted = {(n, a) for n, a in expected(spec) if a in args.architectures or a == 'all'}
        available = {(r['Package'], r['Architecture']) for r in records(sys.stdin.read())
                     if source_matches(r, args.source, args.version) and r['Version'] == args.version
                     and re.fullmatch('[0-9a-f]{64}', r.get('SHA256', ''))}
        if args.version != expected_version(args.source, spec):
            raise ValueError(f'{args.source}: completion requested for an unintended full version')
        if not wanted <= available:
            sys.exit(1)
    elif args.command == 'simulation':
        validate_simulation(sys.stdin.read(), records(Path(args.index).read_text()), data)
    elif args.command == 'freshness':
        current = freshness(data)
        if args.registry:
            publication_freshness(data, authenticated_project_index(args.registry), current)
    elif args.command == 'bundle':
        rows = local_rows(args.directories)
        validate_bundle(rows, data)
        print(json.dumps(rows))
    elif args.command == 'preflight-existing':
        rows = json.loads(Path(args.bundle).read_text())
        index = [r for p in args.indices for r in records(Path(p).read_text())]
        preflight_existing(rows, index)
    elif args.command == 'verify-index':
        rows = json.loads(Path(args.bundle).read_text())
        index = [r for p in args.indices for r in records(Path(p).read_text())]
        verify_index(rows, index)
    elif args.command == 'preflight':
        installed = [dict(zip(('Package', 'Architecture', 'InstalledVersion'), line.split()))
                     for line in Path(args.installed).read_text().splitlines() if line.strip()]
        index = [r for p in args.indices for r in records(Path(p).read_text())]
        targets = preflight(installed, index, data)
        if targets:
            sys.stdout.write('\n'.join(targets) + '\n')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, StopIteration, OSError, subprocess.CalledProcessError) as error:
        print(f'managed.py: {error}', file=sys.stderr)
        sys.exit(1)
