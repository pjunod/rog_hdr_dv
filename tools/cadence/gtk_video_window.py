#!/usr/bin/env python3
"""A plain GtkVideo window for cadence runs: the GTK media path, nothing else.

usage: gtk_video_window.py FILE SECONDS [--fullscreen]

Plays FILE with Gtk.Video (GTK's GStreamer media backend), autoplay, looping
off, and quits after SECONDS. No custom sink, clock or timing code is added,
so the measured cadence is the toolkit's own.
"""

import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402


def main(argv):
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    path, seconds = argv[1], float(argv[2])
    fullscreen = "--fullscreen" in argv[3:]
    app = Gtk.Application(application_id="org.rog_hdr_dv.CadenceGtkVideo")

    def activate(application):
        window = Gtk.ApplicationWindow(application=application, title="cadence GtkVideo")
        window.set_default_size(1280, 720)
        video = Gtk.Video.new_for_filename(path)
        video.set_autoplay(True)
        video.set_loop(False)
        window.set_child(video)
        if fullscreen:
            window.fullscreen()
        window.present()
        GLib.timeout_add(int(seconds * 1000), lambda: (application.quit(), False)[1])

    app.connect("activate", activate)
    return app.run([argv[0]])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
