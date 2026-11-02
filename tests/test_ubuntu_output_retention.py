"""Offline output lifecycle regressions; no Docker, network or real packages.

Exercise the real rebuild/registry/retention code with fake external build,
Ubuntu query and publication boundaries. Fake records stay under ignored work/
for failure diagnosis, never in system temporary storage or public artifacts.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / "packaging/ubuntu"
SPEC = importlib.util.spec_from_file_location("ubuntu_outputs", PACKAGING / "outputs.py")
assert SPEC is not None and SPEC.loader is not None
OUTPUTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OUTPUTS)


class UbuntuOutputRetentionTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "work/ubuntu-output-retention-tests"
        scratch.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="case-", dir=scratch))
        self.here = self.root / "repo/packaging/ubuntu"
        self.here.mkdir(parents=True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.work = self.root / "retained outputs"
        for name in ("rebuild.sh", "registry.sh", "outputs.py", "REVISION"):
            shutil.copy2(PACKAGING / name, self.here / name)
        self.revision = (self.here / "REVISION").read_text().strip()
        self.write(self.root / "repo/scripts/check_repository.py", "# fake offline prerequisite\n")
        self.executable(self.bin / "docker", "#!/bin/sh\nprintf 'testrelease 1.0-1 2.0-1\\n'\n")
        self.executable(self.bin / "curl", r'''#!/usr/bin/env python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
if "-o" in args:
    Path(args[args.index("-o") + 1]).write_bytes(b"fake registry dependency")
else:
    if os.environ.get("PUBLISHED") == "yes":
        version = os.environ["REVISION"]
        print(f"Package: libdisplay-info3\nSource: libdisplay-info\nVersion: 1.0-1+nativehdr{version}\n")
        print(f"Package: mutter\nVersion: 2.0-1+nativehdr{version}\n")
    print("200")
''')
        self.executable(self.here / "build.sh", r'''#!/usr/bin/env python3
import hashlib
import os
import sys
from pathlib import Path
src, out = sys.argv[1:3]
out = Path(out)
arch = sys.argv[sys.argv.index("--arch") + 1]
ubuntu = sys.argv[sys.argv.index("--version") + 1]
version = ubuntu + "+nativehdr" + os.environ["REVISION"]
print("private full build diagnostic", flush=True)
(out / "partial").write_bytes(b"partial bytes")
if os.environ.get("FAIL_BUILD") == "yes":
    sys.exit(9)
(out / "partial").unlink()
for suffix in ("deb", "changes", "buildinfo"):
    (out / f"{src}_{version}_{arch}.{suffix}").write_bytes(b"fake " + suffix.encode())
if arch == "amd64":
    archive = f"{src}_{ubuntu}.orig.tar.xz"
    data = b"fake original source archive"
    (out / archive).write_bytes(data)
    (out / f"{src}_{version}.dsc").write_text(
        f"Source: {src}\nVersion: {version}\nChecksums-Sha256:\n {hashlib.sha256(data).hexdigest()} {len(data)} {archive}\n")
(out / f"{src}-{arch}-build.log").write_text("fake complete build log\n")
''')
        self.executable(self.here / "multiarch-same.sh", "#!/bin/sh\nexit 0\n")
        self.executable(self.here / "publish.sh", '''#!/usr/bin/env python3
import os
import sys
from pathlib import Path
# Actual producer outputs must still be present at the publication boundary.
for item in sys.argv[1:]:
    path = Path(item)
    if path.is_dir():
        assert list(path.glob("*.deb"))
if os.environ.get("FAIL_PUBLISH") == "yes":
    sys.exit(7)
''')
        self.env = os.environ.copy()
        self.env.pop("FORGEJO_TOKEN", None)
        self.env.update(PATH=str(self.bin) + os.pathsep + self.env["PATH"],
                        REVISION=self.revision, FORGEJO_URL="http://registry.invalid",
                        FORGEJO_OWNER="operator", PUBLISHED="no", FAIL_BUILD="no",
                        FAIL_PUBLISH="no")

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def executable(self, path, text):
        self.write(path, text)
        path.chmod(0o755)

    def start(self, **env):
        return subprocess.Popen(["bash", str(self.here / "rebuild.sh"), str(self.work)],
                                env=dict(self.env, **env), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def run_rebuild(self, expected=0, **env):
        process = self.start(**env)
        stdout, stderr = process.communicate(timeout=30)
        self.assertEqual(process.returncode, expected, stdout + stderr)
        return stdout, stderr

    def snapshot(self):
        return {p.relative_to(self.work).as_posix():
                (p.stat().st_mode, p.stat().st_mtime_ns,
                 hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None)
                for p in [self.work, *self.work.rglob("*")]}

    def old_outputs(self):
        self.write(self.work / "successful/original.dsc", "previous exact source\n")
        self.write(self.work / "failed/partial.log", "previous failure\n")
        self.write(self.work / "unknown", "caller-owned data\n")

    def runs(self):
        return sorted(self.work.glob("run-*"))

    def test_published_noop_leaves_successful_partial_and_unknown_bytes_and_metadata(self):
        self.old_outputs()
        before = self.snapshot()
        stdout, _ = self.run_rebuild(PUBLISHED="yes")
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn("retained build outputs:", stdout)
        self.assertEqual(self.runs(), [])

    def test_published_noop_does_not_create_output_root(self):
        self.run_rebuild(PUBLISHED="yes")
        self.assertFalse(self.work.exists())

    def test_concurrent_runs_are_exclusive_and_do_not_mix_outputs(self):
        first, second = self.start(), self.start()
        for process in (first, second):
            stdout, stderr = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        runs = self.runs()
        self.assertEqual(len(runs), 2)
        self.assertNotEqual(runs[0], runs[1])
        for run in runs:
            self.assertEqual(run.stat().st_mode & 0o777, 0o700)
            for name in ("libdisplay-info-amd64", "libdisplay-info-i386", "mutter-amd64"):
                OUTPUTS.verify(run / name, run / (name + ".manifest.json"))
            self.assertEqual(len(list(run.glob("with/*.deb"))), 2)

    def test_publication_failure_preserves_completed_original_records(self):
        self.old_outputs()
        before = {p: p.read_bytes() for p in self.work.rglob("*") if p.is_file()}
        stdout, stderr = self.run_rebuild(expected=7, FAIL_PUBLISH="yes")
        self.assertNotIn("private full build diagnostic", stdout + stderr)
        self.assertEqual(len(self.runs()), 1)
        run = self.runs()[0]
        for arch in ("amd64", "i386"):
            out = run / ("libdisplay-info-" + arch)
            OUTPUTS.verify(out, out.with_suffix(".manifest.json"))
            self.assertEqual(len(list(out.glob("*.buildinfo"))), 1)
            self.assertEqual(len(list(out.glob("*.changes"))), 1)
            self.assertIn("private full build diagnostic", (out / "invocation.log").read_text())
        amd64 = run / "libdisplay-info-amd64"
        self.assertEqual(len(list(amd64.glob("*.dsc"))), 1)
        self.assertEqual(len(list(amd64.glob("*.orig.tar.xz"))), 1)
        self.assertFalse((run / "mutter-amd64").exists())
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)

    def test_build_failure_preserves_partial_output_and_diagnostics(self):
        self.run_rebuild(expected=1, FAIL_BUILD="yes")
        out = self.runs()[0] / "libdisplay-info-amd64"
        self.assertEqual((out / "partial").read_bytes(), b"partial bytes")
        self.assertIn("private full build diagnostic", (out / "invocation.log").read_text())
        self.assertFalse(out.with_suffix(".manifest.json").exists())
        self.run_rebuild(PUBLISHED="yes")
        self.assertEqual((out / "partial").read_bytes(), b"partial bytes")

    def test_manifest_detects_changed_missing_and_additional_bytes(self):
        out = self.root / "build"
        self.write(out / "source.dsc", "original source\n")
        self.write(out / "nested/source.tar.xz", "original archive\n")
        manifest = self.root / "build.manifest.json"
        OUTPUTS.seal(out, manifest, "mutter", "2.0-1", "2.0-1+nativehdr13", "amd64")
        record = json.loads(manifest.read_text())
        self.assertEqual((record["source"], record["version"], record["architecture"]),
                         ("mutter", "2.0-1+nativehdr13", "amd64"))
        original = (out / "source.dsc").read_bytes()
        (out / "source.dsc").write_bytes(b"different source\n")
        with self.assertRaises(ValueError):
            OUTPUTS.verify(out, manifest)
        (out / "source.dsc").write_bytes(original)
        (out / "nested/source.tar.xz").unlink()
        with self.assertRaises(ValueError):
            OUTPUTS.verify(out, manifest)
        self.write(out / "nested/source.tar.xz", "original archive\n")
        self.write(out / "extra", "unexpected bytes\n")
        with self.assertRaises(ValueError):
            OUTPUTS.verify(out, manifest)
        (out / "extra").unlink()
        OUTPUTS.verify(out, manifest)
        with self.assertRaises(FileExistsError):
            OUTPUTS.seal(out, manifest, "mutter", "2.0-1", "2.0-1+nativehdr13", "amd64")

    def test_manifest_rejects_symlink_outputs(self):
        out = self.root / "build"
        out.mkdir()
        (out / "external").symlink_to(self.here, target_is_directory=True)
        with self.assertRaises(ValueError):
            OUTPUTS.inventory(out)


if __name__ == "__main__":
    unittest.main()
