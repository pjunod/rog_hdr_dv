"""Synthetic display evidence and failure boundaries; no live display reads."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/inspect_display.py"
SPEC = importlib.util.spec_from_file_location("inspect_display", SCRIPT)
display = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(display)

# Deliberately include private strings in fields that must never be emitted.
GNOME = """(uint32 7, [(('eDP-2', 'Acme', 'Panel', 'SERIAL_PRIVATE'),
[('private-mode-id', 2560, 1600, 240.0, 1.0, [1.0, 2.0],
 {'is-current': <true>, 'is-preferred': <true>}),
 ('inactive', 1280, 800, 60.0, 1.0, [1.0], {'is-current': <false>})],
 {'color-mode': <uint32 1>, 'supported-color-modes': <[uint32 0, 1, 2]>,
  'display-name': <'private-user@private-host /home/private-user 10.42.1.2'>})],
 [(0, 0, 2.0, uint32 0, true,
   [('eDP-2', 'Acme', 'Panel', 'SERIAL_PRIVATE')], @a{sv} {})],
 {'layout-mode': <uint32 1>})"""


def success(stdout, code=0):
    return {"status": "ok", "returncode": code, "stdout": stdout}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sysfs = self.root / "sys"
        self.release = self.root / "os-release"
        self.release.write_text('ID=ubuntu\nNAME="Ubuntu Linux"\nVERSION_ID="26.10"\n'
                                'HOME_URL="https://private-host/"\n')
        self.calls = []
        self.profile = self.root / "private-user.icc"
        self.profile.write_bytes(b"synthetic profile fixture")
        self.environment = {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
                            "HOME": "/home/private-user", "USER": "private-user",
                            "LOGNAME": "private-user", "HOSTNAME": "private-host"}
        self.inspector = display.Inspector(self.sysfs, self.release, self.runner,
                                           self.environment, timeout=0.25)

    def put(self, relative, value):
        path = self.sysfs / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else value.encode())
        return path

    def hardware(self):
        self.put("class/drm/card0/device/vendor", "0x8086\n")
        self.put("class/drm/card0/device/device", "0x7d55\n")
        driver = self.sysfs / "bus/pci/drivers/i915"
        driver.mkdir(parents=True)
        (self.sysfs / "class/drm/card0/device/driver").symlink_to(driver)
        self.put("class/drm/card0-eDP-2/status", "connected\n")
        self.put("class/drm/card0-eDP-2/enabled", "enabled\n")
        self.put("class/drm/card0-eDP-2/modes", "2560x1600\n1280x800\n")
        self.edid = b"synthetic EDID SERIAL_PRIVATE /home/private-user"
        self.put("class/drm/card0-eDP-2/edid", self.edid)
        for key, value in {"brightness": "80", "actual_brightness": "78",
                           "max_brightness": "100", "type": "raw"}.items():
            self.put("class/backlight/intel_backlight/" + key, value + "\n")

    def runner(self, argv, timeout):
        self.calls.append((argv, timeout))
        if argv[0] == "dpkg-query":
            return success("mutter\t51.0-1ubuntu3+nativehdr2\tii \n"
                           "colord\t1.4.8\trc \n", code=1)
        method = argv[argv.index("--method") + 1]
        if method.endswith("GetCurrentState"):
            return success(GNOME)
        if method.endswith("GetDevicesByKind"):
            self.assertEqual(argv[-1], "display")
            return success("([objectpath '/org/freedesktop/ColorManager/devices/private_user'],)")
        if argv[-1] == "Profiles":
            return success("(<[objectpath '/org/freedesktop/ColorManager/profiles/private_user']>,)")
        if argv[-1] == "Title":
            return success("(<'private-user@private-host SERIAL_PRIVATE'>,)")
        if argv[-1] == "Filename":
            return success("(<" + repr(str(self.profile)) + ">,)")
        self.fail("Unexpected read command: " + repr(argv))


class EvidenceTests(Fixture):
    def test_complete_snapshot_preserves_evidence_and_omits_private_payloads(self):
        self.hardware()
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.inspector.collect("Linux", "7.3.0-rc5-nativehdr1")
        gpu = report["gpus"]["items"][0]
        self.assertEqual(gpu["vendor"]["value"], "0x8086")
        self.assertEqual(gpu["device"]["value"], "0x7d55")
        self.assertEqual(gpu["driver"]["value"], "i915")
        edid = report["drm_connectors"]["items"][0]["edid"]
        self.assertEqual(edid["length_bytes"], len(self.edid))
        self.assertEqual(edid["sha256"], hashlib.sha256(self.edid).hexdigest())
        light = report["backlights"]["items"][0]
        self.assertEqual(light["brightness"]["value"], 80)
        self.assertEqual(light["actual_brightness"]["value"], 78)
        self.assertEqual(light["max_brightness"]["value"], 100)
        monitor = report["gnome"]["monitors"][0]
        self.assertEqual(monitor["colour_properties"]["color-mode"], 1)
        self.assertEqual(monitor["current_modes"], [
            {"width": 2560, "height": 1600, "refresh_hz": 240.0, "preferred_scale": 1.0}])
        profiles = report["colord"]["displays"][0]["profiles"]
        self.assertEqual(profiles[0]["file"]["sha256"], hashlib.sha256(self.profile.read_bytes()).hexdigest())
        self.assertEqual(report["packages"]["items"], [
            {"package": "mutter", "version": "51.0-1ubuntu3+nativehdr2"}])
        self.assertTrue(report["packages"]["unmatched_patterns_possible"])
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["capability_verdict"], "not_evaluated")
        encoded = json.dumps(report)
        for secret in ("private-user", "private_user", "private-host", "SERIAL_PRIVATE",
                       "private-mode-id", "/home/", "10.42.1.2", str(self.root), "HOME_URL"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertTrue(all(timeout == 0.25 for _, timeout in self.calls))
        methods = [argv[argv.index("--method") + 1] for argv, _ in self.calls if argv[0] == "gdbus"]
        self.assertTrue(all(method.endswith(("Get", "GetDevicesByKind", "GetCurrentState")) for method in methods))

    def test_disconnected_and_zero_length_edid_do_not_infer_unsupported(self):
        self.hardware()
        self.put("class/drm/card0-eDP-2/status", "disconnected")
        self.put("class/drm/card0-eDP-2/edid", b"")
        report = self.inspector.collect("Linux", "test")
        self.assertEqual(report["drm_connectors"]["items"][0]["edid"]["length_bytes"], 0)
        self.assertEqual(report["capability_verdict"], "not_evaluated")

    def test_missing_sysfs_and_commands_are_explicitly_unavailable(self):
        self.inspector.runner = lambda argv, timeout: display.problem("command_missing", "unavailable")
        report = self.inspector.collect("Linux", "test")
        for key in ("gpus", "drm_connectors", "backlights", "packages", "gnome", "colord"):
            self.assertEqual(report[key]["status"], "unavailable")
        self.assertEqual(report["capability_verdict"], "not_evaluated")

    def test_permission_failure_is_local_and_excludes_exception_text(self):
        self.hardware()
        original = os.open
        def denied(path, *args, **kwargs):
            if Path(path).name == "edid":
                raise PermissionError("private-user@private-host denied")
            return original(path, *args, **kwargs)
        with mock.patch.object(os, "open", denied):
            report = self.inspector.collect("Linux", "test")
        self.assertEqual(report["drm_connectors"]["items"][0]["edid"],
                         {"status": "error", "reason": "permission_denied"})
        self.assertEqual(report["gpus"]["status"], "ok")
        self.assertNotIn("private-user", json.dumps(report))

    def test_malformed_file_values_do_not_leak_arbitrary_text(self):
        self.hardware()
        self.put("class/backlight/intel_backlight/brightness", "/home/private-user")
        self.put("class/drm/card0/device/vendor", "SERIAL_PRIVATE")
        self.put("class/drm/card0-eDP-2/modes", "10.42.1.2")
        report = self.inspector.collect("Linux", "test")
        self.assertEqual(report["backlights"]["items"][0]["brightness"]["reason"], "invalid_integer")
        self.assertEqual(report["gpus"]["items"][0]["vendor"]["reason"], "unexpected_value")
        self.assertNotIn("10.42.1.2", json.dumps(report))

    def test_unsupported_platform_never_reads_or_runs_probes(self):
        with mock.patch.object(self.inspector, "read", side_effect=AssertionError("filesystem read")):
            report = self.inspector.collect("Darwin")
        self.assertEqual(report["status"], "unsupported_platform")
        self.assertEqual(self.calls, [])
        self.assertNotIn("kernel_release", report)

    def test_absent_session_environment_never_guesses_another_bus(self):
        self.inspector.environment = {"XDG_RUNTIME_DIR": "/run/user/1000"}
        result = self.inspector.gnome()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(self.calls, [])

    def test_command_errors_and_unparsed_dbus_remain_errors_without_raw_output(self):
        for result, reason in ((success("SERIAL_PRIVATE", code=2), "command_failed"),
                               (success("SERIAL_PRIVATE"), "unparsed_dbus_response"),
                               (display.problem("timeout"), "timeout")):
            with self.subTest(reason=reason):
                self.inspector.runner = lambda argv, timeout: result
                actual = self.inspector.gnome()
                self.assertEqual(actual["reason"], reason)
                self.assertNotIn("SERIAL_PRIVATE", json.dumps(actual))

    def test_changed_display_interface_shape_is_not_a_false_capability_verdict(self):
        self.inspector.runner = lambda argv, timeout: success("(uint32 7, [], {})")
        self.assertEqual(self.inspector.gnome()["reason"], "unexpected_display_state_shape")

    def test_gnome_wrong_map_containers_return_shape_error_without_private_data(self):
        responses = (
            # Four entries previously passed the length check, then raised KeyError.
            "{'a': <1>, 'b': <2>, 'c': <3>, 'private-user': <4>}",
            "(uint32 7, {'private-user': <1>}, [], {})",
            "(uint32 7, [{'a': <1>, 'b': <2>, 'private-user': <3>}], [], {})",
            "(uint32 7, [({'a': <1>, 'b': <2>, 'c': <3>, 'private-user': <4>}, [], {})], [], {})",
        )
        for response in responses:
            with self.subTest(response=response):
                self.inspector.runner = lambda argv, timeout: success(response)
                result = self.inspector.gnome()
                self.assertEqual(result, {"status": "error", "reason": "unexpected_display_state_shape"})
                self.assertNotIn("private-user", json.dumps(result))

    def test_colord_wrong_map_outer_replies_return_shape_error_at_each_query(self):
        normal_runner = self.runner
        for stage in ("GetDevicesByKind", "Profiles", "Title", "Filename"):
            with self.subTest(stage=stage):
                def malformed_runner(argv, timeout):
                    method = argv[argv.index("--method") + 1]
                    if (stage == "GetDevicesByKind" and method.endswith(stage)) or argv[-1] == stage:
                        return success("{'private-user': <'SERIAL_PRIVATE'>}")
                    return normal_runner(argv, timeout)
                self.inspector.runner = malformed_runner
                result = self.inspector.colord()
                self.assertEqual(result, {"status": "error", "reason": "unexpected_colord_response_shape"})
                self.assertNotIn("private-user", json.dumps(result))
                self.assertNotIn("SERIAL_PRIVATE", json.dumps(result))

    def test_profile_read_failure_is_reported_without_filename(self):
        self.profile.unlink()
        result = self.inspector.colord()
        profile = result["displays"][0]["profiles"][0]
        self.assertEqual(profile["file"]["reason"], "profile_file_missing")
        self.assertNotIn(str(self.profile), json.dumps(result))

    def test_non_display_colord_paths_are_rejected(self):
        self.inspector.runner = lambda argv, timeout: success("(['/org/freedesktop/ColorManager/printers/private_user'],)")
        self.assertEqual(self.inspector.colord()["reason"], "unexpected_colord_response_shape")

    def test_profile_fifo_is_rejected_without_blocking(self):
        self.profile.unlink()
        os.mkfifo(self.profile)
        result = self.inspector.colord()
        self.assertEqual(result["displays"][0]["profiles"][0]["file"]["reason"],
                         "not_regular_profile_file")

    def test_oversize_edid_has_no_partial_hash(self):
        self.hardware()
        self.put("class/drm/card0-eDP-2/edid", b"x" * (display.FILE_LIMIT + 1))
        evidence = self.inspector.connectors()["items"][0]["edid"]
        self.assertEqual(evidence, {"status": "error", "reason": "file_limit"})


class ProcessAndOutputTests(unittest.TestCase):
    def test_real_timeout_and_output_limit(self):
        timeout = display.run_command([sys.executable, "-c", "import time; time.sleep(2)"], 0.05)
        self.assertEqual(timeout["reason"], "timeout")
        limit = display.run_command([sys.executable, "-c", "print('x' * 100000)"], 2)
        self.assertEqual(limit["reason"], "output_limit")
        self.assertNotIn("stdout", limit)

    def test_missing_denied_and_failed_commands_hide_stderr(self):
        for error, reason in ((FileNotFoundError(), "command_missing"),
                              (PermissionError("private"), "permission_denied")):
            with mock.patch.object(subprocess, "Popen", side_effect=error):
                self.assertEqual(display.run_command(["gdbus"], 1)["reason"], reason)
        result = display.run_command([sys.executable, "-c", "import sys; sys.stderr.write('private'); sys.exit(4)"], 2)
        self.assertEqual(result["returncode"], 4)
        self.assertNotIn("private", json.dumps(result))

    def test_output_is_private_and_existing_files_and_symlinks_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            display.write_report(path, '{"schema_version": 1}\n')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                display.write_report(path, "replacement")
            self.assertEqual(json.loads(path.read_text()), {"schema_version": 1})
            alias = Path(directory) / "alias.json"
            alias.symlink_to(path)
            with self.assertRaises(FileExistsError):
                display.write_report(alias, "replacement")
            self.assertEqual(json.loads(path.read_text()), {"schema_version": 1})


if __name__ == "__main__":
    unittest.main()
