"""Source-only checks for iq_run helpers; these tests are intentionally not run here."""
import importlib.util
import json
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
                session_id="auto", scene=None, monitor="eDP-2")
            with patch.object(iq_run, "unlocked"), patch.object(iq_run, "ScreenCast", side_effect=RuntimeError("setup failed")):
                self.assertEqual(iq_run.run(args), 1)
            record = json.loads((args.out_dir / "run.json").read_text())
            self.assertIn("setup failed", record["error"])


if __name__ == "__main__":
    unittest.main()
