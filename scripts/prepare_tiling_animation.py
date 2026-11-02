#!/usr/bin/env python3
"""Replay only the pinned tiling patch and check syntax; never run tests/install."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = 'tiling-assistant@leleat-on-github'


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='new durable owned source directory')
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    component = next(item for item in json.loads((ROOT / 'sources.json').read_text())['series']
                     if item['component'] == 'ubuntu-tiling-assistant')
    source = args.base_repository.resolve()
    output = args.output.resolve()
    forbidden = (Path('/tmp'), Path('/private/tmp'), Path('/var/tmp'), Path.home() / 'code')
    for path in (source, output, args.receipt.resolve()):
        if any(path == root or root in path.parents for root in forbidden):
            parser.error('use durable owned paths, not temporary folders or owner checkouts')
    if output.exists() or output == ROOT or ROOT in output.parents:
        parser.error('--output must be absent and outside the delivery repository')
    base = component['base_commit']
    assert run('git', 'rev-parse', base + '^{tree}', cwd=source) == component['base_tree']
    for name, digest in component['installed_source_sha256'].items():
        data = subprocess.check_output(['git', 'show', f'{base}:{EXTENSION}/{name}'], cwd=source)
        assert hashlib.sha256(data).hexdigest() == digest, name
    sums = dict(line.split('  ', 1)[::-1] for line in (ROOT / 'SHA256SUMS').read_text().splitlines())
    for name in component['patch_order']:
        path = Path('patches') / component['component'] / name
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sums[str(path)]
    output.parent.mkdir(parents=True, exist_ok=True)
    run('git', 'clone', '--no-hardlinks', '--no-checkout', str(source), str(output))
    run('git', 'checkout', '--detach', base, cwd=output)
    run('git', 'config', 'user.name', 'HDR Builder', cwd=output)
    run('git', 'config', 'user.email', 'hdr-builder@users.noreply.github.com', cwd=output)
    for name in component['patch_order']:
        run('git', 'am', str(ROOT / 'patches' / component['component'] / name), cwd=output)
    tree = run('git', 'rev-parse', 'HEAD^{tree}', cwd=output)
    assert tree == component['candidate_tree']
    checked = []
    for name in ('windowAnimation.js', 'tilingWindowManager.js', 'keybindingHandler.js'):
        path = Path(EXTENSION) / 'src/extension' / name
        run('node', '--check', str(path), cwd=output)
        checked.append(str(path))
    run('node', '--check', str(ROOT / 'tests/tiling-animation-ownership.mjs'))
    receipt = {
        'schema': 1, 'scope': 'source replay and syntax only',
        'base_commit': base, 'base_tree': component['base_tree'],
        'candidate_tree': tree, 'source_candidate_commit': component['candidate_commit'],
        'installed_callsite_hashes_verified': True, 'syntax_checked': checked,
        'node_version': run('node', '--version'), 'unit_tests_executed': 0,
        'packaged': False, 'installed': False, 'live_display_actions': 0,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
