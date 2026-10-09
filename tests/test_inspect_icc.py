"""Synthetic ICC bounds, colour encodings and private-report contracts."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/inspect_icc.py"
SPEC = importlib.util.spec_from_file_location("inspect_icc", SCRIPT)
icc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(icc)


def uint(value):
    return struct.pack(">I", value)


def fixed(*values):
    return b"".join(struct.pack(">i", round(value * 65536)) for value in values)


def typed(kind, body=b""):
    return kind + b"\0" * 4 + body


def profile(tags=(), shared=()):
    """Create a minimal bounded profile, not a full conformance fixture."""
    header = bytearray(128)
    header[8] = 4
    header[12:24] = b"mntrRGB XYZ "
    header[36:40] = b"acsp"
    header[48:56] = b"SECRMODL"  # Omitted manufacturer/model fields.
    table = bytearray(uint(len(tags) + len(shared)))
    payloads = bytearray()
    locations = {}
    start = 132 + 12 * (len(tags) + len(shared))
    for signature, payload in tags:
        offset = start + len(payloads)
        locations[signature] = (offset, len(payload))
        table.extend(signature + uint(offset) + uint(len(payload)))
        payloads.extend(payload)
        payloads.extend(b"\0" * (-len(payloads) % 4))
    for signature, target in shared:
        offset, size = locations[target]
        table.extend(signature + uint(offset) + uint(size))
    result = header + table + payloads
    result[:4] = uint(len(result))
    return bytes(result)


def change(data, offset, value):
    result = bytearray(data)
    result[offset:offset + len(value)] = value
    return bytes(result)


def mhc(count=2, matrix=True, values=(0, 1), shared=False):
    # Microsoft's raw row-major 3x4 matrix, then sf32 blocks, relative offsets.
    matrix_data = fixed(1, 0, 0, 7, 0, 1, 0, -3, 0, 0, 1, 2) if matrix else b""
    lut = typed(b"sf32", fixed(*values)) if count else b""
    matrix_offset = 36 if matrix else 0
    first = 36 + len(matrix_data)
    offsets = ([first] * 3 if shared else [first + len(lut) * i for i in range(3)]) if count else [0] * 3
    return typed(b"MHC2", uint(count) + fixed(0.001, 500) + uint(matrix_offset) +
                 b"".join(uint(o) for o in offsets)) + matrix_data + lut * (1 if shared else 3)


class ProfileTests(unittest.TestCase):
    def assert_bad(self, data, reason):
        with self.assertRaises(icc.ProfileError) as caught:
            icc.parse_profile(data)
        self.assertEqual(str(caught.exception), reason)

    def test_xyz_signed_values_and_adaptation_are_not_native_gamut(self):
        data = profile([(b"rXYZ", typed(b"XYZ ", fixed(-0.25, 0.5, 0.75))),
                        (b"lumi", typed(b"XYZ ", fixed(0, 275, 0))),
                        (b"chad", typed(b"sf32", fixed(1, 0, 0, 0, 1, 0, 0, 0, 1)))])
        report = icc.parse_profile(data)
        tags = {row["signature"]: row["decoded"] for row in report["tags"]}
        self.assertEqual(tags["rXYZ"]["XYZ"], [-0.25, 0.5, 0.75])
        self.assertEqual(tags["rXYZ"]["xy"], [-0.25, 0.5])
        self.assertEqual(tags["lumi"]["Y_units"], "cd/m2")
        self.assertEqual(tags["chad"]["matrix_rows"], [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertEqual(report["native_primary_reconstruction"], "not_performed")

    def test_shared_payloads_are_permitted_but_partial_overlap_is_rejected(self):
        data = profile([(b"rTRC", typed(b"curv", uint(1) + struct.pack(">H", 563)))],
                       [(b"gTRC", b"rTRC"), (b"bTRC", b"rTRC")])
        tags = icc.parse_profile(data)["tags"]
        self.assertEqual(len(tags), 3)
        self.assertTrue(all(row["decoded"]["gamma"] == 563 / 256 for row in tags))
        self.assert_bad(change(data, 152, uint(12)), "tag_data_overlap")

    def test_identity_gamma_and_sampled_curves_have_compact_summaries(self):
        for count, samples in ((0, []), (1, [512]), (4, [0, 40000, 30000, 65535])):
            payload = typed(b"curv", uint(count) + b"".join(struct.pack(">H", v) for v in samples))
            row = icc.parse_profile(profile([(b"rTRC", payload)]))["tags"][0]["decoded"]
            self.assertEqual(row["entries"], count)
            if count == 0:
                self.assertEqual(row["representation"], "identity")
            elif count == 1:
                self.assertEqual(row["gamma"], 2)
            else:
                self.assertEqual(row["endpoints"], [0, 1])
                self.assertFalse(row["nondecreasing"])
                self.assertNotIn("samples", row)

    def test_every_supported_parametric_type_preserves_signed_parameters(self):
        for kind, count in enumerate((1, 3, 4, 5, 7)):
            params = [2] + [-0.125] * (count - 1)
            data = typed(b"para", struct.pack(">HH", kind, 0) + fixed(*params))
            result = icc.parse_profile(profile([(b"rTRC", data)]))["tags"][0]["decoded"]
            self.assertEqual(result["function_type"], kind)
            self.assertEqual(list(result["parameters"].values()), params)
            self.assertEqual(result["function_validity"], "not_evaluated")

    def test_curve_lengths_limits_and_reserved_bytes_are_checked(self):
        cases = [(typed(b"curv", uint(2) + b"\0\0"), "invalid_curve_length"),
                 (typed(b"curv", uint(icc.MAX_CURVE_ENTRIES + 1)), "curve_entry_limit"),
                 (typed(b"para", struct.pack(">HH", 5, 0)), "unsupported_parametric_function"),
                 (typed(b"para", struct.pack(">HH", 4, 0)), "invalid_parametric_length"),
                 (typed(b"para", struct.pack(">HH", 0, 1) + fixed(2)), "selected_tag_reserved_nonzero"),
                 (b"curv" + uint(1) + uint(0), "selected_tag_reserved_nonzero")]
        for payload, reason in cases:
            with self.subTest(reason=reason):
                self.assert_bad(profile([(b"rTRC", payload)]), reason)

    def test_mhc2_ignores_fourth_matrix_column_and_summarizes_shared_luts(self):
        result = icc.parse_profile(profile([(b"MHC2", mhc(shared=True))]))["tags"][0]["decoded"]
        self.assertTrue(result["matrix"]["identity"])
        self.assertEqual(result["matrix"]["fourth_column"], "ignored")
        self.assertEqual(result["peak_luminance_cd_m2"], 500)
        self.assertTrue(all(row["identity_at_stored_knots"] for row in result["luts"].values()))
        self.assertNotIn("matrix_rows", result["matrix"])
        identity = icc.parse_profile(profile([(b"MHC2", mhc(count=0, matrix=False))]))["tags"][0]["decoded"]
        self.assertTrue(identity["matrix"]["identity"])
        self.assertTrue(identity["luts"]["red"]["identity"])

    def test_mhc2_nonidentity_and_lut_monotonicity(self):
        payload = change(mhc(values=(0.25, 0.1)), 36, fixed(0.9))
        result = icc.parse_profile(profile([(b"MHC2", payload)]))["tags"][0]["decoded"]
        self.assertFalse(result["matrix"]["identity"])
        self.assertFalse(result["luts"]["red"]["identity_at_stored_knots"])
        self.assertFalse(result["luts"]["red"]["nondecreasing"])

    def test_mhc2_offsets_counts_ranges_and_types_are_bounded(self):
        base = mhc()
        cases = [(change(base, 20, uint(37)), "mhc2_offset_misaligned"),
                 (change(base, 20, uint(4)), "mhc2_offset_out_of_bounds"),
                 (change(base, 24, uint(0xfffffffc)), "mhc2_offset_out_of_bounds"),
                 (change(base, 24, uint(36)), "mhc2_blocks_overlap"),
                 (change(base, 8, uint(4097)), "mhc2_lut_entry_limit"),
                 (change(base, 8, uint(0)), "inconsistent_mhc2_lut_offsets"),
                 (change(base, 24, uint(0)), "inconsistent_mhc2_lut_offsets"),
                 (change(base, 12, fixed(-1)), "invalid_mhc2_luminance"),
                 (change(base, 84, b"NOPE"), "unexpected_selected_tag_type"),
                 (change(base, 92, fixed(-0.25)), "mhc2_lut_value_out_of_range")]
        for payload, reason in cases:
            with self.subTest(reason=reason):
                self.assert_bad(profile([(b"MHC2", payload)]), reason)

    def test_header_and_tag_table_corruption_is_controlled(self):
        base = profile([(b"DVB1", typed(b"priv", b"PRIVATE_SERIAL"))])
        # Remove the tag record's size word and keep the declared size exact,
        # so the parser reaches the table-length check rather than size checks.
        truncated_table = change(base[:140], 0, uint(140))
        cases = [(b"\0" * 127, "truncated_profile_header_or_table"),
                 (change(base, 0, uint(len(base) + 4)), "declared_size_mismatch"),
                 (change(base, 36, b"bad!"), "invalid_profile_signature"),
                 (change(base, 128, uint(257)), "tag_count_limit"),
                 (truncated_table, "truncated_tag_table"),
                 (change(base, 136, uint(145)), "tag_offset_misaligned"),
                 (change(base, 136, uint(128)), "tag_out_of_bounds"),
                 (change(base, 140, uint(0xffffffff)), "tag_out_of_bounds"),
                 (change(base, 140, uint(7)), "tag_data_too_short")]
        for data, reason in cases:
            with self.subTest(reason=reason):
                self.assert_bad(data, reason)
        duplicate = profile([(b"DVB1", typed(b"priv")), (b"DVB1", typed(b"priv"))])
        self.assert_bad(duplicate, "duplicate_tag_signature")
        unaligned = base[:-1]
        self.assert_bad(change(unaligned, 0, uint(len(unaligned))), "profile_size_misaligned")

    def test_unknown_and_private_tags_do_not_emit_payloads_or_tag_hashes(self):
        data = profile([(b"DVB1", typed(b"priv", b"PRIVATE_SERIAL /home/operator/profile.icc")),
                        (b"desc", typed(b"desc", b"PRIVATE_DESCRIPTION")),
                        (b"vcgt", typed(b"vcgt", b"PRIVATE_LUT"))])
        result = icc.parse_profile(data)
        encoded = json.dumps(result)
        for secret in ("PRIVATE", "/home/", "profile.icc", "SECR", "MODL"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(result["tags"][0], {"signature": "DVB1", "size_bytes":
                         len(typed(b"priv", b"PRIVATE_SERIAL /home/operator/profile.icc"))})
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(encoded.count("sha256"), 1)
        self.assertEqual(result["tags"][2]["decoded"]["reason"], "presence_only")

    def test_nonprintable_fixed_signatures_are_sanitized(self):
        data = change(profile([(b"\0A\xffZ", typed(b"priv"))]), 12, b"\0X\xffY")
        result = icc.parse_profile(data)
        self.assertEqual(result["header"]["profile_class"], "invalid_4cc")
        self.assertEqual(result["tags"][0]["signature"], "invalid_4cc")


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "PRIVATE_DESCRIPTION.icc"
        self.source.write_bytes(profile([(b"DVB1", typed(b"priv", b"PRIVATE_SERIAL"))]))

    def test_output_is_exclusive_private_and_source_unchanged(self):
        original = self.source.read_bytes()
        output = self.root / "report.json"
        self.assertEqual(icc.main([str(self.source), "--output", str(output)]), 0)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(self.source.read_bytes(), original)
        captured = output.read_text()
        self.assertNotIn(str(self.root), captured)
        self.assertNotIn("PRIVATE", captured)
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(icc.main([str(self.source), "--output", str(output)]), 1)
        self.assertEqual(errors.getvalue(), "ICC report error: output_write_failed\n")
        self.assertEqual(output.read_text(), captured)
        link = self.root / "report-link.json"
        link.symlink_to(output)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(icc.main([str(self.source), "--output", str(link)]), 1)
        self.assertEqual(output.read_text(), captured)

    def test_missing_permission_and_invalid_path_errors_do_not_expose_input(self):
        self.assertEqual(icc.inspect_profile(self.root / "PRIVATE_MISSING")["reason"], "input_read_failed")
        with mock.patch.object(icc.os, "open", side_effect=PermissionError("PRIVATE_ERROR")):
            result = icc.inspect_profile(self.source)
        self.assertEqual(result["reason"], "input_read_failed")
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertEqual(icc.inspect_profile("PRIVATE\0PATH")["reason"], "input_read_failed")

    def test_fifo_directory_and_symlink_do_not_block_or_activate_anything(self):
        fifo = self.root / "input.fifo"
        os.mkfifo(fifo)
        process = subprocess.run([sys.executable, str(SCRIPT), str(fifo)],
                                 capture_output=True, text=True, timeout=3)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)["reason"], "input_not_regular_file")
        self.assertEqual(icc.inspect_profile(self.root)["reason"], "input_not_regular_file")
        link = self.root / "input-link.icc"
        link.symlink_to(self.source)
        self.assertEqual(icc.inspect_profile(link)["reason"], "input_read_failed")

    def test_sparse_oversized_input_and_read_race_are_rejected(self):
        oversized = self.root / "large.icc"
        with oversized.open("wb") as output:
            output.truncate(icc.MAX_BYTES + 1)
        self.assertEqual(icc.inspect_profile(oversized)["reason"], "profile_too_large")
        original_read = icc.os.read
        calls = []

        def changing_read(fd, length):
            result = original_read(fd, length)
            if not calls:
                calls.append(True)
                with self.source.open("ab") as source:
                    source.write(b"MORE")
            return result

        with mock.patch.object(icc.os, "read", side_effect=changing_read):
            self.assertEqual(icc.inspect_profile(self.source)["reason"], "input_changed_during_read")

    def test_malformed_profile_cli_has_controlled_json_and_exit_code(self):
        self.source.write_bytes(b"PRIVATE_RAW_TRUNCATED_PROFILE")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(icc.main([str(self.source)]), 2)
        report = json.loads(output.getvalue())
        self.assertEqual(report["reason"], "truncated_profile_header_or_table")
        self.assertNotIn("PRIVATE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
