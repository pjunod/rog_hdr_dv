# SPDX-License-Identifier: MIT
"""Deferred focused launcher regressions. No media, renderer or physical display.

The classifier fixtures are IPC shape fixtures, not Dolby metadata/trims.
Run only after complete-candidate independent review and corrections.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_player', ROOT / 'tools/native_player/player.py')
assert SPEC is not None and SPEC.loader is not None
player = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(player)


def observation(pts, matrix='dolbyvision', passes=None, vo='gpu-next'):
    data = {'video-pts': pts, 'current-vo': vo,
            'video-out-params': {'colormatrix': matrix},
            'vo-passes': {'fresh': [{'desc': 'color decoding, reshaping'}]} if passes is None else passes}
    return {'properties': {name: {'error': 'success', 'data': value} for name, value in data.items()}}


class PlayerTests(unittest.TestCase):
    @contextlib.contextmanager
    def lifecycle(self, exit_code=7, already_exited=False):
        # Real private receipt bytes; only the child/clock/control are fixtures.
        # Validation supplies a durable task-owned TMPDIR, never system /tmp.
        with tempfile.TemporaryDirectory() as base, contextlib.ExitStack() as stack:
            directory = Path(base)
            state = {'code': exit_code if already_exited else None, 'clock': 0}
            child = mock.Mock()
            child.poll.side_effect = lambda: state['code']
            def wait(timeout=None):
                state['code'] = exit_code
                return exit_code
            child.wait.side_effect = wait
            def sleep(seconds):
                state['clock'] += seconds
            handlers = {}
            original = {sig: object() for sig in (player.signal.SIGINT, player.signal.SIGTERM)}
            def signal(sig, handler):
                previous = handlers.get(sig, original[sig])
                handlers[sig] = handler
                return previous
            stderr = io.StringIO()
            stack.enter_context(mock.patch.object(player, 'state_directory', return_value=directory))
            popen = stack.enter_context(mock.patch.object(player.subprocess, 'Popen', return_value=child))
            sampled = stack.enter_context(mock.patch.object(player, 'sample', return_value=observation(1)['properties']))
            stack.enter_context(mock.patch.object(player.time, 'monotonic', side_effect=lambda: state['clock']))
            stack.enter_context(mock.patch.object(player.time, 'sleep', side_effect=sleep))
            stack.enter_context(mock.patch.object(player.signal, 'signal', side_effect=signal))
            stack.enter_context(mock.patch.object(player.os, 'umask'))
            stack.enter_context(mock.patch.object(player.sys, 'stderr', stderr))
            yield {'directory': directory, 'state': state, 'child': child, 'sample': sampled,
                   'popen': popen, 'stderr': stderr, 'handlers': handlers, 'original': original}

    def assert_clean_exit(self, run):
        run['child'].terminate.assert_not_called()
        run['child'].kill.assert_not_called()
        self.assertEqual(run['handlers'], run['original'])
        self.assertFalse((run['directory'] / 'ipc').exists())

    def test_deterministic_native_command_and_literal_media(self):
        media = ['/owned/-strange name;literal.mp4']
        args = player.command(media, Path('/owned/run'))
        self.assertEqual(args[0], '/usr/bin/mpv')
        for flag in ('--no-config', '--load-scripts=no', '--hwdec=no', '--vo=gpu-next',
                     '--gpu-api=vulkan', '--gpu-context=waylandvk',
                     '--target-colorspace-hint=yes', '--target-colorspace-hint-mode=target'):
            self.assertIn(flag, args)
        self.assertEqual(args[-2:], ['--', media[0]])
        self.assertFalse(any(a.startswith(('--target-peak=', '--target-trc=', '--target-prim=')) for a in args))
        self.assertNotIn('--audio=no', args)
        self.assertFalse(any(a.startswith(('--log-file=', '--msg-level=')) for a in args))

    def test_silent_changes_only_player_audio(self):
        normal = player.command(['a'], Path('/owned/run'))
        silent = player.command(['a'], Path('/owned/run'), True)
        self.assertEqual([a for a in silent if a != '--audio=no'], normal)

    def test_no_files_opens_drag_drop_window(self):
        args = player.command([], Path('/owned/run'))
        self.assertIn('--idle=yes', args)
        self.assertIn('--force-window=yes', args)

    def test_classifier_requires_correlated_reshaping_and_progress(self):
        result = player.evidence([observation(1), observation(2)])
        self.assertEqual(result['status'], 'observed-dv-reshaping')
        self.assertIn('VO input', result['input_property'])
        self.assertEqual(result['output_encoding_property'], 'video-target-params')
        for samples in ([observation(1)], [observation(1), observation(1)],
                        [observation(2), observation(1)],
                        [observation(1, 'bt.2020-ncl'), observation(2, 'bt.2020-ncl')],
                        [observation(1, passes={}), observation(2, passes={})],
                        [observation(1, vo='gpu'), observation(2, vo='gpu')]):
            with self.subTest(samples=samples):
                self.assertEqual(player.evidence(samples)['status'], 'unconfirmed')

    def test_invalid_pts_never_confirms(self):
        for pts in (None, True, '1', float('nan'), float('inf')):
            with self.subTest(pts=pts):
                self.assertEqual(player.evidence([observation(pts), observation(2)])['status'], 'unconfirmed')

    def test_reshaping_must_be_real_pass_description(self):
        self.assertFalse(player.reshaping({'config': 'reshaping'}))
        self.assertFalse(player.reshaping('reshaping'))
        self.assertTrue(player.reshaping({'fresh': [{'desc': 'color decoding, reshaping'}]}))

    def test_error_reply_is_not_property_value(self):
        self.assertIsNone(player.value({'x': {'error':'property unavailable','data':'dolbyvision'}}, 'x'))
        self.assertIsNone(player.value({}, 'x'))

    def test_ipc_reply_correlation_ignores_events_and_other_requests(self):
        left, right = socket.socketpair()
        replies = [{'event':'property-change'}, {'request_id':3,'data':'wrong'},
                   {'request_id':7,'error':'success','data':123}]
        def server():
            try:
                right.recv(4096)
                right.sendall(b''.join((json.dumps(x)+'\n').encode() for x in replies))
            finally:
                right.close()
        thread = threading.Thread(target=server)
        thread.start()
        try:
            with left, left.makefile('rb') as stream:
                self.assertEqual(player.query(left, stream, 'video-pts', 7), {'error':'success','data':123})
        finally:
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_ipc_truncated_and_excess_events_are_rejected(self):
        for content in (b'{"request_id":1}', b'{"event":"x"}\n' * 64):
            with self.subTest(content=content[:30]):
                connection = mock.Mock()
                with self.assertRaises(ValueError):
                    player.query(connection, io.BytesIO(content), 'video-pts', 1)

    def test_ipc_aggregate_byte_bound_covers_events_and_partial_lines(self):
        for content in (b'x' * (player.MAX_IPC_BYTES + 1),
                        (b'{"event":"' + b'x' * 2048 + b'"}\n') * 64):
            with self.subTest(event_stream=content.startswith(b'{')):
                stream = io.BytesIO(content)
                with self.assertRaisesRegex(ValueError, 'byte bound'):
                    player.query(mock.Mock(), stream, 'video-pts', 1)
                self.assertEqual(stream.tell(), player.MAX_IPC_BYTES)

    def test_ipc_absolute_deadline_covers_trickled_incomplete_line(self):
        stream = io.BytesIO(b'{"request_id":1}\n')
        with mock.patch.object(player.time, 'monotonic', side_effect=[0, 1, 2]):
            with self.assertRaisesRegex(ValueError, 'deadline'):
                player.query(mock.Mock(), stream, 'video-pts', 1, deadline=2)
        self.assertEqual(stream.tell(), 2)

    def test_mid_playback_write_or_rename_failure_retains_last_receipt_and_child(self):
        for operation in ('write_bytes', 'replace'):
            with self.subTest(operation=operation), self.lifecycle() as run:
                original = getattr(Path, operation)
                calls = []
                def failing(path, *args, **kwargs):
                    if path.name == 'receipt.new':
                        calls.append(path)
                        if len(calls) == 3:
                            raise OSError('disk full')
                    return original(path, *args, **kwargs)
                with mock.patch.object(Path, operation, failing):
                    self.assertEqual(player.main([]), 7)
                self.assertEqual(len(calls), 3)  # No persistence retry at exit.
                receipt = json.loads((run['directory'] / 'receipt.json').read_bytes())
                self.assertEqual(len(receipt['samples']), 1)
                self.assertNotIn('mpv_exit_code', receipt)
                self.assertFalse((run['directory'] / 'receipt.new').exists())
                self.assertEqual(run['stderr'].getvalue().count('stale or incomplete'), 1)
                run['child'].wait.assert_called_once_with()
                self.assert_clean_exit(run)

    def test_final_persistence_failure_does_not_mask_actual_child_status(self):
        for operation in ('write_bytes', 'replace'):
            for code in (0, 7, -player.signal.SIGTERM):
                with self.subTest(operation=operation, code=code), self.lifecycle(code, True) as run:
                    original = getattr(Path, operation)
                    calls = []
                    def failing(path, *args, **kwargs):
                        if path.name == 'receipt.new':
                            calls.append(path)
                            if len(calls) == 2:
                                raise OSError('removed run directory')
                        return original(path, *args, **kwargs)
                    with mock.patch.object(Path, operation, failing):
                        self.assertEqual(player.main([]), code if code >= 0 else 128 - code)
                    receipt = json.loads((run['directory'] / 'receipt.json').read_bytes())
                    self.assertNotIn('mpv_exit_code', receipt)
                    self.assertEqual(len(calls), 2)
                    self.assertEqual(run['stderr'].getvalue().count('stale or incomplete'), 1)
                    self.assert_clean_exit(run)

    def test_final_serialization_failure_is_advisory(self):
        with self.lifecycle(already_exited=True) as run:
            original = json.dumps
            def serialize(data, *args, **kwargs):
                if isinstance(data, dict) and 'mpv_exit_code' in data:
                    raise TypeError('unsupported diagnostic value')
                return original(data, *args, **kwargs)
            with mock.patch.object(player.json, 'dumps', side_effect=serialize):
                self.assertEqual(player.main([]), 7)
            self.assertNotIn('mpv_exit_code', json.loads((run['directory'] / 'receipt.json').read_bytes()))
            self.assert_clean_exit(run)

    def test_mid_playback_serialization_failure_disables_persistence(self):
        with self.lifecycle() as run:
            original = json.dumps
            failed = []
            def serialize(data, *args, **kwargs):
                if isinstance(data, dict) and len(data.get('samples', [])) == 2:
                    failed.append(True)
                    raise ValueError('diagnostic serialization failed')
                return original(data, *args, **kwargs)
            with mock.patch.object(player.json, 'dumps', side_effect=serialize):
                self.assertEqual(player.main([]), 7)
            self.assertEqual(failed, [True])
            receipt = json.loads((run['directory'] / 'receipt.json').read_bytes())
            self.assertEqual(len(receipt['samples']), 1)
            self.assertNotIn('mpv_exit_code', receipt)
            self.assert_clean_exit(run)

    def test_initial_receipt_failure_starts_no_child(self):
        with self.lifecycle() as run, mock.patch.object(Path, 'write_bytes', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                player.main([])
            run['popen'].assert_not_called()

    def test_child_start_failure_propagates_without_diagnostic_status_claim(self):
        with self.lifecycle() as run:
            run['popen'].side_effect = OSError('mpv unavailable')
            with self.assertRaisesRegex(OSError, 'mpv unavailable'):
                player.main([])
            run['sample'].assert_not_called()
            run['child'].wait.assert_not_called()
            receipt = json.loads((run['directory'] / 'receipt.json').read_bytes())
            self.assertNotIn('mpv_exit_code', receipt)
            self.assertEqual(run['handlers'], {})

    def test_unavailable_ipc_has_startup_bound_and_no_log_or_false_confirmation(self):
        with self.lifecycle() as run:
            run['sample'].side_effect = OSError('unavailable ' + 'x' * 2000)
            self.assertEqual(player.main([]), 7)
            receipt_path = run['directory'] / 'receipt.json'
            receipt = json.loads(receipt_path.read_bytes())
            self.assertEqual(run['sample'].call_count, player.COLLECTION_SECONDS)
            self.assertEqual(receipt['samples'], [])
            self.assertEqual(receipt['evidence']['status'], 'unconfirmed')
            self.assertEqual(len(receipt['last_diagnostic_error']), player.MAX_ERROR_CHARS)
            self.assertLessEqual(receipt_path.stat().st_size, player.MAX_RECEIPT_BYTES)
            self.assertFalse((run['directory'] / 'mpv.log').exists())
            self.assertFalse(receipt['diagnostic_limits']['continuous_log'])
            self.assert_clean_exit(run)

    def test_unavailable_ipc_attempt_limit_is_independent_of_clock_progress(self):
        with self.lifecycle() as run:
            run['sample'].side_effect = OSError('IPC unavailable')
            with mock.patch.object(player.time, 'sleep'):
                self.assertEqual(player.main([]), 7)
            self.assertEqual(run['sample'].call_count, player.MAX_SAMPLES)
            self.assert_clean_exit(run)

    def test_sample_count_bound_is_independent_of_clock_progress(self):
        with self.lifecycle() as run:
            with mock.patch.object(player.time, 'sleep'):
                self.assertEqual(player.main([]), 7)
            self.assertEqual(run['sample'].call_count, player.MAX_SAMPLES)
            receipt = json.loads((run['directory'] / 'receipt.json').read_bytes())
            self.assertEqual(len(receipt['samples']), player.MAX_SAMPLES)
            self.assert_clean_exit(run)

    def test_sample_and_total_retained_byte_bounds(self):
        for payload_bytes in (50000, player.MAX_SAMPLE_BYTES + 1):
            with self.subTest(payload_bytes=payload_bytes), self.lifecycle() as run:
                run['sample'].return_value = {'bounded_fixture': 'x' * payload_bytes}
                self.assertEqual(player.main([]), 7)
                path = run['directory'] / 'receipt.json'
                receipt = json.loads(path.read_bytes())
                self.assertEqual(receipt['collection_stop'], 'retained sample byte bound')
                sizes = [len(json.dumps(s, separators=(',', ':'), allow_nan=False).encode()) for s in receipt['samples']]
                self.assertTrue(all(size <= player.MAX_SAMPLE_BYTES for size in sizes))
                self.assertLessEqual(sum(sizes), player.MAX_RETAINED_SAMPLE_BYTES)
                self.assertLessEqual(path.stat().st_size, player.MAX_RECEIPT_BYTES)
                self.assert_clean_exit(run)

    def test_receipt_byte_overflow_after_start_is_advisory(self):
        with self.lifecycle() as run:
            def overflow(*args):
                # Initial receipt has already been saved, so invalidate only
                # the subsequent bounded diagnostic write, not startup.
                setattr(player, 'MAX_RECEIPT_BYTES', 1)
                return observation(1)['properties']
            run['sample'].side_effect = overflow
            with mock.patch.object(player, 'MAX_RECEIPT_BYTES', player.MAX_RECEIPT_BYTES):
                self.assertEqual(player.main([]), 7)
            receipt = json.loads((run['directory'] / 'receipt.json').read_bytes())
            self.assertNotIn('mpv_exit_code', receipt)
            self.assertEqual(run['stderr'].getvalue().count('stale or incomplete'), 1)
            self.assert_clean_exit(run)

    def test_signals_forward_and_restore_without_terminating_exited_child(self):
        for sig in (player.signal.SIGINT, player.signal.SIGTERM):
            with self.subTest(sig=sig), self.lifecycle(-sig) as run:
                def deliver(*args):
                    run['handlers'][sig](sig, None)
                    run['state']['code'] = -sig
                    return observation(1)['properties']
                run['sample'].side_effect = deliver
                (run['directory'] / 'ipc').touch()
                self.assertEqual(player.main([]), 128 + sig)
                run['child'].send_signal.assert_called_once_with(sig)
                self.assert_clean_exit(run)

    def test_signal_exit_race_is_not_a_fatal_control_failure(self):
        with self.lifecycle(0) as run:
            def race(sig):
                run['state']['code'] = 0
                raise ProcessLookupError('already exited')
            run['child'].send_signal.side_effect = race
            def deliver(*args):
                run['handlers'][player.signal.SIGTERM](player.signal.SIGTERM, None)
                return observation(1)['properties']
            run['sample'].side_effect = deliver
            self.assertEqual(player.main([]), 0)
            self.assert_clean_exit(run)

    def test_cancellation_and_unrelated_fatal_error_cleanup_and_reap_child(self):
        for failure in (KeyboardInterrupt(), RuntimeError('fatal control failure')):
            with self.subTest(failure=type(failure).__name__), self.lifecycle() as run:
                run['sample'].side_effect = failure
                run['child'].wait.side_effect = [subprocess.TimeoutExpired('mpv', 3), 7]
                (run['directory'] / 'ipc').touch()
                with self.assertRaises(type(failure)):
                    player.main([])
                run['child'].terminate.assert_called_once_with()
                run['child'].kill.assert_called_once_with()
                self.assertEqual(run['child'].wait.call_args_list, [mock.call(timeout=3), mock.call()])
                self.assertEqual(run['handlers'], run['original'])
                self.assertFalse((run['directory'] / 'ipc').exists())

    def test_partial_signal_registration_failure_still_reaps_child(self):
        with self.lifecycle() as run:
            original = player.signal.signal
            def install(sig, handler):
                if sig == player.signal.SIGTERM:
                    raise RuntimeError('signal registration failed')
                return original(sig, handler)
            with mock.patch.object(player.signal, 'signal', side_effect=install):
                with self.assertRaisesRegex(RuntimeError, 'registration'):
                    player.main([])
            run['child'].terminate.assert_called_once_with()
            run['child'].wait.assert_called_once_with(timeout=3)
            self.assertEqual(run['handlers'][player.signal.SIGINT], run['original'][player.signal.SIGINT])

    def test_cleanup_unlink_failure_does_not_mask_exit_status(self):
        with self.lifecycle(already_exited=True) as run:
            original = Path.unlink
            def unlink(path, *args, **kwargs):
                if path.name == 'ipc':
                    raise OSError('permission changed')
                return original(path, *args, **kwargs)
            with mock.patch.object(Path, 'unlink', unlink):
                self.assertEqual(player.main([]), 7)
            self.assertEqual(run['stderr'].getvalue().count('stale or incomplete'), 1)
            self.assert_clean_exit(run)

    def test_private_durable_state_permissions(self):
        with tempfile.TemporaryDirectory() as base:
            # Test runner TMPDIR must be under the task-owned durable root.
            with mock.patch.dict(os.environ, {'XDG_STATE_HOME':base}):
                old = os.umask(0o077)
                try:
                    directory = player.state_directory()
                finally:
                    os.umask(old)
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                self.assertTrue(directory.is_relative_to(Path(base)))

    def test_state_rejects_ephemeral_relative_and_socket_overflow(self):
        for base in ('/tmp/player', '/private/tmp/player', '/var/tmp/player', 'relative', '/owned/'+'x'*120):
            with self.subTest(base=base), mock.patch.dict(os.environ, {'XDG_STATE_HOME':base}):
                with self.assertRaises(ValueError):
                    player.state_directory()

    def test_desktop_control_and_no_global_configuration_payload(self):
        directory = ROOT / 'tools/native_player'
        desktop = (directory / 'player.desktop').read_text()
        control = (directory / 'control').read_text()
        self.assertIn('Exec=hermes-hdr-player -- %F', desktop)
        self.assertIn('Architecture: all', control)
        self.assertIn('libplacebo360 (>= 7.360.1)', control)
        self.assertNotIn('mutter', control.split('Description:',1)[0])
        self.assertNotIn('pulseaudio', control)


if __name__ == '__main__':
    unittest.main()
