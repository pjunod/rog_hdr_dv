"""Contracts for the cadence fixture generator (FFmpeg is always mocked)."""

import contextlib
from fractions import Fraction
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_cadence_fixtures.py"
SPEC = importlib.util.spec_from_file_location("generate_cadence_fixtures", SCRIPT)
gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gen)


def fake_ffmpeg(returncode):
    def run(argv, **kwargs):
        Path(argv[-1]).write_bytes(b"partial")
        return mock.Mock(returncode=returncode)
    return run


class CadenceFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "fixtures"

    def parse(self, *extra):
        with contextlib.redirect_stderr(io.StringIO()):
            return gen.parse_args([str(self.out), *extra])

    def test_default_rates_are_exact(self):
        rates = self.parse().rates
        self.assertEqual(rates, [Fraction(24000, 1001), 24, 25, Fraction(30000, 1001),
                                 30, 50, Fraction(60000, 1001), 60])

    def test_decimal_refused_with_hint(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
            gen.parse_args([str(self.out), "--rates", "23.976"])
        self.assertIn("24000/1001", err.getvalue())

    def test_duplicate_refused(self):
        with self.assertRaises(SystemExit):
            self.parse("--rates", "24", "48/2")

    def test_filenames(self):
        self.assertEqual(gen.fixture_name("sdr", Fraction(24000, 1001), 1920, 1080, 660),
                         "cadence-sdr-24000-1001-1920x1080-660s.mp4")
        self.assertEqual(gen.fixture_name("hdr10", Fraction(60), 1920, 1080, 660),
                         "cadence-hdr10-60-1920x1080-660s.mp4")

    def test_hdr10_argv(self):
        argv = gen.build_argv("ffmpeg", "hdr10", Fraction(24000, 1001), 660, 1920, 1080, "o.mkv")
        self.assertIn(gen.X265_HDR10, argv)
        self.assertIn("hdr10=1", gen.X265_HDR10)
        self.assertEqual(argv[argv.index("-color_primaries") + 1], "bt2020")
        self.assertEqual(argv[argv.index("-g") + 1], "48")
        self.assertEqual(argv[argv.index("-r") + 1], "24000/1001")
        self.assertEqual(argv[argv.index("-video_track_timescale") + 1], "24000")

    def test_timescales_are_exact(self):
        for rate in gen.DEFAULT_RATES:
            value = Fraction(rate)
            scale = gen.track_timescale(value)
            self.assertEqual((scale / value).denominator, 1, rate)

    def test_expected_frames_in_manifest(self):
        with mock.patch.object(gen.subprocess, "run", fake_ffmpeg(0)):
            self.assertEqual(gen.main([str(self.out), "--rates", "24000/1001"]), 0)
        entry = json.loads((self.out / "manifest.json").read_text())["fixtures"][0]
        self.assertEqual(entry["expected_frames"], 15824)

    def test_dry_run_writes_nothing(self):
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(gen.main([str(self.out), "--dry-run"]), 0)
        self.assertFalse(self.out.exists())
        self.assertEqual(len(json.loads(buf.getvalue())), 8)

    def test_repo_internal_output_refused(self):
        with self.assertRaises(SystemExit):
            self.parse_inside()

    def parse_inside(self):
        with contextlib.redirect_stderr(io.StringIO()):
            return gen.parse_args([str(gen.REPO / "docs" / "new-fixtures")])

    def test_failing_ffmpeg_cleans_up(self):
        with mock.patch.object(gen.subprocess, "run", fake_ffmpeg(1)), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(gen.main([str(self.out), "--rates", "24"]), 1)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_success_writes_manifest_with_sha256(self):
        with mock.patch.object(gen.subprocess, "run", fake_ffmpeg(0)):
            self.assertEqual(gen.main([str(self.out), "--rates", "25", "--kind", "hdr10"]), 0)
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["schema"], "cadence-fixtures-v1")
        entry = manifest["fixtures"][0]
        self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(entry["size_bytes"], 7)
        self.assertEqual(entry["rate"], "25")


if __name__ == "__main__":
    unittest.main()
