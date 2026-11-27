"""Presentation-cadence trace parsing, verdicts and timing models."""

import argparse
from fractions import Fraction
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/presentation_cadence.py"
SPEC = importlib.util.spec_from_file_location("presentation_cadence", SCRIPT)
cadence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cadence)

FLIP = ("  gnome-shell-2011    [003] d.h1. {t:.6f}: intel_crtc_flip_done: "
        "dev 0000:00:02.0, pipe {p}, frame={f}, scanline=1601")
ARM = ("  gnome-shell-2011    [003] ..... {t:.6f}: intel_plane_update_arm: "
       "dev 0000:00:02.0, pipe {p}, {plane}, frame={f}, scanline=1500, "
       "format=XR30 little-endian (0x30335258), 2560.000000x1600.000000+0.000000+0.000000 -> 2560x1600+0+0")
CRC = ("  <idle>-0    [000] d.h1. {t:.6f}: intel_pipe_crc: dev 0000:00:02.0, "
       "pipe A, frame={f}, scanline=1601 crc={c:08x} 00000000 00000000 00000000 00000000")


def flips(times, pipe="A", plane="plane 1A", start_frame=100, refresh=1 / 240):
    lines = []
    for t in times:
        frame = start_frame + round(t / refresh)
        lines.append(ARM.format(t=t - 0.001, p=pipe, plane=plane, f=frame))
        lines.append(FLIP.format(t=t, p=pipe, f=frame))
    return lines


class ParseRate(unittest.TestCase):
    def test_exact_fraction(self):
        self.assertEqual(cadence.parse_rate("24000/1001"), Fraction(24000, 1001))

    def test_decimal_refused(self):
        with self.assertRaises(argparse.ArgumentTypeError) as caught:
            cadence.parse_rate("23.976")
        self.assertIn("24000/1001", str(caught.exception))


class AnalyzeFlips(unittest.TestCase):
    def test_even_24(self):
        times = [1000 + k / 24 for k in range(24 * 30)]
        report = cadence.analyze(flips(times), Fraction(24), skip_s=1)
        self.assertEqual(report["verdict"], "even")
        self.assertEqual(report["refresh_histogram"], {"10": report["frames"]})

    def test_periodic_long_hold_found(self):
        tick = 1 / 240
        times = cadence.model(Fraction(24000, 1001), 30, refresh_hz=240)
        report = cadence.analyze(flips([1000 + t for t in times]),
                                 Fraction(24000, 1001), skip_s=0)
        self.assertEqual(report["verdict"], "uneven")
        self.assertAlmostEqual(report["irregular_every_s"], 4.171, places=2)
        self.assertEqual(set(report["refresh_histogram"]), {"10", "11"})
        self.assertAlmostEqual(report["max_ms"], 11 * tick * 1000, places=2)

    def test_other_pipe_and_cursor_flips_ignored(self):
        times = [1000 + k / 60 for k in range(600)]
        lines = flips(times)
        lines += flips([1000.004 + k / 60 for k in range(600)], pipe="B")
        lines += flips([1000.009 + k / 60 for k in range(0, 600, 7)], plane="cursor A")
        lines.sort(key=lambda line: float(line.split(": ")[0].split()[-1]))
        report = cadence.analyze(lines, Fraction(60), skip_s=0.5)
        self.assertEqual(report["verdict"], "even")
        self.assertGreater(report["cursor_only_flips"], 0)

    def test_dropped_frame_is_a_long_hold(self):
        times = [1000 + k / 50 for k in range(500) if k != 250]
        report = cadence.analyze(flips(times), Fraction(50), skip_s=0)
        self.assertEqual(report["verdict"], "uneven")
        self.assertEqual(report["long_holds"], 1)

    def test_too_short_is_incomplete(self):
        report = cadence.analyze(flips([1000, 1000.04]), Fraction(25), skip_s=0)
        self.assertEqual(report["verdict"], "incomplete")


class AnalyzeCrc(unittest.TestCase):
    def crc_lines(self, pictures, start=500):
        return [CRC.format(t=1000 + i / 240, f=start + i, c=pic)
                for i, pic in enumerate(pictures)]

    def test_even_from_refresh_content(self):
        pictures = [k // 10 + 1 for k in range(240 * 20)]
        report = cadence.analyze(self.crc_lines(pictures), Fraction(24), skip_s=1)
        self.assertEqual(report["source"], "crc")
        self.assertEqual(report["verdict"], "even")

    def test_returning_picture_is_uneven(self):
        pictures = [k // 10 + 1 for k in range(240 * 20)]
        pictures[2000:2010] = [pictures[1990]] * 10
        report = cadence.analyze(self.crc_lines(pictures), Fraction(24), skip_s=0)
        self.assertEqual(report["verdict"], "uneven")

    def test_lost_refreshes_are_incomplete(self):
        pictures = [k // 10 + 1 for k in range(240 * 20)]
        lines = self.crc_lines(pictures)
        del lines[3000:3005]
        report = cadence.analyze(lines, Fraction(24), skip_s=0)
        self.assertEqual(report["verdict"], "incomplete")
        self.assertEqual(report["lost_refreshes"], 5)


class Models(unittest.TestCase):
    def verdict(self, rate, **kwargs):
        starts = cadence.model(rate, 60, **kwargs)
        return cadence.summarise(starts, [], rate, 0.75)["verdict"]

    def test_fixed_240(self):
        self.assertEqual(self.verdict(Fraction(24), refresh_hz=240), "even")
        self.assertEqual(self.verdict(Fraction(25), refresh_hz=240), "uneven")

    def test_vrr_floor_breaks_film_and_lfc_restores_it(self):
        film = Fraction(24000, 1001)
        self.assertEqual(self.verdict(film, vrr_min_hz=48, vrr_max_hz=240), "uneven")
        k = cadence.lfc_multiplier(film, 48, 240)
        self.assertEqual(k, 3)
        self.assertEqual(self.verdict(film, vrr_min_hz=48, vrr_max_hz=240,
                                      multiplier=k), "even")

    def test_in_range_rates_need_no_multiplier(self):
        self.assertEqual(cadence.lfc_multiplier(Fraction(60), 48, 240), 1)


class CaptureGuard(unittest.TestCase):
    def test_output_inside_repository_refused(self):
        with self.assertRaises(SystemExit):
            cadence.capture(cadence.PROJECT_ROOT / "capture-here", 1)


if __name__ == "__main__":
    unittest.main()
