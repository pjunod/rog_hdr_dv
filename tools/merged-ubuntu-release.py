#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Construct or audit a normal source release from an exact committed Ubuntu candidate.

Native builder only. All writes are below a fresh durable output. No APT, host
installation or tests. Existing distribution quilt state is copied, never forged.
The generated source package is extracted again and is the actual binary input.
The FINAL delivered .dsc (a binary build regenerates the source artifacts) is
extracted once more and bound to the same typed source manifest.

``--audit-existing PATH`` inspects an already constructed .dsc or an extracted
source tree against the canonical source without constructing or building
anything. Missing typed-manifest metadata alone never requires a rebuild.
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
import stat
import subprocess
import tarfile

MUTTER_TREE = '08740f943fb2ddda60411fa4d72bb4ccc4238e5f'
LIBRARY_TREE = '96d65c11ed0f408792c41cd42c2866255b1089d0'
MUTTER_ORIG = '5d28f3ae225692428fcafb96500d673f34328b698b86960c9c1460d0b1d983b3'
VERSION = '51.0-1ubuntu3+nativehdr10.1'
AGGREGATE_PATCH = 'merged-hdr-runtime.patch'
CHANGELOG = '''mutter (51.0-1ubuntu3+nativehdr10.1) stonking; urgency=medium

  * Release merged nativehdr10, asynchronous lifetime/offscreen and GTK frames
    corrections as one coherent source/binary set with a unique version.
  * Preserve the SONAME, distribution packaging and qualified runtime source.
    Record the privately staged hdr9 dependency in normal shlibs metadata.
  * Supersede the provisional same-version common-bin artifacts. Construction
    uses nocheck; scoped qualification and physical installation are separate.

 -- HDR Engineering Agent <hdr-agent@users.noreply.github.com>  Thu, 15 Oct 2026 23:30:00 +0000

'''

# Typed source manifest policy. Directories are implied by their members: neither
# git archive nor dpkg-source carries an empty directory, so none is inventoried.
MANIFEST_POLICY = {
    'file': 'sha256 of the content plus whether any execute bit is set',
    'symlink': 'literal link target; never followed, never resolved outside the root',
    'directory': 'implied by members; empty directories are not carried by the archives',
    'other': 'rejected: sockets, fifos and devices are not source',
}
PACKAGING_EXCLUDED = ('.pc', 'debian')
# The only packaging entries allowed to differ between the canonical git archive
# and the final extracted .dsc, with the reason for each. Everything else under
# debian/ must be byte-identical; the runtime manifest must have no delta at all.
ALLOWED_PACKAGING_DELTAS = {
    'mutter': {
        'debian/changelog': 'unique release version entry prepended by the recipe',
        'debian/shlibs.local': 'added: hdr9 runtime floor for the privately staged library',
        'debian/patches/series': 'aggregate runtime patch appended by dpkg-source --commit',
        'debian/patches/' + AGGREGATE_PATCH: 'added: mechanical aggregate of the merged runtime source',
    },
    'libdisplay-info': {
        'debian/patches/series': 'aggregate runtime patch appended by dpkg-source --commit',
        'debian/patches/' + AGGREGATE_PATCH: 'added: mechanical aggregate of the merged runtime source',
    },
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def text(command, cwd=None):
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def manifest(root, excluded=PACKAGING_EXCLUDED):
    """Typed manifest of a tree: regular files, symlinks, rejected other types.

    Symlinks are inventoried by their literal target and never followed, so a
    link pointing outside the root can neither be read nor hide a difference.
    """
    root = Path(root)
    result = {}
    for directory, names, files in os.walk(root, followlinks=False):
        relative = Path(directory).relative_to(root)
        if not relative.parts:
            names[:] = [name for name in names if name not in excluded]
            files = [name for name in files if name not in excluded]
        for name in sorted(names + files):
            path = Path(directory) / name
            key = str(relative / name)
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                result[key] = {'type': 'symlink', 'target': os.readlink(path)}
            elif stat.S_ISREG(mode):
                result[key] = {'type': 'file', 'sha256': sha(path), 'executable': bool(mode & 0o111)}
            elif stat.S_ISDIR(mode):
                continue
            else:
                raise ValueError('unsupported source entry type: ' + key)
    return result


def files(root):
    """Regular-file digests only (compatibility view of manifest())."""
    return {k: v['sha256'] for k, v in manifest(root).items() if v['type'] == 'file'}


def packaging_inventory(tree):
    """Typed inventory of the distribution packaging, kept apart from runtime source."""
    debian = Path(tree) / 'debian'
    if not debian.is_dir():
        return {}
    return {'debian/' + key: value for key, value in manifest(debian, excluded=()).items()}


def compare_manifests(canonical, candidate, allowed=None):
    """Return (deltas, unexplained): every differing key, and those not allowed."""
    allowed = allowed or {}
    deltas = {}
    for key in sorted(set(canonical) | set(candidate)):
        if canonical.get(key) != candidate.get(key):
            deltas[key] = {'canonical': canonical.get(key), 'candidate': candidate.get(key),
                           'allowed': allowed.get(key)}
    unexplained = sorted(key for key, delta in deltas.items() if delta['allowed'] is None)
    return deltas, unexplained


def check_packaging(component, canonical_packaging, candidate_packaging):
    """Packaging deltas against the allowlist: (deltas, problems)."""
    allowed = ALLOWED_PACKAGING_DELTAS[component]
    deltas, unexplained = compare_manifests(canonical_packaging, candidate_packaging, allowed)
    problems = ['unexplained packaging delta: ' + key for key in unexplained]
    problems += ['expected packaging delta absent: ' + key for key in sorted(set(allowed) - set(deltas))]
    return deltas, problems


def quilt_state(tree):
    """Read the actual applied-patches bookkeeping of a tree; never write it."""
    applied = Path(tree) / '.pc/applied-patches'
    if not applied.is_file():
        return None
    return applied.read_text().splitlines()


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


def canonical_tree(source, orig, component, out):
    """Materialise the canonical git archive plus the pinned gvdb restoration."""
    tree = out / 'canonical'
    tree.mkdir()
    archive = out / 'canonical-source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(source), 'archive', 'HEAD'], stdout=stream, check=True)
    with tarfile.open(archive) as packed:
        packed.extractall(tree, filter='data')
    if component == 'mutter':
        with tarfile.open(orig) as packed:
            for member in packed.getmembers():
                if member.name.startswith('mutter-51.0/subprojects/gvdb/'):
                    member.name = member.name.removeprefix('mutter-51.0/')
                    packed.extract(member, tree, filter='data')
    return tree, archive


def patch_header(component, head, expected, source):
    """Deterministic factual DEP3 header for the aggregate patch: no template
    placeholders, no invented review, signoff or forwarding claim."""
    date = text(['git', '-C', str(source), 'log', '-1', '--format=%cs', 'HEAD'])
    return (
        'Description: Mechanical aggregate of the merged HDR runtime source\n'
        ' This patch is the normal source-package representation of the committed\n'
        ' canonical ' + component + ' tree. It was generated by dpkg-source --commit from\n'
        ' the exact tree below and carries no review, signoff or upstream status.\n'
        ' Original per-change authorship and licences are preserved in the public\n'
        ' repository patch series from which that tree was built.\n'
        'Origin: other, commit:' + head + '\n'
        'X-Canonical-Tree: ' + expected + '\n'
        'Last-Update: ' + date + '\n'
        '---\n'
    )


def extract_dsc(dsc, destination, log):
    command = ['dpkg-source', '--no-check', '-x', str(dsc), str(destination)]
    with log.open('a') as stream:
        stream.write('\nCOMMAND ' + repr(command) + '\n')
        stream.flush()
        subprocess.run(command, cwd=dsc.parent, env=dict(os.environ, LC_ALL='C'),
                       stdout=stream, stderr=subprocess.STDOUT, check=True)


def dsc_references(dsc):
    """Files referenced by a .dsc: name -> (size, sha256) from Checksums-Sha256."""
    result = {}
    section = False
    for line in Path(dsc).read_text().splitlines():
        if line.startswith('Checksums-Sha256:'):
            section = True
            continue
        if section and line.startswith(' '):
            digest, size, name = line.split()
            result[name] = (int(size), digest)
        elif section:
            break
    return result


def bind_source_package(dsc):
    """Hash binding of a .dsc and every archive it references, sizes verified."""
    dsc = Path(dsc)
    archives = {}
    for name, (size, digest) in dsc_references(dsc).items():
        path = dsc.parent / name
        if not path.is_file() or path.stat().st_size != size or sha(path) != digest:
            raise ValueError('source package reference does not match: ' + name)
        archives[name] = {'size': size, 'sha256': digest}
    return {'dsc': dsc.name, 'dsc_sha256': sha(dsc), 'dsc_size': dsc.stat().st_size,
            'archives': archives}


def source_comparison(component, canonical, candidate):
    """Typed runtime equality plus explained packaging deltas and quilt state.

    Differences are recorded, not hidden: 'problems' lists every runtime delta
    and every packaging delta outside the allowlist. Construction refuses on any
    problem; an audit records them for assessment without rebuilding anything.
    """
    runtime_canonical = manifest(canonical)
    runtime_candidate = manifest(candidate)
    deltas, _ = compare_manifests(runtime_canonical, runtime_candidate)
    packaging, problems = check_packaging(component, packaging_inventory(canonical),
                                          packaging_inventory(candidate))
    problems = ['runtime delta: ' + key for key in deltas] + problems
    return {'runtime_manifest': runtime_candidate,
            'runtime_deltas': deltas, 'problems': problems,
            'runtime_manifest_sha256': hashlib.sha256(
                json.dumps(runtime_candidate, sort_keys=True).encode()).hexdigest(),
            'runtime_entry_counts': {
                kind: sum(1 for v in runtime_candidate.values() if v['type'] == kind)
                for kind in ('file', 'symlink')},
            'runtime_executables': sorted(k for k, v in runtime_candidate.items()
                                          if v['type'] == 'file' and v['executable']),
            'runtime_equal': not deltas,
            'packaging_deltas': packaging,
            'packaging_inventory_sha256': hashlib.sha256(json.dumps(
                packaging_inventory(candidate), sort_keys=True).encode()).hexdigest(),
            'quilt_applied': quilt_state(candidate)}


def builder_required():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or os.geteuid() == 0:
        raise ValueError('authorized unprivileged native x86_64 builder required')


def audit(args):
    """Supplemental audit of an EXISTING .dsc or extracted tree; nothing is built."""
    builder_required()
    expected = MUTTER_TREE if args.component == 'mutter' else LIBRARY_TREE
    source = args.source.resolve()
    head = verify_source(source, expected)
    existing = args.audit_existing.resolve()
    if not existing.exists():
        raise ValueError('existing source package or tree required')
    if args.component == 'mutter' and sha(args.orig) != MUTTER_ORIG:
        raise ValueError('Mutter orig hash mismatch')
    if args.component == 'libdisplay-info' and sha(args.orig) != args.orig_sha256:
        raise ValueError('library orig hash mismatch')
    out = durable_output(args.output)
    if source == out or source in out.parents or out in source.parents:
        raise ValueError('source and output must be disjoint')
    out.mkdir(parents=True)
    log = out / 'audit.log'
    canonical, archive = canonical_tree(source, args.orig, args.component, out)
    receipt = {'schema': 1, 'kind': 'source-audit', 'component': args.component,
               'repository_commit': args.repository_commit, 'canonical_commit': head,
               'canonical_tree': expected, 'canonical_archive_sha256': sha(archive),
               'orig_sha256': sha(args.orig), 'manifest_policy': MANIFEST_POLICY,
               'audited': str(existing), 'constructed': False, 'binary_build': False,
               'units_executed': 0, 'host_installs': 0}
    if existing.is_dir():
        candidate = existing
        receipt['source_package'] = None
    else:
        receipt['source_package'] = bind_source_package(existing)
        candidate = out / 'source-from-dsc'
        extract_dsc(existing, candidate, log)
    receipt.update(source_comparison(args.component, canonical, candidate))
    (out / 'source-audit.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'runtime_manifest'}, indent=2))
    # A recorded difference is a finding to assess, never a silent rebuild.
    return 2 if receipt['problems'] else 0


def recipe(args):
    builder_required()
    if not re.fullmatch('[0-9a-f]{40}', args.repository_commit):
        raise ValueError('full packaging repository commit required')
    if args.audit_existing:
        return audit(args)
    if not args.quilt_state:
        raise ValueError('preserved actual quilt bookkeeping is required')
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
    original = out / args.orig.name
    shutil.copyfile(args.orig, original)
    canonical, archive = canonical_tree(source, original, args.component, out)
    tree = out / 'prepared'
    shutil.copytree(canonical, tree, symlinks=True)
    shutil.copytree(pc, tree / '.pc', symlinks=True)
    if args.component == 'mutter':
        changelog = tree / 'debian/changelog'
        changelog.write_text(CHANGELOG + changelog.read_text())
        (tree / 'debian/shlibs.local').write_text('libdisplay-info 3 libdisplay-info3 (>= 0.3.0-1ubuntu1~hdr9)\n')
    header = patch_header(args.component, head, expected, source)
    # local-patch-header is read by dpkg-source --commit and is never part of
    # the generated source package, so the packaging inventory stays explicit.
    (tree / 'debian/source').mkdir(exist_ok=True)
    (tree / 'debian/source/local-patch-header').write_text(header)
    env = dict(os.environ, TMPDIR=str(scratch), LC_ALL='C',
               DEB_BUILD_OPTIONS='nocheck parallel=2', DEB_BUILD_PROFILES='nocheck',
               EDITOR='true', VISUAL='true')
    commands = []
    log = out / 'construction.log'

    def run(command, cwd=tree):
        commands.append(command)
        with log.open('a') as stream:
            stream.write('\nCOMMAND ' + repr(command) + '\n')
            stream.flush()
            subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                           stderr=subprocess.STDOUT, check=True)

    run(['dpkg-source', '--commit', '.', AGGREGATE_PATCH])
    patch = tree / 'debian/patches' / AGGREGATE_PATCH
    if not patch.read_text().startswith(header):
        raise ValueError('aggregate patch header is not the deterministic factual header')
    (tree / 'debian/source/local-patch-header').unlink()
    run(['dpkg-buildpackage', '-S', '-us', '-uc', '-d', '-nc'])
    dsc, = out.glob('*.dsc')
    staged = bind_source_package(dsc)
    extracted = out / 'source-from-dsc'
    commands.append(['dpkg-source', '--no-check', '-x', str(dsc), str(extracted)])
    extract_dsc(dsc, extracted, log)
    comparison = source_comparison(args.component, canonical, extracted)
    if comparison['problems']:
        raise ValueError('source package roundtrip: ' + '; '.join(comparison['problems']))
    receipt = {'schema': 2, 'component': args.component,
               'repository_commit': args.repository_commit,
               'canonical_commit': head, 'canonical_tree': expected,
               'canonical_archive_sha256': sha(archive), 'orig_sha256': sha(original),
               'actual_quilt_state': str(pc), 'quilt_applied': applied,
               'quilt_applied_after_commit': quilt_state(tree),
               'aggregate_patch': AGGREGATE_PATCH, 'aggregate_patch_sha256': sha(patch),
               'aggregate_patch_header_sha256': hashlib.sha256(header.encode()).hexdigest(),
               'manifest_policy': MANIFEST_POLICY,
               'runtime_input_sha256': files(extracted),
               'source_roundtrip_equal': comparison['runtime_equal'],
               'staged_source': staged, 'commands': commands,
               'units_executed': 0, 'host_installs': 0, 'binary_build': False}
    receipt.update(comparison)
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
        audit_output = subprocess.run(['dpkg-checkbuilddeps', '-Pnocheck'], cwd=extracted,
                                      env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / 'build-dependencies.log').write_text(audit_output.stdout)
        exception = offline.staged_dependency_exception(audit_output.returncode, audit_output.stdout, '0.3.0-1ubuntu1~hdr9')
        command = ['dpkg-buildpackage', '-F', '-us', '-uc']
        if exception:
            command.append('-d')
        run(command, cwd=extracted)
        receipt.update(binary_build=True, dependency_exception=exception, library_inputs=library_inputs)
    # Bind the FINAL delivered source package. A -F build regenerates the .dsc
    # and debian archive from the extracted tree; compare that output as well.
    dsc, = out.glob('*.dsc')
    final = bind_source_package(dsc)
    final_extracted = out / 'source-from-final-dsc'
    commands.append(['dpkg-source', '--no-check', '-x', str(dsc), str(final_extracted)])
    extract_dsc(dsc, final_extracted, log)
    final_comparison = source_comparison(args.component, canonical, final_extracted)
    if final_comparison['problems']:
        raise ValueError('final source package: ' + '; '.join(final_comparison['problems']))
    receipt['final_source'] = dict(final, regenerated_by_binary_build=(final != staged),
                                   runtime_manifest_sha256=final_comparison['runtime_manifest_sha256'],
                                   packaging_inventory_sha256=final_comparison['packaging_inventory_sha256'],
                                   quilt_applied=final_comparison['quilt_applied'])
    if final_comparison['runtime_manifest_sha256'] != comparison['runtime_manifest_sha256']:
        raise ValueError('final source package differs from the staged source package')
    artifacts = [p for p in sorted(out.iterdir()) if p.is_file() and p.suffix
                 in ('.deb', '.ddeb', '.dsc', '.xz', '.bz2', '.changes', '.buildinfo')]
    receipt['artifacts'] = {p.name: sha(p) for p in artifacts}
    receipt['artifact_sizes'] = {p.name: p.stat().st_size for p in artifacts}
    receipt['construction_log_sha256'] = sha(log)
    (out / 'source-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items()
                      if k not in ('runtime_input_sha256', 'runtime_manifest')}, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=['mutter', 'libdisplay-info'])
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--quilt-state', type=Path, help='preserved actual .pc directory (construction only)')
    parser.add_argument('--orig', required=True, type=Path)
    parser.add_argument('--orig-sha256', default='')
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--audit-existing', type=Path,
                        help='audit this existing .dsc or extracted source tree instead of constructing')
    parser.add_argument('--build', action='store_true', help='construct Mutter binaries from the extracted .dsc, nocheck')
    parser.add_argument('--library-dev', type=Path)
    parser.add_argument('--library-runtime', type=Path)
    parser.add_argument('--dev-sha256', default='')
    parser.add_argument('--runtime-sha256', default='')
    raise SystemExit(recipe(parser.parse_args()) or 0)


if __name__ == '__main__':
    main()
