#!/usr/bin/env python3
"""Compile actual production SEI walkers and compare structural NAL fixtures.

Reads Git objects without changing the supplied checkout. Retains generated C,
executables and raw results in an owned output directory. This is not FATE or a
VideoToolbox encode test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

SOURCE = 'libavcodec/videotoolboxenc.c'
STUBS = r'''
#include <stdint.h>
#include <stddef.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
typedef struct AVCodecContext { int unused; } AVCodecContext;
#define H264_NAL_SEI 6
#define AVERROR_INVALIDDATA (-1094995529)
#define AV_LOG_ERROR 16
static void av_log(void *ctx, int level, const char *fmt, ...) {
    (void) ctx; (void) level; (void) fmt;
}
'''
MAIN = r'''
int main(int argc, char **argv) {
    size_t n, i;
    uint8_t *data, *end = NULL;
    AVCodecContext ctx = {0};
    int result;
    if (argc != 2 || strlen(argv[1]) % 2) return 2;
    n = strlen(argv[1]) / 2;
    data = malloc(n ? n : 1);
    if (!data) return 2;
    for (i = 0; i < n; i++) {
        unsigned value;
        if (sscanf(argv[1] + i * 2, "%2x", &value) != 1) return 2;
        data[i] = value;
    }
    result = find_sei_end(&ctx, data, n, &end);
    printf("{\"result\":%d,\"offset\":%td}\n", result, end ? end - data : -1);
    free(data);
    return 0;
}
'''


def git(source: Path, *args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(source), *args])


def function(text: str, name: str) -> str:
    # These two production functions have no brace characters in literals or
    # comments. Refuse unexpected forms rather than compiling an edited body.
    start = re.search(r'^static int ' + name + r'\(', text, re.M)
    if not start:
        raise ValueError(f'missing production function {name}')
    opening = text.index('{', start.start())
    depth = 1
    pos = opening + 1
    while depth:
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
        pos += 1
    return text[start.start():pos] + '\n'


def extended(value: int) -> bytes:
    return bytes([255] * (value // 255) + [value % 255])


def message(kind: int, payload: bytes) -> bytes:
    return extended(kind) + extended(len(payload)) + payload


def escape(rbsp: bytes) -> bytes:
    # Independent RBSP->EBSP fixture constructor, not production parser code.
    encoded = bytearray([6])
    zeros = 0
    for byte in rbsp:
        if zeros == 2 and byte <= 3:
            encoded.append(3)
            zeros = 0
        encoded.append(byte)
        zeros = zeros + 1 if byte == 0 else 0
    return bytes(encoded)


def fixtures() -> list[dict]:
    # User_data_unregistered (type5): 16-byte UUID plus arbitrary user bytes.
    uuid = bytes(range(16))
    values = [
        ('unregistered_plain', message(5, uuid)),
        ('unregistered_escaped_uuid', message(5, b'\x00\x00\x01' + uuid[3:])),
        ('unregistered_escaped_zero_uuid', message(5, bytes(16))),
        ('unregistered_escaped_payload_00', message(5, uuid + b'\x00\x00\x00')),
        ('unregistered_escaped_payload_01', message(5, uuid + b'\x00\x00\x01')),
        ('unregistered_escaped_payload_02', message(5, uuid + b'\x00\x00\x02')),
        ('unregistered_escaped_payload_03', message(5, uuid + b'\x00\x00\x03')),
        ('unregistered_size_255', message(5, uuid + b'U' * 239)),
        ('unregistered_size_256', message(5, uuid + b'U' * 240)),
        ('two_escaped_messages', message(5, bytes(16)) + message(5, uuid + b'\x00\x00\x02')),
        # Structurally well-formed unknown type: no known-payload interpretation.
        ('extended_unknown_payload_type', message(260, uuid)),
    ]
    rows = []
    for name, rbsp in values:
        nal = escape(rbsp + b'\x80')
        if name == 'unregistered_escaped_uuid' and nal.hex() != '06051000000301030405060708090a0b0c0d0e0f80':
            raise ValueError('Fixture escape constructor differs from the literal escaped UUID NAL')
        rows.append(dict(name=name, category='well-formed SEI syntax', hex=nal.hex(),
                         expected_result=len(nal), expected_offset=len(nal) - 1))
    malformed = [
        ('header_only', bytes([6])),
        ('truncated_payload', escape(bytes([5, 16, 1, 2, 3]))),
        ('missing_trailing_byte', escape(message(5, uuid))),
        ('truncated_type_extension', bytes([6, 255])),
        ('truncated_size_extension', bytes([6, 5, 255])),
        ('invalid_emulation_prevention', bytes([6, 5, 4, 0, 0, 3, 4, 128])),
        ('truncated_emulation_prevention', bytes([6, 5, 4, 0, 0, 3])),
        ('missing_emulation_prevention', bytes([6, 5, 3, 0, 0, 1, 128])),
    ]
    for name, nal in malformed:
        rows.append(dict(name=name, category='malformed/truncated syntax', hex=nal.hex(),
                         expected_result=-1094995529, expected_offset=-1))
    for name, nal in [('empty', b''), ('non_sei', b'\x65\x80')]:
        rows.append(dict(name=name, category='not SEI', hex=nal.hex(),
                         expected_result=0, expected_offset=-1))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline', default='16efe6927d850d23766aee15820abedcb1219121')
    parser.add_argument('--candidate', default='prep/caption-sei')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cc', default=os.environ.get('CC', 'clang'))
    args = parser.parse_args()
    # No deletion, checkout or package install. Avoid overwriting prior receipts.
    args.output.mkdir(parents=True, exist_ok=False)
    cc = shlex.split(args.cc)
    report = {'scope': 'Production SEI walker only; no VideoToolbox/FATE/encoder execution',
              'source_path': SOURCE, 'compiler': subprocess.check_output(cc + ['--version'], text=True).splitlines()[0],
              'flags': ['-std=c11', '-Wall', '-Wextra', '-Werror', '-O1', '-g', '-fsanitize=address,undefined'],
              'fixtures': fixtures(), 'variants': {}}
    for label, ref in [('baseline', args.baseline), ('candidate', args.candidate)]:
        commit = git(args.source, 'rev-parse', ref).decode().strip()
        source = git(args.source, 'show', f'{commit}:{SOURCE}')
        text = source.decode()
        names = (['read_sei_byte'] if re.search(r'^static int read_sei_byte\(', text, re.M) else []) + ['find_sei_end']
        functions = {name: function(text, name) for name in names}
        c = args.output / f'{label}.c'
        c.write_text(STUBS + '\n'.join(functions.values()) + MAIN)
        exe = args.output / label
        command = cc + report['flags'] + [str(c), '-o', str(exe)]
        subprocess.run(command, check=True)
        variant = dict(commit=commit, source_sha256=hashlib.sha256(source).hexdigest(),
                       function_sha256={name: hashlib.sha256(body.encode()).hexdigest() for name, body in functions.items()},
                       generated_c_sha256=hashlib.sha256(c.read_bytes()).hexdigest(),
                       compile_command=command, results=[])
        for row in report['fixtures']:
            result = subprocess.run([str(exe.resolve()), row['hex']], text=True, capture_output=True,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1'))
            observed = json.loads(result.stdout) if result.returncode == 0 else None
            passed = observed == {'result': row['expected_result'], 'offset': row['expected_offset']}
            variant['results'].append(dict(name=row['name'], passed=passed, observed=observed,
                                           process_exit=result.returncode, stderr=result.stderr))
        variant['passed'] = sum(row['passed'] for row in variant['results'])
        variant['failed'] = len(variant['results']) - variant['passed']
        report['variants'][label] = variant
    (args.output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    for label, row in report['variants'].items():
        print(f"{label}: {row['passed']} pass, {row['failed']} fail")
        for result in row['results']:
            if not result['passed']:
                print(' ', result['name'], result['observed'], 'exit', result['process_exit'])
    baseline_failures = {row['name'] for row in report['variants']['baseline']['results'] if not row['passed']}
    required_failures = {'unregistered_escaped_uuid', 'unregistered_escaped_zero_uuid'}
    return 0 if required_failures <= baseline_failures and not report['variants']['candidate']['failed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
