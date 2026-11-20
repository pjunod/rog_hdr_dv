import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / "packaging/quality/verify-subtitle-carrier.py"
spec = importlib.util.spec_from_file_location("subtitle_carrier", path)
carrier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(carrier)


class SubtitleCarrierTest(unittest.TestCase):
    def setUp(self):
        checksum = "SHA256:" + "ab" * 32
        self.video = {
            "streams": [{"codec_name": "hevc", "codec_tag_string": "dvhe", "time_base": "1/24",
                         "extradata_hash": checksum, "side_data_list": [
                             {"side_data_type": "DOVI configuration record", "dv_profile": 5,
                              "rpu_present_flag": 1}]}],
            "packets": [{"size": 20, "pts": n, "dts": n - 1, "duration": 1,
                         "data_hash": checksum} for n in (0, 1)],
        }

    def fractional_clock_pair(self):
        reference = copy.deepcopy(self.video)
        reference["streams"][0]["time_base"] = "1/60000"
        # Preserve a presentation inversion in the two carriers' shared decode order.
        decode_order = [*range(29), 31, 29, 30, 32]
        reference["packets"] = [
            {"size": 20, "pts": ordinal * 1001, "dts": (decode_index - 2) * 1001,
             "duration": 1001, "data_hash": f"SHA256:{ordinal:064x}"}
            for decode_index, ordinal in enumerate(decode_order)
        ]
        remux = copy.deepcopy(reference)
        remux["streams"][0]["time_base"] = "1/120000"
        for packet in remux["packets"]:
            for field in ("pts", "dts", "duration"):
                packet[field] *= 2
        return reference, remux

    def test_remux_without_dolby_configuration_is_rejected(self):
        stream = self.video["streams"][0]
        for configs in ([], [{"side_data_type": "DOVI configuration record", "rpu_present_flag": 0}]):
            with self.subTest(configs=configs):
                stream["side_data_list"] = configs
                with self.assertRaises(ValueError):
                    carrier.signature(self.video)

    def test_prefix_applies_only_to_reference(self):
        reference = carrier.signature(self.video, 1)
        self.assertNotEqual(reference, carrier.signature(self.video))
        remux = copy.deepcopy(self.video)
        remux["packets"].pop()
        self.assertEqual(reference, carrier.signature(remux))
        with self.assertRaises(ValueError):
            carrier.signature(remux, 2)

    def test_different_packets_timing_or_profile_change_signature(self):
        reference = carrier.signature(self.video)
        for key, value in (("pts", 7), ("dts", 5), ("duration", 4), ("size", 99),
                           ("data_hash", "SHA256:" + "cd" * 32)):
            with self.subTest(key=key):
                remux = copy.deepcopy(self.video)
                remux["packets"][0][key] = value
                self.assertNotEqual(reference, carrier.signature(remux))
        self.video["streams"][0]["side_data_list"][0]["dv_profile"] = 8
        self.assertNotEqual(reference, carrier.signature(self.video))

    def test_fractional_rate_remux_matches_across_exact_time_bases(self):
        reference, remux = self.fractional_clock_pair()
        self.assertEqual(carrier.signature(reference), carrier.signature(remux))

    def test_fractional_rate_one_millisecond_early_pts_changes_signature(self):
        reference, remux = self.fractional_clock_pair()
        packet = next(packet for packet in remux["packets"] if packet["pts"] == 30 * 2002)
        packet["pts"] -= 120  # Exactly 1 ms at 120,000 ticks per second.
        self.assertEqual(len(reference["packets"]), len(remux["packets"]))
        self.assertNotEqual(carrier.signature(reference), carrier.signature(remux))

    def test_same_packet_count_does_not_hide_drop_and_duplicate(self):
        reference, remux = self.fractional_clock_pair()
        remux["packets"][-2] = remux["packets"][-3].copy()
        self.assertEqual(len(reference["packets"]), len(remux["packets"]))
        self.assertNotEqual(carrier.signature(reference), carrier.signature(remux))

    def test_fractional_rate_remux_preserves_packet_order(self):
        reference, remux = self.fractional_clock_pair()
        packets = remux["packets"]
        packets[29], packets[30] = packets[30], packets[29]
        self.assertNotEqual(carrier.signature(reference), carrier.signature(remux))

    def test_color_description_changes_signature(self):
        stream = self.video["streams"][0]
        stream["side_data_list"][0].update(dv_profile=8, dv_bl_signal_compatibility_id=1)
        stream.update(color_transfer="smpte2084", color_range="tv", color_primaries="bt2020",
                      color_space="bt2020nc", pix_fmt="yuv420p10le", chroma_location="left")
        reference = carrier.signature(self.video)
        for field, value in (("color_transfer", "arib-std-b67"), ("color_range", "pc"),
                             ("color_primaries", "bt709"), ("color_space", "bt709"),
                             ("pix_fmt", "yuv420p"), ("pix_fmt", "yuv444p10le"),
                             ("chroma_location", "center")):
            with self.subTest(field=field, value=value):
                remux = copy.deepcopy(self.video)
                remux["streams"][0][field] = value
                self.assertNotEqual(reference, carrier.signature(remux))

    def test_missing_pixel_format_and_chroma_location_are_optional_but_compared(self):
        reference = carrier.signature(self.video)
        remux = copy.deepcopy(self.video)
        self.assertEqual(reference, carrier.signature(remux))
        for field, value in (("pix_fmt", "yuv420p10le"), ("chroma_location", "left")):
            with self.subTest(field=field):
                remux["streams"][0][field] = value
                self.assertNotEqual(reference, carrier.signature(remux))
                del remux["streams"][0][field]

    def test_inspect_requests_pixel_format_and_chroma_location(self):
        self.video["streams"][0].update(pix_fmt="yuv420p10le", chroma_location="left")
        with patch.object(carrier.subprocess, "check_output",
                          return_value=json.dumps(self.video).encode()) as check_output:
            self.assertEqual(carrier.inspect(Path("carrier.mp4")), carrier.signature(self.video))
        command = check_output.call_args.args[0]
        entries = command[command.index("-show_entries") + 1]
        stream_fields = entries.split(":", 1)[0].removeprefix("stream=").split(",")
        self.assertIn("pix_fmt", stream_fields)
        self.assertIn("chroma_location", stream_fields)
