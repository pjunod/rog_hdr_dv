# Licensing and attribution

This repository collects modifications to separately licensed upstream
projects. It does not relicense those projects or grant rights to proprietary
OEM components.

- libdisplay-info patches retain upstream MIT-licensed context and notices;
  consult the pinned source's `LICENSE` for the complete terms.
- Mutter patches retain the upstream project's applicable GPL and file-level
  notices; consult the pinned source's `COPYING` and affected file headers.
- Linux patches retain the kernel's applicable GPL-2.0 and file-level SPDX
  terms. Preserve original authorship, assistance and signoff trailers.
- Wine patches retain LGPL-2.1-or-later notices; consult the pinned source's
  `COPYING.LIB` and affected file headers.
- The vendored Wayland colour-management protocol XML retains its upstream
  MIT notice; its source and digest are pinned beside the probe.
- Ubuntu packaging changes retain their source package's copyright/licensing
  declarations, including notices carried by the patch series.

## Original utilities and documentation — MIT

The owner selected MIT licensing for the original utilities and documentation
on 2026-10-18. Owner-original repository utility code (including the Dolby
harness, packaging/build helpers and test utilities) and documentation are
licensed under the [MIT License](LICENSE-MIT). Existing contributor attribution
is retained; this notice does not invent individual copyright ownership,
years, signoffs or authority over third-party material.

For `rog-hdr-dm-experimental`, this grant covers the owner-original files in
`tools/dolby_harness/`, `packaging/rog-hdr-dm-experimental/`, the selected
`scripts/` and `tests/` utilities, accompanying `docs/`, and these licensing
notices. The source preparation manifest inventories the actual included
files; Debian copyright records their MIT terms and retained third-party terms.
The native consumer's existing reference to this file resolves to that grant
without changing its source bytes or historical compile bindings.

This grant does NOT relicense upstream-derived patches or library files,
vendored dependencies/protocols, vendor/OEM material, or other separately
licensed third-party content. In particular, libplacebo and modifications to
it retain their LGPL/file-level notices, and fast_float retains its original
Apache-2.0-or-MIT terms. The combined executable's LGPL-2.1 section 6 obligations
(including customer modification and reverse engineering for debugging those
modifications, shared-library/relinking and corresponding-source requirements)
remain applicable; MIT imposes no additional prohibition on those activities.
Selecting MIT is not proof that a not-yet-built package meets all obligations.

Publication of patches does not imply upstream acceptance. No Dolby/ASUS
binary, proprietary documentation or profile payload is distributed here.
