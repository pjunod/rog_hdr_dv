"""Independent TIFF decoding and deterministic synthetic source contracts."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_hdr_corpus.py"
SPEC = importlib.util.spec_from_file_location("generate_hdr_corpus", SCRIPT)
corpus = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(corpus)


def decode_tiff(data):
    """Read TIFF tags and pixels without the writer's constants or helpers."""
    if data[:2] != b"II" or struct.unpack_from("<H", data, 2)[0] != 42:
        raise AssertionError("not little-endian classic TIFF")
    start = struct.unpack_from("<I", data, 4)[0]
    count = struct.unpack_from("<H", data, start)[0]
    entries = {}
    tag_order = []
    for index in range(count):
        offset = start + 2 + index * 12
        tag, kind, length = struct.unpack_from("<HHI", data, offset)
        tag_order.append(tag)
        if tag in entries or kind not in (3, 4):
            raise AssertionError("duplicate tag or unsupported field")
        size = {3: 2, 4: 4}[kind] * length
        value_start = offset + 8 if size <= 4 else struct.unpack_from("<I", data, offset + 8)[0]
        if value_start + size > len(data):
            raise AssertionError("out of bounds TIFF field")
        entries[tag] = (kind, struct.unpack_from("<" + {3: "H", 4: "I"}[kind] * length,
                                                data, value_start))
    if tag_order != sorted(tag_order):
        raise AssertionError("unsorted TIFF tags")
    if struct.unpack_from("<I", data, start + 2 + count * 12)[0] != 0:
        raise AssertionError("unexpected second image")
    width, height = entries[256][1][0], entries[257][1][0]
    expected = {256: (4, (width,)), 257: (4, (height,)),
                258: (3, (16, 16, 16)), 259: (3, (1,)), 262: (3, (2,)),
                274: (3, (1,)), 277: (3, (3,)), 278: (4, (height,)),
                279: (4, (width * height * 6,)), 284: (3, (1,)),
                339: (3, (1, 1, 1))}
    for tag, value in expected.items():
        if entries.get(tag) != value:
            raise AssertionError("incorrect TIFF contract tag %d" % tag)
    if set(entries) != set(expected) | {273} or entries[273][0] != 4:
        raise AssertionError("unexpected TIFF directory")
    pixel_start = entries[273][1][0]
    if pixel_start < start + 2 + count * 12 + 4 or pixel_start + width * height * 6 != len(data):
        raise AssertionError("bad strip offset or length")
    values = struct.unpack_from("<" + "H" * (width * height * 3), data, pixel_start)
    return width, height, [values[index:index + 3] for index in range(0, len(values), 3)]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


class EncodingTests(unittest.TestCase):
    def test_pq_golden_values_and_full_range_quantization(self):
        # Independently tabulated inverse ST 2084 values, not writer-derived.
        for nits, normalized, code in ((0, 0.000000730955902578, 0),
                                       (1, 0.149945732100180, 9827),
                                       (100, 0.508078421517399, 33297),
                                       (1000, 0.751827096247041, 49271)):
            with self.subTest(nits=nits):
                self.assertAlmostEqual(corpus.pq_encode(nits), normalized, places=12)
                self.assertEqual(corpus.quantize(nits), code)
        self.assertEqual(corpus.quantize(203), 38055)
        self.assertEqual(corpus.quantize(400), 42767)

    def test_monotonic_channel_range_and_invalid_values(self):
        values = [corpus.quantize(index / 10) for index in range(10001)]
        self.assertEqual(values, sorted(values))
        self.assertEqual((values[0], values[-1]), (0, 49271))
        for invalid in (-0.01, 1000.01, float("nan"), float("inf")):
            with self.subTest(value=invalid), self.assertRaises(corpus.CorpusError):
                corpus.pq_encode(invalid)

    def test_source_patch_bounds_and_colored_luminance(self):
        frames = corpus.corpus_design(24, 8)
        for frame in frames:
            for region in frame["patches"]:
                x, y, width, height = region["rect_xywh"]
                self.assertTrue(0 <= x < 24 and 0 < width <= 24 - x)
                self.assertTrue(0 <= y < 8 and 0 < height <= 8 - y)
                self.assertTrue(all(0 <= value <= 1000 for value in region["linear_rgb_cd_m2"]))
        red = next(p for p in frames[4]["patches"] if p["label"] == "red_channels_1000")
        self.assertEqual(red["linear_rgb_cd_m2"], [1000, 0, 0])
        self.assertEqual(red["photometric_y_cd_m2"], 262.7)
        self.assertEqual(red["encoded_rgb_u16"], [49271, 0, 0])
        ramp = frames[0]["patches"]
        self.assertEqual(ramp[0]["linear_rgb_cd_m2"], [0, 0, 0])
        self.assertEqual(ramp[-1]["linear_rgb_cd_m2"], [1000, 1000, 1000])
        self.assertEqual([p["linear_rgb_cd_m2"][0] for p in frames[2]["patches"]],
                         [0, 100, 203, 400, 616, 1000])


class CorpusTests(unittest.TestCase):
    def test_independent_tiff_decode_agrees_with_every_manifest_patch(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "corpus"
            manifest = corpus.generate_corpus(output, width=24, height=8, fps=25)
            self.assertEqual(json.loads((output / "manifest.json").read_bytes()), manifest)
            self.assertEqual(manifest["dimensions_and_timing"], {
                "width": 24, "height": 8, "fps_numerator": 25,
                "fps_denominator": 1, "frame_count": 6})
            self.assertEqual(sorted(p.name for p in output.iterdir()),
                             ["frame_%06d.tif" % index for index in range(6)] + ["manifest.json"])
            for index, frame in enumerate(manifest["frames"]):
                self.assertEqual(frame["index"], index)
                self.assertEqual(frame["scene_id"], index)
                self.assertEqual(frame["cut_before"], index != 0)
                payload = (output / frame["filename"]).read_bytes()
                self.assertEqual((digest(payload), len(payload)), (frame["sha256"], frame["bytes"]))
                width, height, pixels = decode_tiff(payload)
                self.assertEqual((width, height), (24, 8))
                expected = [None] * (width * height)
                for region in frame["patches"]:
                    x, y, w, h = region["rect_xywh"]
                    for row in range(y, y + h):
                        for column in range(x, x + w):
                            expected[row * width + column] = tuple(region["encoded_rgb_u16"])
                self.assertNotIn(None, expected)
                self.assertEqual(pixels, expected)

    def test_deterministic_files_and_all_input_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, second = Path(temporary) / "first", Path(temporary) / "second"
            manifest = corpus.generate_corpus(first, 24, 8)
            self.assertEqual(manifest, corpus.generate_corpus(second, 24, 8))
            for path in first.iterdir():
                self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
            design = [{key: value for key, value in frame.items() if key not in ("sha256", "bytes")}
                      for frame in manifest["frames"]]
            self.assertEqual(manifest["input_hashes"], {
                "generator_sha256": digest(SCRIPT.read_bytes()),
                "parameters_canonical_json_sha256": digest(json_bytes(manifest["dimensions_and_timing"])),
                "design_canonical_json_sha256": digest(json_bytes(design))})
            self.assertEqual(manifest["external_inputs"], [])
            self.assertEqual(manifest["encoding"]["pq_normalization_cd_m2"], 10000)
            self.assertEqual(manifest["mastering_intent"]["peak_cd_m2"], 1000)
            self.assertTrue(manifest["mastering_intent"]["synthetic_design_only"])
            self.assertFalse(manifest["mastering_intent"]["panel_measurement"])

    def test_existing_file_directory_and_symlink_are_never_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            sentinel = parent / "sentinel"
            sentinel.write_bytes(b"untouched")
            existing = parent / "existing"
            existing.mkdir()
            link = parent / "link"
            link.symlink_to(sentinel)
            for output in (sentinel, existing, link):
                with self.subTest(name=output.name), self.assertRaisesRegex(corpus.CorpusError, "already exists"):
                    corpus.generate_corpus(output, 24, 8)
            self.assertEqual(sentinel.read_bytes(), b"untouched")
            self.assertEqual(list(existing.iterdir()), [])
            self.assertTrue(link.is_symlink())
            self.assertEqual(sorted(p.name for p in parent.iterdir()), ["existing", "link", "sentinel"])

    def test_bad_parameters_parent_and_repository_destination_leave_no_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for values in ((11, 8, 24), (24, 3, 24), (4096, 4096, 24),
                           (24, 8, 0), (24, 8, 121), (24.0, 8, 24), (True, 8, 24)):
                with self.subTest(values=values), self.assertRaises(corpus.CorpusError):
                    corpus.generate_corpus(parent / "out", *values)
            with self.assertRaises(corpus.CorpusError):
                corpus.generate_corpus(parent / "missing" / "out", 24, 8)
            with self.assertRaisesRegex(corpus.CorpusError, "outside the source repository"):
                corpus.generate_corpus(SCRIPT.parent.parent / "generated-corpus", 24, 8)
            self.assertEqual(list(parent.iterdir()), [])

    def test_write_failure_cleans_staging_before_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            write = corpus._write_file

            def fail_manifest(path, data):
                if path.name == "manifest.json":
                    raise OSError("simulated disk failure")
                write(path, data)

            with mock.patch.object(corpus, "_write_file", side_effect=fail_manifest):
                with self.assertRaises(corpus.CorpusError):
                    corpus.generate_corpus(parent / "out", 24, 8)
            self.assertEqual(list(parent.iterdir()), [])

    def test_publish_failure_cleans_staging_and_reserved_empty_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with mock.patch.object(corpus.os, "rename", side_effect=OSError("simulated publish failure")):
                with self.assertRaises(corpus.CorpusError):
                    corpus.generate_corpus(parent / "out", 24, 8)
            self.assertEqual(list(parent.iterdir()), [])

    def test_destination_appearing_during_generation_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            output = parent / "out"
            write = corpus._write_file

            def racing_write(path, data):
                write(path, data)
                if path.name == "manifest.json":
                    output.mkdir()
                    (output / "other-file").write_bytes(b"untouched")

            with mock.patch.object(corpus, "_write_file", side_effect=racing_write):
                with self.assertRaises(corpus.CorpusError):
                    corpus.generate_corpus(output, 24, 8)
            self.assertEqual(list(parent.iterdir()), [output])
            self.assertEqual((output / "other-file").read_bytes(), b"untouched")

    def test_cli_failure_is_clear_and_success_is_quietly_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "out"
            stderr, stdout = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
                self.assertEqual(corpus.main([str(output), "--width", "11"]), 1)
            self.assertIn("HDR corpus error: require width", stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")
            self.assertFalse(output.exists())
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(corpus.main([str(output), "--width", "24", "--height", "8"]), 0)
            self.assertIn("six synthetic PQ RGB TIFF frames", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
