#!/usr/bin/env python3
"""Hash exact post-strip package payload; not a signature or vendor receipt."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
P = 'rog-hdr-dm-experimental'
paths = sorted(p for folder in (stage / 'usr/lib' / P, stage / 'usr/libexec' / P,
                                stage / 'usr/share' / P) for p in folder.rglob('*') if p.is_file())
files = {str(p.relative_to(stage)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
elfs = ('usr/lib/rog-hdr-dm-experimental/libplacebo.so.368',
        'usr/libexec/rog-hdr-dm-experimental/open-dm-render')
notes = {rel: subprocess.check_output(['readelf', '-n', str(stage / rel)], text=True) for rel in elfs}
dynamic = subprocess.check_output(['readelf', '-d', str(stage / elfs[1])], text=True)
library_dynamic = subprocess.check_output(['readelf', '-d', str(stage / elfs[0])], text=True)
if any(token in line for line in library_dynamic.splitlines() if 'RPATH' in line or 'RUNPATH' in line
       for token in ('/work/', '/build/', '/Users/')):
    raise ValueError('installed library retained a build-tree runtime search path')
if '$ORIGIN/../../lib/rog-hdr-dm-experimental' not in dynamic or '/work/' in dynamic:
    raise ValueError('consumer must retain package-relative RUNPATH without a build root')
manifest = {'schema': 'hdr.abi368.package-installed.v1',
            'package': P, 'version': '0.1.0~abi368.1-0ubuntu26.10.1', 'abi': 368,
            'files': files, 'elf_notes': notes, 'consumer_dynamic': dynamic,
            'library_dynamic': library_dynamic,
            'scope': 'integrity manifest, not authentication; use authenticated package distribution'}
(stage / 'usr/share' / P / 'PACKAGE-INSTALLED.json').write_text(json.dumps(manifest, indent=2) + '\n')
