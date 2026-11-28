#!/usr/bin/env python3
"""One receipt per run directory: flip cadence, client feedback and VRR state.

usage: summarise_runs.py RUNS_DIR OUT.json [--skip S] [--window W]

Each run directory holds trace.txt and capture.json from
presentation_cadence.py capture, wayland-debug.log, run.json and
journal-flip.txt from run-one.sh. The run label's rate field (for example
`mpv-fs-24000-1001`) gives the source rate. Only derived numbers go into the
receipt; raw traces stay where they are.
"""

import importlib.util
import json
from fractions import Fraction
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cadence = load("presentation_cadence")
wayland = load("parse_wayland_debug")
KEEP = ("verdict", "reason", "frames", "expected_frames", "frame_deficit", "median_ms",
        "min_ms", "max_ms", "stdev_ms", "off_median", "long_holds", "irregular_every_s",
        "refresh_histogram", "cursor_only_flips", "arm_interval_ms")


def rate_of(label):
    match = re.search(r"-(\d+)(?:-(\d+))?$", label)
    return Fraction(int(match[1]), int(match[2] or 1))


def vrr_summary(capture, crtc="152"):
    states = [dict((str(c), v) for c, v in sample[1:]).get(crtc) for sample in
              capture.get("vrr_samples", [])]
    changes = [s for i, s in enumerate(states) if i == 0 or s != states[i - 1]]
    return {"sequence": changes, "fraction_on": round(states.count(1) / len(states), 3)
            if states else None}


def receipt(run, skip, window):
    label = run.name
    rate = rate_of(label)
    out = {"label": label, "rate": f"{rate.numerator}/{rate.denominator}"}
    with open(run / "trace.txt", errors="replace") as handle:
        flips = cadence.analyze(handle, rate, skip_s=skip, window_s=window)
    out["flips"] = {k: flips[k] for k in KEEP if k in flips}
    log = run / "wayland-debug.log"
    if log.exists():
        with open(log, errors="replace") as handle:
            client = wayland.report(wayland.parse(handle), rate, skip_s=skip, window_s=window)
        out["client"] = {k: client[k] for k in KEEP + ("discarded", "flags", "refresh_ns", "buffer_commit_interval_ms",
                                                         "surface") if k in client}
    capture = json.loads((run / "capture.json").read_text())
    out["vrr"] = vrr_summary(capture)
    out["page_flip_errors"] = sum(1 for _ in open(run / "journal-flip.txt")) \
        if (run / "journal-flip.txt").exists() else None
    out["run"] = json.loads((run / "run.json").read_text()) if (run / "run.json").exists() else {}
    return out


def main(argv):
    runs, target = Path(argv[1]), Path(argv[2])
    skip = float(argv[argv.index("--skip") + 1]) if "--skip" in argv else 6.0
    window = float(argv[argv.index("--window") + 1]) if "--window" in argv else 48.0
    receipts = [receipt(run, skip, window) for run in sorted(runs.iterdir())
                if (run / "trace.txt").exists()]
    target.write_text(json.dumps({"schema": "cadence-baseline-v1", "skip_s": skip,
                                  "window_s": window, "runs": receipts}, indent=1) + "\n")
    for r in receipts:
        f, c = r["flips"], r.get("client", {})
        commit = c.get("buffer_commit_interval_ms", {}).get("stdev")
        arm = f.get("arm_interval_ms", {}).get("stdev")
        print(f"{r['label']:26} vrr={r['vrr']['sequence']} n={f.get('frames')}/{f.get('expected_frames')} "
              f"flip med={f.get('median_ms')} sd={f.get('stdev_ms')} [{f.get('min_ms')}..{f.get('max_ms')}] "
              f"| commit sd={commit} arm sd={arm} present sd={c.get('stdev_ms')} | pf_err={r['page_flip_errors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
