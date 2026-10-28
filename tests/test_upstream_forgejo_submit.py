"""FFmpeg Forgejo API and credential transport tests; no real service calls."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('forgejo_transport', ROOT / 'upstream/cinema/forgejo.py')
forgejo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forgejo)


class Response(io.BytesIO):
    def __init__(self, value, status=200):
        super().__init__(json.dumps(value).encode())
        self.status = status


class ForgejoTransportTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work/cinema/forgejo-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        token = self.root / 'token'
        token.write_text('fixture-sensitive-token\n')
        self.client = forgejo.Forgejo('code.ffmpeg.org', token)

    def test_token_is_header_only_and_not_in_request_url(self):
        with patch.object(forgejo, 'urlopen', return_value=Response({'login': 'pjunod'})) as call:
            self.assertEqual(self.client.login(), 'pjunod')
        request = call.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'), 'token fixture-sensitive-token')
        self.assertNotIn('fixture-sensitive-token', request.full_url)
        self.assertEqual(request.full_url, 'https://code.ffmpeg.org/api/v1/user')

    def test_unsupported_host_refuses_before_credentials(self):
        with self.assertRaises(ValueError):
            forgejo.Forgejo('another.example', self.root / 'does-not-exist')

    def test_existing_wrong_parent_fork_is_preserved(self):
        result = {'fork': True, 'parent': {'full_name': 'Other/Repo'}}
        with patch.object(self.client, 'api', return_value=(200, result)) as call:
            with self.assertRaises(ValueError): self.client.ensure_fork('FFmpeg/FFmpeg')
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.args[0], 'GET')

    def test_create_fork_then_verify_canonical_parent(self):
        result = {'fork': True, 'parent': {'full_name': 'FFmpeg/FFmpeg'}}
        with patch.object(self.client, 'api', side_effect=[(404, {}), (201, result), (200, result)]) as call:
            self.assertEqual(self.client.ensure_fork('FFmpeg/FFmpeg'),
                             'https://code.ffmpeg.org/pjunod/FFmpeg.git')
        self.assertEqual(call.call_args_list[1].args[:2], ('POST', '/repos/FFmpeg/FFmpeg/forks'))

    def test_pr_listing_checks_exact_fork_and_branch_across_pages(self):
        row = {'number': 7, 'html_url': 'url', 'state': 'closed', 'merged': True,
               'head': {'ref': 'upstream/fix', 'repo': {'full_name': 'pjunod/FFmpeg'}},
               'base': {'ref': 'master'}}
        other = dict(row, number=8, head={'ref': 'upstream/fix', 'repo': {'full_name': 'someone/FFmpeg'}})
        with patch.object(self.client, 'api', side_effect=[(200, [other]), (200, [row]), (200, [])]) as call:
            found = self.client.pull_requests('FFmpeg/FFmpeg', 'upstream/fix')
        self.assertEqual([x['number'] for x in found], [7])
        self.assertEqual(found[0]['state'], 'MERGED')
        self.assertIn('state=all', call.call_args_list[0].args[1])
        self.assertIn('page=3', call.call_args.args[1])

    def test_missing_historical_source_repository_refuses_resubmission(self):
        row = {'head': {'ref': 'upstream/fix', 'repo': None}}
        with patch.object(self.client, 'api', return_value=(200, [row])):
            with self.assertRaises(ValueError):
                self.client.pull_requests('FFmpeg/FFmpeg', 'upstream/fix')

    def test_askpass_file_contains_no_token(self):
        checkout = self.root / 'checkout'
        (checkout / '.git').mkdir(parents=True)
        env = self.client.git_environment(checkout)
        askpass = Path(env['GIT_ASKPASS'])
        self.assertNotIn(self.client.token, askpass.read_text())
        self.assertEqual(askpass.stat().st_mode & 0o777, 0o700)
        self.assertEqual(env['UPSTREAM_FORGEJO_TOKEN'], self.client.token)

    def test_real_api_transport_does_not_follow_authorized_redirect(self):
        hits = []
        class Target(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.headers.get('Authorization'))
                self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
            def log_message(self, *args): pass
        target = ThreadingHTTPServer(('127.0.0.1', 0), Target)
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header('Location', f'http://localhost:{target.server_port}/elsewhere')
                self.end_headers()
            def log_message(self, *args): pass
        source = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
        threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in [source, target]]
        for thread in threads: thread.start()
        try:
            request = Request(f'http://127.0.0.1:{source.server_port}/api',
                              headers={'Authorization': 'token fixture-sensitive-token'})
            with self.assertRaises(HTTPError) as raised:
                forgejo.urlopen(request, timeout=5)
            self.assertEqual(raised.exception.code, 302)
            raised.exception.close()
            self.assertEqual(hits, [])
        finally:
            for server in [source, target]: server.shutdown(); server.server_close()
            for thread in threads: thread.join()

    def test_create_pr_uses_description_file_and_exact_target(self):
        body = self.root / 'DESCRIPTION.md'
        body.write_text('Prepared with AI assistants; human review pending.\n')
        with patch.object(self.client, 'api', return_value=(201, {'html_url': 'url'})) as call:
            with patch('sys.stdout', new_callable=io.StringIO):
                self.client.create('FFmpeg/FFmpeg', 'upstream/fix', 'master', 'Fix', body, False)
        method, path, payload = call.call_args.args
        self.assertEqual((method, path), ('POST', '/repos/FFmpeg/FFmpeg/pulls'))
        self.assertEqual(payload['head'], 'pjunod:upstream/fix')
        self.assertEqual(payload['base'], 'master')
        self.assertEqual(payload['body'], body.read_text())


if __name__ == '__main__': unittest.main()
