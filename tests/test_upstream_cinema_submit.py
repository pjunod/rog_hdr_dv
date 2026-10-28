"""Failure paths for the cinema GitHub submitter without network mutations."""
from contextlib import redirect_stdout
import importlib.util
import importlib.machinery
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cinema_submit', ROOT / 'upstream/cinema/submit.py')
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


class CinemaSubmitTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work/cinema/helper-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.units = []
        self.add_unit('01')
        self.manifest = dict(repository='team/project', target_branch='main', base='base', units=self.units)
        self.calls = []
        self.env_calls = []
        self.current = 'base'
        self.remote = ''
        self.remote_head = 'candidate'
        self.prs = []
        self.login = 'pjunod'
        self.fork_parent = 'team/project'

    def add_unit(self, n):
        slug = n + '-fix'
        d = self.project / slug
        d.mkdir()
        (d / 'DESCRIPTION.md').write_text('# Fix\n\nPrepared with AI assistants; human review pending.\n')
        (d / 'fix.patch').write_text('fixture patch')
        self.units.append(dict(id=n, slug=slug, inventory_ids=[], title='Fix',
                               patches=[slug + '/fix.patch'], status='ready-for-human-review'))

    def fake_run(self, args, *, cwd=None, capture=False, env_overrides=None):
        self.calls.append((args, cwd))
        if env_overrides:
            self.env_calls.append((args, env_overrides))
        if args[:3] == ['git', '-c', 'credential.helper=']:
            args = ['git', *args[5:]]
        if args[:3] == ['gh', 'api', 'user']:
            return self.login
        if args[:2] == ['gh', 'api'] and args[2].startswith('repos/'):
            return json.dumps({'fork': True, 'parent': {'full_name': self.fork_parent}})
        if args[:3] == ['git', 'rev-parse', 'HEAD']:
            return self.current if not any(c[0][0] == 'git' and 'am' in c[0] for c in self.calls) else 'candidate'
        if args[:3] == ['git', 'rev-parse', 'FETCH_HEAD']:
            return self.remote_head
        if args[:2] == ['git', 'ls-remote']:
            return self.remote
        if args[:3] == ['gh', 'pr', 'list']:
            return json.dumps(self.prs)
        return ''

    def invoke(self, unit='01', dry=False):
        (self.project / 'manifest.json').write_text(json.dumps(self.manifest))
        argv = ['submit.py', str(self.project), unit] + (['--dry-run'] if dry else [])
        with patch.object(submit.sys, 'argv', argv), patch.object(submit, 'run', self.fake_run), \
             patch.dict(os.environ, UPSTREAM_WORK_ROOT=str(self.root / 'cache')), redirect_stdout(io.StringIO()):
            return submit.main()

    def mutations(self):
        return [a for a, _ in self.calls if a[:2] == ['git', 'push'] or
                a[:3] in (['gh', 'repo', 'fork'], ['gh', 'pr', 'create'])]

    def test_dry_run_has_no_signoff_or_network_mutation(self):
        self.assertEqual(self.invoke(dry=True), 0)
        self.assertFalse(self.mutations())
        self.assertFalse(any(a[0] == 'gh' for a, _ in self.calls))
        self.assertFalse(any('--signoff' in a for a, _ in self.calls))

    def test_held_live_unit_refuses_before_any_command(self):
        self.units[0]['status'] = 'design-hold'
        with self.assertRaises(SystemExit): self.invoke()
        self.assertEqual(self.calls, [])

    def test_held_unsigned_preview_is_allowed(self):
        self.units[0]['status'] = 'design-hold'
        self.assertEqual(self.invoke(dry=True), 0)
        self.assertFalse(self.mutations())

    def test_upstream_drift_refuses_publication(self):
        self.current = 'changed-base'
        with self.assertRaises(SystemExit): self.invoke()
        self.assertFalse(self.mutations())
        self.assertFalse(any(a[0] == 'git' and 'am' in a for a, _ in self.calls))

    def test_missing_later_patch_refuses_before_any_command(self):
        self.add_unit('02')
        (self.project / '02-fix/fix.patch').unlink()
        with self.assertRaises(SystemExit): self.invoke('all')
        self.assertEqual(self.calls, [])

    def test_missing_description_refuses_before_any_command(self):
        (self.project / '01-fix/DESCRIPTION.md').unlink()
        with self.assertRaises(SystemExit): self.invoke()
        self.assertEqual(self.calls, [])

    def test_escaping_patch_refuses_before_any_command(self):
        (self.root / 'outside.patch').write_text('outside')
        self.units[0]['patches'] = ['../outside.patch']
        with self.assertRaises(SystemExit): self.invoke()
        self.assertEqual(self.calls, [])

    def test_wrong_account_refuses_publication(self):
        self.login = 'someone-else'
        with self.assertRaises(SystemExit): self.invoke()
        self.assertFalse(self.mutations())

    def test_wrong_parent_fork_is_not_pushed(self):
        self.fork_parent = 'someone/other-project'
        with self.assertRaises(SystemExit): self.invoke()
        self.assertFalse(any(a[:2] == ['git', 'push'] for a, _ in self.calls))
        self.assertFalse(any(a[:3] == ['gh', 'pr', 'create'] for a, _ in self.calls))

    def test_existing_different_commit_is_not_overwritten(self):
        self.remote = 'remote refs/heads/branch'
        self.remote_head = 'same-tree-wrong-commit'
        with self.assertRaises(SystemExit): self.invoke()
        self.assertFalse(any(a[:2] == ['git', 'push'] for a, _ in self.calls))
        self.assertFalse(any(a[:3] == ['gh', 'pr', 'create'] for a, _ in self.calls))

    def test_existing_closed_pr_is_idempotent(self):
        self.remote = 'candidate refs/heads/branch'
        self.prs = [dict(number=1, state='CLOSED', url='https://github.com/team/project/pull/1', baseRefName='main')]
        self.assertEqual(self.invoke(), 0)
        self.assertFalse(any(a[:2] == ['git', 'push'] for a, _ in self.calls))
        self.assertFalse(any(a[:3] == ['gh', 'pr', 'create'] for a, _ in self.calls))

    def test_closed_pr_without_branch_does_not_resurrect_it(self):
        self.remote = ''
        self.prs = [dict(number=1, state='MERGED', url='url', baseRefName='main')]
        self.assertEqual(self.invoke(), 0)
        self.assertFalse(any(a[:2] == ['git', 'push'] for a, _ in self.calls))

    def test_forgejo_private_fork_reads_use_configured_token_noninteractively(self):
        env = {'GIT_ASKPASS': '/owned/askpass', 'GIT_TERMINAL_PROMPT': '0',
               'UPSTREAM_FORGEJO_TOKEN': 'fixture-sensitive-token'}
        class Client:
            def __init__(self, host): pass
            def login(self): return 'pjunod'
            def ensure_fork(self, repository): return 'https://code.ffmpeg.org/pjunod/project.git'
            def pull_requests(self, repository, branch): return []
            def git_environment(self, checkout): return env
            def create(self, *args): pass
        class Loader:
            def create_module(self, spec): return None
            def exec_module(self, module): module.Forgejo = Client
        self.manifest['venue'] = 'forgejo'
        self.remote = 'candidate refs/heads/branch'
        spec = importlib.machinery.ModuleSpec('fixture_forgejo', Loader())
        with patch.object(importlib.util, 'spec_from_file_location', return_value=spec):
            self.assertEqual(self.invoke(), 0)
        reads = [(a, e) for a, e in self.env_calls if 'ls-remote' in a or 'fetch' in a]
        self.assertEqual(len(reads), 2)
        for args, variables in reads:
            self.assertEqual(args[:5], ['git', '-c', 'credential.helper=', '-c', 'http.followRedirects=false'])
            self.assertEqual(variables['GIT_TERMINAL_PROMPT'], '0')
            self.assertEqual(variables['UPSTREAM_FORGEJO_TOKEN'], 'fixture-sensitive-token')
            self.assertFalse(any('fixture-sensitive-token' in arg for arg in args))

    def test_existing_wrong_base_is_not_retargeted(self):
        self.remote = 'candidate refs/heads/branch'
        self.prs = [dict(number=1, state='OPEN', url='url', baseRefName='other')]
        with self.assertRaises(SystemExit): self.invoke()
        self.assertFalse(any(a[:3] == ['gh', 'pr', 'create'] for a, _ in self.calls))

    def test_live_signs_and_forks_without_modifying_caller_remotes(self):
        self.assertEqual(self.invoke(), 0)
        self.assertTrue(any('--signoff' in a for a, _ in self.calls))
        forks = [(a, cwd) for a, cwd in self.calls if a[:3] == ['gh', 'repo', 'fork']]
        self.assertIn('--remote=false', forks[0][0])
        self.assertIsNotNone(forks[0][1])

    def test_sparse_paths_limit_source_checkout_before_application(self):
        self.manifest['sparse_paths'] = ['packages/plugin', '.changeset']
        self.assertEqual(self.invoke(dry=True), 0)
        clones = [a for a, _ in self.calls if a[:2] == ['git', 'clone']]
        self.assertIn('--filter=blob:none', clones[0])
        self.assertIn('--no-checkout', clones[0])
        self.assertTrue(any(a[:3] == ['git', 'sparse-checkout', 'set'] for a, _ in self.calls))

    def test_escaping_sparse_path_refuses_before_any_command(self):
        self.manifest['sparse_paths'] = ['../owner']
        with self.assertRaises(SystemExit): self.invoke(dry=True)
        self.assertEqual(self.calls, [])

    def test_real_local_apply_preserves_non_patch_subject_brackets(self):
        source = self.root / 'source'
        source.mkdir()
        def git(*args):
            return subprocess.check_output(
                ['git', '-c', 'user.name=Paul Junod', '-c', 'user.email=donujp@gmail.com',
                 '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', *args],
                cwd=source, text=True, stderr=subprocess.DEVNULL)
        git('init', '-q', '-b', 'main')
        (source / 'file').write_text('base\n')
        git('add', 'file'); git('commit', '-q', '-m', 'base')
        base = git('rev-parse', 'HEAD').strip()
        git('switch', '-q', '-c', 'fix')
        (source / 'file').write_text('fixed\n')
        git('add', 'file')
        subject = '[android][splash-screen] Annotate an API level'
        git('commit', '-q', '-m', subject)
        (self.project / '01-fix/fix.patch').write_text(git('format-patch', '-1', '--stdout'))
        git('switch', '-q', 'main')
        self.manifest.update(source_url=str(source), base=base)
        (self.project / 'manifest.json').write_text(json.dumps(self.manifest))
        argv = ['submit.py', str(self.project), '01', '--dry-run']
        with patch.object(submit.sys, 'argv', argv), \
             patch.dict(os.environ, UPSTREAM_WORK_ROOT=str(self.root / 'cache')), redirect_stdout(io.StringIO()):
            self.assertEqual(submit.main(), 0)
        checkout = next((self.root / 'cache').glob('project-01-*'))
        message = subprocess.check_output(['git', '-C', str(checkout), 'log', '-1', '--format=%B'], text=True)
        self.assertEqual(message.splitlines()[0], subject)
        self.assertNotIn('Signed-off-by:', message)


if __name__ == '__main__': unittest.main()
