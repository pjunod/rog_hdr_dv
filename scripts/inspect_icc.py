#!/usr/bin/env python3
"""Bounded, read-only ICC characterisation; reports are private evidence."""

import argparse
import hashlib
import json
import os
import stat
import struct
import sys

MAX_BYTES = 16 * 1024 * 1024
MAX_TAGS = 256
MAX_CURVE_ENTRIES = 65536
MHC2_SOURCE = "https://learn.microsoft.com/en-us/windows/win32/wcs/display-calibration-mhc"


class ProfileError(Exception):
    """An allowlisted reason, never an input path or arbitrary exception text."""


def require(condition, reason):
    if not condition:
        raise ProfileError(reason)


def u32(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def fixed(data, offset):
    return struct.unpack_from(">i", data, offset)[0] / 65536


def fourcc(data):
    return data.decode("ascii") if all(32 <= b <= 126 for b in data) else "invalid_4cc"


def read_profile(path):
    """Open nonblocking so a FIFO cannot stall before the regular-file check."""
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode), "input_not_regular_file")
            require(before.st_size <= MAX_BYTES, "profile_too_large")
            chunks, length = [], 0
            while True:
                chunk = os.read(fd, min(65536, MAX_BYTES + 1 - length))
                if not chunk:
                    break
                chunks.append(chunk)
                length += len(chunk)
                require(length <= MAX_BYTES, "profile_too_large")
            after = os.fstat(fd)
            require(length == before.st_size == after.st_size and
                    before.st_mtime_ns == after.st_mtime_ns and
                    before.st_ctime_ns == after.st_ctime_ns, "input_changed_during_read")
            return b"".join(chunks)
        finally:
            os.close(fd)
    except (OSError, ValueError):
        raise ProfileError("input_read_failed") from None


def typed(data, signature, minimum):
    require(len(data) >= minimum, "selected_tag_truncated")
    require(data[:4] == signature, "unexpected_selected_tag_type")
    require(data[4:8] == b"\0" * 4, "selected_tag_reserved_nonzero")


def xyz(data, signature):
    typed(data, b"XYZ ", 20)
    require(len(data) == 20, "invalid_xyz_length")
    values = [fixed(data, i) for i in (8, 12, 16)]
    result = {"status": "ok", "XYZ": values}
    if signature == b"lumi":
        result.update({"context": "absolute_luminance", "Y_units": "cd/m2"})
    else:
        result["context"] = "profile_XYZ_not_native_panel_primaries"
        total = sum(values)
        result["xy"] = [values[0] / total, values[1] / total] if total > 0 else None
    return result


def curve(data):
    require(len(data) >= 12, "selected_tag_truncated")
    if data[:4] == b"curv":
        typed(data, b"curv", 12)
        count = u32(data, 8)
        require(count <= MAX_CURVE_ENTRIES, "curve_entry_limit")
        require(len(data) == 12 + 2 * count, "invalid_curve_length")
        result = {"status": "ok", "type": "curv", "entries": count}
        if count == 0:
            result["representation"] = "identity"
        elif count == 1:
            result.update({"representation": "gamma", "gamma":
                           struct.unpack_from(">H", data, 12)[0] / 256})
        else:
            first, previous, monotonic = None, None, True
            for (value,) in struct.iter_unpack(">H", memoryview(data)[12:]):
                if first is None:
                    first = value
                if previous is not None and value < previous:
                    monotonic = False
                previous = value
            result.update({"representation": "sampled", "endpoints":
                           [first / 65535, previous / 65535], "nondecreasing": monotonic})
        return result
    if data[:4] == b"para":
        typed(data, b"para", 12)
        kind = struct.unpack_from(">H", data, 8)[0]
        require(data[10:12] == b"\0\0", "selected_tag_reserved_nonzero")
        require(kind <= 4, "unsupported_parametric_function")
        names = (("g",), ("g", "a", "b"), ("g", "a", "b", "c"),
                 ("g", "a", "b", "c", "d"), ("g", "a", "b", "c", "d", "e", "f"))[kind]
        require(len(data) == 12 + 4 * len(names), "invalid_parametric_length")
        return {"status": "ok", "type": "para", "function_type": kind,
                "parameters": {name: fixed(data, 12 + 4 * i) for i, name in enumerate(names)},
                "function_validity": "not_evaluated"}
    raise ProfileError("unexpected_selected_tag_type")


def chad(data):
    typed(data, b"sf32", 44)
    require(len(data) == 44, "invalid_chad_length")
    values = [fixed(data, 8 + 4 * i) for i in range(9)]
    return {"status": "ok", "matrix_rows": [values[i:i + 3] for i in (0, 3, 6)],
            "context": "chromatic_adaptation_to_PCS_D50",
            "reverse_adaptation": "not_performed"}


def mhc2(data):
    typed(data, b"MHC2", 36)
    count = u32(data, 8)
    require(count <= 4096, "mhc2_lut_entry_limit")
    minimum, peak = fixed(data, 12), fixed(data, 16)
    require(0 <= minimum <= peak and peak > 0, "invalid_mhc2_luminance")
    matrix_offset = u32(data, 20)
    offsets = [u32(data, i) for i in (24, 28, 32)]
    require((count == 0 and all(o == 0 for o in offsets)) or
            (count > 0 and all(o != 0 for o in offsets)), "inconsistent_mhc2_lut_offsets")
    ranges = []

    def block(offset, size, kind):
        require(offset % 4 == 0, "mhc2_offset_misaligned")
        require(offset >= 36 and offset <= len(data) and
                size <= len(data) - offset, "mhc2_offset_out_of_bounds")
        current = (offset, offset + size)
        for start, end, previous_kind in ranges:
            require((current == (start, end) and kind == previous_kind == "lut") or
                    current[1] <= start or offset >= end,
                    "mhc2_blocks_overlap")
        ranges.append((offset, offset + size, kind))
        return memoryview(data)[offset:offset + size]

    matrix = {"identity": True, "representation": "implicit_identity"}
    if matrix_offset:
        raw = block(matrix_offset, 48, "matrix")
        integers = [struct.unpack_from(">i", raw, 4 * i)[0] for i in range(12)]
        effective = [integers[row * 4 + col] for row in range(3) for col in range(3)]
        matrix = {"identity": effective == [65536, 0, 0, 0, 65536, 0, 0, 0, 65536],
                  "representation": "stored_3x4_effective_3x3", "fourth_column": "ignored"}
    luts = []
    for offset in offsets:
        if not offset:
            luts.append({"entries": 0, "representation": "implicit_identity", "identity": True})
            continue
        raw = block(offset, 8 + 4 * count, "lut")
        typed(raw, b"sf32", 8)
        values = [struct.unpack_from(">i", raw, 8 + 4 * i)[0] for i in range(count)]
        require(all(0 <= v <= 65536 for v in values), "mhc2_lut_value_out_of_range")
        # Exact identity at stored knots; no claim about driver interpolation.
        identity = count >= 2 and all(v * (count - 1) == i * 65536
                                      for i, v in enumerate(values))
        luts.append({"entries": count, "identity_at_stored_knots": identity,
                     "nondecreasing": all(a <= b for a, b in zip(values, values[1:]))})
    return {"status": "ok", "minimum_luminance_cd_m2": minimum,
            "peak_luminance_cd_m2": peak, "matrix": matrix,
            "luts": dict(zip(("red", "green", "blue"), luts)),
            "matrix_space": "XYZ_adjustment", "lut_space": "after_wire_transfer_encoding",
            "source": MHC2_SOURCE, "platform_acceptance": "not_evaluated"}


def parse_profile(data):
    require(len(data) <= MAX_BYTES, "profile_too_large")
    require(len(data) >= 132, "truncated_profile_header_or_table")
    require(u32(data, 0) == len(data), "declared_size_mismatch")
    require(len(data) % 4 == 0, "profile_size_misaligned")
    require(data[36:40] == b"acsp", "invalid_profile_signature")
    count = u32(data, 128)
    require(count <= MAX_TAGS, "tag_count_limit")
    table_end = 132 + 12 * count
    require(table_end <= len(data), "truncated_tag_table")
    entries, signatures, ranges = [], set(), set()
    for i in range(count):
        base = 132 + 12 * i
        signature, offset, size = data[base:base + 4], u32(data, base + 4), u32(data, base + 8)
        require(signature not in signatures, "duplicate_tag_signature")
        signatures.add(signature)
        require(offset % 4 == 0, "tag_offset_misaligned")
        require(size >= 8, "tag_data_too_short")
        require(offset >= table_end and offset <= len(data) and
                size <= len(data) - offset, "tag_out_of_bounds")
        entries.append((signature, offset, size))
        ranges.add((offset, offset + size))
    ordered = sorted(ranges)
    require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), "tag_data_overlap")
    tags = []
    for signature, offset, size in entries:
        row = {"signature": fourcc(signature), "size_bytes": size}
        payload = memoryview(data)[offset:offset + size]
        if signature in (b"rXYZ", b"gXYZ", b"bXYZ", b"wtpt", b"lumi"):
            row["decoded"] = xyz(payload, signature)
        elif signature in (b"rTRC", b"gTRC", b"bTRC"):
            row["decoded"] = curve(payload)
        elif signature == b"chad":
            row["decoded"] = chad(payload)
        elif signature == b"MHC2":
            row["decoded"] = mhc2(payload)
        elif signature == b"vcgt":
            row["decoded"] = {"status": "unsupported", "reason": "presence_only"}
        tags.append(row)
    return {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "header": {"profile_class": fourcc(data[12:16]),
                       "data_colour_space": fourcc(data[16:20]),
                       "PCS": fourcc(data[20:24]), "major_version": data[8]},
            "tag_count": count, "tags": tags,
            "RGB_column_context": "ICC_profile_PCS_D50_columns_not_native_gamut",
            "native_primary_reconstruction": "not_performed",
            "profile_conformance": "not_fully_validated"}


def inspect_profile(path):
    report = {"schema_version": 1, "read_only": True, "evidence_class": "private_profile_structure",
              "calibration_accuracy": "not_evaluated", "profile_consumption": "not_evaluated"}
    try:
        report.update({"status": "ok", "profile": parse_profile(read_profile(path))})
    except ProfileError as error:
        report.update({"status": "error", "reason": str(error)})
    return report


def write_report(report, path):
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if path is None:
        sys.stdout.write(encoded)
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write(encoded)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", help="local profile to inspect; never installed or activated")
    parser.add_argument("--output", help="create a new private JSON report (0600)")
    args = parser.parse_args(argv)
    report = inspect_profile(args.profile)
    try:
        write_report(report, args.output)
    except (OSError, ValueError):
        print("ICC report error: output_write_failed", file=sys.stderr)
        return 1
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
