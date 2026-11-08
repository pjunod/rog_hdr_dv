#!/usr/bin/env python3
"""Compare the first Dolby video track in short subtitle qualification fixtures."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha256_field(value):
    if not isinstance(value, str) or not re.fullmatch(r"SHA256:[0-9a-fA-F]{64}", value):
        raise ValueError("Expected a SHA-256 hash from ffprobe")
    return value.lower()


def stream_identity(stream):
    configs = [item for item in stream.get("side_data_list", [])
               if item.get("side_data_type") == "DOVI configuration record"]
    if len(configs) != 1 or configs[0].get("rpu_present_flag") != 1:
        raise ValueError("Expected one Dolby Vision configuration with RPU present")
    fields = ("codec_name", "codec_tag_string", "width", "height",
              "color_range", "color_space", "color_transfer", "color_primaries")
    return tuple(stream.get(key) for key in fields), sha256_field(stream["extradata_hash"]), configs[0]


def signature(probe, reference_packets=None):
    streams = probe["streams"]
    if len(streams) != 1:
        raise ValueError("Expected one selected video track")
    identity = stream_identity(streams[0])
    packets = probe["packets"]
    if not packets:
        raise ValueError("Empty video track")
    if reference_packets is not None:
        if not 1 <= reference_packets <= len(packets):
            raise ValueError("Requested prefix is outside the reference video")
        packets = packets[:reference_packets]
    scale = Fraction(streams[0]["time_base"])
    digest = hashlib.sha256()
    for packet in packets:
        times = [str(int(packet[key]) * scale) for key in ("pts", "dts", "duration")]
        fields = [*times, str(int(packet["size"])), sha256_field(packet["data_hash"])]
        digest.update(("\t".join(fields) + "\n").encode("ascii"))
    return identity, len(packets), digest.digest()


def inspect(path, reference_packets=None):
    fields = ("stream=codec_name,codec_tag_string,width,height,color_range,color_space,"
              "color_transfer,color_primaries,extradata_hash,time_base:stream_side_data:"
              "packet=pts,dts,duration,size,data_hash")
    output = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", fields,
        "-show_data_hash", "sha256", "-of", "json", "-i", str(path),
    ])
    return signature(json.loads(output), reference_packets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-prefix-packets", type=int, metavar="N",
                        help="Compare a complete remux with the first N reference video packets")
    parser.add_argument("reference", type=Path)
    parser.add_argument("remux", type=Path, nargs="+")
    args = parser.parse_args()
    try:
        reference = inspect(args.reference, args.reference_prefix_packets)
        for i, path in enumerate(args.remux, 1):
            if inspect(path) != reference:
                raise ValueError(f"Remux {i} differs in configuration, coded data or timing")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Matched Dolby configuration, codec initialization and {reference[1]} timed "
          f"video packets in {len(args.remux)} remux(es).")


if __name__ == "__main__":
    main()
