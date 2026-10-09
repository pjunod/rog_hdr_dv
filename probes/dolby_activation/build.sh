#!/bin/sh
# Cross-compile only. This script never runs the executable or installs tools.
set -eu
probe_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output_dir=${1:?Usage: build.sh OUTPUT_DIRECTORY}
mkdir -p "$output_dir"
"${CXX:-x86_64-w64-mingw32-g++}" -std=c++17 -O2 -Wall -Wextra -Werror \
    -D_WIN32_WINNT=0x0602 -municode -static -static-libgcc -static-libstdc++ \
    -Wl,--no-insert-timestamp \
    "$probe_dir/probe.cpp" -o "$output_dir/dolby-activation-probe.exe" \
    -lole32 -lmfuuid -luuid
