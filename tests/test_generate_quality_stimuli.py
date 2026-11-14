"""Independent Y4M decoding and deterministic image-quality stimulus contracts."""

import contextlib
import hashlib
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
    if colour not in ("420mpeg2", "420jpeg", "420p10"):
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
    """Return (index, checksum_ok) from block centres, or raise."""
    bits = []
    for block in range(24):
        samples = [luma[y][block * 8 + x] for y in range(8) for x in range(8)]
        bits.append(1 if sum(samples) / 64 > 502 else 0)
    if bits[:2] != [1, 0] or bits[-2:] != [0, 1]:
        raise AssertionError("bad start/stop markers")
    index = int("".join(map(str, bits[2:18])), 2)
    check = int("".join(map(str, bits[18:22])), 2)
    return index, check == index % 16


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

    def test_input_hashes(self):
        hashes = self.manifest["input_hashes"]
        self.assertEqual(hashes["generator_sha256"], digest(SCRIPT.read_bytes()))
        self.assertEqual(hashes["parameters_canonical_json_sha256"], digest(json_bytes(
            {"width": W, "height": H, "cadence_fps": FPS, "cadence_seconds": 1})))

    def test_headers_and_frame_counts(self):
        expected = {"chroma_siting/chroma_siting_c420mpeg2_8bit.y4m": ("420mpeg2", [], 2),
                    "chroma_siting/chroma_siting_c420jpeg_8bit.y4m": ("420jpeg", [], 2),
                    "chroma_siting/chroma_siting_c420p10_10bit.y4m": ("420p10", ["XYSCSS=420P10"], 2),
                    "scaling/scaling_p10.y4m": ("420p10", ["XYSCSS=420P10"], 3),
                    "dither/dither_ramps_p10.y4m": ("420p10", ["XYSCSS=420P10"], 2),
                    "cadence/cadence_24fps_p10.y4m": ("420p10", ["XYSCSS=420P10"], 24),
                    "cadence/cadence_60fps_p10.y4m": ("420p10", ["XYSCSS=420P10"], 60)}
        self.assertEqual(sorted(self.entries), sorted(expected))
        for path, (colour, extras, count) in expected.items():
            with self.subTest(path=path):
                video = self.load(path)
                self.assertEqual((video["colour"], video["extras"], len(video["frames"])),
                                 (colour, extras, count))
                self.assertEqual((video["width"], video["height"]), (W, H))
                self.assertEqual(self.entries[path]["frame_count"], count)
        self.assertEqual(self.load("cadence/cadence_24fps_p10.y4m")["fps"], (24, 1))
        self.assertEqual(self.load("cadence/cadence_60fps_p10.y4m")["fps"], (60, 1))
        self.assertTrue((self.output / "cadence/cadence_60fps_p10.y4m").read_bytes()
                        .startswith(b"YUV4MPEG2 W192 H72 F60:1 Ip A1:1 C420p10 XYSCSS=420P10\n"))

    def test_reader_roundtrip_of_sample_ranges_and_little_endian(self):
        video = self.load("dither/dither_ramps_p10.y4m")
        raw = (self.output / "dither/dither_ramps_p10.y4m").read_bytes()
        start = raw.index(b"\n") + 1 + 6
        self.assertEqual(raw[start], video["frames"][0][0][0][0] & 255)
        self.assertEqual(raw[start + 1], video["frames"][0][0][0][0] >> 8)
        for path in self.entries:
            if "10bit" in path or "p10" in path:
                for y, cb, cr in self.load(path)["frames"]:
                    self.assertTrue(all(64 <= v <= 940 for r in y for v in r), path)
                    self.assertTrue(all(64 <= v <= 960 for p in (cb, cr) for r in p for v in r), path)

    def test_chroma_steps_and_siting_midpoints_match_planes(self):
        files = [p for p in self.entries if p.startswith("chroma_siting/")]
        videos = {p: self.load(p) for p in files}
        mp, jp, p10 = (videos["chroma_siting/chroma_siting_c420%s.y4m" % n]
                       for n in ("mpeg2_8bit", "jpeg_8bit", "p10_10bit"))
        self.assertEqual(mp["frames"], jp["frames"])
        for path in files:
            entry = self.entries[path]["expected"]
            video = videos[path]
            scale = 4 if "10bit" in path else 1
            y, cb, cr = video["frames"][0]
            self.assertTrue(all(v == 120 * scale for r in y for v in r))
            a = (90 * scale, 240 * scale)
            b = (240 * scale, 90 * scale)
            for edge in entry["vertical_edges"]:
                k = edge["k"]
                row = [(cb[3][i], cr[3][i]) for i in range(W // 2)]
                self.assertEqual((row[k - 1], row[k]) in ((a, b), (b, a)), True)
                self.assertEqual(row[k - 2], row[k - 1])
                self.assertEqual(row[k], row[k + 1])
                self.assertEqual(edge["midpoint_luma_x_left_cosited"], (2 * (k - 1) + 2 * k) / 2)
                self.assertEqual(edge["midpoint_luma_x_centre"], (2 * (k - 1) + 0.5 + 2 * k + 0.5) / 2)
                self.assertEqual(edge["midpoint_luma_x_centre"] - edge["midpoint_luma_x_left_cosited"], 0.5)
            _, hcb, hcr = video["frames"][1]
            for edge in entry["horizontal_edges"]:
                j = edge["j"]
                self.assertNotEqual((hcb[j - 1][5], hcr[j - 1][5]), (hcb[j][5], hcr[j][5]))
                self.assertEqual(len(set(hcb[j])), 1)
                self.assertEqual(edge["midpoint_luma_y_top"], (2 * (j - 1) + 2 * j) / 2)
                self.assertEqual(edge["midpoint_luma_y_centre"], (2 * (j - 1) + 0.5 + 2 * j + 0.5) / 2)
        self.assertEqual([[v // 4 for v in r] for r in p10["frames"][0][1]], mp["frames"][0][1])
        self.assertEqual([[v // 4 for v in r] for r in p10["frames"][1][2]], mp["frames"][1][2])
        implied = {p: self.entries[p]["expected"]["siting_tag_implied"]["horizontal"] for p in files}
        self.assertEqual(sorted(implied.values()), ["centre", "left", "left"])

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

    def test_bar_wraps_at_width(self):
        self.assertEqual(stimuli.bar_x(48, 192), 0)
        self.assertEqual(stimuli.bar_x(47, 192), 188)

    def test_dither_columns_match_manifest_and_levels(self):
        video = self.load("dither/dither_ramps_p10.y4m")
        ramps = self.entries["dither/dither_ramps_p10.y4m"]["expected"]["ramps"]
        for (y, cb, cr), ramp, (low, high) in zip(video["frames"], ramps, ((64, 96), (448, 480))):
            codes = ramp["column_codes"]
            self.assertEqual(len(codes), W)
            for row in y:
                self.assertEqual(row, codes)
            self.assertEqual((min(codes), max(codes)), (low, high))
            self.assertEqual(codes, sorted(codes))
            self.assertEqual(ramp["distinct_codes_10bit"], 33)
            self.assertEqual(ramp["distinct_levels_8bit_truncated"], 9)
            self.assertEqual(len({c >> 2 for c in codes}), 9)
            self.assertTrue(all(v == 512 for r in cb for v in r))
            self.assertTrue(all(v == 512 for r in cr for v in r))

    def test_zone_plate_formula_and_scaling_content(self):
        video = self.load("scaling/scaling_p10.y4m")
        expected = self.entries["scaling/scaling_p10.y4m"]["expected"]
        zone = expected["zone_plate"]
        radius = zone["R_pixels"]
        self.assertAlmostEqual(radius, math.hypot(W, H), places=5)
        self.assertAlmostEqual(zone["source_nyquist_ring_radius_pixels"], radius / 2)
        plate = video["frames"][0][0]
        for x, y in ((0, 0), (96, 36), (95, 35), (10, 50), (190, 70), (100, 20)):
            r2 = (x + 0.5 - W / 2) ** 2 + (y + 0.5 - H / 2) ** 2
            self.assertEqual(plate[y][x], math.floor(502 + 438 * math.cos(math.pi * r2 / radius) + 0.5))
        self.assertTrue(all(64 <= v <= 940 for r in plate for v in r))
        # local frequency r/R: horizontal phase advance per pixel at x offset d is ~ d/R cycles
        d = 60
        r1, r2_ = d, d + 1
        self.assertAlmostEqual((r2_ ** 2 - r1 ** 2) / (2 * radius), (d + 0.5) / radius, places=9)
        self.assertEqual(zone["predicted_ring_radius_source_pixels_by_scale"]["0.5"], 0.25 * radius)
        for y, cb, cr in video["frames"]:
            self.assertTrue(all(v == 512 for r in cb for v in r))
        grat = video["frames"][1][0]
        self.assertEqual([grat[0][x] for x in range(4)], [940, 64, 940, 64])
        self.assertEqual([grat[0][x] for x in range(96, 104)], [940, 940, 64, 64, 940, 940, 64, 64])
        self.assertEqual([grat[y][0] for y in range(36, 40)], [940, 64, 940, 64])
        self.assertEqual([grat[y][100] for y in range(36, 42)], [940, 940, 64, 64, 940, 940])
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
            self.assertEqual((first / "cadence/cadence_24fps_p10.y4m").read_bytes(),
                             (self.output / "cadence/cadence_24fps_p10.y4m").read_bytes())


class FailureTests(unittest.TestCase):
    def test_existing_output_is_refused_and_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            existing = parent / "out"
            existing.mkdir()
            (existing / "keep").write_bytes(b"untouched")
            with self.assertRaises(stimuli.StimulusError):
                stimuli.generate_stimuli(existing, W, H, FPS, 1)
            self.assertEqual((existing / "keep").read_bytes(), b"untouched")
            self.assertEqual(sorted(p.name for p in parent.iterdir()), ["out"])
            with self.assertRaises(stimuli.StimulusError):
                stimuli.generate_stimuli(parent / "no" / "out", W, H, FPS, 1)

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

    def test_staging_cleaned_on_mid_stream_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with mock.patch.object(stimuli, "cadence_frame_rows", side_effect=ValueError("simulated")):
                with self.assertRaises(stimuli.StimulusError):
                    stimuli.generate_stimuli(parent / "out", W, H, FPS, 1)
            self.assertEqual(list(parent.iterdir()), [])

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
            out.rename(parent / "moved")
            stimuli.generate_stimuli(out, W, H, FPS, 1, max_total_bytes=total)
            (parent / "moved").rename(parent / "moved2")
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
            self.assertIn("Created 6 Y4M stimulus files", stdout.getvalue())
            self.assertEqual(stimuli.main([str(output)]), 1)


if __name__ == "__main__":
    unittest.main()
