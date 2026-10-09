#!/usr/bin/env python3
"""Generate owned synthetic PQ/BT.2020 TIFFs; no Dolby metadata or tools."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile

PQ_SOURCE = "https://www.itu.int/rec/R-REC-BT.2100"
MAX_CHANNEL_CD_M2 = 1000
MAX_PIXELS = 1024 * 1024
Y_WEIGHTS = (0.2627, 0.6780, 0.0593)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CorpusError(Exception):
    """A clear, bounded failure reason."""


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def pq_encode(channel_cd_m2):
    """Inverse ST 2084 EOTF: absolute RGB channel value, normalized by 10000.

    ITU-R BT.2100 Table 4 supplies the PQ constants and transfer equation.
    This is display-linear source encoding, without a scene OOTF.
    """
    if not math.isfinite(channel_cd_m2) or not 0 <= channel_cd_m2 <= MAX_CHANNEL_CD_M2:
        raise CorpusError("RGB channel must be finite and in 0..1000 cd/m2")
    power = (channel_cd_m2 / 10000) ** (2610 / 16384)
    return ((3424 / 4096 + (2413 / 128) * power) /
            (1 + (2392 / 128) * power)) ** (2523 / 32)


def quantize(channel_cd_m2):
    """Full-range unsigned 16-bit; round to nearest, half upward."""
    return math.floor(pq_encode(channel_cd_m2) * 65535 + 0.5)


def patch(label, rect, rgb):
    rgb = list(rgb)
    return {"label": label, "rect_xywh": list(rect), "linear_rgb_cd_m2": rgb,
            "photometric_y_cd_m2": round(sum(w * v for w, v in zip(Y_WEIGHTS, rgb)), 9),
            "encoded_rgb_u16": [quantize(v) for v in rgb]}


def bars(width, height, entries):
    result = []
    for index, (label, rgb) in enumerate(entries):
        left = index * width // len(entries)
        right = (index + 1) * width // len(entries)
        result.append(patch(label, (left, 0, right - left, height), rgb))
    return result


def corpus_design(width, height):
    """Every region is explicit; later patches paint over earlier patches."""
    near_black = (0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5)
    highlights = (0, 100, 203, 400, 616, 1000)
    colors = (("black", (0, 0, 0)), ("red", (1, 0, 0)), ("green", (0, 1, 0)),
              ("blue", (0, 0, 1)), ("yellow", (1, 1, 0)), ("cyan", (0, 1, 1)),
              ("magenta", (1, 0, 1)), ("white", (1, 1, 1)))
    scenes = [("neutral_linear_ramp", [
        patch("ramp_column_%04d" % x, (x, 0, 1, height),
              (1000 * x / (width - 1),) * 3) for x in range(width)]),
        ("near_black_steps", bars(width, height, [
            ("gray_%g" % v, (v,) * 3) for v in near_black])),
        ("gray_highlights", bars(width, height, [
            ("gray_%g" % v, (v,) * 3) for v in highlights]))]
    for level in (203, 1000):
        scenes.append(("rgb_channels_%d" % level, bars(width, height, [
            ("%s_channels_%d" % (name, level), tuple(v * level for v in rgb))
            for name, rgb in colors])))
    window_width, window_height = max(1, width // 4), max(1, height // 4)
    scenes.append(("dark_scene_with_peak_window", [
        patch("gray_1_background", (0, 0, width, height), (1, 1, 1)),
        patch("gray_1000_window", ((width - window_width) // 2,
                                  (height - window_height) // 2,
                                  window_width, window_height), (1000, 1000, 1000))]))
    return [{"index": index, "filename": "frame_%06d.tif" % index,
             "label": label, "scene_id": index, "cut_before": index != 0,
             "paint_order": "later patches replace earlier patches",
             "patches": patches} for index, (label, patches) in enumerate(scenes)]


def tiff_bytes(width, height, patches):
    """Classic TIFF, one uncompressed interleaved RGB strip, little-endian."""
    pixels = bytearray(width * height * 6)
    for region in patches:
        x, y, w, h = region["rect_xywh"]
        if not (0 <= x < width and 0 <= y < height and
                0 < w <= width - x and 0 < h <= height - y):
            raise CorpusError("patch outside image bounds")
        row = struct.pack("<3H", *region["encoded_rgb_u16"]) * w
        for line in range(y, y + h):
            start = (line * width + x) * 6
            pixels[start:start + len(row)] = row
    count = 12
    extra_offset = 8 + 2 + count * 12 + 4
    pixel_offset = extra_offset + 12
    tags = [(256, 4, 1, width), (257, 4, 1, height),
            (258, 3, 3, extra_offset), (259, 3, 1, 1), (262, 3, 1, 2),
            (273, 4, 1, pixel_offset), (274, 3, 1, 1), (277, 3, 1, 3),
            (278, 4, 1, height), (279, 4, 1, len(pixels)),
            (284, 3, 1, 1), (339, 3, 3, extra_offset + 6)]
    ifd = struct.pack("<H", count)
    for tag, kind, length, value in tags:
        ifd += struct.pack("<HHII", tag, kind, length, value)
    return (b"II" + struct.pack("<HI", 42, 8) + ifd + struct.pack("<I", 0) +
            struct.pack("<6H", 16, 16, 16, 1, 1, 1) + pixels)


def validate_parameters(width, height, fps):
    if (any(type(value) is not int for value in (width, height, fps)) or
            not 12 <= width <= 4096 or not 4 <= height <= 4096 or
            width * height > MAX_PIXELS or not 1 <= fps <= 120):
        raise CorpusError("require width 12..4096, height 4..4096, at most 1048576 pixels, fps 1..120")


def _write_file(path, data):
    with path.open("xb") as stream:
        stream.write(data)


def generate_corpus(output, width=192, height=108, fps=24):
    """Publish a complete new directory; existing paths are never reused."""
    validate_parameters(width, height, fps)
    output = Path(output)
    if output.name in ("", ".", ".."):
        raise CorpusError("output must name a new directory")
    try:
        parent = output.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        raise CorpusError("output parent must be an existing directory") from None
    output = parent / output.name
    if not parent.is_dir():
        raise CorpusError("output parent must be an existing directory")
    if output == PROJECT_ROOT or PROJECT_ROOT in output.parents:
        raise CorpusError("generated corpus must be outside the source repository")
    if os.path.lexists(output):
        raise CorpusError("output path already exists")
    frames = corpus_design(width, height)
    parameters = {"width": width, "height": height, "fps_numerator": fps,
                  "fps_denominator": 1, "frame_count": len(frames)}
    try:
        generator_hash = sha256(Path(__file__).read_bytes())
    except OSError:
        raise CorpusError("cannot hash generator source") from None
    manifest = {
        "schema": "synthetic-hdr-corpus-v1", "generator": "generate_hdr_corpus.py",
        "dimensions_and_timing": parameters,
        "input_hashes": {"generator_sha256": generator_hash,
                         "parameters_canonical_json_sha256": sha256(canonical_json(parameters)),
                         "design_canonical_json_sha256": sha256(canonical_json(frames))},
        "external_inputs": [],
        "source_intent": "Owned synthetic display-linear RGB; no scene OOTF, Dolby metadata or trims",
        "mastering_intent": {"synthetic_design_only": True, "peak_cd_m2": 1000,
                             "black_cd_m2": 0, "panel_measurement": False},
        "encoding": {"container": "classic TIFF little-endian", "compression": "none",
                     "samples": "unsigned 16-bit interleaved RGB", "range": "full 0..65535",
                     "transfer": "PQ / SMPTE ST 2084 inverse EOTF", "pq_normalization_cd_m2": 10000,
                     "transfer_source": PQ_SOURCE, "primaries": "BT.2020", "white_point": "D65",
                     "primary_xy": {"red": [0.708, 0.292], "green": [0.170, 0.797],
                                    "blue": [0.131, 0.046]}, "white_xy": [0.3127, 0.3290],
                     "channel_bounds_cd_m2": [0, 1000],
                     "quantization": "floor(PQ(channel_cd_m2) * 65535 + 0.5)",
                     "colour_tags": "TIFF RGB only; transfer/primaries are declared in this manifest"},
        "patch_semantics": {"rect_xywh": "top-left origin; integer pixels",
                            "rgb": "absolute linear BT.2020 RGB channel intensities in cd/m2",
                            "y": "photometric Y = 0.2627 R + 0.6780 G + 0.0593 B; not a colored channel value"},
        "frames": [],
    }
    staging = None
    reserved = False
    try:
        staging = Path(tempfile.mkdtemp(prefix=".hdr-corpus-", dir=parent))
        for frame in frames:
            payload = tiff_bytes(width, height, frame["patches"])
            _write_file(staging / frame["filename"], payload)
            manifest["frames"].append(dict(frame, sha256=sha256(payload), bytes=len(payload)))
        _write_file(staging / "manifest.json", canonical_json(manifest))
        # Reserve using mkdir's no-replace semantics. Rename replaces only our
        # empty placeholder; a concurrent nonempty directory makes rename fail.
        os.mkdir(output, mode=0o700)
        reserved = True
        os.rename(staging, output)
        staging = None
        reserved = False
    except (OSError, ValueError):
        raise CorpusError("cannot write or publish corpus; no existing output was overwritten") from None
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        if reserved:
            # Never recursively remove the destination: it could have changed.
            try:
                output.rmdir()
            except OSError:
                pass
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", help="new directory outside this repository; parent must exist")
    parser.add_argument("--width", type=int, default=192)
    parser.add_argument("--height", type=int, default=108)
    parser.add_argument("--fps", type=int, default=24, help="integer frame rate, default 24")
    args = parser.parse_args(argv)
    try:
        generate_corpus(args.output_directory, args.width, args.height, args.fps)
    except (CorpusError, ValueError) as error:
        print("HDR corpus error: %s" % error, file=sys.stderr)
        return 1
    print("Created six synthetic PQ RGB TIFF frames and manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
