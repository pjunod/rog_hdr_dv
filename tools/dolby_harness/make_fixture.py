#!/usr/bin/env python3
"""Create a PUBLIC metadata-free asymmetric PQ fixture; never create an RPU."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args = parser.parse_args()
    root = Path(args.directory)
    root.mkdir(parents=True, exist_ok=False)
    # Literal normalized PQ code values, not physical target measurements.
    samples = (0, 0, 0, 0.2, 0.1, 0.05, 0.5, 0.5, 0.5, 0.65, 0.4, 0.2)
    raw = struct.pack('<12f', *samples)
    (root / 'frame.f32').write_bytes(raw)
    prim = [0.708, 0.292, 0.170, 0.797, 0.131, 0.046, 0.3127, 0.3290]
    obj = {'schema': 1,
           'frame': {'input': {'file': 'frame.f32', 'sha256': hashlib.sha256(raw).hexdigest()},
                     'width': 2, 'height': 2, 'index': 0, 'pts': {'num': 0, 'den': 24},
                     'content_id': 'public-asymmetric-pq-stage1-v1'},
           'source': {'system': 'rgb', 'transfer': 'pq', 'primaries': 'bt2020',
                      'range': 'full', 'bit_depth': 10, 'layout': 'c3-f32le', 'orientation': 'top-left',
                      'mastering': {'min_nits': 0, 'max_nits': 10000, 'primaries': prim}},
           'target': {'id': 'synthetic-bt2020-10000', 'min_nits': 0, 'max_nits': 10000, 'primaries': prim},
           'metadata': None}
    (root / 'frame.json').write_text(json.dumps(obj, indent=2) + '\n')
    print(root / 'frame.json')


if __name__ == '__main__':
    main()
