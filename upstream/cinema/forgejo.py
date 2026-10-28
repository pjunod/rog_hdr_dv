"""Prepared Forgejo transport for FFmpeg; never used by an unsigned dry run."""
from __future__ import annotations
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        return None


urlopen = build_opener(NoRedirect()).open


class Forgejo:
    def __init__(self, host: str, token_path: Path | None = None):
        if host != 'code.ffmpeg.org':
            raise ValueError('unsupported Forgejo submission host')
        self.host = host
        self.token_path = token_path or Path.home() / '.config/upstream' / (host + '.token')
        self.token = self.token_path.read_text().strip()
        if not self.token:
            raise ValueError('empty Forgejo token file')

    def api(self, method: str, path: str, body=None, allowed=(200, 201)):
        data = None if body is None else json.dumps(body).encode()
        request = Request('https://' + self.host + '/api/v1' + path, data=data,
                          method=method, headers={'Authorization': 'token ' + self.token,
                                                  'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            if error.code not in allowed:
                status = error.code
                error.close()
                raise ValueError(f'Forgejo {method} {path} failed (HTTP {status})') from None
            response = error
        with response:
            result = json.load(response)
            status = response.status
        if status not in allowed:
            raise ValueError(f'Forgejo {method} {path} failed (HTTP {status})')
        return status, result

    def login(self) -> str:
        return self.api('GET', '/user')[1]['login']

    def ensure_fork(self, repository: str) -> str:
        fork = 'pjunod/' + repository.rsplit('/', 1)[1]
        status, metadata = self.api('GET', '/repos/' + fork, allowed=(200, 404))
        if status == 404:
            self.api('POST', '/repos/' + repository + '/forks', {'name': fork.split('/', 1)[1]})
            for _ in range(30):
                status, metadata = self.api('GET', '/repos/' + fork, allowed=(200, 404))
                if status == 200:
                    break
                time.sleep(2)
            else:
                raise ValueError('fork import did not become available')
        parent = metadata.get('parent', {}).get('full_name', '')
        if not metadata.get('fork') or parent.lower() != repository.lower():
            raise ValueError('destination is not a fork of the recorded FFmpeg upstream')
        return 'https://' + self.host + '/' + fork + '.git'

    def pull_requests(self, repository: str, branch: str) -> list[dict]:
        found = []
        fork = 'pjunod/' + repository.rsplit('/', 1)[1]
        for page in range(1, 101):
            query = urlencode({'state': 'all', 'limit': 100, 'page': page})
            rows = self.api('GET', '/repos/' + repository + '/pulls?' + query)[1]
            if not rows:
                return found
            for pr in rows:
                head = pr.get('head') or {}
                if head.get('ref') != branch:
                    continue
                head_repository = (head.get('repo') or {}).get('full_name')
                if not head_repository:
                    raise ValueError('matching historical PR has no source repository identity; inspect before resubmission')
                if head_repository.lower() == fork.lower():
                    found.append({'number': pr['number'], 'url': pr['html_url'],
                                  'state': 'MERGED' if pr.get('merged') else pr['state'].upper(),
                                  'baseRefName': pr['base']['ref']})
        raise ValueError('PR listing exceeded its bounded pagination; inspect manually')

    def create(self, repository: str, branch: str, target: str, title: str, body: Path, draft: bool):
        if draft:
            title = 'WIP: ' + title
        result = self.api('POST', '/repos/' + repository + '/pulls',
                          {'base': target, 'head': 'pjunod:' + branch,
                           'title': title, 'body': body.read_text()})[1]
        print(result['html_url'])

    def git_environment(self, checkout: Path) -> dict[str, str]:
        askpass = checkout / '.git/upstream-forgejo-askpass'
        askpass.write_text('#!/bin/sh\ncase "$1" in Username*) printf "%s\\n" pjunod ;; *) printf "%s\\n" "$UPSTREAM_FORGEJO_TOKEN" ;; esac\n')
        askpass.chmod(0o700)
        return {'GIT_ASKPASS': str(askpass), 'GIT_TERMINAL_PROMPT': '0',
                'UPSTREAM_FORGEJO_TOKEN': self.token}
