#!/bin/sh
# Scan a commit range and the tree at HEAD for private data before a push:
# LAN addresses, tokens, private keys and home-directory paths.
# Usage: scan_publication.sh RANGE   (for example main..HEAD)
# Prints matches and exits 1 if any added line matches. Synthetic redaction
# fixtures in tests/ (documentation addresses such as 10.42.1.2) are
# reported for review; they are expected.
set -u
[ "$#" -eq 1 ] || { echo 'Usage: scan_publication.sh RANGE' >&2; exit 2; }
case $1 in -*) echo 'Expected a revision range, not an option' >&2; exit 2;; esac
cd "$(dirname "$0")/.." || exit 2
pat='192\.168\.|10\.[0-9]+\.[0-9]+\.[0-9]+|gh[opsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|BEGIN [A-Z ]*PRIVATE KEY|/Users/[A-Za-z]|/home/[a-z]+/(code|\.ssh)'
git rev-list "$1" -- >/dev/null || exit 2
history=$(git log -p "$1" -- . ':(exclude)tools/scan_publication.sh') || exit 2
# No unchecked pipelines: a failed history read/filter must never mean clean.
found=$(printf '%s\n' "$history" | python3 -c 'import re, sys
pat = re.compile(sys.argv[1])
for n, line in enumerate(sys.stdin, 1):
    if line.startswith("+") and not line.startswith("+++") and pat.search(line):
        print(f"{n}:{line}", end="")' "$pat") || exit 2
tree_status=0
tree=$(git grep -n -I -E "$pat" HEAD -- . ':(exclude)tools/scan_publication.sh' ':(exclude)tests/') || tree_status=$?
case $tree_status in 0|1) ;; *) echo 'Tree scan failed' >&2; exit 2;; esac
[ -n "$found" ] && printf 'Added lines:\n%s\n' "$found"
[ -n "$tree" ] && printf 'Tree (outside tests/):\n%s\n' "$tree"
if [ -n "$found$tree" ]; then echo "scan: review the matches above"; exit 1; fi
echo "scan: clean"
