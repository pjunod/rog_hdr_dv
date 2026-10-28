"""Exercise the submitter with real local Git and a fake GitLab transport."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GitLabSubmitTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work' / 'upstream-submit-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='case with spaces ', dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.up = self.root / 'upstream'
        self.fork = self.root / 'fork.git'
        self.git = shutil.which('git')
        self.env = os.environ.copy()
        self.env.update(HOME=str(self.home), GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM='1', GIT_AUTHOR_NAME='Paul Junod',
                        GIT_AUTHOR_EMAIL='donujp@gmail.com',
                        GIT_COMMITTER_NAME='Paul Junod', GIT_COMMITTER_EMAIL='donujp@gmail.com')
        self.run_git('init', '-q', '-b', 'main', str(self.up))
        (self.up / 'base').write_text('base\n')
        self.commit('Initial source')
        self.base = self.run_git('-C', str(self.up), 'rev-parse', 'HEAD').strip()
        self.run_git('init', '-q', '--bare', str(self.fork))
        self.project = self.root / 'kit' / 'project'
        self.project.mkdir(parents=True)
        lib = self.project.parent / 'lib'
        lib.mkdir()
        shutil.copy(ROOT / 'upstream/lib/gitlab-submit.sh', lib)
        self.units = []
        self.make_unit('01', '-', 'ready')
        self.make_unit('02', '01', 'ready')
        self.run_git('-C', str(self.up), 'reset', '--hard', self.base)
        self.write_manifest()
        self.script = self.project / 'submit.sh'
        self.script.write_text('''#!/bin/sh
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
GL_HOST=gitlab.example
GL_UPSTREAM=team/project
GL_TARGET=main
GL_BASE=${FIXTURE_QUALIFIED_BASE:-}
BRANCH_PREFIX=test-
LINK_POLICY=${TEST_LINK_POLICY:-none}
SERIES_ISSUE_FILE=$HOME/.config/upstream/series-issue
. "$PROJECT_DIR/../lib/gitlab-submit.sh"
''')
        self.script.chmod(0o755)
        (self.project / '00-ISSUE.md').write_text('# Design discussion\n\nPrepared with AI assistants.\n')
        token = self.home / '.config/upstream/gitlab.example.token'
        token.parent.mkdir(parents=True)
        token.write_text('fixture-token\n')
        self.log = self.root / 'transport.jsonl'
        self.env.update(PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        FIXTURE_GIT=self.git, FIXTURE_UP=str(self.up),
                        FIXTURE_FORK=str(self.fork), FIXTURE_LOG=str(self.log),
                        UPSTREAM_SUBMIT_DIR=str(self.root / 'cache'))
        (self.bin / 'git').write_text('''#!/usr/bin/env python3
import json,os,subprocess,sys
args=sys.argv[1:]
if 'clone' in args:
 i=args.index('clone'); original=args[-2]; args[-2]=os.environ['FIXTURE_UP']
 rc=subprocess.call([os.environ['FIXTURE_GIT'],*args])
 if rc==0: subprocess.check_call([os.environ['FIXTURE_GIT'],'-C',args[-1],'remote','set-url','origin',original])
 sys.exit(rc)
if 'fetch' in args:
 i=args.index('fetch'); args=[os.environ['FIXTURE_UP'] if a=='origin' else a for a in args]
if 'push' in args or 'ls-remote' in args:
 with open(os.environ['FIXTURE_LOG'],'a') as f: f.write(json.dumps({'git':args})+'\\n')
 args=[os.environ['FIXTURE_FORK'] if a.startswith('https://gitlab.example/pjunod/') else a for a in args]
sys.exit(subprocess.call([os.environ['FIXTURE_GIT'],*args]))
''')
        (self.bin / 'git').chmod(0o755)
        (self.bin / 'curl').write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]; method=args[args.index('-X')+1]; url=args[-1]
path=url.split('/api/v4',1)[1]; payload=args[args.index('--data-binary')+1] if '--data-binary' in args else None
with open(os.environ['FIXTURE_LOG'],'a') as f: f.write(json.dumps({'method':method,'path':path,'payload':payload})+'\\n')
code=200
if method=='GET' and path=='/user': body={'username':os.environ.get('FIXTURE_LOGIN','pjunod')}
elif method=='GET' and path=='/projects/team%2Fproject': body={'id':10}
elif method=='GET' and path=='/projects/pjunod%2Fproject': body={'id':20,'forked_from_project':{'id':10},'import_status':'finished'}
elif method=='GET' and '/merge_requests?' in path: body=[{'iid':4,'source_project_id':20,'target_project_id':int(os.environ.get('FIXTURE_MR_TARGET_PROJECT','10')),'target_branch':os.environ.get('FIXTURE_MR_TARGET_BRANCH','main'),'state':os.environ.get('FIXTURE_MR_STATE','opened')}] if os.environ.get('FIXTURE_EXISTING') else []
elif method=='POST' and path.endswith('/merge_requests'): body={'iid':4}; code=201
elif method=='PUT': body={'iid':4}; code=int(os.environ.get('FIXTURE_PUT_STATUS','200'))
elif method=='POST' and path.endswith('/issues'): body={'web_url':'https://gitlab.example/team/project/-/issues/3'}; code=201
else: body={'message':'unexpected fixture route'}; code=500
Path(args[args.index('-o')+1]).write_text(json.dumps(body)); print(code,end='')
''')
        (self.bin / 'curl').chmod(0o755)

    def run_git(self, *args):
        return subprocess.check_output([self.git, *args], env=self.env, text=True, stderr=subprocess.DEVNULL)

    def commit(self, title):
        self.run_git('-C', str(self.up), 'add', '.')
        self.run_git('-C', str(self.up), 'commit', '-q', '-m', title)

    def make_unit(self, n, deps, status):
        (self.up / f'file{n}').write_text(n + '\n')
        self.commit(f'area: change {n}\n\nExplain change.\n\nLink: https://gitlab.example/team/project/-/issues/1')
        unit = self.project / f'{n}-unit'
        unit.mkdir()
        patch = self.run_git('-C', str(self.up), 'format-patch', '-1', '--stdout')
        (unit / '0001.patch').write_text(patch)
        (unit / 'DESCRIPTION.md').write_text(f'# Change {n}\n\nPrepared with AI assistants.\n')
        self.units.append((n, 'unit', deps, status, f'Change {n}'))

    def write_manifest(self):
        (self.project / 'units.tsv').write_text('\n'.join('\t'.join(row) for row in self.units) + '\n')

    def placeholders(self):
        for p in self.project.glob('*/*.patch'):
            p.write_text(p.read_text().replace('Link: https://gitlab.example/team/project/-/issues/1', 'Link: TBD-MR'))

    def invoke(self, *args, **extra):
        return subprocess.run([str(self.script), *args], env={**self.env, **extra}, text=True, capture_output=True)

    def records(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def cache(self):
        return self.root / 'cache/team_project'

    def test_dry_run_applies_chain_without_signoff_or_remote_mutation(self):
        r = self.invoke('all', '--dry-run')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.records(), [])
        messages = self.run_git('-C', str(self.cache()), 'log', '--format=%B', self.base + '..HEAD')
        self.assertNotIn('Signed-off-by:', messages)
        self.assertEqual(self.run_git('-C', str(self.cache()), 'rev-list', '--count', self.base + '..HEAD').strip(), '2')

    def test_issue_option_resolves_stacked_links_and_preserves_ampersands(self):
        self.placeholders()
        url = 'https://gitlab.example/team/project/-/issues/3?x=1&y=2'
        r = self.invoke('02', '--dry-run', '--issue', url, TEST_LINK_POLICY='tbd')
        self.assertEqual(r.returncode, 0, r.stderr)
        messages = self.run_git('-C', str(self.cache()), 'log', '--format=%B', self.base + '..HEAD')
        self.assertEqual(messages.count('Link: ' + url), 2)
        self.assertNotIn('TBD-MR', messages)

    def test_dry_run_all_restores_per_unit_automatic_link_policy(self):
        self.placeholders()
        self.units[1] = ('02', 'unit', '-', 'ready', 'Change 02')
        self.write_manifest()
        r = self.invoke('all', '--dry-run', TEST_LINK_POLICY='tbd')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count('--- MR title: Draft:'), 2)

    def test_real_path_uses_lease_and_adds_signoff_only_at_submission(self):
        r = self.invoke('01')
        self.assertEqual(r.returncode, 0, r.stderr)
        pushes = [x['git'] for x in self.records() if 'git' in x and 'push' in x['git']]
        self.assertEqual(len(pushes), 1)
        self.assertTrue(any(a.startswith('--force-with-lease=') for a in pushes[0]))
        message = self.run_git('-C', str(self.cache()), 'log', '-1', '--format=%B')
        self.assertEqual(message.count('Signed-off-by: Paul Junod <donujp@gmail.com>'), 1)

    def test_existing_mr_update_failure_is_not_reported_as_success(self):
        r = self.invoke('01', FIXTURE_EXISTING='1', FIXTURE_PUT_STATUS='500')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('HTTP 500', r.stderr)
        self.assertNotIn('updated existing MR', r.stderr)

    def test_unowned_cache_is_preserved(self):
        cache = self.cache()
        cache.mkdir(parents=True)
        (cache / 'keep').write_text('owner work')
        r = self.invoke('01', '--dry-run')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('refusing unowned cache', r.stderr)
        self.assertEqual((cache / 'keep').read_text(), 'owner work')

    def test_dirty_owned_cache_is_preserved(self):
        first = self.invoke('01', '--dry-run')
        self.assertEqual(first.returncode, 0, first.stderr)
        (self.cache() / 'keep').write_text('owner work')
        r = self.invoke('01', '--dry-run')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('cache has local changes', r.stderr)
        self.assertEqual((self.cache() / 'keep').read_text(), 'owner work')

    def test_real_submission_refuses_held_unit_but_preview_remains_available(self):
        self.units[0] = ('01', 'unit', '-', 'hold', 'Change 01')
        self.write_manifest()
        r = self.invoke('01')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is 'hold'", r.stderr)
        self.assertEqual(self.records(), [])
        preview = self.invoke('01', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)

    def test_remote_branch_without_ownership_receipt_is_preserved(self):
        self.run_git('-C', str(self.up), 'push', str(self.fork), 'HEAD:refs/heads/test-01-unit')
        r = self.invoke('01')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('refusing to overwrite unowned or changed remote branch', r.stderr)
        tip = self.run_git('--git-dir', str(self.fork), 'rev-parse', 'refs/heads/test-01-unit').strip()
        self.assertEqual(tip, self.base)

    def test_merged_mr_is_idempotent_without_push(self):
        r = self.invoke('01', FIXTURE_EXISTING='1', FIXTURE_MR_STATE='merged')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('already merged', r.stderr)
        self.assertFalse(any('git' in x and 'push' in x['git'] for x in self.records()))
        self.assertFalse(any(x.get('method') in ('POST','PUT') for x in self.records()))

    def test_closed_mr_is_not_recreated_or_pushed(self):
        r = self.invoke('01', FIXTURE_EXISTING='1', FIXTURE_MR_STATE='closed')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('is closed', r.stderr)
        self.assertFalse(any('git' in x and 'push' in x['git'] for x in self.records()))
        self.assertFalse(any(x.get('method') in ('POST','PUT') for x in self.records()))

    def test_repeat_submission_uses_recorded_remote_tip(self):
        first = self.invoke('01')
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.invoke('01', FIXTURE_EXISTING='1')
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn('updated existing MR', second.stderr)

    def test_real_submission_refuses_unqualified_upstream(self):
        r = self.invoke('01', FIXTURE_QUALIFIED_BASE='0' * 40)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('upstream moved from qualified base', r.stderr)
        self.assertEqual(self.records(), [])

    def test_issue_dry_run_does_not_post_or_persist(self):
        r = self.invoke('00', '--dry-run')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.records(), [])
        self.assertFalse((self.home / '.config/upstream/series-issue').exists())

    def test_issue_refuses_another_authenticated_account_before_posting(self):
        r = self.invoke('00', FIXTURE_LOGIN='another-user')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('expected pjunod', r.stderr)
        self.assertFalse(any(x.get('method') == 'POST' for x in self.records()))

    def test_does_not_retarget_an_existing_mr_for_another_branch(self):
        r = self.invoke('01', FIXTURE_EXISTING='1', FIXTURE_MR_TARGET_BRANCH='other')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(any(x.get('method') == 'PUT' for x in self.records()))
        self.assertTrue(any(x.get('method') == 'POST' for x in self.records()))

    def test_does_not_update_an_existing_mr_for_another_project(self):
        r = self.invoke('01', FIXTURE_EXISTING='1', FIXTURE_MR_TARGET_PROJECT='99')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(any(x.get('method') == 'PUT' for x in self.records()))


if __name__ == '__main__':
    unittest.main()
