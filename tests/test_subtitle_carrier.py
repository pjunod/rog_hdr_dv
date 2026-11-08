import copy
import importlib.util
from pathlib import Path
import unittest


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
