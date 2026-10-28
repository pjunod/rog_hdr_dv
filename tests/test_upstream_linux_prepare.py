"""Kernel-mail preparation safety with all Git/network commands mocked."""
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import shlex
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('linux_prepare', ROOT / 'upstream/linux/prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class KernelPrepareTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work/rog-prep/helper-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'linux'
        self.project.mkdir()
        for name in ['third-party-a.patch', 'third-party-b.patch', 'ours-a.patch', 'ours-b.patch']:
            (self.project / name).write_text('From 0 Mon Sep 17 00:00:00 2001\nFrom: Paul Junod <donujp@gmail.com>\nSubject: fixture\n\n')
        description = self.project / '02-validation/DESCRIPTION.md'
        description.parent.mkdir()
        description.write_text('Source qualification; human review remains required.\n')
        (self.project / 'thread.json').write_text(json.dumps(dict(message_id='cover@example.org', archive_url='https://example.org/thread')))
        (self.project / 'manifest.json').write_text(json.dumps(dict(
            base='base', candidate_tree='tree', target_branch='master', source_url='https://example.org/linux.git',
            units=[dict(id='02', slug='02-validation', candidate_tree='tree',
                        prerequisite_patches=['third-party-a.patch', 'third-party-b.patch'],
                        outgoing_patches=['ours-a.patch', 'ours-b.patch'])])))
        self.calls = []
        self.tree = 'tree'
        self.authors = prepare.OWNER + '\n' + prepare.OWNER

    def fake_run(self, args, *, cwd=None, capture=False):
        self.calls.append(args)
        if args[:2] == ['git', 'clone']:
            Path(args[-1]).mkdir()
        if args[:2] == ['git', 'rev-parse']:
            return self.tree if args[-1] == 'HEAD^{tree}' else 'base'
        if args[:2] == ['git', 'log']:
            return self.authors
        if args[:2] == ['git', 'format-patch']:
            output = Path(args[args.index('--output-directory') + 1])
            output.mkdir()
            (output / '0000-cover-letter.patch').write_text('Subject: *** SUBJECT HERE ***\n\n*** BLURB HERE ***\n')
            for number in [1, 2]:
                (output / f'{number:04}-ours.patch').write_text('From: ' + prepare.OWNER + '\n')
        if args[0].endswith('get_maintainer.pl'):
            return 'Maintainer <maintainer@example.org>\ndri-devel@lists.freedesktop.org (open list)'
        return ''

    def invoke(self, flags):
        argv = ['prepare.py', '02', *flags]
        with patch.object(prepare, 'PROJECT', self.project), patch.object(prepare, 'run', self.fake_run), \
             patch.object(prepare.sys, 'argv', argv), patch.dict(os.environ, UPSTREAM_WORK_ROOT=str(self.root / 'cache')), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return prepare.main()

    def output(self):
        return next((self.root / 'cache').glob('linux-mail-*/outgoing'))

    def test_preview_unsigned_exports_only_our_two_followups(self):
        self.assertEqual(self.invoke(['--dry-run']), 0)
        self.assertFalse(any('--signoff' in args for args in self.calls))
        export = next(args for args in self.calls if args[:2] == ['git', 'format-patch'])
        self.assertEqual(export[-1], 'HEAD~2..HEAD')
        self.assertEqual(len(list(self.output().glob('*.patch'))), 3)
        self.assertFalse((self.output() / 'SEND_COMMAND.sh').exists())
        self.assertFalse(json.loads((self.output() / 'receipt.json').read_text())['mail_sent'])

    def test_human_prepare_signs_only_our_commits_and_never_sends(self):
        self.assertEqual(self.invoke(['--prepare', '--thread', 'latest@example.org']), 0)
        applications = [a for a in self.calls if a[0] == 'git' and 'am' in a]
        self.assertEqual(len(applications), 2)
        self.assertTrue(all(a[:4] == ['git', '-c', 'commit.gpgsign=false', 'am'] for a in applications))
        self.assertNotIn('--signoff', applications[0])
        self.assertIn('--signoff', applications[1])
        self.assertFalse(any(a[:2] == ['git', 'send-email'] for a in self.calls))
        command = (self.output() / 'SEND_COMMAND.sh').read_text()
        self.assertIn('maintainer@example.org', command)
        self.assertNotIn('third-party-a.patch', command)
        self.assertNotIn('third-party-b.patch', command)
        send_args = shlex.split(command.splitlines()[-1])
        self.assertEqual(send_args[send_args.index('--from') + 1], prepare.OWNER)

    def test_network_clone_is_shallow(self):
        self.invoke(['--dry-run'])
        clone = next(a for a in self.calls if a[:2] == ['git', 'clone'])
        self.assertIn('--depth=1', clone)
        self.assertNotIn('--shared', clone)

    def test_cached_source_clone_remains_shared(self):
        self.invoke(['--dry-run', '--source', str(self.root / 'cached-source')])
        clone = next(a for a in self.calls if a[:2] == ['git', 'clone'])
        self.assertIn('--shared', clone)
        self.assertNotIn('--depth=1', clone)

    def test_run_overrides_inherited_committer_identity(self):
        result = SimpleNamespace(stdout='done')
        with patch.dict(os.environ, GIT_COMMITTER_NAME='Other', GIT_COMMITTER_EMAIL='other@example.org'), \
             patch.object(prepare.subprocess, 'run', return_value=result) as execute:
            self.assertEqual(prepare.run(['git', 'version'], capture=True), 'done')
        env = execute.call_args.kwargs['env']
        self.assertEqual(env['GIT_COMMITTER_NAME'], 'Paul Junod')
        self.assertEqual(env['GIT_COMMITTER_EMAIL'], 'donujp@gmail.com')

    def test_prepare_requires_human_verified_thread_before_git(self):
        with self.assertRaises(SystemExit):
            self.invoke(['--prepare'])
        self.assertEqual(self.calls, [])

    def test_missing_patch_fails_before_git(self):
        (self.project / 'ours-b.patch').unlink()
        with self.assertRaises(ValueError):
            self.invoke(['--dry-run'])
        self.assertEqual(self.calls, [])

    def test_third_party_patch_refuses_before_adding_dco(self):
        (self.project / 'ours-a.patch').write_text(
            'From 0 Mon Sep 17 00:00:00 2001\nFrom: Cristian La Spina <cristian.laspina@kernel.srl>\nSubject: fixture\n\n')
        with self.assertRaises(ValueError):
            self.invoke(['--prepare', '--thread', 'cover@example.org'])
        self.assertEqual(self.calls, [])

    def test_wrong_tree_refuses_mail_export(self):
        self.tree = 'different'
        with self.assertRaises(ValueError):
            self.invoke(['--dry-run'])
        self.assertFalse(any(a[:2] == ['git', 'format-patch'] for a in self.calls))

    def test_third_party_author_refuses_mail_export(self):
        self.authors = 'Cristian La Spina <cristian.laspina@kernel.srl>\n' + prepare.OWNER
        with self.assertRaises(ValueError):
            self.invoke(['--dry-run'])
        self.assertFalse(any(a[:2] == ['git', 'format-patch'] for a in self.calls))

    def test_thread_cannot_inject_headers(self):
        with self.assertRaises(ValueError):
            prepare.message_id('cover@example.org\nCc: someone@example.org')

    def test_original_thread_parser_reads_message_id(self):
        reader = prepare.ThreadParser()
        reader.feed('<input type="hidden" name="msgid" value="cover@example.org">')
        self.assertEqual(prepare.message_id(reader.message_id), 'cover@example.org')


if __name__ == '__main__':
    unittest.main()
