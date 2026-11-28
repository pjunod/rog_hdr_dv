#!/usr/bin/env python3
"""Per-commit presented times from a client's WAYLAND_DEBUG=1 log.

The client protocol layer of the cadence measurement (design section 4.1).
It pairs each `wp_presentation.feedback` request with its surface, records
`presented` times, refresh and flags or `discarded`, picks the video surface
(the one with the most presented feedback, unless --surface is given), and
reports with the same metrics and verdict as presentation_cadence.analyze.
Stdlib only; the player is not modified.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import statistics
import sys

_SPEC = importlib.util.spec_from_file_location(
    "presentation_cadence", Path(__file__).resolve().with_name("presentation_cadence.py"))
cadence = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cadence)

MESSAGE = re.compile(
    r"^\[\s*(?P<ts>[\d:.]+)\]\s+(?:\{[^}]*\}\s+)?(?P<request>-> )?"
    r"(?P<iface>[A-Za-z_0-9]+)[#@](?P<id>\d+)\.(?P<msg>\w+)\((?P<args>.*)\)\s*$")
OBJECT = re.compile(r"(?:new id )?(?P<iface>[A-Za-z_0-9]+)[#@](?P<id>\d+)")
FLAGS = {1: "vsync", 2: "hw_clock", 4: "hw_completion", 8: "zero_copy"}


def numbers(args):
    return [int(value) for value in re.findall(r"(?<![#@\w])-?\d+(?![#@\w])", args)]


def wall_seconds(stamp):
    """The log prefix: [HH:MM:SS.us] (wall clock) or [ms.us] (older libwayland)."""
    parts = stamp.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(stamp) / 1000.0


def parse(lines):
    """Return {surface: {"presented", "discarded", "commits", "buffer_commits"}}.

    Only feedback requested in a commit that attached a buffer counts as a
    presentation: Mesa's Vulkan WSI also sends an empty FIFO-barrier commit
    per frame, whose feedback reports the same picture again. `buffer_commits`
    holds the client-side time of each buffer commit (wall clock, for
    intervals only).
    """
    surfaces = {}
    feedback = {}       # feedback object id -> surface id
    pending = {}        # surface -> {"attach": bool, "feedback": [ids]}
    for line in lines:
        match = MESSAGE.match(line)
        if not match:
            continue
        iface, obj, msg, args = match["iface"], int(match["id"]), match["msg"], match["args"]
        if match["request"]:
            if iface == "wl_surface" and msg == "attach" and "nil" not in args:
                pending.setdefault(obj, {"attach": False, "feedback": []})["attach"] = True
            elif iface == "wl_surface" and msg == "commit":
                block = pending.pop(obj, {"attach": False, "feedback": []})
                data = surfaces.setdefault(obj, _empty())
                data["commits"] += 1
                if block["attach"]:
                    data["buffer_commits"].append(wall_seconds(match["ts"]))
                for fb in block["feedback"]:
                    if not block["attach"]:
                        feedback.pop(fb, None)
            elif iface == "wp_presentation" and msg == "feedback":
                objects = {m["iface"]: int(m["id"]) for m in OBJECT.finditer(args)}
                surface = objects.get("wl_surface")
                fb = objects.get("wp_presentation_feedback")
                if surface is not None and fb is not None:
                    feedback[fb] = surface
                    pending.setdefault(surface, {"attach": False, "feedback": []})["feedback"].append(fb)
                    surfaces.setdefault(surface, _empty())
            continue
        if iface != "wp_presentation_feedback" or obj not in feedback:
            continue
        surface = feedback[obj]
        if msg == "presented":
            sec_hi, sec_lo, nsec, refresh, _seq_hi, _seq_lo, flags = numbers(args)[:7]
            when = ((sec_hi << 32) | sec_lo) + nsec / 1e9
            surfaces[surface]["presented"].append((when, refresh, flags))
            del feedback[obj]
        elif msg == "discarded":
            surfaces[surface]["discarded"] += 1
            del feedback[obj]
    return surfaces


def _empty():
    return {"presented": [], "discarded": 0, "commits": 0, "buffer_commits": []}


def report(surfaces, rate, surface=None, skip_s=5.0, window_s=None,
           tolerance_ms=cadence.DEFAULT_TOLERANCE_MS):
    if surface is None:
        candidates = [s for s in surfaces if surfaces[s]["presented"]]
        if not candidates:
            return {"verdict": "incomplete", "reason": "no presented feedback in the log",
                    "surfaces": {str(s): v["commits"] for s, v in surfaces.items()}}
        surface = max(candidates, key=lambda s: len(surfaces[s]["presented"]))
    data = surfaces.get(surface, _empty())
    rows = sorted(data["presented"])
    if rows:
        begin = rows[0][0] + skip_s
        end = begin + window_s if window_s else float("inf")
        rows = [row for row in rows if begin <= row[0] <= end]
    result = cadence.summarise([row[0] for row in rows], [], rate, tolerance_ms,
                               source="wayland-feedback")
    flags = Counter()
    for _, _, value in rows:
        for bit, name in FLAGS.items():
            if value & bit:
                flags[name] += 1
    commits = data["buffer_commits"]
    if len(commits) > 20:
        trim = commits[len(commits) // 10: -(len(commits) // 10)]
        gaps = [1000 * (b - a) for a, b in zip(trim, trim[1:]) if 0 < b - a < 3600]
        if gaps:
            result["buffer_commit_interval_ms"] = {
                "median": round(statistics.median(gaps), 4),
                "stdev": round(statistics.pstdev(gaps), 4),
                "min": round(min(gaps), 3), "max": round(max(gaps), 3)}
    result.update({
        "surface": surface,
        "commits": data["commits"],
        "discarded": data["discarded"],
        "flags": dict(flags),
        "refresh_ns": dict(Counter(str(row[1]) for row in rows).most_common(4)),
        "other_surfaces": {str(s): len(v["presented"]) for s, v in surfaces.items()
                           if s != surface and v["presented"]},
    })
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log", help="stderr of the player run with WAYLAND_DEBUG=1")
    parser.add_argument("--rate", type=cadence.parse_rate, required=True)
    parser.add_argument("--surface", type=int, help="wl_surface id (default: most presented)")
    parser.add_argument("--skip", type=float, default=5.0)
    parser.add_argument("--window", type=float)
    parser.add_argument("--tolerance-ms", type=float, default=cadence.DEFAULT_TOLERANCE_MS)
    args = parser.parse_args(argv)
    with open(args.log, errors="replace") as handle:
        surfaces = parse(handle)
    result = report(surfaces, args.rate, args.surface, args.skip, args.window,
                    args.tolerance_ms)
    print(json.dumps(result, indent=1))
    return 0 if result["verdict"] == "even" else 1


if __name__ == "__main__":
    sys.exit(main())
