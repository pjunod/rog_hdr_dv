"""WAYLAND_DEBUG presentation-feedback parsing and surface selection."""

from fractions import Fraction
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/cadence/parse_wayland_debug.py"
SPEC = importlib.util.spec_from_file_location("parse_wayland_debug", SCRIPT)
wl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wl)


def log(times, surface=7, fb_base=40, refresh=0, flags=0x7, queue=True,
        discard_every=None):
    q = "{Default Queue} " if queue else ""
    lines = []
    for k, when in enumerate(times):
        fb = fb_base + k % 3        # ids are reused, as libwayland does
        lines.append(f"[1234567.{k:03d}] {q} -> wp_presentation#5.feedback("
                     f"wl_surface#{surface}, new id wp_presentation_feedback#{fb})")
        lines.append(f"[1234567.{k:03d}] {q} -> wl_surface#{surface}.commit()")
        sec, nsec = int(when), round((when - int(when)) * 1e9)
        if discard_every and k % discard_every == 0:
            lines.append(f"[1234568.{k:03d}] {q}wp_presentation_feedback#{fb}.discarded()")
        else:
            lines.append(f"[1234568.{k:03d}] {q}wp_presentation_feedback#{fb}.sync_output(wl_output#12)")
            lines.append(f"[1234568.{k:03d}] {q}wp_presentation_feedback#{fb}.presented("
                         f"0, {sec}, {nsec}, {refresh}, 0, {1000 + k}, {flags})")
    return lines


class Parse(unittest.TestCase):
    def test_even_25_with_zero_refresh(self):
        times = [5000 + k / 25 for k in range(25 * 40)]
        result = wl.report(wl.parse(log(times)), Fraction(25), skip_s=1)
        self.assertEqual(result["verdict"], "even")
        self.assertEqual(result["surface"], 7)
        self.assertEqual(result["refresh_ns"], {"0": result["frames"] + 1})
        self.assertEqual(result["flags"]["vsync"], result["frames"] + 1)

    def test_video_surface_chosen_over_ui_surface(self):
        video = log([5000 + k / 24 for k in range(24 * 20)], surface=7)
        ui = log([5000.001 + k for k in range(20)], surface=3, fb_base=90, queue=False)
        result = wl.report(wl.parse(video + ui), Fraction(24), skip_s=1)
        self.assertEqual(result["surface"], 7)
        self.assertEqual(result["other_surfaces"], {"3": 20})

    def test_fixed_240_quantisation_is_uneven(self):
        tick = 1 / 240
        times = [5000 + round((k * 1 / 25) / tick + 0.5) * tick for k in range(25 * 20)]
        result = wl.report(wl.parse(log(times)), Fraction(25), skip_s=0)
        self.assertEqual(result["verdict"], "uneven")

    def test_discarded_counted(self):
        times = [5000 + k / 30 for k in range(300)]
        result = wl.report(wl.parse(log(times, discard_every=50)), Fraction(30), skip_s=0)
        self.assertEqual(result["discarded"], 6)

    def test_clock_time_prefix(self):
        lines = [l.replace("[1234567.", "[23:53:13.") for l in log([5000 + k / 24 for k in range(100)])]
        self.assertEqual(len(wl.parse(lines)[7]["presented"]), 100)

    def test_no_feedback_is_incomplete(self):
        lines = ["[1.000] {Default Queue}  -> wl_surface#7.commit()"]
        result = wl.report(wl.parse(lines), Fraction(24))
        self.assertEqual(result["verdict"], "incomplete")


if __name__ == "__main__":
    unittest.main()
