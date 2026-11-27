#!/usr/bin/env python3
"""Generate long synthetic fixtures for measuring presentation cadence.

Frames are identified by a hardware per-refresh CRC of the display pipe, which
only tells pictures apart. Source frame n therefore shows pattern n mod 16 (a
flat grey level 16+14p plus a white vertical bar in column p of 16), built
with lavfi color+geq only: no fonts and nothing time-varying, so equal
patterns are pixel-identical. A calibration pass records each CRC once.

--sync (default on for standard/matroska) adds a once-per-second flash: the
first frame at or after each whole second is full white (luma 235). That is
a 17th distinct picture, and those frames break the 16-cycle identity; the
manifest records sync_flash so the analyser treats them as extra known
pictures. An audio click (1 kHz, 20 ms) marks each second for A/V sync.

Variants: standard (MP4, exact track timescale), silent (MP4, no audio, no
flash), matroska (24000/1001 only, default 1 ms Matroska timestamps) and
rate-change (one silent MP4, 24000/1001 then 60000/1001, each seconds/2).
Encoding is done by FFmpeg on the target.
"""

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
PRESETS = ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow")
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


PATTERNS = 16
VARIANTS = ("standard", "silent", "matroska", "rate-change")
SUFFIX = {"standard": "", "silent": "-silent", "matroska": "-mkv", "rate-change": ""}
MKV_RATE = Fraction(24000, 1001)
CHANGE_RATES = (Fraction(24000, 1001), Fraction(60000, 1001))
CHANGE_TIMESCALE = 120000  # 120000*1001/24000 = 5005, 120000*1001/60000 = 2002


def fixture_name(kind, rate, width, height, seconds, variant="standard"):
    """rate is a Fraction, or None for the rate-change variant."""
    label = "-to-".join(rate_label(r) for r in CHANGE_RATES) if rate is None \
        else rate_label(rate)
    ext = "mkv" if variant == "matroska" else "mp4"
    return f"cadence-{kind}-{label}-{width}x{height}-{seconds}s{SUFFIX[variant]}.{ext}"


def track_timescale(rate):
    """Smallest multiple of 90000 (or the numerator) giving integer frame durations."""
    for scale in (90000, rate.numerator, rate.numerator * 1000):
        if (scale / rate).denominator == 1:
            return scale
    raise ValueError(f"no exact timescale for {rate}")


def video_source(rate, seconds, width, height, sync):
    """One lavfi input: the PATTERNS pictures rendered once by geq, then looped.

    geq per pixel is slow, so only the first PATTERNS frames are computed;
    `loop` repeats them and `setpts` restores an exact constant-rate
    timeline. The optional sync flash is a full-frame drawbox on the first
    frame of each second (half-frame offset keeps it robust to rounding).
    """
    r = rate_text(rate)
    p = f"mod(N,{PATTERNS})"
    lum = f"if(eq(floor(X/(W/{PATTERNS})),{p}),235,16+{p}*14)"
    chain = (f"color=c=black:s={width}x{height}:r={r},format=yuv420p,"
             f"trim=end_frame={PATTERNS},geq=lum='{lum}':cb=128:cr=128,"
             f"loop=loop=-1:size={PATTERNS}:start=0,setpts=N/({r})/TB,"
             f"trim=duration={seconds}")
    if sync:
        chain += (f",drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:"
                  f"enable='lt(mod(t+{1 / (2 * rate)},1),{1 / rate})'")
    return chain


def codec_args(kind, preset, rate_hint):
    """Intra-only, constant QP, no adaptive quantisation.

    Inter prediction or rate control would decode frame n and n+16 to
    slightly different pixels and break CRC identity; intra-only constant QP
    decodes every repetition of a pattern identically (checked by framemd5
    on the laptop, November 27). rate_hint is unused but kept for callers.
    """
    if kind == "sdr":
        return ["-c:v", "libx264", "-preset", preset, "-qp", "16", "-g", "1",
                "-bf", "0", "-aq-mode", "0",
                "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
                "-color_trc", "bt709", "-colorspace", "bt709"]
    return ["-c:v", "libx265", "-preset", preset,
            "-pix_fmt", "yuv420p10le", "-x265-params",
            X265_HDR10 + ":qp=16:keyint=1:bframes=0:aq-mode=0",
            "-color_primaries", "bt2020", "-color_trc", "smpte2084",
            "-colorspace", "bt2020nc"]


def pix_fmt(kind):
    return "yuv420p" if kind == "sdr" else "yuv420p10le"


def build_argv(ffmpeg, kind, rate, seconds, width, height, out, preset="medium",
               variant="standard", sync=True):
    """Return the FFmpeg argv (no shell) for one single-rate fixture."""
    r = rate_text(rate)
    audio = variant != "silent"
    sync = sync and audio
    argv = [ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i",
            video_source(rate, seconds, width, height, sync)]
    if audio:
        argv += ["-f", "lavfi", "-i",
                 f"sine=frequency=1000:sample_rate=48000:duration={seconds},"
                 "volume='if(lt(mod(t,1),0.02),1,0)':eval=frame",
                 "-map", "0:v", "-map", "1:a"]
    argv += ["-vf", f"format={pix_fmt(kind)}", *codec_args(kind, preset, rate),
             "-r", r, "-fps_mode", "cfr"]
    if variant != "matroska":
        # MP4 timescale dividing the frame period exactly; Matroska's default
        # 1 ms timestamps would build +-0.5 ms jitter into the fixture.
        argv += ["-video_track_timescale", str(track_timescale(rate)),
                 "-movflags", "+faststart"]
    if audio:
        argv += ["-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest"]
    return argv + [str(out)]


def build_rate_change_steps(ffmpeg, kind, seconds, width, height, out, preset="medium"):
    """Steps for one silent MP4: seconds/2 at 24000/1001, then seconds/2 at 60000/1001.

    Each segment is encoded on its own with a time base that holds both frame
    periods exactly, then the concat demuxer joins them by stream copy.
    Joining in a filter graph rounded the second segment onto the first
    segment's grid (checked on the laptop, November 27).
    Returns (steps, concat_list_path, temporary_paths).
    """
    out = Path(out)
    half = seconds // 2
    parts = [out.with_name(f"{out.stem}.part{k}.mp4") for k in range(len(CHANGE_RATES))]
    steps = []
    for rate, part in zip(CHANGE_RATES, parts):
        steps.append([ffmpeg, "-hide_banner", "-y", "-f", "lavfi",
                      "-i", video_source(rate, half, width, height, False),
                      "-vf", f"format={pix_fmt(kind)}", *codec_args(kind, preset, rate),
                      "-video_track_timescale", str(CHANGE_TIMESCALE), str(part)])
    listing = out.with_name(f"{out.stem}.parts.txt")
    steps.append([ffmpeg, "-hide_banner", "-y", "-f", "concat", "-safe", "0",
                  "-i", str(listing), "-c", "copy", "-video_track_timescale",
                  str(CHANGE_TIMESCALE), "-movflags", "+faststart", str(out)])
    return steps, listing, parts


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
    p.add_argument("--rates", nargs="+", type=parse_rate, default=None)
    p.add_argument("--seconds", type=bounded(1, 7200), default=660)
    p.add_argument("--width", type=bounded(320, 3840, 2), default=1920)
    p.add_argument("--height", type=bounded(180, 2160, 2), default=1080)
    p.add_argument("--kind", choices=("sdr", "hdr10"), default="sdr")
    p.add_argument("--variant", choices=VARIANTS, default="standard")
    p.add_argument("--sync", action=argparse.BooleanOptionalAction, default=True,
                   help="once-per-second white flash frame (ignored for silent/rate-change)")
    p.add_argument("--preset", default="medium",
                   help="x264/x265 preset; picture quality does not affect cadence")
    p.add_argument("--ffmpeg", default="ffmpeg")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.rates is not None and len(set(args.rates)) != len(args.rates):
        p.error("duplicate rates after reduction")
    if args.variant == "rate-change":
        if args.rates is not None:
            p.error("--rates is not allowed with --variant rate-change")
        if args.seconds % 2:
            p.error("--seconds must be even for rate-change")
    elif args.variant == "matroska":
        if args.rates not in (None, [MKV_RATE]):
            p.error("--variant matroska supports only --rates 24000/1001")
        args.rates = [MKV_RATE]
    elif args.rates is None:
        args.rates = [parse_rate(r) for r in DEFAULT_RATES]
    if args.preset not in PRESETS:
        p.error(f"--preset must be one of {', '.join(PRESETS)}")
    args.sync = args.sync and args.variant in ("standard", "matroska")
    out = args.output_dir.resolve()
    if out.exists():
        p.error(f"{out} already exists")
    if not out.parent.is_dir():
        p.error(f"parent of {out} does not exist")
    if (REPO / ".git").exists() and (out == REPO or REPO in out.parents):
        p.error("OUTPUT_DIR must be outside the repository")
    args.output_dir = out
    return args


def plan(args):
    """Manifest entries (with argv) for the requested variant."""
    d = args.output_dir
    common = {"sync_flash": args.sync, "timestamps":
              "matroska-1ms" if args.variant == "matroska" else "exact"}
    if args.variant == "rate-change":
        name = fixture_name(args.kind, None, args.width, args.height, args.seconds,
                            args.variant)
        half = args.seconds // 2
        segments = [{"rate": rate_text(r), "start_seconds": i * half,
                     "expected_frames": math.floor(half * r)}
                    for i, r in enumerate(CHANGE_RATES)]
        steps, listing, parts = build_rate_change_steps(
            args.ffmpeg, args.kind, args.seconds, args.width, args.height, d / name,
            args.preset)
        return [{"file": name, "segments": segments, "timescale": CHANGE_TIMESCALE,
                 "expected_frames": sum(s["expected_frames"] for s in segments),
                 **common, "steps": steps,
                 "concat_list": {"path": str(listing), "parts": [str(p) for p in parts]}}]
    entries = []
    for rate in args.rates:
        name = fixture_name(args.kind, rate, args.width, args.height, args.seconds,
                            args.variant)
        cmd = build_argv(args.ffmpeg, args.kind, rate, args.seconds, args.width,
                         args.height, d / name, args.preset, args.variant, args.sync)
        entries.append({"file": name, "rate": rate_text(rate), "rate_float": float(rate),
                        "expected_frames": math.floor(args.seconds * rate),
                        **common, "steps": [cmd]})
    return entries


def main(argv=None):
    args = parse_args(argv)
    entries = plan(args)
    if args.dry_run:
        print(json.dumps([e["steps"] for e in entries], indent=2))
        return 0
    args.output_dir.mkdir()
    for entry in entries:
        path = args.output_dir / entry["file"]
        concat = entry.pop("concat_list", None)
        temporary = []
        if concat:
            temporary = [Path(concat["path"])] + [Path(p) for p in concat["parts"]]
            Path(concat["path"]).write_text(
                "".join(f"file '{Path(p).name}'\n" for p in concat["parts"]))
        ok = True
        for step in entry["steps"]:
            try:
                ok = subprocess.run(step, check=False).returncode == 0
            except OSError as exc:
                print(f"cannot run ffmpeg: {exc}", file=sys.stderr)
                ok = False
            if not ok:
                break
        for leftover in temporary:
            leftover.unlink(missing_ok=True)
        if not ok:
            path.unlink(missing_ok=True)
            print(f"ffmpeg failed for {entry['file']}", file=sys.stderr)
            return 1
        entry["size_bytes"] = path.stat().st_size
        entry["sha256"] = sha256(path)
    manifest = {"schema": "cadence-fixtures-v2", "patterns": PATTERNS,
                "variant": args.variant, "kind": args.kind,
                "width": args.width, "height": args.height,
                "seconds": args.seconds, "fixtures": entries}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
