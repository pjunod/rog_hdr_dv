#!/bin/sh
# Compile only. Generated files must live outside the source checkout.
set -eu
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output_dir=${1:?Usage: build.sh EXTERNAL_BUILD_DIRECTORY}
output_dir=$(python3 - "$output_dir" <<'PY'
import pathlib, sys
print(pathlib.Path(sys.argv[1]).resolve())
PY
)
checkout=$source_dir
repo_root=$(CDPATH= cd -- "$source_dir/../.." && pwd)
if test -e "$repo_root/.git" || test -f "$repo_root/AGENTS.md"; then checkout=$repo_root; fi
case "$output_dir/" in "$checkout/"*) echo 'Build directory must be outside the source checkout' >&2; exit 2;; esac
python3 - "$source_dir" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
pin = json.loads((root / 'source_manifest.json').read_text())
if hashlib.sha256((root / 'color-management-v1.xml').read_bytes()).hexdigest() != pin['sha256']:
    raise SystemExit('Pinned protocol digest mismatch')
PY
mkdir -p "$output_dir"
wayland-scanner client-header "$source_dir/color-management-v1.xml" "$output_dir/color-management-client.h"
wayland-scanner private-code "$source_dir/color-management-v1.xml" "$output_dir/color-management-protocol.c"
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -I"$output_dir" \
    "$source_dir/probe.c" "$output_dir/color-management-protocol.c" \
    -o "$output_dir/wayland-color-info" $(pkg-config --cflags --libs wayland-client)
