#!/usr/bin/env python3
"""Per-frame presentation cadence from i915 tracepoints, for any player.

`capture` (root, on the laptop) records page-flip completion, plane updates
and, optionally, the per-refresh pipe CRC into a private tracefs instance.
`analyze` turns that trace into per-frame presentation durations and a
verdict. `model` predicts the cadence a source rate gets under fixed refresh
or variable refresh with the hardware's own repeat at the VRR floor, so a
measurement can be compared with what the timing alone allows. Stdlib only.
"""

import argparse
from collections import Counter
from fractions import Fraction
import json
import math
import os
import random
from pathlib import Path
import re
import signal
import statistics
import sys
import threading
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRACEFS = Path("/sys/kernel/tracing")
DRI_DEBUGFS = Path("/sys/kernel/debug/dri")
EVENTS = (
    "i915/intel_crtc_flip_done",
    "i915/intel_plane_update_arm",
    "i915/intel_pipe_crc",
    "drm/drm_vblank_event",
)
DEFAULT_TOLERANCE_MS = 0.75
LINE = re.compile(
    r"^\s*(?P<task>.+?)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+(?:\S+\s+)?"
    r"(?P<ts>\d+\.\d+):\s+(?P<event>\w+):\s+(?P<body>.*)$")
PIPE = re.compile(r"\bpipe (?P<pipe>[A-Z])\b")
FRAME = re.compile(r"\bframe=(?P<frame>\d+)")
VBLANK = re.compile(r"crtc=(?P<crtc>\d+), seq=(?P<seq>\d+), time=(?P<time>-?\d+)")
CRC = re.compile(r"\bcrc=(?P<crc>[0-9a-f]{8}(?: [0-9a-f]{8})*)")
PLANE = re.compile(r"pipe [A-Z], (?P<plane>[^,]+), frame=")


def parse_rate(text):
    """Exact source rate: an integer or N/D; decimals such as 23.976 are refused."""
    if not re.fullmatch(r"\d+(?:/\d+)?", text):
        raise argparse.ArgumentTypeError(
            f"rate {text!r} must be an integer or N/D (use 24000/1001, not 23.976)")
    rate = Fraction(text)
    if not 1 <= rate <= 1000:
        raise argparse.ArgumentTypeError(f"rate {text} outside 1..1000")
    return rate


def parse_trace(lines, pipe="A"):
    """Return flips, plane updates and CRC refreshes for one pipe, in time order.

    A flip is an `intel_crtc_flip_done` where the kernel emits it. On display
    version 14 it does not, and the page-flip completion is the
    `drm_vblank_event` delivered for the commit: its `time` is the hardware
    vblank timestamp (CLOCK_MONOTONIC ns) the compositor also receives, and
    `seq` the vblank count, so it is used instead (crtc index = pipe letter).
    """
    flips, vblanks, planes, crcs = [], [], [], []
    crtc_index = ord(pipe) - ord("A")
    for line in lines:
        match = LINE.match(line)
        if not match:
            continue
        event, body = match["event"], match["body"]
        if event == "drm_vblank_event":
            found = VBLANK.search(body)
            if found and int(found["crtc"]) == crtc_index:
                vblanks.append((int(found["time"]) / 1e9, int(found["seq"])))
            continue
        found = PIPE.search(body)
        if not found or found["pipe"] != pipe:
            continue
        when = float(match["ts"])
        frame = FRAME.search(body)
        frame = int(frame["frame"]) if frame else None
        if event == "intel_crtc_flip_done":
            flips.append((when, frame))
        elif event == "intel_plane_update_arm":
            plane = PLANE.search(body)
            planes.append((when, plane["plane"].strip() if plane else "?"))
        elif event == "intel_pipe_crc":
            value = CRC.search(body)
            if value:
                crcs.append((when, frame, value["crc"]))
    if not flips and vblanks:
        flips = latched_flips(sorted(vblanks), planes)
        planes = []   # already applied: cursor-only arms were never flips
    return flips, planes, crcs


def latched_flips(vblanks, planes):
    """Presentations from plane arms: each arm is shown at the next vblank.

    Mutter also receives vblank events that carry no new picture (a refresh
    the panel repeated on its own, or a wait with no commit), so a vblank is
    a flip only when a non-cursor plane was armed since the previous one.
    """
    arms = [when for when, name in planes if "cursor" not in name]
    flips, index = [], 0
    for when, seq in vblanks:
        armed = False
        while index < len(arms) and arms[index] <= when:
            armed = True
            index += 1
        if armed:
            flips.append((when, seq))
    return flips


def parse_trace_arms(lines, pipe="A"):
    """(time, plane) of every plane arm on the pipe: when the compositor committed."""
    arms = []
    for line in lines:
        match = LINE.match(line)
        if match and match["event"] == "intel_plane_update_arm":
            found = PIPE.search(match["body"])
            plane = PLANE.search(match["body"])
            if found and found["pipe"] == pipe:
                arms.append((float(match["ts"]), plane["plane"].strip() if plane else "?"))
    return arms


def content_flips(flips, planes):
    """Drop flips whose commit touched only cursor planes (no new picture)."""
    kept, cursor_only, index = [], 0, 0
    for when, frame in flips:
        touched = set()
        while index < len(planes) and planes[index][0] <= when:
            touched.add(planes[index][1])
            index += 1
        if touched and all("cursor" in name for name in touched):
            cursor_only += 1
            continue
        kept.append((when, frame))
    return kept, cursor_only


def crc_presentations(crcs):
    """Collapse per-refresh CRCs into (start, refreshes, crc) content segments."""
    segments, lost = [], 0
    for when, frame, crc in crcs:
        if segments and frame is not None and segments[-1][3] is not None:
            gap = (frame - segments[-1][3]) & 0xFFFFFFFF
            if gap != 1:
                lost += max(gap - 1, 0)
        if segments and segments[-1][2] == crc:
            start, count, value, _ = segments[-1]
            segments[-1] = (start, count + 1, value, frame)
        else:
            segments.append((when, 1, crc, frame))
    return [(start, count, crc) for start, count, crc, _ in segments], lost


def summarise(starts, refreshes, rate, tolerance_ms, repeats_returning=0,
              lost_refreshes=0, source="flips"):
    """Metrics and verdict for presentation start times of successive frames."""
    period_ms = 1000.0 / float(rate)
    durations = [1000.0 * (b - a) for a, b in zip(starts, starts[1:])]
    report = {
        "source": source,
        "rate": f"{rate.numerator}/{rate.denominator}",
        "nominal_ms": round(period_ms, 4),
        "tolerance_ms": tolerance_ms,
        "frames": len(durations),
    }
    if len(durations) < 2:
        report["verdict"] = "incomplete"
        report["reason"] = "fewer than three presentations in the window"
        return report
    span_s = starts[-1] - starts[0]
    median = statistics.median(durations)
    off = [i for i, d in enumerate(durations) if abs(d - median) > tolerance_ms]
    long_holds = [i for i, d in enumerate(durations) if d > 1.5 * period_ms]
    expected = span_s * float(rate)
    histogram = Counter(round(d, 1) for d in durations)
    report.update({
        "span_s": round(span_s, 3),
        "expected_frames": round(expected, 1),
        "frame_deficit": round(expected - len(durations), 1),
        "median_ms": round(median, 4),
        "min_ms": round(min(durations), 4),
        "max_ms": round(max(durations), 4),
        "stdev_ms": round(statistics.pstdev(durations), 4),
        "off_median": len(off),
        "long_holds": len(long_holds),
        "returning_content": repeats_returning,
        "lost_refreshes": lost_refreshes,
        "duration_histogram_ms": {str(k): v for k, v in sorted(histogram.items())[:24]},
    })
    if refreshes:
        report["refresh_histogram"] = {
            str(k): v for k, v in sorted(Counter(refreshes).items())}
    if off:
        gaps = [starts[b] - starts[a] for a, b in zip(off, off[1:])]
        report["irregular_every_s"] = round(statistics.median(gaps), 3) if gaps else None
        report["first_irregular_s"] = round(starts[off[0]] - starts[0], 3)
    rate_ok = abs(median - period_ms) <= tolerance_ms
    if lost_refreshes:
        report["verdict"] = "incomplete"
        report["reason"] = f"{lost_refreshes} refreshes missing from the CRC stream"
    elif not off and rate_ok and not long_holds and not repeats_returning:
        report["verdict"] = "even"
    else:
        report["verdict"] = "uneven"
        reasons = []
        if not rate_ok:
            reasons.append(f"median {median:.3f} ms differs from the {period_ms:.3f} ms source period")
        if off:
            reasons.append(f"{len(off)} frames off the median by more than {tolerance_ms} ms")
        if long_holds:
            reasons.append(f"{len(long_holds)} holds longer than 1.5 source periods")
        if repeats_returning:
            reasons.append(f"{repeats_returning} earlier pictures shown again")
        report["reason"] = "; ".join(reasons)
    return report


PATTERNS = 16


def decode_patterns(segments, calibration):
    """Map CRC segments to fixture pattern indices and count sequence faults.

    The fixtures show pattern n mod PATTERNS for source frame n, with an
    optional all-white sync flash replacing one frame per second. Successive
    segments must advance by exactly one pattern; a larger step is skipped
    source frames, a backward step is an earlier frame shown again, and a CRC
    outside the calibration is a picture the fixture does not contain.
    """
    lookup = {crc: index for index, crc in enumerate(calibration["patterns"])}
    flash = calibration.get("flash")
    skipped = backward = foreign = flashes = 0
    previous = None   # pattern index of the last known segment
    pending = 0       # segments since then that were flashes
    for _, _, crc in segments:
        if crc == flash:
            flashes += 1
            pending += 1
            continue
        index = lookup.get(crc)
        if index is None:
            foreign += 1
            continue
        if previous is not None:
            # A flash stands in for one source frame, so it consumes one step.
            step = (index - previous - pending) % PATTERNS
            if 0 < step < PATTERNS // 2:
                skipped += step - 1
            else:
                backward += 1   # same or earlier pattern after an interruption
        previous, pending = index, 0
    return {"skipped_frames": skipped, "shown_again": backward,
            "foreign_pictures": foreign, "sync_flashes": flashes}


def analyze(lines, rate, pipe="A", skip_s=5.0, window_s=None,
            tolerance_ms=DEFAULT_TOLERANCE_MS, calibration=None):
    lines_cache = list(lines)
    flips, planes, crcs = parse_trace(lines_cache, pipe)
    flips, cursor_only = content_flips(flips, planes)
    decoded = None
    if crcs:
        segments, lost = crc_presentations(crcs)
        if segments:
            begin = segments[0][0] + skip_s
            end = begin + window_s if window_s else math.inf
            segments = [seg for seg in segments if begin <= seg[0] <= end]
        returning = 0
        if calibration:
            decoded = decode_patterns(segments, calibration)
            returning = decoded["shown_again"]
        rows = [(start, count) for start, count, _ in segments]
        source = "crc"
    else:
        lost, returning = 0, 0
        frames = [frame for _, frame in flips]
        rows = [(when, ((b - a) & 0xFFFFFFFF) if a is not None and b is not None else None)
                for (when, a), b in zip(flips, frames[1:] + [None])]
        if rows:
            begin = rows[0][0] + skip_s
            end = begin + window_s if window_s else math.inf
            rows = [row for row in rows if begin <= row[0] <= end]
        source = "flips"
    starts = [row[0] for row in rows]
    refreshes = [row[1] for row in rows[:-1] if row[1] is not None]
    report = summarise(starts, refreshes, rate, tolerance_ms, returning, lost, source)
    report["pipe"] = pipe
    report["cursor_only_flips"] = cursor_only
    arms = [when for when, name in parse_trace_arms(lines_cache) if "cursor" not in name] \
        if lines_cache else []
    if len(arms) > 20:
        trim = arms[len(arms) // 10: -(len(arms) // 10)]
        gaps = [1000 * (b - a) for a, b in zip(trim, trim[1:])]
        report["arm_interval_ms"] = {"median": round(statistics.median(gaps), 4),
                                     "stdev": round(statistics.pstdev(gaps), 4),
                                     "min": round(min(gaps), 3), "max": round(max(gaps), 3)}
    report["crc_refreshes"] = len(crcs)
    if crcs:
        report["distinct_crcs"] = len({crc for _, _, crc in crcs})
        report["content_identity"] = "decoded" if calibration else "change-only"
    if decoded:
        report.update(decoded)
        if report["verdict"] == "even" and (decoded["skipped_frames"] or decoded["foreign_pictures"]):
            report["verdict"] = "uneven"
            report["reason"] = (f"{decoded['skipped_frames']} skipped source frames, "
                                f"{decoded['foreign_pictures']} pictures outside the fixture")
    return report


def calibrate(lines, first_pattern=0, pipe="A", flash_position=None):
    """Calibration from a frame-stepped capture: distinct CRCs in step order."""
    _, _, crcs = parse_trace(lines, pipe)
    segments, _ = crc_presentations(crcs)
    order = []
    for _, _, crc in segments:
        if not order or order[-1] != crc:
            order.append(crc)
    flash = None
    if flash_position is not None:
        flash = order[flash_position]   # the flash stands in for that step's frame
    patterns = [None] * PATTERNS
    for k, crc in enumerate(order):
        if k == flash_position:
            continue
        index = (first_pattern + k) % PATTERNS
        if patterns[index] is None:
            patterns[index] = crc
        elif patterns[index] != crc:
            raise SystemExit(f"step {k} does not repeat the cycle; was a frame skipped while stepping?")
    if None in patterns:
        raise SystemExit(f"only {PATTERNS - patterns.count(None)} patterns seen; step through all {PATTERNS}")
    if len(set(patterns)) != PATTERNS or flash in patterns:
        raise SystemExit("two pictures share a CRC; the pipe CRC cannot tell them apart")
    return {"schema": "cadence-crc-calibration-v1", "pipe": pipe,
            "patterns": patterns, "flash": flash}


def model(rate, seconds, refresh_hz=None, vrr_min_hz=None, vrr_max_hz=None,
          multiplier=1, phase=0.37, jitter_ms=0.0, seed=1):
    """Presentation starts of each source frame under a timing model.

    Fixed refresh: a frame first appears at the first refresh at or after its
    due time. VRR: a flip latches once the minimum frame time has passed since
    the last refresh began; with no flip by the maximum frame time the
    hardware repeats the current picture, and a flip then waits for that
    repeat's minimum frame time. `multiplier` > 1 models a compositor that
    re-presents each frame at an even 1/multiplier of the source period.
    `jitter_ms` adds a uniform, seeded error to each commit time.
    """
    noise = random.Random(seed)
    period = 1.0 / float(rate)
    count = int(seconds * float(rate))
    starts = []
    if refresh_hz:
        tick = 1.0 / refresh_hz
        for k in range(count):
            due = k * period + phase * tick
            starts.append(math.ceil(due / tick - 1e-9) * tick)
        return starts
    shortest, longest = 1.0 / vrr_max_hz, 1.0 / vrr_min_hz
    begun = -longest
    for k in range(count):
        for step in range(multiplier):
            due = k * period + step * period / multiplier
            due += noise.uniform(-jitter_ms, jitter_ms) / 1000.0
            while due - begun > longest + 1e-12:
                begun += longest          # hardware repeat at the VRR floor
            start = max(due, begun + shortest)
            begun = start
            if step == 0:
                starts.append(start)
    return starts


def lfc_multiplier(rate, vrr_min_hz, vrr_max_hz, margin=0.1):
    """Smallest even repeat count keeping the refresh clear of both VRR limits."""
    for k in range(1, 64):
        hz = float(rate) * k
        if vrr_min_hz * (1 + margin) <= hz <= vrr_max_hz * (1 - margin / 10):
            return k
    return None


def crtc_properties(card=0, crtc_id=None):
    """Read-only libdrm query of CRTC properties: {crtc_id: {name: value}}.

    Uses the unprivileged property ioctls on /dev/dri/cardN; it does not take
    DRM master and changes nothing. Returns {} when libdrm is unavailable.
    """
    import ctypes
    import ctypes.util

    class Res(ctypes.Structure):
        _fields_ = [("count_fbs", ctypes.c_int), ("fbs", ctypes.POINTER(ctypes.c_uint32)),
                    ("count_crtcs", ctypes.c_int), ("crtcs", ctypes.POINTER(ctypes.c_uint32)),
                    ("count_connectors", ctypes.c_int), ("connectors", ctypes.POINTER(ctypes.c_uint32)),
                    ("count_encoders", ctypes.c_int), ("encoders", ctypes.POINTER(ctypes.c_uint32)),
                    ("min_width", ctypes.c_uint32), ("max_width", ctypes.c_uint32),
                    ("min_height", ctypes.c_uint32), ("max_height", ctypes.c_uint32)]

    class Props(ctypes.Structure):
        _fields_ = [("count_props", ctypes.c_uint32), ("props", ctypes.POINTER(ctypes.c_uint32)),
                    ("prop_values", ctypes.POINTER(ctypes.c_uint64))]

    class Prop(ctypes.Structure):
        _fields_ = [("prop_id", ctypes.c_uint32), ("flags", ctypes.c_uint32),
                    ("name", ctypes.c_char * 32)]

    name = ctypes.util.find_library("drm")
    if not name:
        return {}
    drm = ctypes.CDLL(name)
    drm.drmModeGetResources.restype = ctypes.POINTER(Res)
    drm.drmModeObjectGetProperties.restype = ctypes.POINTER(Props)
    drm.drmModeGetProperty.restype = ctypes.POINTER(Prop)
    fd = os.open(f"/dev/dri/card{card}", os.O_RDONLY | os.O_CLOEXEC)
    result = {}
    try:
        res = drm.drmModeGetResources(fd)
        if not res:
            return {}
        ids = [res.contents.crtcs[i] for i in range(res.contents.count_crtcs)]
        drm.drmModeFreeResources(res)
        for cid in ids:
            if crtc_id is not None and cid != crtc_id:
                continue
            props = drm.drmModeObjectGetProperties(fd, cid, 0xcccccccc)
            if not props:
                continue
            values = {}
            for i in range(props.contents.count_props):
                prop = drm.drmModeGetProperty(fd, props.contents.props[i])
                if prop:
                    values[prop.contents.name.decode()] = props.contents.prop_values[i]
                    drm.drmModeFreeProperty(prop)
            drm.drmModeFreeObjectProperties(props)
            result[cid] = values
    finally:
        os.close(fd)
    return result


def tracefs_write(path, value):
    with open(path, "w") as handle:
        handle.write(value)


def display_snapshot(card):
    root = DRI_DEBUGFS / str(card)
    snapshot = {"time_mono": time.monotonic()}
    try:
        snapshot["crtc_properties"] = {str(k): v for k, v in crtc_properties(card).items()}
    except OSError as exc:
        snapshot["crtc_properties"] = f"unreadable: {exc}"
    for name in ("i915_display_info", "i915_edp_psr_status"):
        try:
            snapshot[name] = (root / name).read_text(errors="replace")
        except OSError as exc:
            snapshot[name] = f"unreadable: {exc}"
    for connector in sorted(root.glob("*/vrr_range")):
        try:
            snapshot[f"{connector.parent.name}/vrr_range"] = connector.read_text().strip()
        except OSError:
            continue  # disconnected connectors report no range
    return snapshot


def capture(output, seconds, card=0, crc_crtc=None, buffer_kb=16384):
    """Record the events into OUTPUT/trace.txt; always remove the instance."""
    output = Path(output).resolve()
    in_checkout = (PROJECT_ROOT / ".git").exists()
    if in_checkout and (PROJECT_ROOT in output.parents or output == PROJECT_ROOT):
        raise SystemExit("capture output belongs outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    instance = TRACEFS / "instances" / f"presentation-cadence-{os.getpid()}"
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    header = {"schema": "presentation-cadence-capture-v1", "seconds": seconds,
              "card": card, "crc_crtc": crc_crtc, "events": list(EVENTS),
              "before": display_snapshot(card)}
    crc_lines = []
    instance.mkdir()
    try:
        tracefs_write(instance / "trace_clock", "mono")
        tracefs_write(instance / "buffer_size_kb", str(buffer_kb))
        for event in EVENTS:
            tracefs_write(instance / "events" / event / "enable", "1")
        crc_thread = None
        if crc_crtc is not None:
            data = DRI_DEBUGFS / str(card) / f"crtc-{crc_crtc}" / "crc" / "data"

            def drain():
                with open(data, "rb", buffering=0) as handle:
                    while not stop.is_set():
                        chunk = handle.read(4096)
                        if chunk:
                            crc_lines.append(chunk)
            crc_thread = threading.Thread(target=drain, daemon=True)
            crc_thread.start()
        vrr_samples = header.setdefault("vrr_samples", [])

        def sample_vrr():
            while not stop.is_set():
                try:
                    props = crtc_properties(card)
                except OSError:
                    props = {}
                vrr_samples.append([round(time.monotonic(), 3)] + [
                    [cid, values.get("VRR_ENABLED")] for cid, values in props.items()])
                stop.wait(0.5)
        threading.Thread(target=sample_vrr, daemon=True).start()
        deadline = time.monotonic() + seconds
        with open(instance / "trace_pipe", "rb", buffering=0) as pipe, \
                open(output / "trace.txt", "wb") as out:
            os.set_blocking(pipe.fileno(), False)
            while not stop.is_set() and time.monotonic() < deadline:
                try:
                    chunk = pipe.read(65536)
                except BlockingIOError:
                    chunk = None
                if chunk:
                    out.write(chunk)
                else:
                    time.sleep(0.05)
            stop.set()
            tracefs_write(instance / "tracing_on", "0")
            os.set_blocking(pipe.fileno(), False)
            try:
                while chunk := pipe.read(65536):
                    out.write(chunk)
            except BlockingIOError:
                pass
        if crc_thread:
            crc_thread.join(timeout=2)
    except KeyboardInterrupt:
        stop.set()
    finally:
        stop.set()
        for event in EVENTS:
            try:
                tracefs_write(instance / "events" / event / "enable", "0")
            except OSError:
                pass
        instance.rmdir()
        header["after"] = display_snapshot(card)
        header["dropped_crc_reader_chunks"] = 0
        if crc_lines:
            (output / "crc-data.txt").write_bytes(b"".join(crc_lines))
        (output / "capture.json").write_text(json.dumps(header, indent=1) + "\n")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture", help="record a trace (root, on the laptop)")
    cap.add_argument("output", help="new directory outside the repository")
    cap.add_argument("--seconds", type=float, default=630)
    cap.add_argument("--card", type=int, default=0)
    cap.add_argument("--crc-crtc", type=int, help="also hold crtc-N/crc/data open")
    ana = sub.add_parser("analyze", help="per-frame cadence report from a trace")
    ana.add_argument("trace")
    ana.add_argument("--rate", type=parse_rate, required=True)
    ana.add_argument("--pipe", default="A")
    ana.add_argument("--skip", type=float, default=5.0)
    ana.add_argument("--window", type=float)
    ana.add_argument("--tolerance-ms", type=float, default=DEFAULT_TOLERANCE_MS)
    ana.add_argument("--calibration", help="JSON from the calibrate command")
    cal = sub.add_parser("calibrate", help="pattern CRCs from a frame-stepped capture")
    cal.add_argument("trace")
    cal.add_argument("--first-pattern", type=int, default=0,
                     help="pattern index (frame number mod 16) of the first stepped frame")
    cal.add_argument("--flash-position", type=int,
                     help="step position of the sync flash, if one was stepped over")
    cal.add_argument("--pipe", default="A")
    mod = sub.add_parser("model", help="predicted cadence under a timing model")
    mod.add_argument("--rate", type=parse_rate, action="append", required=True)
    mod.add_argument("--seconds", type=float, default=600)
    mod.add_argument("--refresh-hz", type=float)
    mod.add_argument("--vrr", nargs=2, type=float, metavar=("MIN_HZ", "MAX_HZ"))
    mod.add_argument("--lfc", action="store_true",
                     help="with --vrr, re-present at the lfc_multiplier choice")
    mod.add_argument("--jitter-ms", type=float, default=0.0,
                     help="uniform error added to each VRR commit time")
    args = parser.parse_args(argv)
    if args.command == "capture":
        print(capture(args.output, args.seconds, args.card, args.crc_crtc))
        return 0
    if args.command == "analyze":
        calibration = None
        if args.calibration:
            with open(args.calibration) as handle:
                calibration = json.load(handle)
        with open(args.trace, errors="replace") as handle:
            report = analyze(handle, args.rate, args.pipe, args.skip, args.window,
                             args.tolerance_ms, calibration)
        print(json.dumps(report, indent=1))
        return 0 if report["verdict"] == "even" else 1
    if args.command == "calibrate":
        with open(args.trace, errors="replace") as handle:
            print(json.dumps(calibrate(handle, args.first_pattern, args.pipe,
                                       args.flash_position), indent=1))
        return 0
    if bool(args.refresh_hz) == bool(args.vrr):
        parser.error("model needs exactly one of --refresh-hz or --vrr")
    reports = []
    for rate in args.rate:
        multiplier = 1
        if args.vrr and args.lfc:
            multiplier = lfc_multiplier(rate, *args.vrr) or 1
        starts = model(rate, args.seconds, args.refresh_hz,
                       *(args.vrr or (None, None)), multiplier=multiplier,
                       jitter_ms=args.jitter_ms)
        report = summarise(starts, [], rate, DEFAULT_TOLERANCE_MS, source="model")
        report["multiplier"] = multiplier
        reports.append(report)
    print(json.dumps(reports, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
