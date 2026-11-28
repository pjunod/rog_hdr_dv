"""The mpv-fel-system-dv series that builds the system mpv 0.42 package."""

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "patches/mpv-fel-system-dv"
WAYLAND_PATCH = "0009-stop-dispatching-Wayland-events-after-a-fatal-display-error.patch"
RECORD_PATCH = "0010-log-a-fresh-Dolby-success-record-after-each-reset.patch"
LEVEL_PATCH = "0011-report-enhancement-layer-composition-as-a-level.patch"
NLQ_PATCH = "0012-report-whether-the-composed-enhancement-layer-nlq-is-active.patch"


def entry():
    sources = json.loads((ROOT / "sources.json").read_text())
    return next(item for item in sources["series"] if item["component"] == "mpv-fel-system-dv")


class MpvSystemSeriesTests(unittest.TestCase):
    def test_series_file_registry_and_checksums_agree(self):
        names = (SERIES / "series").read_text().split()
        self.assertEqual(names, entry()["patch_order"])
        self.assertEqual(len(names), entry()["patch_count"])
        self.assertEqual(names[-4:], [WAYLAND_PATCH, RECORD_PATCH, LEVEL_PATCH, NLQ_PATCH])
        self.assertEqual(sorted(names), sorted(p.name for p in SERIES.glob("*.patch")))
        sums = dict(line.split("  ", 1)[::-1] for line in (ROOT / "SHA256SUMS").read_text().splitlines() if line)
        for name in names:
            digest = hashlib.sha256((SERIES / name).read_bytes()).hexdigest()
            self.assertEqual(sums[f"patches/mpv-fel-system-dv/{name}"], digest, name)

    def test_package_version_is_the_newest_changelog_overlay(self):
        overlay = (ROOT / "packaging/system-dv/mpv-042-ubuntu-el-nlq-level.diff").read_text()
        version = re.search(r"^\+mpv \(([^)]+)\)", overlay, re.M).group(1)
        self.assertEqual(entry()["candidate_package_version"], version)
        self.assertTrue(version.endswith("+rogdv5.8"))

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


    def test_a_frame_queue_reset_requires_a_fresh_success_record(self):
        text = (SERIES / RECORD_PATCH).read_text()
        self.assertIn("+++ b/video/out/vo_gpu_next.c", text)
        # The flag clears where the queue and the provider are reset...
        self.assertRegex(text, r" +dv_provider387_reset\(p->dovi_provider\);\n(?:\+ +//.*\n)*\+ +p->dovi_physical_logged = false;\n")
        # ...and nowhere else, so only a later successful map logs the record.
        self.assertEqual(text.count("+            p->dovi_physical_logged = false;"), 1)
        self.assertNotIn("+    p->dovi_physical_logged = true;", text)
        self.assertIn("+++ b/DOCS/man/input.rst", text)

    def test_enhancement_layer_composition_is_a_level(self):
        text = (SERIES / LEVEL_PATCH).read_text()
        added = "\n".join(l[1:] for l in text.splitlines() if l.startswith("+") and not l.startswith("+++"))
        # The property reports the level next to active and generation.
        self.assertIn('{"enhancement-layer-composed", SUB_PROP_BOOL(state.enhancement_layer_composed)},', added)
        self.assertIn(".enhancement_layer_composed = p->dovi_el_composed,", added)
        # Each frame carries its own record, found by its RPU among the render's frames;
        # captures render without a mix and record nothing.
        self.assertIn("if (image->dovi_rpu == rpu) {", added)
        self.assertIn("if (!p->dovi_mix)\n        return;", added)
        # A map starts unattested; only the successful private physical map carries the flag.
        self.assertRegex(text, r"\+    set_dovi_frame_el\(p, rpu, false\);\n     if \(!p->dovi_physical_active")
        self.assertRegex(text, r"\+    set_dovi_frame_el\(p, rpu, enhancement_layer_composed\);\n     return 1;\n")
        # An unmapped read clears every frame of that render not attested in it.
        self.assertIn("if (fp->dovi_el_serial != p->dovi_render_serial)\n            fp->dovi_el_composed = false;", added)
        # The presented level is that frame's record, false on a failed or blank render.
        self.assertIn("p->dovi_mix = &mix;\n    p->dovi_render_serial++;", added)
        # The presented frame is the latest at or before the instant, which every mixer reads.
        self.assertIn("if (mix->timestamps[i] <= 0)\n            frame = mix->frames[i];", added)
        self.assertIn("render_ok ? dovi_covering_frame(&mix) : NULL;", added)
        self.assertIn("set_dovi_el_composed(p, vo, covering_fp && covering_fp->dovi_el_composed);", added)
        self.assertNotIn("pl_frame_mix_nearest", added)
        # A queue error, the frame-queue reset and a generation change clear it...
        self.assertRegex(text, r'Failed updating frames!\\n"\);\n\+ +set_dovi_el_composed\(p, vo, false\);\n')
        self.assertRegex(text, r" +p->dovi_physical_logged = false;\n(?:\+ +//.*\n)*\+ +set_dovi_el_composed\(p, vo, false\);\n")
        self.assertIn("        p->dovi_el_composed = false;", added)
        # ...and every change notifies the property.
        self.assertIn("if (composed == p->dovi_el_composed)\n        return;\n    p->dovi_el_composed = composed;\n    vo_event(vo, VO_EVENT_WIN_STATE);", added)
        self.assertIn("+++ b/DOCS/man/input.rst", text)

    def test_the_nlq_level_is_libplacebos_per_frame_decision(self):
        text = (SERIES / NLQ_PATCH).read_text()
        added = "\n".join(l[1:] for l in text.splitlines() if l.startswith("+") and not l.startswith("+++"))
        removed = "\n".join(l[1:] for l in text.splitlines() if l.startswith("-") and not l.startswith("---"))
        # The property reports the level next to the composition level.
        self.assertIn('{"enhancement-layer-nlq-active", SUB_PROP_BOOL(state.enhancement_layer_nlq_active)},', added)
        self.assertIn(".enhancement_layer_nlq_active = p->dovi_el_nlq_active,", added)
        # Each frame records libplacebo's own mapping of its RPU, only with a composition.
        # It is libplacebo's sampling condition: an attached layer and an active NLQ.
        self.assertIn("fp->dovi_el_nlq_active = composed && image->enhancement_layer &&\n"
                      "                                     image->repr.dovi &&\n"
                      "                                     image->repr.dovi->nlq_active;", added)
        # Nothing re-parses the RPU.
        self.assertNotIn("dovi_parse", added)
        self.assertNotIn("rpu_parser", added)
        # The published level is the covering frame's, implies composed and notifies on change.
        self.assertIn("covering_fp && covering_fp->dovi_el_nlq_active);", added)
        self.assertIn("nlq_active = composed && nlq_active;", added)
        self.assertRegex(text, r"\+    if \(composed == p->dovi_el_composed && nlq_active == p->dovi_el_nlq_active\)\n"
                               r"         return;\n     p->dovi_el_composed = composed;\n"
                               r"\+    p->dovi_el_nlq_active = nlq_active;\n     vo_event\(vo, VO_EVENT_WIN_STATE\);")
        # It clears wherever the composition level clears.
        self.assertIn("fp->dovi_el_composed = fp->dovi_el_nlq_active = false;", added)
        self.assertIn("p->dovi_el_composed = p->dovi_el_nlq_active = false;", added)
        self.assertEqual(added.count("set_dovi_el_composed(p, vo, false, false);"), 2)
        self.assertNotIn("set_dovi_el_composed(p, vo, false);", added)
        self.assertEqual(removed.count("set_dovi_el_composed(p, vo, false);"), 2)
        self.assertIn("+++ b/DOCS/man/input.rst", text)

if __name__ == "__main__":
    unittest.main()
