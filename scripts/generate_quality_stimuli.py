#!/usr/bin/env python3
"""Generate owned synthetic Y4M image-quality source stimuli; stdlib only."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_WIDTH, MIN_HEIGHT = 192, 72
MAX_WIDTH, MAX_HEIGHT = 3840, 2160
DEFAULT_CADENCE_FPS = (24, 25, 30, 50, 60)
MAX_CADENCE_FILES = 16
DEFAULT_MAX_TOTAL_BYTES = 64 * 1024 * 1024

# 10-bit limited-range code values (BT.2020 NCL, PQ declared in the manifest).
Y_BLACK, Y_WHITE, C_NEUTRAL, C_MAX = 64, 940, 512, 960
Y_MID, Y_AMP = 502, 438
GREY_Y10 = 480
# Chroma step colours, 8-bit limited-range (Cb, Cr) codes; the p10 file uses 4x these.
CHROMA_A8, CHROMA_B8, GREY_Y8, NEUTRAL8 = (94, 195), (188, 94), 120, 128
BT2020_KR, BT2020_KB = 0.2627, 0.0593
COORDINATE_CONVENTION = ("luma pixel i covers [i, i+1) and its centre is at i+0.5; positions are in "
                         "luma-pixel units from the frame's top-left corner; siting midpoints are "
                         "defined in the code-value domain")
# tag -> (horizontal, vertical, H.273 chroma location type, carried by the file)
SITING_BY_TAG = {"420mpeg2": ("left", "centre", 0, True), "420jpeg": ("centre", "centre", 1, True),
                 "420paldv": ("left", "top", 2, True), "420p10": ("left", "top", 2, False)}
REFRESH_RATES = (60, 50, 120, 144)
HEADER_RANGE = "XCOLORRANGE=LIMITED"

SLANT_DEGREES = 5
SLANT_SLOPE = round(math.tan(math.radians(SLANT_DEGREES)), 12)
GRATING_STRIPES = (1, 2)

BLOCK = 8
BARCODE_START, BARCODE_STOP = (1, 0), (0, 1)
INDEX_BITS, CHECK_BITS = 16, 4
BARCODE_BLOCKS = len(BARCODE_START) + INDEX_BITS + CHECK_BITS + len(BARCODE_STOP)
BARCODE_RECT = (0, 0, BARCODE_BLOCKS * BLOCK, BLOCK)
BAR_WIDTH, BAR_STEP, BAR_TOP = 8, 4, 16
BARCODE_THRESHOLD = (Y_BLACK + Y_WHITE) // 2
BARCODE_DEAD_BAND = (Y_WHITE - Y_BLACK) // 4

DITHER_RAMPS = (("near_black", 64, 96), ("mid_grey", 448, 480))
FRAME_TAG = b"FRAME\n"


class StimulusError(Exception):
    """A clear, bounded failure reason."""


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def round_half_up(value):
    return math.floor(value + 0.5)


# ---------------------------------------------------------------- validation

def validate_parameters(width, height, fps_list, seconds, max_total_bytes):
    if any(type(v) is not int for v in (width, height, seconds, max_total_bytes)):
        raise StimulusError("width, height, cadence seconds and max total bytes must be integers")
    if (not MIN_WIDTH <= width <= MAX_WIDTH or not MIN_HEIGHT <= height <= MAX_HEIGHT
            or width % 2 or height % 2):
        raise StimulusError("require even width %d..%d and even height %d..%d"
                            % (MIN_WIDTH, MAX_WIDTH, MIN_HEIGHT, MAX_HEIGHT))
    if not isinstance(fps_list, (list, tuple)) or not 1 <= len(fps_list) <= MAX_CADENCE_FILES:
        raise StimulusError("cadence fps list must hold 1..%d integers" % MAX_CADENCE_FILES)
    if any(type(f) is not int or not 1 <= f <= 120 for f in fps_list):
        raise StimulusError("each cadence fps must be an integer in 1..120")
    if len(set(fps_list)) != len(fps_list):
        raise StimulusError("cadence fps values must be unique")
    if not 1 <= seconds <= 10:
        raise StimulusError("cadence seconds must be 1..10")
    if max_total_bytes < 1:
        raise StimulusError("max total bytes must be positive")


# ------------------------------------------------------------------ Y4M I/O

def y4m_header(width, height, fps, colourspace, extra=""):
    text = "YUV4MPEG2 W%d H%d F%d:1 Ip A1:1 C%s" % (width, height, fps, colourspace)
    return (text + (" " + extra if extra else "") + "\n").encode("ascii")


def pack_plane(rows, wide):
    """rows: list of int lists. 8-bit bytes or little-endian 16-bit samples."""
    out = bytearray()
    for row in rows:
        if wide:
            for v in row:
                out += bytes((v & 255, v >> 8))
        else:
            out += bytes(row)
    return bytes(out)


def frame_bytes(width, height, wide):
    return (width * height + 2 * (width // 2) * (height // 2)) * (2 if wide else 1)


def frame_payload(y_rows, cb_rows, cr_rows, wide):
    return FRAME_TAG + pack_plane(y_rows, wide) + pack_plane(cb_rows, wide) + pack_plane(cr_rows, wide)


def flat(width, height, value):
    return [[value] * width for _ in range(height)]


# -------------------------------------------------------------- chroma siting

def ycbcr_to_rgb(y, cb, cr, bits):
    """Normalised R'G'B' of limited-range codes under the declared BT.2020 NCL matrix."""
    scale = 1 << (bits - 8)
    yn = (y - 16 * scale) / (219 * scale)
    cbn = (cb - 128 * scale) / (224 * scale)
    crn = (cr - 128 * scale) / (224 * scale)
    r = yn + 2 * (1 - BT2020_KR) * crn
    b = yn + 2 * (1 - BT2020_KB) * cbn
    g = (yn - BT2020_KR * r - BT2020_KB * b) / (1 - BT2020_KR - BT2020_KB)
    return r, g, b


def check_chroma_gamut(y8, pairs8):
    """Both step colours must stay inside [0, 1] R'G'B' at the grey luma."""
    result = []
    for cb, cr in pairs8:
        rgb = ycbcr_to_rgb(y8, cb, cr, 8)
        if not all(-1e-9 <= c <= 1 + 1e-9 for c in rgb):
            raise StimulusError("chroma step colour %r is outside R'G'B' [0,1] at luma %d"
                                % ((cb, cr), y8))
        result.append([round(c, 6) for c in rgb])
    return result


def chroma_edges(width, height):
    cw, ch = width // 2, height // 2
    return ([cw // 4, cw // 2, 3 * cw // 4], [ch // 4, ch // 2, 3 * ch // 4])


def chroma_siting_frames(width, height, scale):
    """Lazily yield (vertical-edge, horizontal-edge) frames; scale 1 = 8-bit, 4 = 10-bit."""
    cw, ch = width // 2, height // 2
    ks, js = chroma_edges(width, height)
    check_chroma_gamut(GREY_Y8, (CHROMA_A8, CHROMA_B8))
    a = tuple(v * scale for v in CHROMA_A8)
    b = tuple(v * scale for v in CHROMA_B8)
    y = flat(width, height, GREY_Y8 * scale)

    def toggled(length, edges):
        state, out = 0, []
        for i in range(length):
            if i in edges:
                state ^= 1
            out.append(state)
        return out

    cols, rows = toggled(cw, ks), toggled(ch, js)
    vertical = [[(a, b)[s] for s in cols] for _ in range(ch)]
    yield y, [[p[0] for p in r] for r in vertical], [[p[1] for p in r] for r in vertical]
    horizontal = [[(a, b)[s]] * cw for s in rows]
    yield y, [[p[0] for p in r] for r in horizontal], [[p[1] for p in r] for r in horizontal]


def siting_entry(width, height, tag):
    ks, js = chroma_edges(width, height)
    h, v, loc_type, carried = SITING_BY_TAG[tag]
    gamut = check_chroma_gamut(GREY_Y8, (CHROMA_A8, CHROMA_B8))
    x_mid = {"left": lambda k: 2 * k - 0.5, "centre": lambda k: 2.0 * k}[h]
    y_mid = {"top": lambda j: 2 * j - 0.5, "centre": lambda j: 2.0 * j}[v]
    return {
        "chroma_a_cb_cr_8bit": list(CHROMA_A8), "chroma_b_cb_cr_8bit": list(CHROMA_B8),
        "luma_8bit": GREY_Y8,
        "rgb_prime_of_chroma_a_b_at_luma": {"a": gamut[0], "b": gamut[1],
                                            "rule": "BT.2020 NCL with Kr/Kb below, limited range; each in [0, 1]"},
        "frames": ["vertical_edges", "horizontal_edges"],
        "siting_tag_implied": {"horizontal": h, "vertical": v, "h273_chroma_loc_type": loc_type,
                               "carried_by_file": carried,
                               "note": "Y4M tag" if carried else
                               "NOT carried by the file (ffprobe reports unspecified); an analysis "
                               "must state the assumed chroma location type"},
        "positions": {"left_cosited_chroma_i_at_luma_x": "2i + 0.5", "centre_chroma_i_at_luma_x": "2i + 1",
                      "top_chroma_j_at_luma_y": "2j + 0.5", "centre_chroma_j_at_luma_y": "2j + 1"},
        "vertical_edges": [{"k": k, "chroma_step_between_columns": [k - 1, k],
                            "midpoint_luma_x_left": 2 * k - 0.5, "midpoint_luma_x_centre": 2.0 * k,
                            "midpoint_luma_x_for_this_file": x_mid(k),
                            "observable_shift_source_px": 0.5} for k in ks],
        "horizontal_edges": [{"j": j, "chroma_step_between_rows": [j - 1, j],
                              "midpoint_luma_y_top": 2 * j - 0.5, "midpoint_luma_y_centre": 2.0 * j,
                              "midpoint_luma_y_for_this_file": y_mid(j),
                              "observable_shift_source_px": 0.5} for j in js]}


# -------------------------------------------------------------------- scaling

def zone_plate_radius(width, height):
    return round(math.hypot(width, height), 6)


def zone_plate_code(x, y, width, height, radius):
    r2 = (x + 0.5 - width / 2) ** 2 + (y + 0.5 - height / 2) ** 2
    return round_half_up(Y_MID + Y_AMP * math.cos(math.pi * r2 / radius))


def grating_code(x, y, width, height):
    stripe = GRATING_STRIPES[0 if x < width // 2 else 1]
    index = x // stripe if y < height // 2 else y // stripe
    return Y_WHITE if index % 2 == 0 else Y_BLACK


def slant_code(x, y, width, height):
    dx = x + 0.5 - width / 2
    dy = y + 0.5 - height / 2
    return Y_WHITE if dx > SLANT_SLOPE * dy else Y_BLACK


def scaling_frames(width, height):
    """Lazily yield the three luma planes."""
    radius = zone_plate_radius(width, height)
    yield [[zone_plate_code(x, y, width, height, radius) for x in range(width)] for y in range(height)]
    yield [[grating_code(x, y, width, height) for x in range(width)] for y in range(height)]
    yield [[slant_code(x, y, width, height) for x in range(width)] for y in range(height)]


def scaling_entry(width, height):
    radius = zone_plate_radius(width, height)
    boundaries = {}
    for scale in (0.5, 0.75, 1, 2):
        bx, by = 0.5 * radius * scale, 0.5 * radius * scale
        boundaries[str(scale)] = {
            "alias_boundary_abs_dx_source_px": bx, "x_axis_can_alias": bx < width / 2,
            "alias_boundary_abs_dy_source_px": by, "y_axis_can_alias": by < height / 2}
    return {
        "frames": ["zone_plate", "line_gratings", "slanted_edge"],
        "chroma_code": C_NEUTRAL,
        "zone_plate": {
            "formula": "Y = round_half_up(mid + amp * cos(pi * r^2 / R)); r in pixels from the "
                       "frame centre, sampled at pixel centres (x+0.5-W/2, y+0.5-H/2)",
            "mid": Y_MID, "amp": Y_AMP, "R_pixels": radius,
            "R_rule": "R = hypot(W, H) rounded to 6 decimals; max source frequency is 0.5 cycles/pixel at the corner",
            "local_frequency_cycles_per_pixel": "f(r) = r / R; along an axis f_x = |dx| / R, f_y = |dy| / R",
            "alias_rule": "After scaling by (sx, sy) a source frequency f_x appears at f_x / sx cycles per "
                          "output pixel (likewise y), so that axis aliases where |dx| > 0.5 * R * sx "
                          "(|dy| > 0.5 * R * sy). If the boundary exceeds the half-size (W/2 or H/2) "
                          "that axis cannot alias",
            "alias_boundary_abs_dx_source_px": "0.5 * R * sx", "alias_boundary_abs_dy_source_px": "0.5 * R * sy",
            "boundaries_by_uniform_scale": boundaries},
        "line_gratings": {
            "levels": [Y_BLACK, Y_WHITE], "stripe_widths_px": list(GRATING_STRIPES),
            "quadrants": {"top_left": "vertical lines, 1 px stripes (period 2 px)",
                          "top_right": "vertical lines, 2 px stripes (period 4 px)",
                          "bottom_left": "horizontal lines, 1 px stripes (period 2 px)",
                          "bottom_right": "horizontal lines, 2 px stripes (period 4 px)"},
            "quadrant_split": [width // 2, height // 2],
            "rule": "stripe index = floor(x / w) (vertical) or floor(y / w) (horizontal), absolute "
                    "frame coordinates; even index Y=940, odd index Y=64"},
        "slanted_edge": {
            "angle_degrees_from_vertical": SLANT_DEGREES, "slope_dx_per_dy": SLANT_SLOPE,
            "levels": {"left": Y_BLACK, "right": Y_WHITE},
            "rule": "Y = 940 if (x+0.5-W/2) > slope * (y+0.5-H/2) else 64; hard edge, no source antialiasing"}}


# --------------------------------------------------------------------- dither

def ramp_code(x, width, low, high):
    return low + (x * (high - low + 1)) // width


def dither_frames(width, height):
    for _, low, high in DITHER_RAMPS:
        row = [ramp_code(x, width, low, high) for x in range(width)]
        yield [row] * height


# 10-bit limited code -> 8-bit level, four path models (integer arithmetic).
BAND_MODELS = {
    "limited_truncate": lambda c: c >> 2,
    "limited_round": lambda c: min(255, (c + 2) >> 2),
    "full_range_expand_round": lambda c: min(255, max(0, (2 * (c - 64) * 255 + 876) // 1752)),
    "full_range_expand_truncate": lambda c: min(255, max(0, (c - 64) * 255 // 876)),
}


def bands(levels):
    result = []
    for column, level in enumerate(levels):
        if result and result[-1]["level"] == level:
            result[-1]["last_column"] = column
        else:
            result.append({"level": level, "first_column": column, "last_column": column})
    return result


def dither_entry(width, height):
    frames = []
    for name, low, high in DITHER_RAMPS:
        codes = [ramp_code(x, width, low, high) for x in range(width)]
        models = {}
        for model, function in BAND_MODELS.items():
            table = bands([function(c) for c in codes])
            models[model] = {"distinct_8bit_levels": len(table), "bands": table}
        frames.append({
            "name": name, "low": low, "high": high,
            "rule": "code(x) = low + floor(x * (high - low + 1) / W)",
            "column_codes": codes, "distinct_codes_10bit": len(set(codes)),
            "band_models": models, "luma_rows_identical": True,
            "capture_scope": "digital (HDMI / framebuffer) capture only; optically unmeasurable under PQ"
            if name == "near_black" else "digital capture; optical measurement is not expected to resolve single codes"})
    return {"frames": [f["name"] for f in frames], "chroma_code": C_NEUTRAL, "ramps": frames,
            "band_model_rules": {
                "limited_truncate": "level = code >> 2",
                "limited_round": "level = (code + 2) >> 2",
                "full_range_expand_round": "level = round((code - 64) * 255 / 876), half up",
                "full_range_expand_truncate": "level = floor((code - 64) * 255 / 876)"}}


# -------------------------------------------------------------------- cadence

def barcode_bits(index):
    index &= 0xFFFF
    check = ~index & 15
    return (list(BARCODE_START) + [(index >> s) & 1 for s in range(INDEX_BITS - 1, -1, -1)]
            + [(check >> s) & 1 for s in range(CHECK_BITS - 1, -1, -1)] + list(BARCODE_STOP))


def bar_x(index, width):
    return (index * BAR_STEP) % width


def cadence_frame_rows(index, width, height):
    rows = flat(width, height, Y_BLACK)
    for block, bit in enumerate(barcode_bits(index)):
        value = Y_WHITE if bit else Y_BLACK
        for y in range(BARCODE_RECT[1], BARCODE_RECT[1] + BLOCK):
            rows[y][block * BLOCK:(block + 1) * BLOCK] = [value] * BLOCK
    x0 = bar_x(index, width)
    for y in range(BAR_TOP, height):
        row = rows[y]
        for i in range(BAR_WIDTH):
            row[(x0 + i) % width] = Y_WHITE
    return rows


def refresh_runs(fps, refresh):
    """Refreshes each source frame is held over one repeat period (integer arithmetic)."""
    period = fps // math.gcd(fps, refresh)
    starts = [-(-n * refresh // fps) for n in range(period + 1)]
    runs = [starts[n + 1] - starts[n] for n in range(period)]
    unit = next(u for u in range(1, period + 1)
                if period % u == 0 and runs == runs[:u] * (period // u))
    return {"period_frames": period, "runs_over_period": runs, "repeating_unit": runs[:unit]}


def cadence_entry(fps, frames, width):
    return {
        "fps": fps, "frame_count": frames, "chroma_code": C_NEUTRAL,
        "barcode": {"rect_xywh": list(BARCODE_RECT), "block_size_px": BLOCK,
                    "block_count": BARCODE_BLOCKS, "block_order": "left to right, one row",
                    "bit_order": "most significant bit first",
                    "layout": "start 1,0 | 16-bit index | 4-bit check nibble | stop 0,1",
                    "levels": {"0": Y_BLACK, "1": Y_WHITE}, "threshold": BARCODE_THRESHOLD,
                    "dead_band": {"centre": BARCODE_THRESHOLD, "half_width": BARCODE_DEAD_BAND},
                    "checksum": "check nibble = bitwise complement of the low 4 bits of the index = 15 - (index mod 16)",
                    "decode_rule": "average each 8x8 block; reject the frame if any block mean is within "
                                   "half_width (25% of the code span) of 502; otherwise above 502 is 1; "
                                   "require start 1,0 and stop 0,1; index = 16 bits; valid if the check "
                                   "nibble equals 15 - (index mod 16)",
                    "limits": "the barcode covers rows 0..7 only; tears elsewhere are invisible to it"},
        "bar": {"width_px": BAR_WIDTH, "step_px_per_frame": BAR_STEP, "rows_from_y": BAR_TOP,
                "level": Y_WHITE, "role": "tear detector below the barcode rows",
                "x_rule": "x(n) = (n * %d) mod W; columns x..x+%d wrap modulo W" % (BAR_STEP, BAR_WIDTH - 1)},
        "index_rule": "frame n carries index n; the index is below 65536 for every allowed length",
        "ideal_display_rule": "on refresh rate r Hz, source frame n is shown from vsync "
                              "ceil(n*r/f) to ceil((n+1)*r/f)-1; a model, not a measurement",
        "refresh_runs": {str(r): refresh_runs(fps, r) for r in REFRESH_RATES}}


# ------------------------------------------------------------------- planning

def plan(width, height, fps_list, seconds):
    """Every output file as a record; sizes are computed before any generation."""
    wide8, wide10 = frame_bytes(width, height, False), frame_bytes(width, height, True)
    records = []

    def add(path, header, n_frames, fbytes, stimulus, fmt, expected, source):
        size = len(header) + n_frames * (len(FRAME_TAG) + fbytes)
        records.append({"path": path, "header": header, "frames": n_frames, "frame_bytes": fbytes,
                        "size": size, "stimulus": stimulus, "format": fmt,
                        "expected": expected, "source": source})

    for name, tag, scale in (("chroma_siting_c420mpeg2_8bit.y4m", "420mpeg2", 1),
                             ("chroma_siting_c420jpeg_8bit.y4m", "420jpeg", 1),
                             ("chroma_siting_c420paldv_8bit.y4m", "420paldv", 1),
                             ("chroma_siting_c420p10_10bit.y4m", "420p10", 4)):
        extra = HEADER_RANGE if scale == 1 else "XYSCSS=420P10 " + HEADER_RANGE
        expected = dict(siting_entry(width, height, tag), scale_to_file_codes=scale)
        add("chroma_siting/" + name, y4m_header(width, height, 1, tag, extra), 2,
            wide10 if scale == 4 else wide8, "chroma_siting", tag, expected, ("siting", scale))
    p10 = "XYSCSS=420P10 " + HEADER_RANGE
    add("scaling/scaling_p10.y4m", y4m_header(width, height, 1, "420p10", p10), 3, wide10,
        "scaling", "420p10", scaling_entry(width, height), ("scaling",))
    add("dither/dither_ramps_p10.y4m", y4m_header(width, height, 1, "420p10", p10), 2, wide10,
        "dither", "420p10", dither_entry(width, height), ("dither",))
    for fps in fps_list:
        add("cadence/cadence_%dfps_p10.y4m" % fps, y4m_header(width, height, fps, "420p10", p10),
            fps * seconds, wide10, "cadence", "420p10",
            cadence_entry(fps, fps * seconds, width), ("cadence", fps * seconds))
    return records


def frames_for(record, width, height):
    """Yield each frame's payload bytes lazily, one frame at a time."""
    kind = record["source"][0]
    cb = flat(width // 2, height // 2, C_NEUTRAL)
    if kind == "siting":
        wide = record["source"][1] == 4
        for y, scb, scr in chroma_siting_frames(width, height, record["source"][1]):
            yield frame_payload(y, scb, scr, wide)
    elif kind in ("scaling", "dither"):
        for y in (scaling_frames if kind == "scaling" else dither_frames)(width, height):
            yield frame_payload(y, cb, cb, True)
    else:
        for index in range(record["source"][1]):
            yield frame_payload(cadence_frame_rows(index, width, height), cb, cb, True)


def _write_file(path, data):
    with path.open("xb") as stream:
        stream.write(data)


def _inside_repository(parent):
    """Case-insensitive-safe: compare real files, not path strings."""
    for ancestor in (parent, *parent.parents):
        try:
            if os.path.samefile(ancestor, PROJECT_ROOT):
                return True
        except OSError:
            continue
    return False


def generate_stimuli(output, width=192, height=108, cadence_fps=DEFAULT_CADENCE_FPS,
                     cadence_seconds=2, max_total_bytes=DEFAULT_MAX_TOTAL_BYTES):
    """Publish a complete new directory; existing paths are never reused."""
    cadence_fps = list(cadence_fps)
    validate_parameters(width, height, cadence_fps, cadence_seconds, max_total_bytes)
    output = Path(output)
    if output.name in ("", ".", ".."):
        raise StimulusError("output must name a new directory")
    try:
        parent = output.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        raise StimulusError("output parent must be an existing directory") from None
    output = parent / output.name
    if not parent.is_dir():
        raise StimulusError("output parent must be an existing directory")
    if _inside_repository(parent):
        raise StimulusError("generated stimuli must be outside the source repository")
    if os.path.lexists(output):
        raise StimulusError("output path already exists")
    records = plan(width, height, cadence_fps, cadence_seconds)
    total = sum(r["size"] for r in records)
    if total > max_total_bytes:
        raise StimulusError("stimuli need %d bytes, above --max-total-bytes %d; nothing was written"
                            % (total, max_total_bytes))
    parameters = {"width": width, "height": height, "cadence_fps": cadence_fps,
                  "cadence_seconds": cadence_seconds}
    design = [{k: r[k] for k in ("path", "header", "frames", "size", "stimulus", "format", "expected")}
              for r in records]
    for item in design:
        item["header"] = item["header"].decode("ascii")
    try:
        generator_hash = sha256(Path(__file__).read_bytes())
    except OSError:
        raise StimulusError("cannot hash generator source") from None
    manifest = {
        "schema": "image-quality-stimuli-v1", "generator": "generate_quality_stimuli.py",
        "coordinate_convention": COORDINATE_CONVENTION,
        "dimensions_and_timing": dict(parameters, stimulus_bytes_total=total),
        "input_hashes": {"generator_sha256": generator_hash,
                         "parameters_canonical_json_sha256": sha256(canonical_json(parameters)),
                         "design_canonical_json_sha256": sha256(canonical_json(design))},
        "external_inputs": [],
        "source_intent": "Owned synthetic digital source fixtures; they prove nothing about a display "
                         "path until captured or measured",
        "encoding": {"container": "YUV4MPEG2 (.y4m)", "chroma_format": "4:2:0 planar",
                     "default_depth_bits": 10, "p10_header_tags": "C420p10 XYSCSS=420P10 XCOLORRANGE=LIMITED",
                     "p10_samples": "unsigned 16-bit little-endian, values 0..1023",
                     "range": "limited: 10-bit Y 64..940, C 64..960, neutral C 512; 8-bit Y 16..235, "
                              "C 16..240, neutral C 128",
                     "matrix_coefficients": "BT.2020 non-constant luminance",
                     "kr": BT2020_KR, "kb": BT2020_KB,
                     "transfer": "PQ / SMPTE ST 2084 (declared; values are code values, not nits)",
                     "primaries": "BT.2020",
                     "chroma_siting": "per file: see files[].expected.siting_tag_implied",
                     "colour_tags": "Y4M has no standard fields for matrix, transfer or primaries; "
                                    "XCOLORRANGE=LIMITED is a non-standard extension some tools read; "
                                    "this manifest is authoritative",
                     "eight_bit_variants": "chroma_siting C420mpeg2, C420jpeg and C420paldv only"},
        "stimuli": {"chroma_siting": "grey luma, saturated chroma step edges, two frames "
                                     "(vertical edges, horizontal edges)",
                    "scaling": "zone plate, line gratings, slanted edge, luma only",
                    "dither": "shallow 10-bit luma ramps, chroma neutral",
                    "cadence": "frame-index barcode plus moving bar, one file per frame rate"},
        "files": [],
    }
    staging = None
    reserved = False
    try:
        staging = Path(tempfile.mkdtemp(prefix=".quality-stimuli-", dir=parent))
        for record in records:
            path = staging / record["path"]
            path.parent.mkdir(exist_ok=True)
            digest, count = hashlib.sha256(), 0
            with path.open("xb") as stream:
                stream.write(record["header"])
                digest.update(record["header"])
                count = len(record["header"])
                for chunk in frames_for(record, width, height):  # lazy: one frame in memory
                    stream.write(chunk)
                    digest.update(chunk)
                    count += len(chunk)
            if count != record["size"]:
                raise StimulusError("internal size mismatch for " + record["path"])
            manifest["files"].append({"path": record["path"], "bytes": count,
                                      "sha256": digest.hexdigest(), "stimulus": record["stimulus"],
                                      "format": record["format"], "frame_count": record["frames"],
                                      "expected": record["expected"]})
        _write_file(staging / "manifest.json", canonical_json(manifest))
        os.mkdir(output, mode=0o700)
        reserved = True
        os.rename(staging, output)
        staging = None
        reserved = False
    except (OSError, ValueError):
        raise StimulusError("cannot write or publish stimuli; no existing output was overwritten") from None
    finally:
        try:
            if staging is not None:
                try:
                    shutil.rmtree(staging)
                except OSError:
                    pass  # never mask the original error
        finally:
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
    parser.add_argument("--cadence-fps", type=int, nargs="+", default=list(DEFAULT_CADENCE_FPS),
                        help="integer frame rates 1..120, default 24 25 30 50 60")
    parser.add_argument("--cadence-seconds", type=int, default=2, help="1..10, default 2")
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES,
                        help="refuse before writing if stimuli exceed this, default 64 MiB")
    args = parser.parse_args(argv)
    try:
        manifest = generate_stimuli(args.output_directory, args.width, args.height, args.cadence_fps,
                                    args.cadence_seconds, args.max_total_bytes)
    except (StimulusError, ValueError) as error:
        print("Image quality stimuli error: %s" % error, file=sys.stderr)
        return 1
    print("Created %d Y4M stimulus files (%d bytes) and manifest.json"
          % (len(manifest["files"]), manifest["dimensions_and_timing"]["stimulus_bytes_total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
