#!/bin/sh
# Scan a commit range and the tree at HEAD for private data before a push:
# LAN addresses, tokens, private keys and home-directory paths.
# Usage: scan_publication.sh RANGE   (for example main..HEAD)
# Prints matches and exits 1 if any added line matches. Synthetic redaction
# fixtures in tests/ (documentation addresses such as 10.42.1.2) are
# reported for review; they are expected.
cd "$(dirname "$0")/.." || exit 2
pat='192\.168\.|10\.[0-9]+\.[0-9]+\.[0-9]+|gh[opsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|BEGIN [A-Z ]*PRIVATE KEY|/Users/[A-Za-z]|/home/[a-z]+/(code|\.ssh)'
found=$(git log -p "$1" -- . ':(exclude)tools/scan_publication.sh' | grep -n -E "$pat" | grep '^[0-9]*:+' | grep -v '^[0-9]*:+++')
tree=$(git grep -n -I -E "$pat" HEAD -- . ':(exclude)tools/scan_publication.sh' ':(exclude)tests/')
[ -n "$found" ] && printf 'Added lines:\n%s\n' "$found"
[ -n "$tree" ] && printf 'Tree (outside tests/):\n%s\n' "$tree"
if [ -n "$found$tree" ]; then echo "scan: review the matches above"; exit 1; fi
echo "scan: clean"
