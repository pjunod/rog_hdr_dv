#!/usr/bin/env python3
"""Generate long synthetic fixtures for measuring presentation cadence.

Every frame differs (testsrc2 plus a burned-in frame number) so a per-refresh
hardware CRC can tell frames apart; a bar and an audio click at each whole
second allow later A/V sync checks. Encoding is done by FFmpeg on the target.
"""

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
DEFAULT_RATES = "24000/1001 24 25 30000/1001 30 50 60000/1001 60".split()
MASTER_DISPLAY = "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)"
X265_HDR10 = ("hdr10=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:"
              f"colormatrix=bt2020nc:master-display={MASTER_DISPLAY}:max-cll=1000,400")


def parse_rate(text):
    """Parse N/D or an integer into a reduced Fraction in 1..240."""
    try:
        rate = Fraction(text)
    except (ValueError, ZeroDivisionError):
        raise argparse.ArgumentTypeError(f"invalid rate {text!r}")
    if "." in text or "e" in text.lower():
        raise argparse.ArgumentTypeError(
            f"decimal rate {text!r} refused; use an exact fraction such as 24000/1001")
    if not 1 <= rate <= 240:
        raise argparse.ArgumentTypeError(f"rate {text!r} outside 1..240")
    return rate


def rate_text(rate):
    return str(rate)  # Fraction prints "24" or "24000/1001" when reduced


def rate_label(rate):
    return rate_text(rate).replace("/", "-")


def fixture_name(kind, rate, width, height, seconds):
    return f"cadence-{kind}-{rate_label(rate)}-{width}x{height}-{seconds}s.mkv"


def build_argv(ffmpeg, kind, rate, seconds, width, height, out):
    """Return the FFmpeg argv (no shell) for one fixture."""
    r = rate_text(rate)
    video = (
        f"testsrc2=size={width}x{height}:rate={r}:duration={seconds},"
        f"drawbox=x=0:y=0:w=iw:h=ih/12:color=white:t=fill:"
        f"enable='lt(mod(t,1),{1 / rate})',"
        f"drawtext=text='%{{frame_num}}':start_number=0:fontsize={height // 8}:"
        f"fontcolor=black:box=1:boxcolor=white:boxborderw={height // 40}:"
        f"x=w/20:y=h-th-h/20")
    audio = (f"sine=frequency=1000:sample_rate=48000:duration={seconds},"
             "volume='if(lt(mod(t,1),0.02),1,0)':eval=frame")
    argv = [ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", video,
            "-f", "lavfi", "-i", audio, "-map", "0:v", "-map", "1:a"]
    gop = ["-g", str(2 * round(rate))]
    if kind == "sdr":
        argv += ["-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "medium",
                 "-crf", "18", "-pix_fmt", "yuv420p", *gop,
                 "-color_primaries", "bt709", "-color_trc", "bt709",
                 "-colorspace", "bt709"]
    else:
        argv += ["-vf", "format=yuv420p10le", "-c:v", "libx265", "-preset", "medium",
                 "-crf", "18", "-pix_fmt", "yuv420p10le", *gop,
                 "-x265-params", X265_HDR10,
                 "-color_primaries", "bt2020", "-color_trc", "smpte2084",
                 "-colorspace", "bt2020nc"]
    argv += ["-r", r, "-fps_mode", "cfr", "-c:a", "aac", "-ar", "48000",
             "-ac", "2", "-shortest", str(out)]
    return argv


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bounded(low, high, step=1):
    def parse(text):
        value = int(text)
        if not low <= value <= high or value % step:
            raise argparse.ArgumentTypeError(f"{value} outside {low}..{high}")
        return value
    return parse


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output_dir", type=Path)
    p.add_argument("--rates", nargs="+", type=parse_rate,
                   default=[parse_rate(r) for r in DEFAULT_RATES])
    p.add_argument("--seconds", type=bounded(1, 7200), default=660)
    p.add_argument("--width", type=bounded(320, 3840, 2), default=1920)
    p.add_argument("--height", type=bounded(180, 2160, 2), default=1080)
    p.add_argument("--kind", choices=("sdr", "hdr10"), default="sdr")
    p.add_argument("--ffmpeg", default="ffmpeg")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if len(set(args.rates)) != len(args.rates):
        p.error("duplicate rates after reduction")
    out = args.output_dir.resolve()
    if out.exists():
        p.error(f"{out} already exists")
    if not out.parent.is_dir():
        p.error(f"parent of {out} does not exist")
    if out == REPO or REPO in out.parents:
        p.error("OUTPUT_DIR must be outside the repository")
    args.output_dir = out
    return args


def main(argv=None):
    args = parse_args(argv)
    entries = []
    for rate in args.rates:
        name = fixture_name(args.kind, rate, args.width, args.height, args.seconds)
        cmd = build_argv(args.ffmpeg, args.kind, rate, args.seconds, args.width,
                         args.height, args.output_dir / name)
        entries.append({"file": name, "rate": rate_text(rate), "rate_float": float(rate),
                        "expected_frames": math.floor(args.seconds * rate),
                        "argv": cmd})
    if args.dry_run:
        print(json.dumps([e["argv"] for e in entries], indent=2))
        return 0
    args.output_dir.mkdir()
    for entry in entries:
        path = args.output_dir / entry["file"]
        try:
            result = subprocess.run(entry["argv"], check=False)
            ok = result.returncode == 0
        except OSError as exc:
            print(f"cannot run ffmpeg: {exc}", file=sys.stderr)
            ok = False
        if not ok:
            path.unlink(missing_ok=True)
            print(f"ffmpeg failed for {entry['file']}", file=sys.stderr)
            return 1
        entry["size_bytes"] = path.stat().st_size
        entry["sha256"] = sha256(path)
    manifest = {"schema": "cadence-fixtures-v1", "kind": args.kind,
                "width": args.width, "height": args.height,
                "seconds": args.seconds, "fixtures": entries}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
