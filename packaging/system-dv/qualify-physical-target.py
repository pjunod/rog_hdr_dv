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
for name in ('mpv', 'media', 'weston_config', 'fixture_module', 'output'):
    p.add_argument('--' + name.replace('_', '-'), required=True)
a = p.parse_args()
out = Path(a.output).resolve()
out.mkdir(mode=0o700, parents=True, exist_ok=False)
runtime = out / 'runtime'
runtime.mkdir(mode=0o700)
env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime), WAYLAND_DISPLAY='physical-test')
processes = []

def wait_until(predicate, seconds=30):
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
        s.settimeout(20)
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

try:
    with (out / 'weston-stdout.log').open('wb') as log:
        processes.append(subprocess.Popen(['weston', '--config=' + a.weston_config,
            '--backend=headless', '--renderer=gl', '--socket=physical-test',
            '--modules=' + a.fixture_module, '--width=1920', '--height=1080',
            '--log=' + str(out / 'weston.log')], env=env, stdout=log, stderr=log))
    wait_until(lambda: (runtime / 'physical-test').exists() and (runtime / 'physical-target-control').exists())
    with (out / 'mpv.log').open('wb') as log:
        processes.append(subprocess.Popen([a.mpv, '--no-config', '--vo=gpu-next',
            '--gpu-api=vulkan', '--gpu-context=waylandvk', '--gpu-sw=yes', '--target-colorspace-hint=yes',
            '--loop-file=inf', '--input-ipc-server=' + str(runtime / 'mpv-ipc'), a.media],
            env=env, stdout=log, stderr=log))
    wait_until(lambda: len(mappings()) >= 1)
    first = mappings()[-1]
    assert abs(float(first[0]) - .0004) < 1e-8 and float(first[1]) == 616 and float(first[2]) == 142, first
    ipc(['set_property', 'screenshot-tag-colorspace', False])
    ipc(['screenshot-to-file', str(out / 'A-window.png'), 'window'])
    ipc(['screenshot-to-file', str(out / 'A-video.png'), 'video'])
    ipc(['set_property', 'screenshot-tag-colorspace', True])
    ipc(['screenshot-to-file', str(out / 'A-native.png'), 'video'])
    ipc(['set_property', 'screenshot-tag-colorspace', False])
    # B halves physical peak/reference together, retaining the normalized peak.
    # A new generation and raw 308/.0002/71 prove cache identity is physical.
    fd = os.open(runtime / 'physical-target-control', os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(fd, b'B\n')
    finally:
        os.close(fd)
    wait_until(lambda: any(float(x[1]) == 308 and float(x[2]) == 71 for x in mappings()))
    second = mappings()[-1]
    assert abs(float(second[0]) - .0002) < 1e-8 and int(second[3]) > int(first[3]), second
    ipc(['screenshot-to-file', str(out / 'B-window.png'), 'window'])
    fd = os.open(runtime / 'physical-target-control', os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(fd, b'A\n')
    finally:
        os.close(fd)
    wait_until(lambda: any(float(x[1]) == 616 and int(x[3]) > int(second[3]) for x in mappings()))
    third = mappings()[-1]
    assert abs(float(third[0]) - .0004) < 1e-8 and float(third[2]) == 142, third
    assert int(first[3]) < int(second[3]) < int(third[3])
    ipc(['screenshot-to-file', str(out / 'A-return-window.png'), 'window'])
    ipc(['quit'])
    processes[-1].wait(timeout=15)
    processes.pop()
    controls = {}
    for name, option in [('target-peak', '--target-peak=500'),
                         ('source-hint', '--target-colorspace-hint-mode=source')]:
        with (out / (name + '.log')).open('wb') as log:
            proc = subprocess.run([a.mpv, '--no-config', '--vo=gpu-next',
                '--gpu-api=vulkan', '--gpu-context=waylandvk', '--gpu-sw=yes',
                '--target-colorspace-hint=yes', option, '--frames=12', a.media],
                env=env, stdout=log, stderr=log, timeout=90)
        text = (out / (name + '.log')).read_text(errors='replace')
        assert proc.returncode == 0 and 'automatic DV physical target' not in text, name
        assert 'VO: [gpu-next]' in text, 'negative control did not render: ' + name
        controls[name] = 'rendered; automatic physical mapping suppressed'
    (out / 'receipt.json').write_text(json.dumps({'status': 'pass', 'A': first, 'B': second, 'A_return': third, 'controls': controls,
        'scope': 'automatic physical target and feedback-cache runtime; screenshots retained',
        'physical_accuracy': 'unmeasured; compositor-declared target only'}, indent=2) + '\n')
finally:
    for proc in reversed(processes):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
