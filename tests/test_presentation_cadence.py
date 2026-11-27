"""Presentation-cadence trace parsing, verdicts and timing models."""

import argparse
from fractions import Fraction
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/cadence/presentation_cadence.py"
SPEC = importlib.util.spec_from_file_location("presentation_cadence", SCRIPT)
cadence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cadence)

FLIP = ("  gnome-shell-2011    [003] d.h1. {t:.6f}: intel_crtc_flip_done: "
        "dev 0000:00:02.0, pipe {p}, frame={f}, scanline=1601")
ARM = ("  gnome-shell-2011    [003] ..... {t:.6f}: intel_plane_update_arm: "
       "dev 0000:00:02.0, pipe {p}, {plane}, frame={f}, scanline=1500, "
       "format=XR30 little-endian (0x30335258), 2560.000000x1600.000000+0.000000+0.000000 -> 2560x1600+0+0")
ZEROS = " 00000000" * 4
CRC = ("  <idle>-0    [000] d.h1. {t:.6f}: intel_pipe_crc: dev 0000:00:02.0, "
       "pipe A, frame={f}, scanline=1601 crc={c:08x} 00000000 00000000 00000000 00000000")


def flips(times, pipe="A", plane="plane 1A", start_frame=100, refresh=1 / 240):
    lines = []
    for t in times:
        frame = start_frame + round(t / refresh)
        lines.append(ARM.format(t=t - 0.001, p=pipe, plane=plane, f=frame))
        lines.append(FLIP.format(t=t, p=pipe, f=frame))
    return lines


VBL = ("  <idle>-0       [019] d.h2. {t:.6f}: drm_vblank_event: crtc={c}, seq={s}, "
       "time={ns}, high-prec=true")


class VblankFlips(unittest.TestCase):
    """Display version 14: flips are vblank events that follow a plane arm."""

    def lines(self, arms, vblank_times, plane="plane 1A"):
        out = [ARM.format(t=a, p="A", plane=plane, f=0) for a in arms]
        out += [VBL.format(t=v + 0.0001, c=0, s=1000 + k, ns=round(v * 1e9))
                for k, v in enumerate(vblank_times)]
        out += [VBL.format(t=v, c=1, s=5, ns=round(v * 1e9)) for v in vblank_times]
        return sorted(out, key=lambda line: float(line.split(": ")[0].split()[-1]))

    def test_vblank_without_arm_is_not_a_flip(self):
        frames = [1000 + k / 24 for k in range(24 * 10)]
        repeats = [t + 0.0208 for t in frames]          # panel repeats, no commit
        arms = [t - 0.002 for t in frames]
        flips, _, _ = cadence.parse_trace(self.lines(arms, frames + repeats))
        self.assertEqual(len(flips), len(frames))
        report = cadence.analyze(self.lines(arms, frames + repeats), Fraction(24), skip_s=0)
        self.assertEqual(report["verdict"], "even")

    def test_cursor_arm_does_not_make_a_flip(self):
        frames = [1000 + k / 24 for k in range(48)]
        cursor = self.lines([1000.03], [1000.031], plane="cursor A")
        lines = self.lines([t - 0.002 for t in frames], frames) + cursor
        lines.sort(key=lambda line: float(line.split(": ")[0].split()[-1]))
        flips, _, _ = cadence.parse_trace(lines)
        self.assertEqual(len(flips), len(frames))


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
    """Pipe CRC per refresh at 240 Hz of a 24 fps, 16-pattern fixture."""

    CAL = {"patterns": [f"{0x1000 + p:08x}" + ZEROS for p in range(16)],
           "flash": f"{0xF1A5:08x}" + ZEROS}

    def crc_lines(self, pictures, start=500):
        return [CRC.format(t=1000 + i / 240, f=start + i, c=pic)
                for i, pic in enumerate(pictures)]

    def frames(self, count=480):
        return [0x1000 + (n % 16) for n in range(count)]

    def refreshes(self, frames, hold=10):
        return [pic for pic in frames for _ in range(hold)]

    def analyze(self, pictures, **kwargs):
        return cadence.analyze(self.crc_lines(pictures), Fraction(24), skip_s=0,
                               calibration=self.CAL, **kwargs)

    def test_even_and_decoded(self):
        report = self.analyze(self.refreshes(self.frames()))
        self.assertEqual(report["verdict"], "even")
        self.assertEqual(report["content_identity"], "decoded")
        self.assertEqual((report["skipped_frames"], report["shown_again"]), (0, 0))

    def test_skipped_frame_found_even_when_timing_hides_it(self):
        frames = self.frames()
        del frames[200]          # one source frame never shown
        pictures = self.refreshes(frames)
        report = self.analyze(pictures)
        self.assertEqual(report["skipped_frames"], 1)
        self.assertEqual(report["verdict"], "uneven")

    def test_earlier_frame_shown_again(self):
        frames = self.frames()
        frames.insert(201, frames[199])
        report = self.analyze(self.refreshes(frames))
        self.assertEqual(report["shown_again"], 1)
        self.assertEqual(report["verdict"], "uneven")

    def test_sync_flash_consumes_one_frame(self):
        frames = self.frames()
        for n in range(0, len(frames), 24):
            frames[n] = 0xF1A5
        report = self.analyze(self.refreshes(frames))
        self.assertEqual(report["sync_flashes"], 20)
        self.assertEqual((report["skipped_frames"], report["shown_again"]), (0, 0))

    def test_foreign_picture_counted(self):
        pictures = self.refreshes(self.frames())
        pictures[1000:1010] = [0xBEEF] * 10   # e.g. an OSD over one frame
        report = self.analyze(pictures)
        self.assertEqual(report["foreign_pictures"], 1)

    def test_change_only_without_calibration(self):
        report = cadence.analyze(self.crc_lines(self.refreshes(self.frames())),
                                 Fraction(24), skip_s=0)
        self.assertEqual(report["content_identity"], "change-only")
        self.assertEqual(report["verdict"], "even")

    def test_lost_refreshes_are_incomplete(self):
        lines = self.crc_lines(self.refreshes(self.frames()))
        del lines[3000:3005]
        report = cadence.analyze(lines, Fraction(24), skip_s=0)
        self.assertEqual(report["verdict"], "incomplete")
        self.assertEqual(report["lost_refreshes"], 5)

    def test_paused_frame_is_one_picture(self):
        report = cadence.analyze(self.crc_lines([0x1003] * 2400), Fraction(24), skip_s=0)
        self.assertEqual(report["distinct_crcs"], 1)


class Calibrate(unittest.TestCase):
    def stepped(self, first, count, flash_at=None):
        pictures = []
        for k in range(count):
            pic = 0xF1A5 if k == flash_at else 0x2000 + (first + k) % 16
            pictures += [pic] * 60   # each step held a quarter second
        return [CRC.format(t=1000 + i / 240, f=i, c=p) for i, p in enumerate(pictures)]

    def test_patterns_in_cycle_order(self):
        result = cadence.calibrate(self.stepped(5, 18), first_pattern=5)
        self.assertEqual(result["patterns"][5], f"{0x2005:08x}" + ZEROS)
        self.assertEqual(result["patterns"][4], f"{0x2004:08x}" + ZEROS)

    def test_flash_position(self):
        result = cadence.calibrate(self.stepped(0, 20, flash_at=3), first_pattern=0,
                                   flash_position=3)
        self.assertEqual(result["flash"], f"{0xF1A5:08x}" + ZEROS)

    def test_too_few_steps_refused(self):
        with self.assertRaises(SystemExit):
            cadence.calibrate(self.stepped(0, 10))


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
