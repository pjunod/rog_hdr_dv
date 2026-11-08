#!/usr/bin/env python3
"""One isolated product run of the normal packaged sink; not a unit suite.

Requires the self-owned 24fps chart with graded frames at .25 seconds, the
normal packaged Showtime binder, and the metadata-only reviewoverlay plugin.
All artifacts remain in --output. The compositor is owned by the caller.
"""
import argparse
import ast
import gc
import json
import math
import os
from pathlib import Path
import pwd
import subprocess
import threading
import time

p = argparse.ArgumentParser()
p.add_argument('--media', required=True)
p.add_argument('--showtime-module', required=True)
p.add_argument('--target-command', required=True)
p.add_argument('--output', required=True)
p.add_argument('--decoder', default='nvh265dec', choices=('nvh265dec', 'avdec_h265', 'vah265dec'))
p.add_argument('--peak-a', type=float, default=616)
p.add_argument('--peak-b', type=float, default=308)
a = p.parse_args()
out = Path(a.output)
out.mkdir(parents=True, exist_ok=False)
runtime = Path(os.environ['XDG_RUNTIME_DIR'])
socket = runtime / os.environ['WAYLAND_DISPLAY']
assert runtime.resolve() != Path('/run/user') / str(os.getuid())
assert not socket.is_symlink() and socket.is_socket(), 'private compositor required'
assert os.environ.get('DBUS_SESSION_BUS_ADDRESS')
assert Path(os.environ['HOME']) != Path(pwd.getpwuid(os.getuid()).pw_dir)

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GdkWayland', '4.0')
from gi.repository import Gdk, GdkWayland, GLib, GObject, Gst, Gtk
Gst.init(None)
Gtk.init()

# Use the shipped surface/lease publisher, without importing the rest of the
# application UI. No target fields or readiness witnesses are synthesized.
module = ast.parse(Path(a.showtime_module).read_text())
node = next(n for n in module.body if isinstance(n, ast.ClassDef)
            and n.name == 'DoviSurfaceBinding')
namespace = dict(Gdk=Gdk, GdkWayland=GdkWayland, GLib=GLib, GObject=GObject,
                 Gst=Gst, Gtk=Gtk)
exec(compile(ast.Module(body=[node], type_ignores=[]), a.showtime_module, 'exec'), namespace)
Binding = namespace['DoviSurfaceBinding']
context = GLib.MainContext.default()
assert context.acquire(), 'fixture must own GTK main context'
errors = []


def pump(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        if errors:
            raise RuntimeError(errors[-1])
        time.sleep(.01)


def wait(test, label, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = test()
        if result:
            return result
        pump(.05)
    raise RuntimeError('Timed out: ' + label)


def control(fn, label):
    result = []
    failure = []

    def work():
        try:
            result.append(fn())
        except BaseException as error:
            failure.append(error)

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    wait(lambda: not worker.is_alive(), label)
    if failure:
        raise failure[0]
    return result[0]


def target(peak):
    result = subprocess.run(['/usr/bin/python3', a.target_command, str(peak)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    pump(.3)
    return result.stdout


class Product:
    def __init__(self, ordinary=False):
        self.ordinary = ordinary
        source = ('videotestsrc is-live=true ! '
                  'video/x-raw,format=RGBA64_LE,width=2560,height=1280,framerate=24/1'
                  if ordinary else 'filesrc location=' + json.dumps(a.media) +
                  ' ! qtdemux ! h265parse ! ' + a.decoder)
        self.pipeline = Gst.parse_launch(source +
            ' ! reviewoverlay name=before mode=0 ! gtkdovimap name=mapper')
        self.before = self.pipeline.get_by_name('before')
        self.mapper = self.pipeline.get_by_name('mapper')
        self.after = Gst.ElementFactory.make('reviewoverlay', 'after')
        self.after.set_property('mode', 1)
        self.sink = Gst.ElementFactory.make('gtk4paintablesink', 'sink')
        self.sink.set_property('enable-last-sample', False)
        # Normal clients obtain the paintable before linking: this initializes
        # the product's shared GDK GL context and refreshes its GL caps.
        self.paintable = self.sink.get_property('paintable')
        holder = Gst.Bin.new('actual-overlay-sink')
        precision = Gst.ElementFactory.make('capsfilter', 'precision')
        holder.add(precision)
        holder.add(self.after)
        holder.add(self.sink)
        assert precision.link(self.after)
        assert self.after.link(self.sink)
        holder.add_pad(Gst.GhostPad.new('sink', precision.get_static_pad('sink')))
        gl = Gst.ElementFactory.make('glsinkbin', 'gl')
        gl.set_property('sink', holder)
        self.pipeline.add(gl)
        assert self.mapper.link(gl)
        self.after.set_property('paintable', self.paintable)
        self.picture = Gtk.Picture.new_for_paintable(self.paintable)
        self.window = Gtk.Window(default_width=960, default_height=540,
                                 title='Isolated paused-overlay product control')
        self.window.set_child(self.picture)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.error_handler = self.bus.connect('message::error', self.error)
        self.binding = Binding(self.picture, self.mapper, self.pipeline, precision, self.sink)
        self.window.fullscreen()
        self.window.present()
        self.pipeline.set_state(Gst.State.PLAYING)
        if ordinary:
            wait(lambda: self.capture()['texture_count'] > 0, 'ordinary first frame')
        else:
            wait(lambda: self.binding.dolby_stream and self.binding.render_state() is not None,
                 'real native HDR surface lease', timeout=45)

    def error(self, _bus, message):
        error, debug = message.parse_error()
        errors.append(str(error) + ': ' + str(debug))

    def capture(self):
        return json.loads(self.after.emit('capture'))

    def metadata(self):
        return json.loads(self.after.emit('metadata'))

    def lifetimes(self):
        return json.loads(self.after.emit('lifetimes'))

    @staticmethod
    def overlays(snapshot):
        return [t for t in snapshot['textures']
                if t['pixel_w'] == 16 and t['pixel_h'] == 16]

    @staticmethod
    def base(snapshot):
        return [t for t in snapshot['textures']
                if t['pixel_w'] > 16 or t['pixel_h'] > 16]

    def assert_rectangles(self, snapshot, metadata):
        expected = [r for meta in metadata['metas'] for r in meta]
        actual = self.overlays(snapshot)
        assert len(expected) == len(actual), (expected, actual)
        for want, got in zip(expected, actual):
            for field in ('x', 'y', 'w', 'h', 'alpha'):
                assert math.isclose(want[field], got[field], abs_tol=1e-6), (want, got)

    def select(self, mode, position):
        self.after.set_property('mode', mode)
        control(lambda: self.pipeline.set_state(Gst.State.PAUSED), 'pause pipeline')
        pump(.3)
        assert control(lambda: self.pipeline.seek_simple(Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE, int(position * Gst.SECOND)), 'seek new source frame')
        wait(lambda: self.metadata().get('pts') == int(position * Gst.SECOND), 'exact paused frame')
        pump(.6)
        metadata = self.metadata()
        snapshot = self.capture()
        self.assert_rectangles(snapshot, metadata)
        assert len(metadata['metas']) == {1: 3, 2: 2, 3: 0}[mode], metadata
        return metadata, snapshot

    def case(self, mode, position, retired_ids=()):
        target(a.peak_a)
        metadata, initial = self.select(mode, position)
        if retired_ids:
            wait(lambda: all(entry['finalized'] for entry in self.lifetimes()
                             if entry['id'] in retired_ids),
                 'previous visible downstream compositions released on source change')
        original_overlays = self.overlays(initial)
        original_base = self.base(initial)
        assert original_base
        ledger = self.lifetimes()
        visible = {}
        for entry in ledger:
            if entry['pts'] == metadata['pts'] and entry['mode'] in ((0, 1) if mode == 1 else (mode,)):
                visible[(entry['mode'], entry['ordinal'])] = entry
        visible_ids = {entry['id'] for entry in visible.values()}
        assert len(visible_ids) == {1: 3, 2: 2, 3: 0}[mode]

        def preserved():
            snapshot = self.capture()
            assert self.metadata() == metadata, 'streamed buffer changed during paused redraw'
            entries = {entry['id']: entry for entry in self.lifetimes()}
            assert all(not entries[i]['finalized'] for i in visible_ids)
            if snapshot['texture_count'] == 0:
                return None  # A real lease transition may temporarily hide pixels.
            self.assert_rectangles(snapshot, metadata)
            assert self.overlays(snapshot) == original_overlays
            return snapshot

        def grade(matches_original):
            snapshot = preserved()
            if snapshot is None:
                return None
            return snapshot if (self.base(snapshot) == original_base) == matches_original else None

        target_b = target(a.peak_b)
        changed = wait(lambda: grade(False), 'actual paused grade changed')
        target_a = target(a.peak_a)
        restored = wait(lambda: grade(True), 'original grade restored exactly')
        # Conservative availability-denial control: copy the actual published
        # target, deny readiness and composition, and keep its valid physical target.
        # This injects no positive readiness or target values.
        current = self.mapper.get_context('gst.gtk.dovi.target.v1')
        denied = current.get_structure().copy()
        denied.set_name('gst.gtk.dovi.target.v1')
        self.binding.serial += 1
        denied.set_value('generation', GObject.Value(GObject.TYPE_UINT64, self.binding.serial))
        denied.set_value('hdr-ready', False)
        denied.set_value('composed', False)
        context_denied = self.mapper.emit('create-target-context', denied)
        self.mapper.set_context(context_denied)
        self.sink.set_context(context_denied)
        wait(lambda: self.capture()['texture_count'] == 0, 'temporary composition denial clear')
        entries = {entry['id']: entry for entry in self.lifetimes()}
        assert all(not entries[i]['finalized'] for i in visible_ids)
        self.binding.last_context_key = None
        self.binding.changed(self.binding.surface)
        resumed = wait(lambda: grade(True),
                       'eligible retained picture and overlays restored', timeout=45)
        return dict(mode=mode, pts=metadata['pts'], metadata=metadata,
                    visible_composition_ids=sorted(visible_ids),
                    downstream_composition_ids=sorted(entry['id'] for entry in visible.values()
                                                      if entry['mode'] != 0),
                    retired_downstream_ids=list(retired_ids), initial=initial,
                    changed=changed, restored=restored, resumed=resumed,
                    target_b=target_b, target_a=target_a)

    def close(self):
        self.binding.dispose()
        control(lambda: self.pipeline.set_state(Gst.State.NULL), 'stop pipeline')
        self.after.set_property('paintable', None)
        self.picture.set_paintable(None)
        self.window.destroy()
        self.bus.disconnect(self.error_handler)
        self.bus.remove_signal_watch()
        self.binding = self.picture = self.paintable = self.window = None
        self.sink = self.before = self.mapper = self.bus = None
        self.pipeline = None
        gc.collect()
        pump(1)


result = {'scope': 'Normal packaged sink on isolated native compositor; no optical claim',
          'native_cases': [], 'unit_suites_executed': False}
product = None
try:
    target(a.peak_a)
    product = Product()
    retired = []
    for mode, position in ((1, 10.25), (2, 20.25), (3, 30.25)):
        case = product.case(mode, position, retired)
        result['native_cases'].append(case)
        retired = case['downstream_composition_ids']
        (out / 'progress.json').write_text(json.dumps(result, indent=2))
    product.close()
    product = Product(ordinary=True)
    control(lambda: product.pipeline.set_state(Gst.State.PAUSED), 'pause ordinary pipeline')
    pump(.5)
    before = product.capture()
    metadata = product.metadata()
    product.assert_rectangles(before, metadata)
    target(a.peak_b)
    pump(1)
    after = product.capture()
    assert before == after, 'ordinary paused frame/overlay path changed'
    result['ordinary'] = dict(before=before, after=after, metadata=metadata)
    product.close()
    result['pass'] = True
finally:
    if product is not None and product.pipeline is not None:
        product.close()
    (out / 'RESULT.json').write_text(json.dumps(result, indent=2))
    context.release()
