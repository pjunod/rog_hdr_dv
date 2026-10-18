#!/usr/bin/env python3
"""Install only private consumer/library and research source into debhelper stage."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
P = 'rog-hdr-dm-experimental'
stage = Path(sys.argv[1]).resolve()
lib = stage / 'usr/lib' / P
exe = stage / 'usr/libexec' / P
share = stage / 'usr/share' / P
for p in (lib, exe, share):
    p.mkdir(parents=True, exist_ok=True)
# Meson's runtime install strips its build-tree RUNPATH. Never copy the raw
# build library, whose dependency lookup may still point into the build tree.
subprocess.run(['meson', 'install', '-C', str(ROOT / 'build'), '--no-rebuild',
                '--tags', 'runtime', '--destdir', str(stage)], check=True)
if not (lib / 'libplacebo.so.368').is_file():
    raise ValueError('private runtime library not installed by Meson')
shutil.copy2(ROOT / 'build/package-consumer/open-dm-render', exe / 'open-dm-render')
shutil.copy2(ROOT / 'packaging' / P / 'run.py', exe / 'run.py')
for folder in ('tools/dolby_harness', 'wip/libplacebo-dm'):
    shutil.copytree(ROOT / folder, share / folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for name in ('LICENSES.md', 'PACKAGE-SOURCE.json'):
    shutil.copy2(ROOT / name, share / name)
for name in ('SQRTSUM_PQ_Y_POST.md', 'MAPPING_ABI368_DELIVERY.md'):
    (share / 'docs').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'docs' / name, share / 'docs' / name)
doc = stage / 'usr/share/doc' / P
doc.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / 'library/LICENSE', doc / 'COPYING.libplacebo')
for name in ('LICENSE-MIT', 'LICENSE-APACHE'):
    shutil.copy2(ROOT / 'library/3rdparty/fast_float' / name, doc / ('COPYING.fast_float-' + name))
# Public package build record is intentionally separate from the exact private
# compiler dependency evidence retained by build_consumer.py.
r = json.loads((ROOT / 'build/package-consumer/compile-private.json').read_text())
public = {k: r[k] for k in ('schema', 'status', 'library_identity', 'library_sources',
                            'consumer_source_sha256', 'build_recipe_sha256', 'compiler',
                            'binary_sha256', 'library_sha256', 'units_run', 'renders_run')}
public['scope'] = 'pre-strip compile identity; installed ELF hashes bound separately after dh_strip'
(share / 'PACKAGE-COMPILE.json').write_text(json.dumps(public, indent=2) + '\n')
