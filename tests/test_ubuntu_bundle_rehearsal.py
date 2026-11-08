"""Exercise APT's real solver on a tiny offline forward and inverse transaction."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bundle_rehearsal", ROOT / "tools/qualify-ubuntu-bundle.py")
rehearsal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rehearsal)


@unittest.skipUnless(shutil.which("apt-get") and shutil.which("dpkg-deb"), "needs Debian package tools")
class BundleRehearsal(unittest.TestCase):
    def test_exact_forward_inverse_and_wrong_runtime_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            candidate = private / "candidate"
            rollback = private / "rollback"
            candidate.mkdir()
            rollback.mkdir()
            arch = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()

            def package(destination, name, version, dependency=None):
                build = private / (name + "-" + version)
                control_dir = build / "DEBIAN"
                control_dir.mkdir(parents=True)
                control = (f"Package: {name}\nVersion: {version}\nArchitecture: {arch}\n"
                           "Maintainer: Fixture <fixture@example.org>\nDescription: Local APT fixture\n")
                if dependency:
                    control += "Depends: " + dependency + "\n"
                (control_dir / "control").write_text(control)
                archive = destination / f"{name}_{version}_{arch}.deb"
                subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(build), str(archive)],
                               check=True, stdout=subprocess.DEVNULL)
                return archive, control

            app, runtime = "rog-rehearsal-app", "rog-rehearsal-renderer"
            _, old = package(rollback, app, "1")
            package(candidate, app, "2", runtime + " (= 2)")
            correct, _ = package(candidate, runtime, "2")
            status = private / "fixture-status"
            status.write_text(old + "Status: install ok installed\n")
            original = status.read_bytes()

            out = private / "receipt"
            rehearsal.qualify(candidate, rollback, out, status)
            receipt = json.loads((out / "receipt.json").read_text())
            self.assertEqual(receipt["forward_actions"], {"install": {app: "2", runtime: "2"}, "remove": []})
            self.assertEqual(receipt["rollback_actions"], {"install": {app: "1"}, "remove": [runtime]})
            self.assertEqual(status.read_bytes(), original)

            correct.unlink()
            package(candidate, runtime, "1")
            with self.assertRaisesRegex(ValueError, "forward solver failed"):
                rehearsal.qualify(candidate, rollback, private / "wrong-version", status)
            self.assertEqual(status.read_bytes(), original)
