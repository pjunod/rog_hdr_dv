#!/usr/bin/python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Exercise the prepared consumer's real capsfilter and linked native mapper.

Usage: showtime-precision-controls.py PREPARED_SHOWTIME/showtime/play.py
Requires the qualified mapper plugin on GStreamer's normal/plugin-test path.
No player, video decoding, GPU rendering, display or installation is started.
"""
import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst


def consumer_filter(source, dolby):
    tree = ast.parse(source.read_text(), filename=str(source))
    methods = [method for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'DoviSurfaceBinding'
               for method in node.body if isinstance(method, ast.FunctionDef) and method.name == 'configure_composition']
    if len(methods) != 1:
        raise ValueError('expected the prepared consumer composition method')
    conditions = [node for node in methods[0].body if isinstance(node, ast.If)
                  and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                          and call.func.attr == 'set_property' and call.args
                          and isinstance(call.args[0], ast.Constant) and call.args[0].value == 'caps'
                          for call in ast.walk(node))]
    if len(conditions) != 1:
        raise ValueError('expected one actual precision-filter update branch')
    # Execute the consumer's original branch, rather than copying its caps literal.
    method = ast.FunctionDef(name='configure', args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='self')],
        kwonlyargs=[], kw_defaults=[], defaults=[]), body=[conditions[0]], decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    namespace = {'Gst': Gst}
    exec(compile(module, str(source), 'exec'), namespace)
    precision = Gst.ElementFactory.make('capsfilter')
    assert precision is not None
    namespace['configure'](SimpleNamespace(precision_filter=precision,
        precision_dolby=not dolby, dolby_stream=dolby))
    return precision


def main():
    Gst.init(None)
    source = Path(sys.argv[1])
    checks = []
    def require(value, label):
        if not value:
            raise AssertionError(label)
        checks.append(label)
    def caps(text):
        result = Gst.Caps.from_string(text)
        assert result is not None
        return result
    precision = consumer_filter(source, True)
    actual = precision.get_property('caps')
    require(not actual.is_any(), 'Dolby consumer retains an explicit precision contract')
    peer = Gst.ElementFactory.make('fakesink')
    require(peer is not None and precision.link(peer), 'real consumer precision filter links to a normal peer')
    sink = precision.get_static_pad('sink')
    domains = ['', '(memory:GLMemory)', '(memory:GLMemory,meta:GstVideoOverlayComposition)',
               '(memory:SystemMemory,meta:GstVideoOverlayComposition)', '(meta:GstVideoOverlayComposition)']
    for domain in domains:
        candidate = caps('video/x-raw' + domain + ',format=RGBA,width=3840,height=2160,framerate=24/1')
        require(not sink.query_caps(candidate).is_empty(), 'consumer peer accepts RGBA ' + (domain or 'system plain'))
        require(sink.query_accept_caps(candidate), 'consumer ACCEPT_CAPS accepts ' + (domain or 'system plain'))
    for text, label in [
        ('video/x-raw,format=RGB', 'wrong RGB format'),
        ('video/x-raw,format=RGBA64_LE', 'wrong RGBA64 precision for the SDR producer'),
        ('video/x-raw(memory:DMABuf),format=RGBA', 'unsupported DMABuf memory'),
        ('video/x-raw(memory:CUDAMemory),format=RGBA', 'unsupported CUDA consumer memory')]:
        require(sink.query_caps(caps(text)).is_empty(), 'consumer rejects ' + label)
        require(not sink.query_accept_caps(caps(text)), 'consumer ACCEPT_CAPS rejects ' + label)
    precision.unlink(peer)

    # The real mapper's reverse query must traverse this actual consumer filter.
    mapper = Gst.ElementFactory.make('gtkdovimap')
    require(mapper is not None, 'qualified native mapper is present')
    mapper.set_property('destination-kind', 1)
    require(mapper.link(precision) and precision.link(peer), 'native mapper links through the actual consumer precision filter')
    input_pad = mapper.get_static_pad('sink')
    record = '01000a350000000000000000000000000000000000000000'
    for memory in ['', 'memory:CUDAMemory', 'memory:VAMemory']:
        for overlay in [False, True]:
            features = [part for part in (memory, 'meta:GstVideoOverlayComposition' if overlay else '') if part]
            domain = '(' + ','.join(features) + ')' if features else ''
            candidate = caps('video/x-raw' + domain + ',format=P010_10LE,width=3840,height=2160,'
                'framerate=24/1,colorimetry=1:0:0:0,dovi-configuration=(buffer)' + record)
            answer = input_pad.query_caps(candidate)
            require(answer.is_equal(candidate), 'linked native marked P010 preimage preserved for ' + (domain or 'system plain'))
            require(input_pad.query_accept_caps(candidate), 'linked native ACCEPT_CAPS supports ' + (domain or 'system plain'))
    require(input_pad.query_caps(caps('video/x-raw(memory:DMABuf),format=P010_10LE,width=3840,height=2160,'
        'framerate=24/1,dovi-configuration=(buffer)' + record)).is_empty(), 'linked marked unsupported memory stays rejected')
    mapper.unlink(precision); precision.unlink(peer)
    ordinary = consumer_filter(source, False)
    require(ordinary.get_property('caps').is_any(), 'ordinary non-Dolby precision filter remains ANY')
    require(ordinary.link(peer), 'ordinary filter links without Dolby constraints')
    require(not ordinary.get_static_pad('sink').query_caps(caps('video/x-raw,format=RGB')).is_empty(),
            'ordinary non-Dolby RGB route remains available')
    ordinary.unlink(peer)
    print(json.dumps({'checks': len(checks), 'prepared_source': str(source), 'consumer_caps': actual.to_string(),
                      'status': 'passed', 'scope': 'real caps queries only; no decoding/display/optical acceptance'}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
