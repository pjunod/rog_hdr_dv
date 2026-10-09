#!/bin/sh
# Compile the synthetic server only; no display/server execution.
set -eu
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output_dir=${1:?Usage: build-fixture.sh EXTERNAL_BUILD_DIRECTORY}
"$source_dir/build.sh" "$output_dir"
wayland-scanner server-header "$source_dir/color-management-v1.xml" "$output_dir/color-management-server.h"
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -I"$output_dir" \
    "$source_dir/fixture.c" "$output_dir/color-management-protocol.c" \
    -o "$output_dir/color-info-fixture" $(pkg-config --cflags --libs wayland-server)
