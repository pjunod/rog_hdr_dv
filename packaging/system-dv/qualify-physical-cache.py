#!/usr/bin/env python3
"""Run the reviewed mpv in an owned headless compositor; never install packages."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument('--ordinary-media', required=True)
p.add_argument('--start', default='0')
p.add_argument('--check-tagged-png', action='store_true',
               help='also verify the saved window PNG colour declaration (mpv 0.42 +rogdv4 or newer)')
for name in ('mpv', 'media', 'weston_config', 'fixture_module', 'output'):
    p.add_argument('--' + name.replace('_', '-'), required=True)
a = p.parse_args()
out = Path(a.output).resolve()
out.mkdir(mode=0o700, parents=True, exist_ok=False)
runtime = out / 'runtime'
runtime.mkdir(mode=0o700)
env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime), WAYLAND_DISPLAY='physical-test')
processes = []

def wait_until(predicate, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        if any(proc.poll() is not None for proc in processes):
            raise RuntimeError('qualification child exited; inspect retained logs')
        time.sleep(.1)
    raise TimeoutError('qualification condition timed out; inspect retained logs')


def ipc(command):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(90)
        s.connect(str(runtime / 'mpv-ipc'))
        s.sendall((json.dumps({'command': command, 'request_id': 1}) + '\n').encode())
        response = b''
        while True:
            chunk = s.recv(65536)
            if not chunk:
                raise EOFError('mpv IPC closed before command response')
            response += chunk
            while b'\n' in response:
                line, response = response.split(b'\n', 1)
                value = json.loads(line)
                if value.get('request_id') == 1:
                    if value.get('error') != 'success':
                        raise RuntimeError(value)
                    return value


def mappings():
    text = (out / 'mpv.log').read_text(errors='replace')
    return re.findall(r'automatic DV physical target ([\d.e+-]+)\.\.([\d.e+-]+) nits; encoding [^;]+; reference ([\d.e+-]+);.*generation (\d+)', text)

def log_text():
    return (out / 'mpv.log').read_text(errors='replace')


def capture(name, physical, native_csp=0):
    signal = re.findall(r'DV display signal valid=1 cache_reuse=\d peak=([\d.e+-]+)', log_text())
    marker = len(log_text())
    ipc(['screenshot-to-file', str(out / (name + '.png')), 'window'])
    trace = re.findall(rf'DV capture scaled=1 native={native_csp} physical=(\d) signal_valid=(\d) transfer=(\d+) peak=([\d.e+-]+)', log_text()[marker:])
    assert trace, 'no display capture state witness'
    state = trace[-1]
    assert int(state[0]) == physical and int(state[1]) == physical, state
    if physical:
        assert int(state[2]) == 12, state  # PL_COLOR_TRC_PQ in the pinned renderer ABI
        assert signal and abs(float(state[3]) - float(signal[-1])) < 1e-5, state
    assert (out / (name + '.png')).stat().st_size > 0
    return state


try:
    with (out / 'weston-stdout.log').open('wb') as log:
        processes.append(subprocess.Popen(['weston', '--config=' + a.weston_config,
            '--backend=headless', '--renderer=gl', '--socket=physical-test',
            '--modules=' + a.fixture_module, '--width=1920', '--height=1080',
            '--log=' + str(out / 'weston.log')], env=env, stdout=log, stderr=log))
    wait_until(lambda: (runtime / 'physical-test').exists() and (runtime / 'physical-target-control').exists())
    with (out / 'mpv.log').open('wb') as log:
        processes.append(subprocess.Popen([a.mpv, '--no-config', '--vo=gpu-next',
            '--gpu-api=vulkan', '--gpu-context=waylandvk', '--gpu-sw=yes',
            '--target-colorspace-hint=yes', '--msg-level=vo/gpu-next=debug',
            '--start=' + a.start, '--loop-file=inf', '--input-ipc-server=' + str(runtime / 'mpv-ipc'), a.media],
            env=env, stdout=log, stderr=log))
    wait_until(lambda: len(mappings()) >= 1)
    first = mappings()[-1]
    assert float(first[1]) == 616 and float(first[2]) == 142, first
    ipc(['set_property', 'pause', True])
    ipc(['set_property', 'screenshot-tag-colorspace', False])
    # OSD redraw presents a paused cached frame while skipping dovi_map.
    marker = len(log_text())
    ipc(['show-text', 'paused cache regression', 10000])
    wait_until(lambda: 'DV display signal valid=1 cache_reuse=1' in log_text()[marker:])
    cached = capture('A-paused-cache-window', 1)
    tagged = None
    if a.check_tagged_png:
        ipc(['set_property', 'screenshot-tag-colorspace', True])
        tagged = capture('A-tagged-window', 1, native_csp=1)
        stream = json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
            'stream=color_primaries,color_transfer,color_space,color_range',
            '-of', 'json', str(out / 'A-tagged-window.png')]))['streams'][0]
        assert (stream.get('color_primaries'), stream.get('color_transfer'),
                stream.get('color_space'), stream.get('color_range')) == (
                    'bt2020', 'smpte2084', 'gbr', 'pc'), stream
        ipc(['set_property', 'screenshot-tag-colorspace', False])
    fd = os.open(runtime / 'physical-target-control', os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(fd, b'B\n')
    finally:
        os.close(fd)
    wait_until(lambda: any(float(x[1]) == 308 and int(x[3]) > int(first[3]) for x in mappings()))
    second = mappings()[-1]
    changed = capture('B-paused-window', 1)
    # This source has no raw Dolby RPU. The previous target state must not leak.
    marker = len(log_text())
    ipc(['loadfile', a.ordinary_media, 'replace'])
    wait_until(lambda: 'DV display signal valid=0' in log_text()[marker:])
    ordinary = capture('ordinary-window', 0)
    (out / 'receipt.json').write_text(json.dumps({'status':'pass',
        'paused_cache_reuse':True, 'A':first, 'A_cached_capture':cached,
        'A_tagged_window_capture':tagged,
        'B':second, 'B_capture':changed, 'ordinary_source_capture':ordinary,
        'physical_accuracy':'unmeasured; compositor-declared target only'}, indent=2)+'\n')
finally:
    for proc in reversed(processes):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
