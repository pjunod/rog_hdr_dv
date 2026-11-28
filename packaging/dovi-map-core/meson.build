project('rog-dovi-map', 'c', version: '0.1.0',
  default_options: ['c_std=c11', 'warning_level=3', 'werror=true'])
provider = dependency('rog-dv-provider387', version: '>=1')
placebo = dependency('libplacebo-rog387')
avutil = dependency('libavutil', version: '=60.26.102')
gbm = dependency('gbm')
drm = dependency('libdrm')
vulkan = dependency('vulkan')
threads = dependency('threads')
m = meson.get_compiler('c').find_library('m')
core = shared_library('rog-dovi-map', 'rog-dovi-map.c',
  dependencies: [provider, placebo, avutil, gbm, drm, vulkan, threads, m],
  gnu_symbol_visibility: 'hidden', version: '1.0.0', soversion: '1', install: true)
rog_dovi_map_dep = declare_dependency(link_with: core,
  include_directories: include_directories('.'))
meson.override_dependency('rog-dovi-map', rog_dovi_map_dep)
install_headers('rog-dovi-map.h', subdir: 'rog-dovi-map-1')
pkg = import('pkgconfig')
pkg.generate(core, name: 'ROG Dolby Vision mapping core', filebase: 'rog-dovi-map',
  description: 'Per-picture Dolby Vision mapping with a plain C ABI',
  subdirs: 'rog-dovi-map-1', version: meson.project_version())
# Probes: built, never installed. rules runs anywhere; core-map-dump needs a
# GPU, the provider and media (see README.md).
executable('rog-dovi-map-rules', 'probes/rules.c',
  dependencies: [provider, placebo, avutil, gbm, drm, vulkan, threads, m],
  install: false)
executable('core-map-dump', 'probes/core-map-dump.c', link_with: core,
  dependencies: [dependency('libavformat'), dependency('libavcodec'), avutil, drm],
  install: false)
