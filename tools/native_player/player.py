#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Experimental native RPU-aware playback; no display or package configuration changes.

Uses Ubuntu's existing mpv/FFmpeg/libplacebo implementation. Diagnostic evidence
is private, bounded and advisory; an unconfirmed stream is never called DV.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import uuid

MPV = '/usr/bin/mpv'
PROPERTIES = ('video-pts', 'current-vo', 'video-params', 'video-out-params',
              'video-target-params', 'vo-passes', 'decoder-frame-drop-count',
              'frame-drop-count', 'aid')
COLLECTION_SECONDS = 35
MAX_SAMPLES = 35
MAX_IPC_BYTES = 65536  # Total received bytes per property, including events.
MAX_SAMPLE_BYTES = 65536
MAX_RETAINED_SAMPLE_BYTES = 524288
MAX_RECEIPT_BYTES = 1048576
MAX_ERROR_CHARS = 256


def command(media, directory, silent=False):
    args = [MPV, '--no-config', '--load-scripts=no', '--vo=gpu-next', '--gpu-api=vulkan',
            '--gpu-context=waylandvk', '--hwdec=no',
            '--target-colorspace-hint=yes', '--target-colorspace-hint-mode=target',
            '--title=Experimental RPU-aware Player',
            '--input-ipc-server=' + str(directory / 'ipc')]
    if silent:
        args += ['--audio=no']
    if not media:
        args += ['--idle=yes', '--force-window=yes']
    return args + ['--'] + media


def query(connection, stream, name, request_id, deadline=None):
    connection.sendall((json.dumps({'command': ['get_property', name],
                                    'request_id': request_id}) + '\n').encode())
    # Events can be interleaved. Bound aggregate bytes, not just each line.
    # Buffered single-byte reads let the absolute deadline also cover trickled
    # lines; readline's socket timeout alone resets on each underlying read.
    received = 0
    for _ in range(64):
        line = bytearray()
        while True:
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError('diagnostic collection deadline reached')
                connection.settimeout(min(0.5, remaining))
            if received >= MAX_IPC_BYTES:
                raise ValueError('IPC byte bound reached')
            byte = stream.read(1)
            if not byte:
                raise ValueError('incomplete IPC reply')
            received += len(byte)
            line.extend(byte)
            if byte == b'\n':
                break
        reply = json.loads(line)
        if not isinstance(reply, dict):
            raise ValueError('IPC reply must be an object')
        if reply.get('request_id') == request_id:
            return {'error': reply.get('error', 'missing'), 'data': reply.get('data')}
    raise ValueError('IPC response not received within event bound')


def sample(ipc, deadline=None):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(0.5)
        connection.connect(str(ipc))
        with connection.makefile('rb') as stream:
            return {name: query(connection, stream, name, index, deadline)
                    for index, name in enumerate(PROPERTIES, 1)}


def value(sample_data, name):
    reply = sample_data.get(name, {})
    return reply.get('data') if reply.get('error') == 'success' else None


def reshaping(passes):
    if isinstance(passes, dict):
        return (isinstance(passes.get('desc'), str) and
                'reshaping' in passes['desc'].lower()) or any(
                    reshaping(item) for item in passes.values())
    if isinstance(passes, list):
        return any(reshaping(item) for item in passes)
    return False


def evidence(samples):
    # Require DV input and an actual reshaping pass in the same advancing samples.
    pts = []
    for item in samples:
        data = item.get('properties', {})
        out = value(data, 'video-out-params')
        position = value(data, 'video-pts')
        if (value(data, 'current-vo') == 'gpu-next' and isinstance(out, dict) and
                out.get('colormatrix') == 'dolbyvision' and
                reshaping(value(data, 'vo-passes')) and
                isinstance(position, (float, int)) and not isinstance(position, bool) and
                math.isfinite(position)):
            pts.append(position)
    confirmed = any(b > a for a, b in zip(pts, pts[1:]))
    return {'status': 'observed-dv-reshaping' if confirmed else 'unconfirmed',
            'qualifying_samples': len(pts),
            'scope': 'gpu-next DV input and reshaping with advancing PTS; not full CM4, fidelity, certification or compositor pass-through',
            'output_encoding_property': 'video-target-params',
            'input_property': 'video-out-params (filter output / VO input)'}


def state_directory():
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state')))
    if not state.is_absolute():
        raise ValueError('XDG_STATE_HOME must be absolute')
    state = state.resolve()
    if any(state == Path(p) or Path(p) in state.parents
           for p in ('/tmp', '/private/tmp', '/var/tmp')):
        raise ValueError('diagnostics require durable state, not a temporary directory')
    directory = state / 'hermes-hdr/player' / uuid.uuid4().hex[:12]
    if len(os.fsencode(directory / 'ipc')) >= 104:
        raise ValueError('state path too long for private IPC socket; use a shorter durable XDG_STATE_HOME')
    directory.mkdir(parents=True, mode=0o700)
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--silent', action='store_true', help='disable this player audio only')
    parser.add_argument('media', nargs='*', help='local media files; no files opens a drag-and-drop window')
    args = parser.parse_args(argv)
    media = [str(Path(item).expanduser().resolve(strict=True)) for item in args.media]
    if any(not Path(item).is_file() for item in media):
        parser.error('media must be regular local files')
    os.umask(0o077)
    directory = state_directory()
    cmd = command(media, directory, args.silent)
    receipt = {'schema': 2, 'experimental': True, 'command': cmd,
               'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'launcher_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'diagnostic_scope': 'startup only; not every playlist item or late dropped media',
               'diagnostic_limits': {'seconds': COLLECTION_SECONDS, 'samples': MAX_SAMPLES,
                   'ipc_bytes_per_property': MAX_IPC_BYTES, 'sample_bytes': MAX_SAMPLE_BYTES,
                   'retained_sample_bytes': MAX_RETAINED_SAMPLE_BYTES,
                   'receipt_bytes': MAX_RECEIPT_BYTES, 'continuous_log': False},
               'samples': [], 'limitations': ['P7 FEL/residual excluded',
                   'L1 minimum and L2/L8 trims not implemented',
                   'reference accuracy and optical acceptance outstanding',
                   'stock target tagging is not exact preferred-description reuse']}
    receipt_path = directory / 'receipt.json'

    persistence_enabled = True
    warned = False

    def warning():
        nonlocal warned
        if not warned:
            warned = True
            try:
                print('Experimental player: diagnostic persistence/cleanup unavailable; '
                      'playback continues. Receipt may be stale or incomplete.', file=sys.stderr)
            except OSError:
                pass  # A closed diagnostic sink must not close the movie either.

    def save(advisory=False):
        nonlocal persistence_enabled
        if not persistence_enabled:
            return False
        receipt['evidence'] = evidence(receipt['samples'])
        temporary = directory / 'receipt.new'
        try:
            payload = (json.dumps(receipt, separators=(',', ':'), allow_nan=False) + '\n').encode()
            if len(payload) > MAX_RECEIPT_BYTES:
                raise ValueError('diagnostic receipt byte bound reached')
            temporary.write_bytes(payload)
            temporary.replace(receipt_path)
        except (OSError, ValueError, TypeError, RecursionError):
            if not advisory:
                raise
            persistence_enabled = False
            warning()
            # Never change the last atomic successful receipt to imply a final
            # status. A failed partial temporary is bounded and not evidence.
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        return True

    save()
    print('Experimental RPU-aware playback. P5/P8 without residual; no full-fidelity claim.', file=sys.stderr)
    print('Private diagnostics: ' + str(receipt_path), file=sys.stderr)
    process = None

    def stop(signum, _frame):
        if process is not None and process.poll() is None:
            try:
                process.send_signal(signum)
            except ProcessLookupError:
                pass  # Child exited between poll and signal delivery.

    previous = {}
    try:
        process = subprocess.Popen(cmd)
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, stop)
        # Bounded startup collection; no logger persists during movie/idle wait.
        deadline = time.monotonic() + COLLECTION_SECONDS
        retained_bytes = 0
        attempts = 0
        while (process.poll() is None and time.monotonic() < deadline and
               attempts < MAX_SAMPLES and persistence_enabled):
            attempts += 1
            try:
                data = sample(directory / 'ipc', deadline)
                item = {'monotonic': time.monotonic(), 'properties': data}
                size = len(json.dumps(item, separators=(',', ':'), allow_nan=False).encode())
                if size > MAX_SAMPLE_BYTES or retained_bytes + size > MAX_RETAINED_SAMPLE_BYTES:
                    receipt['collection_stop'] = 'retained sample byte bound'
                    break
                receipt['samples'].append(item)
                retained_bytes += size
            except (OSError, ValueError, TypeError, RecursionError) as exc:
                receipt['last_diagnostic_error'] = str(exc)[:MAX_ERROR_CHARS]
            save(advisory=True)
            if not persistence_enabled:
                break
            time.sleep(max(0, min(1, deadline - time.monotonic())))
        receipt.setdefault('collection_stop', 'startup deadline/sample limit or child exit')
        code = process.wait()
        receipt['mpv_exit_code'] = code
        save(advisory=True)
        return code if code >= 0 else 128 - code
    finally:
        try:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            try:
                (directory / 'ipc').unlink(missing_ok=True)
            except OSError:
                warning()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print('Experimental player: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
