"""Deferred regressions for the isolated offline package builder."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "package_ubuntu_offline", Path(__file__).resolve().parents[1] / "tools/package-ubuntu-offline.py")
assert SPEC is not None and SPEC.loader is not None
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


class OfflineDependencyTests(unittest.TestCase):
    def test_installed_dependencies_do_not_enable_exception(self):
        with mock.patch.object(package.subprocess, "run") as run:
            self.assertIsNone(package.staged_dependency_exception(0, "", "0.3.0-1ubuntu1~hdr9"))
        run.assert_not_called()

    def test_only_matching_staged_dependency_is_audited(self):
        error = "dpkg-checkbuilddeps: error: unmet build dependencies: libdisplay-info-dev (>= 0.3.0-1ubuntu1~hdr8~)\n"
        with mock.patch.object(package.subprocess, "run") as run:
            result = package.staged_dependency_exception(1, error, "0.3.0-1ubuntu1~hdr9")
        run.assert_called_once_with(["dpkg", "--compare-versions", "0.3.0-1ubuntu1~hdr9", "ge", "0.3.0-1ubuntu1~hdr8~"], check=True)
        self.assertFalse(result["installed_status_changed"])
        self.assertEqual(result["package"], "libdisplay-info-dev")

    def test_lower_staged_version_is_rejected(self):
        error = "dpkg-checkbuilddeps: error: unmet build dependencies: libdisplay-info-dev (>= 0.3.0-1ubuntu1~hdr8~)"
        with mock.patch.object(package.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["dpkg"])):
            with self.assertRaises(subprocess.CalledProcessError):
                package.staged_dependency_exception(1, error, "0.3.0-1")

    def test_additional_dependency_is_never_bypassed(self):
        error = "dpkg-checkbuilddeps: error: unmet build dependencies: libdisplay-info-dev (>= 0.3.0-1ubuntu1~hdr8~) fakeroot\n"
        with mock.patch.object(package.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                package.staged_dependency_exception(1, error, "0.3.0-1ubuntu1~hdr9")
        run.assert_not_called()

    def test_conflict_or_unknown_failure_is_never_bypassed(self):
        for error in ["dpkg-checkbuilddeps: error: build conflicts: libdisplay-info-dev", "permission denied", "", "dpkg-checkbuilddeps: error: unmet build dependencies: fakeroot"]:
            with self.subTest(error=error), mock.patch.object(package.subprocess, "run") as run:
                with self.assertRaises(ValueError):
                    package.staged_dependency_exception(1, error, "0.3.0-1ubuntu1~hdr9")
                run.assert_not_called()

    def test_unprivileged_native_boundary_is_required(self):
        with mock.patch.object(package.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(ValueError, "native x86_64"):
                package.build(None)
        with mock.patch.object(package.platform, "system", return_value="Linux"), mock.patch.object(package.platform, "machine", return_value="aarch64"):
            with self.assertRaisesRegex(ValueError, "native x86_64"):
                package.build(None)
        with mock.patch.object(package.platform, "system", return_value="Linux"), mock.patch.object(package.platform, "machine", return_value="x86_64"), mock.patch.object(package.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(ValueError, "unprivileged"):
                package.build(None)


if __name__ == "__main__":
    unittest.main()
