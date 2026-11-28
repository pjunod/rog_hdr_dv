project('gst-gtk-dovi-map', 'c', version: '0.1.0',
  default_options: ['c_std=c11', 'warning_level=3', 'werror=true'])
core = dependency('gstreamer-1.0', version: '=1.28.7')
gst = dependency('gstreamer-video-1.0', version: '=1.28.7')
base = dependency('gstreamer-base-1.0', version: '=1.28.7')
bridge = dependency('gstdovipicture-1.0', version: '=0.2.0')
# The mapping rules are the core's; this library adapts GStreamer to it.
dovimap = dependency('rog-dovi-map', version: '=0.1.0')
avutil = dependency('libavutil', version: '=60.26.102')
mapper = shared_library('gstgtkdovicore', ['mapper.c', 'native-frame.c'],
  dependencies: [gst, bridge, dovimap, avutil],
  gnu_symbol_visibility: 'hidden', version: '0.0.0', soversion: '0', install: true)
shared_module('gstgtkdovimap', 'gstgtkdovimap.c', link_with: mapper,
  dependencies: [gst, base, bridge, dovimap], gnu_symbol_visibility: 'hidden',
  install: true, install_dir: core.get_variable(pkgconfig: 'pluginsdir'))
install_headers('mapper.h', subdir: 'gst-gtk-dovi-1.0')
pkg = import('pkgconfig')
pkg.generate(mapper, name: 'GTK Dolby visible picture mapping', filebase: 'gst-gtk-dovi-core',
  subdirs: 'gst-gtk-dovi-1.0', requires: ['gstreamer-video-1.0'], version: '1')
