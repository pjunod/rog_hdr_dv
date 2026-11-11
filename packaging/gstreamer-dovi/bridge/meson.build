project('gstdovipicture', 'c', version: '0.2.0', default_options: ['c_std=c11', 'warning_level=3', 'werror=true'])
gst = dependency('gstreamer-video-1.0', version: '=1.28.7')
pbutils = dependency('gstreamer-pbutils-1.0', version: '=1.28.7')
avutil = dependency('libavutil', version: '=60.26.102')
avcodec = dependency('libavcodec', version: '=62.28.102')
cc = meson.get_compiler('c')
if not cc.has_function('av_dovi_rpu_parser_alloc', prefix: '#include <libavcodec/dovi_parser.h>', dependencies: avcodec)
  error('Requires the reviewed public FFmpeg RPU resolver source extension')
endif
bridge = shared_library('gstdovipicture-1.0', ['gstdovipicture.c', 'gstdoviresolver.c', 'gstdovihevc.c', 'gstdoviconfig.c', 'gstdovifel.c'],
  dependencies: [pbutils, gst, avutil, avcodec], version: '0.0.0', soversion: '0',
  gnu_symbol_visibility: 'hidden', install: true)
install_headers('gstdovipicture.h', subdir: 'gstreamer-dovi-1.0')
pkg = import('pkgconfig')
pkg.generate(bridge, name: 'GStreamer Dolby picture bridge', filebase: 'gstdovipicture-1.0',
  description: 'Owned, decoder-resolved in-process Dolby pictures',
  subdirs: 'gstreamer-dovi-1.0', requires: ['gstreamer-video-1.0', 'gstreamer-pbutils-1.0', 'libavutil', 'libavcodec'])
