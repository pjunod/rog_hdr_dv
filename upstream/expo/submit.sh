#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$project_dir/../cinema/submit.py" "$project_dir" "$@"
