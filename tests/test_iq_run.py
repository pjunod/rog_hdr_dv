"""Source-only checks for iq_run helpers using synthetic inputs."""
import importlib.util
import json
from fractions import Fraction
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "iq_run.py"
SPEC = importlib.util.spec_from_file_location("iq_run", MODULE_PATH)
iq_run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(iq_run)


class ExtractY4MFrameTests(unittest.TestCase):
    @staticmethod
    def cadence_fixture(fps, seconds):
        frame = b"FRAME\n" + bytes(192 * 108 * 3)
        return f"YUV4MPEG2 W192 H108 F{fps}:1 Ip A1:1 C420p10\n".encode() + frame * (fps * seconds)

    def test_session_id_must_be_explicit(self):
        with self.assertRaises(SystemExit):
            iq_run.parser().parse_args(["out", "--stim-dir", "stim", "--stim4k-dir", "stim4k",
                                        "--pw-read", "pw-read", "--pw-seq", "pw-seq"])

    def test_extracts_selected_frame_as_standalone_stream(self):
        header = b"YUV4MPEG2 W2 H2 F24:1 Ip A1:1 C420p10\n"
        payload0, payload1 = bytes(range(12)), bytes(range(12, 24))
        data = header + b"FRAME\n" + payload0 + b"FRAME\n" + payload1
        extracted, geometry = iq_run.extract_y4m_frame(data, 1)
        self.assertEqual(extracted, header + b"FRAME\n" + payload1)
        self.assertEqual(geometry, {"width": 2, "height": 2, "chroma": "420p10"})

    def test_rejects_per_frame_tags_and_truncation(self):
        header = b"YUV4MPEG2 W2 H2 F24:1 Ip A1:1 C420jpeg\n"
        with self.assertRaisesRegex(ValueError, "per-frame tags"):
            iq_run.extract_y4m_frame(header + b"FRAME Xfoo=bar\n" + bytes(6), 0)
        with self.assertRaisesRegex(ValueError, "truncated"):
            iq_run.extract_y4m_frame(header + b"FRAME\n" + bytes(5), 0)

    def test_cadence_request_is_bounded_by_source_frames_and_eight_seconds(self):
        default = iq_run.cadence_capture_plan(self.cadence_fixture(24, 2), 24)
        self.assertEqual(default, {"available_source_frames": 48, "requested_frames": 48,
                                   "requested_duration_seconds": 2.0,
                                   "frame_rate": {"numerator": 24, "denominator": 1},
                                   "requested_duration_exact_seconds": {"numerator": 2, "denominator": 1}})
        long = iq_run.cadence_capture_plan(self.cadence_fixture(24, 10), 24)
        self.assertEqual(long, {"available_source_frames": 240, "requested_frames": 192,
                                "requested_duration_seconds": 8.0,
                                "frame_rate": {"numerator": 24, "denominator": 1},
                                "requested_duration_exact_seconds": {"numerator": 8, "denominator": 1}})

    def test_fractional_capture_plan_keeps_exact_rate_and_duration(self):
        frame = b"FRAME\n" + bytes(192 * 108 * 3)
        for text in ("24000/1001", "30000/1001", "60000/1001"):
            with self.subTest(rate=text):
                rate = Fraction(text)
                count = rate.numerator * 10 // rate.denominator
                header = f"YUV4MPEG2 W192 H108 F{rate.numerator}:{rate.denominator} Ip A1:1 C420p10\n".encode()
                plan = iq_run.cadence_capture_plan(header + frame * count, text)
                requested = rate.numerator * 8 // rate.denominator
                self.assertEqual(plan["requested_frames"], requested)
                duration = Fraction(requested, 1) / rate
                self.assertEqual(plan["requested_duration_exact_seconds"], {"numerator": duration.numerator, "denominator": duration.denominator})
                self.assertLessEqual(duration, 8)
                self.assertLess(8 - duration, 1 / rate)
                with self.assertRaisesRegex(ValueError, "frame rate"):
                    iq_run.cadence_capture_plan(header + frame, round(rate))
                alias = header.replace(f"F{rate.numerator}:{rate.denominator}".encode(),
                                       f"F{rate.numerator * 2}:{rate.denominator * 2}".encode())
                self.assertEqual(iq_run.cadence_capture_plan(alias + frame, text)["requested_frames"], 1)

    def test_fractional_scene_names_are_safe_and_default_scenes_stay_compatible(self):
        base = ["out", "--stim-dir", "stim", "--stim4k-dir", "stim4k", "--pw-read", "read", "--pw-seq", "seq", "--session-id", "1"]
        args = iq_run.parser().parse_args(base + ["--scene", "cadence-48000_2002", "--scene", "cadence-24"])
        self.assertEqual(args.scene, ["cadence-24000_1001", "cadence-24"])
        self.assertEqual(iq_run.parser().parse_args(base).scene, None)
        for scene in ("cadence-23.976", "cadence-24000_0", "cadence-../24", "unknown"):
            with self.subTest(scene=scene), self.assertRaises(SystemExit):
                iq_run.parser().parse_args(base + ["--scene", scene])

    def test_cadence_preflight_rejects_wrong_rate_geometry_and_truncation(self):
        valid = self.cadence_fixture(24, 1)
        with self.assertRaisesRegex(ValueError, "frame rate"):
            iq_run.cadence_capture_plan(valid.replace(b"F24:1", b"F25:1", 1), 24)
        with self.assertRaisesRegex(ValueError, "192x108"):
            iq_run.cadence_capture_plan(valid.replace(b"W192", b"W190", 1), 24)
        with self.assertRaisesRegex(ValueError, "truncated"):
            iq_run.cadence_capture_plan(valid[:-1], 24)

    def test_source_range_preflight_for_still_and_cadence(self):
        header = b"YUV4MPEG2 W192 H108 F24:1 Ip A1:1 C420p10 XYSCSS=420P10"
        pixels = 192 * 108
        frame = b"\nFRAME\n" + b"\x40\x00" * pixels + b"\x00\x02" * (pixels // 2)
        for tags in (b"", b" XCOLORRANGE=LIMITED"):
            with self.subTest(tags=tags):
                data = header + tags + frame
                extracted, _ = iq_run.extract_y4m_frame(data, 0)
                self.assertEqual(extracted, data)
                self.assertEqual(iq_run.cadence_capture_plan(data, 24)["available_source_frames"], 1)

        for tags in (b" XCOLORRANGE=FULL", b" XCOLORRANGE=LIMITED XCOLORRANGE=FULL",
                     b" XCOLORRANGE=FULL XCOLORRANGE=LIMITED"):
            with self.subTest(tags=tags):
                data = header + tags + frame
                with self.assertRaisesRegex(ValueError, "XCOLORRANGE must be LIMITED"):
                    iq_run.extract_y4m_frame(data, 0)
                with self.assertRaisesRegex(ValueError, "XCOLORRANGE must be LIMITED"):
                    iq_run.cadence_capture_plan(data, 24)

    def test_existing_output_is_never_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "existing"
            out.mkdir()
            args = SimpleNamespace(out_dir=out)
            with self.assertRaises(FileExistsError):
                iq_run.run(args)

    def test_failed_capture_setup_still_writes_run_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tools = []
            for name in ("pw-read", "pw-seq"):
                path = root / name
                path.write_text("#!/bin/sh\nexit 0\n")
                path.chmod(0o755)
                tools.append(path)
            args = SimpleNamespace(out_dir=root / "run", stim_dir=root / "stim",
                stim4k_dir=root / "stim4k", pw_read=tools[0], pw_seq=tools[1],
                session_id="auto", scene=["dither"], monitor="eDP-2")
            with patch.object(iq_run, "unlocked"), patch.object(iq_run, "ScreenCast", side_effect=RuntimeError("setup failed")):
                self.assertEqual(iq_run.run(args), 1)
            record = json.loads((args.out_dir / "run.json").read_text())
            self.assertIn("setup failed", record["error"])


if __name__ == "__main__":
    unittest.main()
