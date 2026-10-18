"""Count retained reference-neutral coverage; never evaluate any candidate.

This checks whether marginal neutral residuals constrain a midtone driver.
Uses the existing <=1% reference-linear-BT2020 relative-spread definition.
Usage: python3 astra356_neutral_coverage.py OUTPUT.json
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_eval as f

report = {'schema': 'hdr.astra356.neutral-coverage.v1',
          'scope': 'input/reference population coverage only, no candidate or error metric',
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'shots': {}}
for shot in ('256', '714'):
    _, digest, rows, _ = f.load(shot)
    bins = collections.defaultdict(list)
    for xy, source, reference in rows:
        linear = tuple(f.pq_eotf(v) for v in reference)
        if f.strata_key(linear, f.lum(linear))[0] != 'neutral':
            continue
        y = f.lum(source)
        label = str(math.floor(math.log10(y))) if y > 0 else 'black'
        bins[label].append((xy, y, f.lum(linear)))
    result = {key: {'count': len(values),
                    'source_Y_range': [min(v[1] for v in values), max(v[1] for v in values)],
                    'reference_Y_range': [min(v[2] for v in values), max(v[2] for v in values)]}
              for key, values in sorted(bins.items())}
    report['shots'][shot] = {'input_receipt_sha256': digest, 'source_decades': result}
    print(shot, json.dumps(result), flush=True)
with Path(sys.argv[1]).open('x') as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write('\n')
