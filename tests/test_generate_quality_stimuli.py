"""Independent Y4M decoding and deterministic image-quality stimulus contracts."""

import contextlib
import hashlib
import inspect
import importlib.util
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_quality_stimuli.py"
SPEC = importlib.util.spec_from_file_location("generate_quality_stimuli", SCRIPT)
stimuli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stimuli)

W, H = 192, 72
FPS = [24, 60]


def read_y4m(data):
    """Parse a Y4M stream without the writer's helpers or constants."""
    end = data.index(b"\n")
    tokens = data[:end].decode("ascii").split(" ")
    if tokens[0] != "YUV4MPEG2":
        raise AssertionError("bad signature")
    tags = {t[0]: t[1:] for t in tokens[1:] if t[0] != "X"}
    extras = [t for t in tokens[1:] if t[0] == "X"]
    width, height = int(tags["W"]), int(tags["H"])
    num, den = (int(v) for v in tags["F"].split(":"))
    colour = tags["C"]
    wide = colour.endswith("p10")
    if colour not in ("420mpeg2", "420jpeg", "420paldv", "420p10"):
        raise AssertionError("unsupported colourspace " + colour)
    size = 2 if wide else 1
    cw, ch = width // 2, height // 2
    frames, pos = [], end + 1
    while pos < len(data):
        if data[pos:pos + 6] != b"FRAME\n":
            raise AssertionError("missing FRAME marker")
        pos += 6
        planes = []
        for pw, ph in ((width, height), (cw, ch), (cw, ch)):
            raw = data[pos:pos + pw * ph * size]
            if len(raw) != pw * ph * size:
                raise AssertionError("truncated plane")
            pos += len(raw)
            if wide:
                values = [raw[i] | raw[i + 1] << 8 for i in range(0, len(raw), 2)]
            else:
                values = list(raw)
            planes.append([values[r * pw:(r + 1) * pw] for r in range(ph)])
        frames.append(planes)
    return {"width": width, "height": height, "fps": (num, den), "colour": colour,
            "extras": extras, "tags": tags, "frames": frames}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode_barcode(luma):
    """Return (index, check_ok); reject (AssertionError) on dead-band blocks or bad markers."""
    bits = []
    for block in range(24):
        samples = [luma[y][block * 8 + x] for y in range(8) for x in range(8)]
        mean = sum(samples) / 64
        if abs(mean - 502) < 0.25 * (940 - 64):
            raise AssertionError("block mean %.1f inside the dead band" % mean)
        bits.append(1 if mean > 502 else 0)
    if bits[:2] != [1, 0] or bits[-2:] != [0, 1]:
        raise AssertionError("bad start/stop markers")
    index = int("".join(map(str, bits[2:18])), 2)
    check = int("".join(map(str, bits[18:22])), 2)
    return index, check == 15 - index % 16


def ycbcr_to_rgb(y, cb, cr, bits):
    k = 1 << (bits - 8)
    yn, cbn, crn = (y - 16 * k) / (219 * k), (cb - 128 * k) / (224 * k), (cr - 128 * k) / (224 * k)
    r = yn + 1.4746 * crn
    b = yn + 1.8814 * cbn
    return r, (yn - 0.2627 * r - 0.0593 * b) / 0.6780, b


def upsample(samples, offset, length):
    """Bilinear: chroma sample i sits at luma position 2i + offset (pixel-centre convention)."""
    out = []
    for x in range(length):
        c = x + 0.5
        i = min(max(math.floor((c - offset) / 2), 0), len(samples) - 2)
        t = min(max((c - (2 * i + offset)) / 2, 0.0), 1.0)
        out.append(samples[i] * (1 - t) + samples[i + 1] * t)
    return out


def crossing(values, level, start):
    """Pixel-centre coordinate of the first linear-interpolated crossing of level."""
    for i in range(len(values) - 1):
        a, b = values[i] - level, values[i + 1] - level
        if abs(a) < 1e-9:
            return start + i + 0.5
        if a * b < 0:
            return start + i + 0.5 + (-a) / (b - a)
    raise AssertionError("no crossing")


def mean_period(row, centre, half):
    """Mean zero-crossing spacing about mid-grey, times two, in a window of samples."""
    points = []
    for i in range(centre - half, centre + half):
        a, b = row[i] - 502, row[i + 1] - 502
        if a * b < 0:
            points.append(i + a / (a - b))
    if len(points) < 3:
        return None
    return 2 * (points[-1] - points[0]) / (len(points) - 1)


def generate(parent, **kwargs):
    options = dict(width=W, height=H, cadence_fps=FPS, cadence_seconds=1)
    options.update(kwargs)
    output = Path(parent) / "out"
    return output, stimuli.generate_stimuli(output, **options)


class StimulusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output, cls.manifest = generate(cls.temp.name)
        cls.entries = {e["path"]: e for e in cls.manifest["files"]}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def load(self, path):
        return read_y4m((self.output / path).read_bytes())

    def test_manifest_lists_every_file_with_matching_hash_and_size(self):
        self.assertEqual(json.loads((self.output / "manifest.json").read_bytes()), self.manifest)
        on_disk = sorted(str(p.relative_to(self.output)) for p in self.output.rglob("*") if p.is_file())
        self.assertEqual(on_disk, sorted(list(self.entries) + ["manifest.json"]))
        for path, entry in self.entries.items():
            data = (self.output / path).read_bytes()
            self.assertEqual((digest(data), len(data)), (entry["sha256"], entry["bytes"]))
        total = sum(e["bytes"] for e in self.entries.values())
        self.assertEqual(self.manifest["dimensions_and_timing"]["stimulus_bytes_total"], total)
        self.assertEqual(self.manifest["external_inputs"], [])
        self.assertEqual(self.manifest["encoding"]["matrix_coefficients"], "BT.2020 non-constant luminance")
        self.assertEqual((self.manifest["encoding"]["kr"], self.manifest["encoding"]["kb"]), (0.2627, 0.0593))
        self.assertIn("i+0.5", self.manifest["coordinate_convention"])
        self.assertIn("code-value domain", self.manifest["coordinate_convention"])

    def test_input_hashes_including_design(self):
        hashes = self.manifest["input_hashes"]
        self.assertEqual(hashes["generator_sha256"], digest(SCRIPT.read_bytes()))
        self.assertEqual(hashes["parameters_canonical_json_sha256"], digest(json_bytes(
            {"width": W, "height": H, "cadence_fps": FPS, "cadence_seconds": 1})))
        design = []
        for path, entry in self.entries.items():
            data = (self.output / path).read_bytes()
            design.append({"path": path, "header": data[:data.index(b"\n") + 1].decode("ascii"),
                           "frames": entry["frame_count"], "size": entry["bytes"],
                           "stimulus": entry["stimulus"], "format": entry["format"],
                           "expected": entry["expected"]})
        self.assertEqual(hashes["design_canonical_json_sha256"], digest(json_bytes(design)))

    def test_headers_and_frame_counts(self):
        p10 = ["XYSCSS=420P10", "XCOLORRANGE=LIMITED"]
        low = ["XCOLORRANGE=LIMITED"]
        expected = {"chroma_siting/chroma_siting_c420mpeg2_8bit.y4m": ("420mpeg2", low, 2),
                    "chroma_siting/chroma_siting_c420jpeg_8bit.y4m": ("420jpeg", low, 2),
                    "chroma_siting/chroma_siting_c420paldv_8bit.y4m": ("420paldv", low, 2),
                    "chroma_siting/chroma_siting_c420p10_10bit.y4m": ("420p10", p10, 2),
                    "scaling/scaling_p10.y4m": ("420p10", p10, 3),
                    "dither/dither_ramps_p10.y4m": ("420p10", p10, 2),
                    "cadence/cadence_24fps_p10.y4m": ("420p10", p10, 24),
                    "cadence/cadence_60fps_p10.y4m": ("420p10", p10, 60)}
        self.assertEqual(sorted(self.entries), sorted(expected))
        for path, (colour, extras, count) in expected.items():
            with self.subTest(path=path):
                video = self.load(path)
                self.assertEqual((video["colour"], video["extras"], len(video["frames"])),
                                 (colour, extras, count))
                self.assertEqual((video["width"], video["height"]), (W, H))
                self.assertEqual(self.entries[path]["frame_count"], count)
        self.assertEqual(self.load("cadence/cadence_24fps_p10.y4m")["fps"], (24, 1))
        self.assertTrue((self.output / "cadence/cadence_60fps_p10.y4m").read_bytes().startswith(
            b"YUV4MPEG2 W192 H72 F60:1 Ip A1:1 C420p10 XYSCSS=420P10 XCOLORRANGE=LIMITED\n"))

    def test_reader_roundtrip_little_endian_and_sample_ranges(self):
        raw = (self.output / "dither/dither_ramps_p10.y4m").read_bytes()
        video = read_y4m(raw)
        start = raw.index(b"\n") + 1 + 6
        self.assertEqual(raw[start], video["frames"][0][0][0][0] & 255)
        self.assertEqual(raw[start + 1], video["frames"][0][0][0][0] >> 8)
        for path in self.entries:
            wide = "p10" in path
            ylo, yhi, chi = (64, 940, 960) if wide else (16, 235, 240)
            clo = 64 if wide else 16
            for y, cb, cr in self.load(path)["frames"]:
                self.assertTrue(all(ylo <= v <= yhi for r in y for v in r), path)
                self.assertTrue(all(clo <= v <= chi for p in (cb, cr) for r in p for v in r), path)

    def test_tag_to_siting_binding_per_path(self):
        table = {"mpeg2": ("left", "centre", True), "jpeg": ("centre", "centre", True),
                 "paldv": ("left", "top", True), "p10": ("left", "top", False)}
        for path, entry in self.entries.items():
            if entry["stimulus"] != "chroma_siting":
                continue
            name = path.split("_c420")[1].split("_")[0]
            implied = entry["expected"]["siting_tag_implied"]
            self.assertEqual((implied["horizontal"], implied["vertical"], implied["carried_by_file"]),
                             table[name], path)
            self.assertEqual(implied["h273_chroma_loc_type"],
                             {"mpeg2": 0, "jpeg": 1, "paldv": 2, "p10": 2}[name])
            self.assertEqual(self.load(path)["colour"], "420" + name)
            self.assertEqual(("NOT carried" in implied["note"]), name == "p10")

    def test_chroma_steps_gamut_and_siting_midpoints_from_upsampled_planes(self):
        files = [p for p in self.entries if p.startswith("chroma_siting/")]
        videos = {p: self.load(p) for p in files}
        pre = "chroma_siting/chroma_siting_c420"
        mp, jp, pal, p10 = (videos[pre + n] for n in ("mpeg2_8bit.y4m", "jpeg_8bit.y4m",
                                                       "paldv_8bit.y4m", "p10_10bit.y4m"))
        self.assertEqual(mp["frames"], jp["frames"])
        self.assertEqual(mp["frames"], pal["frames"])
        self.assertEqual([[v // 4 for v in r] for r in p10["frames"][0][1]], mp["frames"][0][1])
        self.assertEqual([[v // 4 for v in r] for r in p10["frames"][1][2]], mp["frames"][1][2])
        for path in files:
            entry = self.entries[path]["expected"]
            bits = 10 if "10bit" in path else 8
            scale = 4 if bits == 10 else 1
            y, cb, cr = videos[path]["frames"][0]
            self.assertTrue(all(v == 120 * scale for r in y for v in r))
            colours = {(cb[3][i], cr[3][i]) for i in range(W // 2)}
            self.assertEqual(len(colours), 2)
            for ccb, ccr in colours:
                rgb = ycbcr_to_rgb(120 * scale, ccb, ccr, bits)
                self.assertTrue(all(-1e-9 <= c <= 1 + 1e-9 for c in rgb), (path, rgb))
            recorded = entry["rgb_prime_of_chroma_a_b_at_luma"]
            for rgb in (recorded["a"], recorded["b"]):
                self.assertTrue(all(0 <= c <= 1 for c in rgb))
            # horizontal: explicit left (offset 0.5) and centre (offset 1) bilinear kernels
            row = cb[3]
            for edge in entry["vertical_edges"]:
                k = edge["k"]
                level = (row[k - 1] + row[k]) / 2
                found = {}
                for name, offset in (("left", 0.5), ("centre", 1.0)):
                    up = upsample(row, offset, W)
                    lo = 2 * k - 8
                    found[name] = crossing(up[lo:lo + 16], level, lo)
                    self.assertAlmostEqual(found[name], edge["midpoint_luma_x_" + name], places=6)
                self.assertAlmostEqual(found["centre"] - found["left"], 0.5, places=6)
                self.assertEqual(edge["midpoint_luma_x_for_this_file"],
                                 edge["midpoint_luma_x_" + entry["siting_tag_implied"]["horizontal"]])
            col = [videos[path]["frames"][1][1][j][5] for j in range(H // 2)]
            for edge in entry["horizontal_edges"]:
                j = edge["j"]
                level = (col[j - 1] + col[j]) / 2
                found = {}
                for name, offset in (("top", 0.5), ("centre", 1.0)):
                    up = upsample(col, offset, H)
                    lo = 2 * j - 8
                    found[name] = crossing(up[lo:lo + 16], level, lo)
                    self.assertAlmostEqual(found[name], edge["midpoint_luma_y_" + name], places=6)
                self.assertAlmostEqual(found["centre"] - found["top"], 0.5, places=6)
                self.assertEqual(edge["midpoint_luma_y_for_this_file"],
                                 edge["midpoint_luma_y_" + entry["siting_tag_implied"]["vertical"]])

    def test_out_of_gamut_chroma_pair_is_refused(self):
        with mock.patch.object(stimuli, "CHROMA_A8", (16, 240)):
            with self.assertRaises(stimuli.StimulusError):
                next(stimuli.chroma_siting_frames(W, H, 1))

    def test_cadence_barcode_decodes_every_frame_and_bar_moves(self):
        for fps in FPS:
            path = "cadence/cadence_%dfps_p10.y4m" % fps
            video = self.load(path)
            self.assertEqual(len(video["frames"]), fps)
            expected = self.entries[path]["expected"]
            self.assertEqual(expected["barcode"]["rect_xywh"], [0, 0, 192, 8])
            for n, (y, cb, cr) in enumerate(video["frames"]):
                self.assertEqual(decode_barcode(y), (n, True))
                x0 = (n * 4) % W
                cols = {x for x in range(W) if y[40][x] == 940}
                self.assertEqual(cols, {(x0 + i) % W for i in range(8)})
                self.assertTrue(all(v == 512 for r in cb for v in r))
                self.assertTrue(all(v in (64, 940) for r in y for v in r))

    def test_blended_frames_are_rejected_by_the_decoder(self):
        video = self.load("cadence/cadence_24fps_p10.y4m")
        for n in (0, 5, 11, 22):
            a, b = video["frames"][n][0], video["frames"][n + 1][0]
            for t in (0.3, 0.5, 0.7):
                blend = [[round(p * (1 - t) + q * t) for p, q in zip(ra, rb)] for ra, rb in zip(a, b)]
                with self.subTest(n=n, t=t), self.assertRaises(AssertionError):
                    decode_barcode(blend)

    def test_bar_wraps_at_width(self):
        self.assertEqual(stimuli.bar_x(48, 192), 0)
        self.assertEqual(stimuli.bar_x(47, 192), 188)

    def test_refresh_runs_against_independent_vsync_model(self):
        from fractions import Fraction
        for fps in FPS:
            runs = self.entries["cadence/cadence_%dfps_p10.y4m" % fps]["expected"]["refresh_runs"]
            self.assertEqual(sorted(runs), ["120", "144", "50", "60"])
            for r in (60, 50, 120, 144):
                period = runs[str(r)]["period_frames"]
                starts = [math.ceil(Fraction(n * r, fps)) for n in range(period + 1)]
                self.assertEqual(runs[str(r)]["runs_over_period"],
                                 [starts[n + 1] - starts[n] for n in range(period)])
                self.assertEqual(sum(runs[str(r)]["runs_over_period"]) * fps, period * r)
        c24 = self.entries["cadence/cadence_24fps_p10.y4m"]["expected"]["refresh_runs"]["60"]
        self.assertEqual(c24["repeating_unit"], [3, 2])
        self.assertEqual(stimuli.refresh_runs(25, 60)["runs_over_period"], [3, 2, 3, 2, 2])
        self.assertEqual(stimuli.refresh_runs(60, 60)["repeating_unit"], [1])

    def test_dither_columns_bands_and_level_models(self):
        from fractions import Fraction
        video = self.load("dither/dither_ramps_p10.y4m")
        expected = self.entries["dither/dither_ramps_p10.y4m"]["expected"]
        models = {"limited_truncate": lambda c: c // 4,
                  "limited_round": lambda c: math.floor(Fraction(c, 4) + Fraction(1, 2)),
                  "full_range_expand_round": lambda c: math.floor(Fraction((c - 64) * 255, 876) + Fraction(1, 2)),
                  "full_range_expand_truncate": lambda c: math.floor(Fraction((c - 64) * 255, 876))}
        self.assertEqual(set(expected["band_model_rules"]), set(models))
        for (y, cb, cr), ramp, (low, high) in zip(video["frames"], expected["ramps"],
                                                  ((64, 96), (448, 480))):
            codes = ramp["column_codes"]
            self.assertNotIn("codes_per_8bit_level", ramp)
            self.assertEqual(len(codes), W)
            for row in y:
                self.assertEqual(row, codes)
            self.assertEqual((min(codes), max(codes)), (low, high))
            self.assertEqual(codes, sorted(codes))
            self.assertEqual(ramp["distinct_codes_10bit"], 33)
            self.assertEqual(ramp["band_models"]["limited_truncate"]["distinct_8bit_levels"], 9)
            for name, function in models.items():
                levels = [function(c) for c in codes]
                recorded = ramp["band_models"][name]
                self.assertEqual(recorded["distinct_8bit_levels"], len(set(levels)))
                covered = []
                for band in recorded["bands"]:
                    span = levels[band["first_column"]:band["last_column"] + 1]
                    self.assertEqual(set(span), {band["level"]})
                    covered += list(range(band["first_column"], band["last_column"] + 1))
                self.assertEqual(covered, list(range(W)))
            self.assertTrue(all(v == 512 for r in cb for v in r))
        self.assertIn("digital", expected["ramps"][0]["capture_scope"])
        self.assertIn("unmeasurable", expected["ramps"][0]["capture_scope"])

    def test_zone_plate_formula_period_and_per_axis_aliasing(self):
        video = self.load("scaling/scaling_p10.y4m")
        expected = self.entries["scaling/scaling_p10.y4m"]["expected"]
        zone = expected["zone_plate"]
        radius = zone["R_pixels"]
        self.assertAlmostEqual(radius, math.hypot(W, H), places=5)
        self.assertNotIn("source_nyquist_ring_radius_pixels", zone)
        plate = video["frames"][0][0]
        for x, y in ((0, 0), (96, 36), (95, 35), (10, 50), (190, 70), (100, 20)):
            r2 = (x + 0.5 - W / 2) ** 2 + (y + 0.5 - H / 2) ** 2
            self.assertEqual(plate[y][x], math.floor(502 + 438 * math.cos(math.pi * r2 / radius) + 0.5))
        row = plate[36]
        for d in (30, 45):
            period = mean_period(row, 96 + d, 10)
            self.assertLess(abs(period - radius / d) / (radius / d), 0.15, (d, period))
        boundaries = zone["boundaries_by_uniform_scale"]["0.5"]
        self.assertAlmostEqual(boundaries["alias_boundary_abs_dx_source_px"], 0.25 * radius)
        self.assertTrue(boundaries["x_axis_can_alias"])
        self.assertFalse(boundaries["y_axis_can_alias"])
        self.assertFalse(zone["boundaries_by_uniform_scale"]["1"]["x_axis_can_alias"])
        decimated = row[::2]
        before, beyond = 30, 80
        self.assertTrue(before < boundaries["alias_boundary_abs_dx_source_px"] < beyond)
        wanted = radius / (2 * before)
        measured = mean_period(decimated, (96 + before) // 2, 6)
        self.assertLess(abs(measured - wanted) / wanted, 0.2, measured)
        wanted = radius / (2 * beyond)
        measured = mean_period(decimated, (96 + beyond) // 2, 6)
        self.assertGreater(measured, 1.5 * wanted)
        self.assertGreaterEqual(measured, 2.0)
        for y, cb, cr in video["frames"]:
            self.assertTrue(all(v == 512 for r in cb for v in r))
        grat = video["frames"][1][0]
        self.assertEqual([grat[0][x] for x in range(4)], [940, 64, 940, 64])
        self.assertEqual([grat[0][x] for x in range(96, 104)], [940, 940, 64, 64, 940, 940, 64, 64])
        self.assertEqual([grat[y][0] for y in range(36, 40)], [940, 64, 940, 64])
        self.assertEqual([grat[y][100] for y in range(36, 42)], [940, 940, 64, 64, 940, 940])
        self.assertEqual(expected["line_gratings"]["stripe_widths_px"], [1, 2])
        slant = video["frames"][2][0]
        slope = expected["slanted_edge"]["slope_dx_per_dy"]
        self.assertAlmostEqual(slope, math.tan(math.radians(5)), places=10)
        for y in (0, 36, 71):
            edge = W / 2 + slope * (y + 0.5 - H / 2)
            self.assertEqual([x for x in range(W) if slant[y][x] == 940][0], math.floor(edge - 0.5) + 1)

    def test_deterministic_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, a = generate(temporary)
            second = Path(temporary) / "second"
            b = stimuli.generate_stimuli(second, W, H, FPS, 1)
            self.assertEqual(a, b)
            for path in self.entries:
                self.assertEqual((first / path).read_bytes(), (second / path).read_bytes())
            self.assertEqual((first / "manifest.json").read_bytes(), (second / "manifest.json").read_bytes())


class FailureTests(unittest.TestCase):
    def test_existing_directory_file_and_symlinks_are_never_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            existing = parent / "out"
            existing.mkdir()
            (existing / "keep").write_bytes(b"untouched")
            file_dest = parent / "file"
            file_dest.write_bytes(b"sentinel")
            link = parent / "link"
            link.symlink_to(existing, target_is_directory=True)
            dangling = parent / "dangling"
            dangling.symlink_to(parent / "nowhere")
            for destination in (existing, file_dest, link, dangling):
                with self.subTest(destination=destination.name), self.assertRaises(stimuli.StimulusError):
                    stimuli.generate_stimuli(destination, W, H, FPS, 1)
            self.assertEqual((existing / "keep").read_bytes(), b"untouched")
            self.assertEqual(file_dest.read_bytes(), b"sentinel")
            self.assertTrue(dangling.is_symlink() and not dangling.exists())
            self.assertEqual(sorted(p.name for p in parent.iterdir()),
                             ["dangling", "file", "link", "out"])
            with self.assertRaises(stimuli.StimulusError):
                stimuli.generate_stimuli(parent / "no" / "out", W, H, FPS, 1)

    def test_destination_inside_repository_is_refused(self):
        inside = stimuli.PROJECT_ROOT / "scripts" / "zz-never-created"
        with self.assertRaises(stimuli.StimulusError):
            stimuli.generate_stimuli(inside, W, H, FPS, 1)
        self.assertFalse(inside.exists())
        self.assertTrue(stimuli._inside_repository(stimuli.PROJECT_ROOT / "scripts"))
        with tempfile.TemporaryDirectory() as temporary:
            self.assertFalse(stimuli._inside_repository(Path(temporary)))

    def test_destination_appearing_during_generation_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            output = parent / "out"
            write = stimuli._write_file

            def racing_write(path, data):
                write(path, data)
                if path.name == "manifest.json":
                    output.mkdir()
                    (output / "other-file").write_bytes(b"untouched")

            with mock.patch.object(stimuli, "_write_file", side_effect=racing_write):
                with self.assertRaises(stimuli.StimulusError):
                    stimuli.generate_stimuli(output, W, H, FPS, 1)
            self.assertEqual(list(parent.iterdir()), [output])
            self.assertEqual((output / "other-file").read_bytes(), b"untouched")

    def test_staging_cleaned_on_write_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with mock.patch.object(stimuli, "_write_file", side_effect=OSError("simulated")):
                with self.assertRaises(stimuli.StimulusError):
                    stimuli.generate_stimuli(parent / "out", W, H, FPS, 1)
            self.assertEqual(list(parent.iterdir()), [])
            with mock.patch.object(stimuli.os, "rename", side_effect=OSError("simulated")):
                with self.assertRaises(stimuli.StimulusError):
                    stimuli.generate_stimuli(parent / "out", W, H, FPS, 1)
            self.assertEqual(list(parent.iterdir()), [])

    def test_cleanup_failure_does_not_mask_original_error_or_skip_reservation_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with mock.patch.object(stimuli.os, "rename", side_effect=OSError("simulated")), \
                    mock.patch.object(stimuli.shutil, "rmtree", side_effect=PermissionError("rm")):
                with self.assertRaises(stimuli.StimulusError) as caught:
                    stimuli.generate_stimuli(parent / "out", W, H, FPS, 1)
            self.assertIn("cannot write or publish", str(caught.exception))
            self.assertFalse((parent / "out").exists())

    def test_staging_cleaned_on_mid_stream_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with mock.patch.object(stimuli, "cadence_frame_rows", side_effect=ValueError("simulated")):
                with self.assertRaises(stimuli.StimulusError):
                    stimuli.generate_stimuli(parent / "out", W, H, FPS, 1)
            self.assertEqual(list(parent.iterdir()), [])

    def test_frames_are_streamed_lazily_to_disk(self):
        real = stimuli.frames_for
        checked = []
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)

            def wrapper(record, width, height):
                generator = real(record, width, height)
                self.assertTrue(inspect.isgenerator(generator))

                def inner():
                    sent = 0
                    for chunk in generator:
                        staged = list(parent.glob(".quality-stimuli-*/" + record["path"]))
                        # everything yielded earlier is already on disk (8 KiB buffer slack)
                        self.assertGreaterEqual(staged[0].stat().st_size,
                                                len(record["header"]) + sent - 8192)
                        sent += len(chunk)
                        checked.append(sent)
                        yield chunk
                return inner()

            with mock.patch.object(stimuli, "frames_for", side_effect=wrapper):
                stimuli.generate_stimuli(parent / "out", W, H, FPS, 1)
        self.assertGreater(len(checked), 60)

    def test_max_total_bytes_refusal_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with mock.patch.object(stimuli.tempfile, "mkdtemp", side_effect=AssertionError("wrote")):
                with self.assertRaises(stimuli.StimulusError) as caught:
                    stimuli.generate_stimuli(parent / "out", W, H, FPS, 1, max_total_bytes=1000)
            self.assertIn("nothing was written", str(caught.exception))
            self.assertEqual(list(parent.iterdir()), [])
            out, manifest = generate(parent)
            total = manifest["dimensions_and_timing"]["stimulus_bytes_total"]
            stimuli.generate_stimuli(parent / "exact", W, H, FPS, 1, max_total_bytes=total)
            with self.assertRaises(stimuli.StimulusError):
                stimuli.generate_stimuli(parent / "third", W, H, FPS, 1, max_total_bytes=total - 1)

    def test_parameter_bounds(self):
        bad = [dict(width=190), dict(width=2), dict(width=3842), dict(height=70),
               dict(height=2162), dict(height=73), dict(cadence_fps=[0]), dict(cadence_fps=[121]),
               dict(cadence_fps=[24, 24]), dict(cadence_fps=[]), dict(cadence_fps=[2.5]),
               dict(cadence_seconds=0), dict(cadence_seconds=11), dict(max_total_bytes=0)]
        with tempfile.TemporaryDirectory() as temporary:
            for index, overrides in enumerate(bad):
                with self.subTest(overrides=overrides), self.assertRaises(stimuli.StimulusError):
                    options = dict(width=W, height=H, cadence_fps=FPS, cadence_seconds=1)
                    options.update(overrides)
                    stimuli.generate_stimuli(Path(temporary) / ("o%d" % index), **options)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_cli_failure_and_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "out"
            stderr, stdout = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(stimuli.main([str(output), "--width", "191"]), 1)
            self.assertIn("Image quality stimuli error: require even width", stderr.getvalue())
            self.assertFalse(output.exists())
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(stimuli.main([str(output), "--width", "192", "--height", "72",
                                               "--cadence-fps", "24", "--cadence-seconds", "1"]), 0)
            self.assertIn("Created 7 Y4M stimulus files", stdout.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(stimuli.main([str(output)]), 1)


if __name__ == "__main__":
    unittest.main()
