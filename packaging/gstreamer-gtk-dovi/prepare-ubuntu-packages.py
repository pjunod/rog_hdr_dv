#!/usr/bin/python3
# SPDX-License-Identifier: LGPL-2.1-or-later
from pathlib import Path
import re,shutil,sys
if len(sys.argv)!=2:raise SystemExit('usage: prepare-ubuntu-packages.py WORKSPACE')
r=Path(sys.argv[1]).resolve();s=r/'source';b=r/'package-originals';b.mkdir(exist_ok=True)
for n in ['control','rules','changelog']:
 for label,p in [('gtk',s/'debian'/n),('showtime',r/'showtime-50.0/debian'/n)]:
  q=b/(label+'-'+n)
  if not q.exists():shutil.copy2(p,q)
c=(b/'gtk-control').read_text();src=c.split('\n\n')[0];src=re.sub(r'Build-Depends:.*?\nStandards-Version:', 'Build-Depends: debhelper-compat (= 13), cargo:native, rustc:native (>= 1.92), pkgconf, libgtk-4-dev (>= 4.20), libgstreamer-plugins-base1.0-dev (>= 1.28.7), libgstgtk-dovi-core-dev (= 0.1.0+rogdv2)\nStandards-Version:',src,flags=re.S)
bin='Package: gstreamer1.0-gtk4'+c.split('Package: gstreamer1.0-gtk4',1)[1];bin=bin.replace(' ${misc:Depends},',' libgtk-4-1 (>= 4.24.1+ds-1+rogdv3),\n libgstgtk-dovi-core0 (= 0.1.0+rogdv2),\n ${misc:Depends},')
(s/'debian/control').write_text(src+'\n\n'+bin)
(s/'debian/rules').write_text('''#!/usr/bin/make -f
include /usr/share/dpkg/architecture.mk
export CARGO_HOME = $(CURDIR)/debian/cargo_home
export CARGO_TARGET_DIR = $(CURDIR)/../gtk-package-target
export CARGO_BUILD_JOBS = 1
export CARGO_PROFILE_RELEASE_LTO = false
FEATURES = gtk_v4_20,x11egl,x11glx,waylandegl,dmabuf,v1_28
%:
\tdh $@ --buildsystem=cargo
override_dh_auto_configure:
\t# The authenticated Ubuntu source includes its complete vendored crate set.
\ttest -f .cargo/config.toml
override_dh_auto_build:
\tcargo build --offline --release -j1 --features $(FEATURES)
override_dh_auto_install:
\tinstall -D $(CARGO_TARGET_DIR)/release/libgstgtk4.so debian/tmp/usr/lib/$(DEB_HOST_MULTIARCH)/gstreamer-1.0/libgstgtk4.so
override_dh_auto_test:
\tcargo test --offline --release -j1 --features $(FEATURES)
override_dh_auto_clean:
\t# Preserve this task's warm compiler target; dh_clean removes package staging.
override_dh_clean:
\tdh_clean --exclude=debian/missing-sources
override_dh_shlibdeps:
\tdh_shlibdeps $(if $(GTK_DOVI_CORE_LIBDIR),-l$(GTK_DOVI_CORE_LIBDIR))
''')
(s/'debian/shlibs.local').write_text('libgstgtkdovicore 0 libgstgtk-dovi-core0 (= 0.1.0+rogdv2)\n')
(s/'debian/changelog').write_text('rust-gst-plugin-gtk4 (0.15.2-1ubuntu2+rogdv2) unstable; urgency=medium\n\n  * Preserve native 16-bit mapped pictures and retarget visible paused frames.\n  * Build the normal plugin features offline from the Ubuntu vendored source.\n\n -- ROG HDR contributors <rog-hdr@invalid>  Sun, 08 Nov 2026 00:00:00 +0000\n\n'+(b/'gtk-changelog').read_text())
t=r/'showtime-50.0';c=(b/'showtime-control').read_text().replace(' gstreamer1.0-gtk4,',' gstreamer1.0-gtk4 (>= 0.15.2-1ubuntu2+rogdv2),\n gstreamer1.0-gtk-dovi (>= 0.1.0+rogdv2),\n libgtk-4-1 (>= 4.24.1+ds-1+rogdv3),').replace(' gir1.2-gtk-4.0 (>= 4.20),',' gir1.2-gtk-4.0 (>= 4.24.1+ds-1+rogdv3),')
(t/'debian/control').write_text(c);(t/'debian/changelog').write_text('showtime (50.0-2+rogdv2) unstable; urgency=medium\n\n  * Bind Dolby streams to their actual native surface target and HDR lease.\n\n -- ROG HDR contributors <rog-hdr@invalid>  Sun, 08 Nov 2026 00:00:00 +0000\n\n'+(b/'showtime-changelog').read_text())
print('normal binary packaging metadata prepared; no private sources included')
