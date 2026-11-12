"""The mpv-fel-system-dv series that builds the system mpv 0.42 package."""

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "patches/mpv-fel-system-dv"
WAYLAND_PATCH = "0009-stop-dispatching-Wayland-events-after-a-fatal-display-error.patch"


def entry():
    sources = json.loads((ROOT / "sources.json").read_text())
    return next(item for item in sources["series"] if item["component"] == "mpv-fel-system-dv")


class MpvSystemSeriesTests(unittest.TestCase):
    def test_series_file_registry_and_checksums_agree(self):
        names = (SERIES / "series").read_text().split()
        self.assertEqual(names, entry()["patch_order"])
        self.assertEqual(len(names), entry()["patch_count"])
        self.assertEqual(names[-1], WAYLAND_PATCH)
        self.assertEqual(sorted(names), sorted(p.name for p in SERIES.glob("*.patch")))
        sums = dict(line.split("  ", 1)[::-1] for line in (ROOT / "SHA256SUMS").read_text().splitlines() if line)
        for name in names:
            digest = hashlib.sha256((SERIES / name).read_bytes()).hexdigest()
            self.assertEqual(sums[f"patches/mpv-fel-system-dv/{name}"], digest, name)

    def test_package_version_is_the_newest_changelog_overlay(self):
        overlay = (ROOT / "packaging/system-dv/mpv-042-ubuntu-wayland-display-error.diff").read_text()
        version = re.search(r"^\+mpv \(([^)]+)\)", overlay, re.M).group(1)
        self.assertEqual(entry()["candidate_package_version"], version)
        self.assertTrue(version.endswith("+rogdv5.5"))

    def test_a_dead_wayland_display_stops_dispatching_and_keeps_sleeping(self):
        text = (SERIES / WAYLAND_PATCH).read_text()
        self.assertIn("+++ b/video/out/wayland_common.c", text)
        # One helper handles the three display calls that can fail for good.
        self.assertIn("+static bool wayland_display_failed(struct vo_wayland_state *wl, int ret)", text)
        self.assertIn("+        if (wayland_display_failed(wl, wl_display_dispatch_pending(wl->display)))", text)
        self.assertIn("+        if (wayland_display_failed(wl, wl_display_read_events(wl->display)))", text)
        self.assertIn("+    wayland_display_failed(wl, wl_display_dispatch_pending(wl->display));", text)
        # It stops using the display, asks the player to close, and logs a protocol error in full.
        self.assertIn("+    wl->display_fd = -1;", text)
        self.assertIn("+    mp_input_put_key(wl->vo->input_ctx, MP_KEY_CLOSE_WIN);", text)
        self.assertIn("wl_display_get_protocol_error", text)
        # Without a display the VO thread still sleeps on its wakeup pipe.
        self.assertIn("+        mp_poll(&wakeup, nfds > 1, timeout_ns);", text)
        # The loop that spun forever no longer ignores the dispatch result.
        self.assertNotIn("\n+        wl_display_dispatch_pending(wl->display);", text)


if __name__ == "__main__":
    unittest.main()
