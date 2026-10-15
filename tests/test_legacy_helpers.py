"""Hermetic control-flow regressions: real helpers, no builds/Wine/host changes.

Scratch defaults to the ignored work/ tree, never the system temporary directory.
Only the Wine helper's literal generated inner shell is run; its privileged outer
installer is deliberately never invoked. External build/runtime tools are stubs.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REAL_GIT = shutil.which("git")
assert REAL_GIT is not None, "Git is required for hermetic helper regressions"
STUB = r'''
import json, os, pathlib, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["TRACE"], "a") as f:
    f.write(json.dumps([name, *args]) + "\n")
if name == "realpath":
    print(pathlib.Path(args[-1]).resolve())
elif name == "git":
    cmd = args[2:] if args[:1] == ["-C"] else args
    action = "-".join(cmd[:2]) if cmd[:1] == ["worktree"] else cmd[0]
    if action == os.environ.get("FAIL_GIT"):
        sys.exit(int(os.environ.get("GIT_EXIT", "128")))
    if cmd == ["rev-parse", "HEAD"] and os.environ.get("WRONG_HEAD"):
        print("0" * 40)
    else:
        os.execv(os.environ["REAL_GIT"], [os.environ["REAL_GIT"], *args])
elif name == "meson":
    if os.environ.get("SETUP_FAIL"):
        sys.exit(7)
    build, source = map(pathlib.Path, args[1:3])
    info = build / "meson-info"
    info.mkdir()
    directories = {"source": str(source), "build": str(build)}
    if os.environ.get("WRONG_ASSOCIATION"):
        directories[os.environ["WRONG_ASSOCIATION"]] = str(build / "unrelated")
    (info / "meson-info.json").write_text(json.dumps({"directories": directories}))
elif name == "ninja":
    build = pathlib.Path(args[1])
    dirs = json.loads((build / "meson-info/meson-info.json").read_text())["directories"]
    head = subprocess.check_output([os.environ["REAL_GIT"], "-C", dirs["source"], "rev-parse", "HEAD"], text=True).strip()
    print("stub build " + head)
    sys.exit(1 if head == os.environ.get("FAIL_COMMIT") else 0)
elif name == "nice":
    os.execvp(args[0], args)
elif name == "timeout":
    if os.environ.get("TIMEOUT_COMMAND") == args[1]:
        sys.exit(124)
    os.execvp(args[1], args[1:])
elif name == "wineboot":
    print("stub initialization")
    sys.exit(int(os.environ.get("INIT_EXIT", "0")))
elif name == "wine":
    print("stub " + args[-1])
    key = "DM_EXIT" if args[-1] == "displaymonitor" else "DC_EXIT"
    sys.exit(int(os.environ.get(key, "0")))
elif name == "wineserver":
    sys.exit(int(os.environ.get("CLEANUP_EXIT", "0")))
elif name in ("sleep", "Xvfb"):
    pass
else:
    raise SystemExit("unexpected stub " + name)
'''


class HelperTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(os.environ.get("HDR_HELPER_TEST_ROOT", ROOT / "work/helper-tests"))
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("git", "realpath", "meson", "ninja", "nice", "timeout",
                     "wineboot", "wine", "wineserver", "Xvfb", "sleep"):
            tool = self.bin / name
            tool.write_text(f"#!{sys.executable}\n" + STUB)
            tool.chmod(0o755)
        self.trace = self.root / "trace.jsonl"
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        TRACE=str(self.trace), REAL_GIT=REAL_GIT,
                        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="Test Agent", GIT_AUTHOR_EMAIL="test@invalid",
                        GIT_COMMITTER_NAME="Test Agent", GIT_COMMITTER_EMAIL="test@invalid")
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "file").write_text("base\n")
        self.base = self.commit("base")
        (self.repo / "file").write_text("first\n")
        self.first = self.commit("first")
        (self.repo / "file").write_text("second\n")
        self.tip = self.commit("second")
        self.build = self.root / "build"
        self.wt = self.root / "build-worktree"
        self.prefix = self.root / "prefix"
        self.prefix.mkdir()

    def git(self, *args):
        return subprocess.check_output([REAL_GIT, "-C", str(self.repo), *args],
                                       env=self.env, text=True).strip()

    def commit(self, subject):
        self.git("add", ".")
        self.git("commit", "-qm", subject)
        return self.git("rev-parse", "HEAD")

    def calls(self, name):
        if not self.trace.exists():
            return []
        return [row[1:] for line in self.trace.read_text().splitlines()
                if (row := json.loads(line))[0] == name]

    def run_helper(self, script, args=(), **env):
        return subprocess.run(["/bin/sh", str(script), *map(str, args)],
                              env=dict(self.env, **env), text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)

    def build_run(self, base=None, **env):
        return self.run_helper(ROOT / "tools/check-each-commit.sh",
                               [self.repo, base or self.base, self.tip,
                                self.build, self.prefix], **env)

    def assert_prerequisite_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("OK ", result.stdout)
        self.assertEqual(self.calls("ninja"), [])

    def test_build_usage(self):
        self.assert_prerequisite_failure(self.run_helper(ROOT / "tools/check-each-commit.sh"))

    def test_build_invalid_range(self):
        self.assert_prerequisite_failure(self.build_run(base="missing-revision"))
        self.assertFalse(self.build.exists())

    def test_build_rev_list_failure(self):
        self.assert_prerequisite_failure(self.build_run(FAIL_GIT="rev-list"))
        self.assertFalse(self.build.exists())

    def test_build_existing_worktree_preserved(self):
        self.git("worktree", "add", "--detach", str(self.wt), self.tip)
        marker = self.wt / "uncommitted"
        marker.write_text("preserve me")
        self.assert_prerequisite_failure(self.build_run())
        self.assertEqual(marker.read_text(), "preserve me")
        self.assertIn(str(self.wt), self.git("worktree", "list", "--porcelain"))

    def test_build_existing_build_preserved(self):
        self.build.mkdir()
        marker = self.build / "uncommitted"
        marker.write_text("preserve me")
        self.assert_prerequisite_failure(self.build_run())
        self.assertEqual(marker.read_text(), "preserve me")
        self.assertFalse(self.wt.exists())

    def test_build_existing_symlink_preserved(self):
        self.wt.symlink_to(self.root / "absent")
        self.assert_prerequisite_failure(self.build_run())
        self.assertTrue(self.wt.is_symlink())

    def test_build_build_symlink_preserved(self):
        self.build.symlink_to(self.root / "absent")
        self.assert_prerequisite_failure(self.build_run())
        self.assertTrue(self.build.is_symlink())
        self.assertFalse((self.root / "absent").exists())

    def test_build_add_failure_not_removed(self):
        self.assert_prerequisite_failure(self.build_run(FAIL_GIT="worktree-add"))
        self.assertFalse(any("remove" in call for call in self.calls("git")))

    def test_build_checkout_failure_cleanup(self):
        self.assert_prerequisite_failure(self.build_run(FAIL_GIT="checkout"))
        self.assertFalse(self.wt.exists())
        self.assertTrue(any("remove" in call for call in self.calls("git")))

    def test_build_wrong_head(self):
        self.assert_prerequisite_failure(self.build_run(WRONG_HEAD="1"))
        self.assertFalse(self.wt.exists())

    def test_build_setup_failure(self):
        self.assert_prerequisite_failure(self.build_run(SETUP_FAIL="1"))
        self.assertTrue((self.root / "build.logs/setup.log").is_file())
        self.assertFalse(self.wt.exists())

    def test_build_source_association(self):
        self.assert_prerequisite_failure(self.build_run(WRONG_ASSOCIATION="source"))
        self.assertFalse(self.wt.exists())

    def test_build_build_association(self):
        self.assert_prerequisite_failure(self.build_run(WRONG_ASSOCIATION="build"))
        self.assertFalse(self.wt.exists())

    def test_build_success_each_commit(self):
        result = self.build_run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [f"OK {self.first} first", f"OK {self.tip} second"])
        self.assertEqual(len(self.calls("ninja")), 2)
        self.assertFalse(self.wt.exists())
        self.assertTrue(self.build.is_dir())

    def test_build_failure_accumulated(self):
        result = self.build_run(FAIL_COMMIT=self.first)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [f"FAIL {self.first} first", f"OK {self.tip} second"])
        self.assertTrue((self.root / f"build.logs/fail-{self.first}.log").is_file())
        self.assertFalse(self.wt.exists())

    def scanner(self, revision=None, **env):
        tools = self.repo / "tools"
        tools.mkdir(exist_ok=True)
        script = tools / "scan_publication.sh"
        shutil.copyfile(ROOT / "tools/scan_publication.sh", script)
        return self.run_helper(script, [revision or f"{self.base}..HEAD"], **env)

    def test_scan_clean_no_match(self):
        result = self.scanner()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scan: clean", result.stdout)

    def test_scan_added_match_even_if_removed(self):
        (self.repo / "secret").write_text("ghp" + "_" + "a" * 24)
        self.commit("synthetic fixture")
        (self.repo / "secret").unlink()
        self.commit("remove fixture")
        result = self.scanner()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Added lines:", result.stdout)
        self.assertNotIn("Tree (", result.stdout)

    def test_scan_tree_match_outside_range(self):
        (self.repo / "secret").write_text("github" + "_pat_" + "b" * 24)
        self.commit("synthetic fixture")
        result = self.scanner("HEAD..HEAD")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Tree (outside tests/):", result.stdout)

    def test_scan_fixture_policy(self):
        (self.repo / "tests").mkdir()
        (self.repo / "tests/fixture").write_text("10." + "42.1.2")
        self.commit("fixture")
        result = self.scanner()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Added lines:", result.stdout)
        self.assertNotIn("Tree (", result.stdout)
        result = self.scanner("HEAD..HEAD")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_scan_invalid_range(self):
        result = self.scanner("absent..HEAD")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("scan: clean", result.stdout)

    def test_scan_history_read_failure(self):
        result = self.scanner(FAIL_GIT="log")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("scan: clean", result.stdout)

    def test_scan_tree_error(self):
        result = self.scanner(FAIL_GIT="grep")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("scan: clean", result.stdout)

    def wine_run(self, make_test_dir=True, **env):
        # Refuse any environment that could shadow our stubs with a real runtime.
        self.assertFalse(Path("/opt/wine-stable/bin").exists())
        text = (ROOT / "tools/wine-runtime-test.sh").read_text()
        body = text.split("<<'IN'\n", 1)[1].split("\nIN\n", 1)[0]
        inner = self.root / "wine-inner.sh"
        inner.write_text(body + "\n")
        if make_test_dir:
            (self.root / "t").mkdir()
        result = self.run_helper(inner, HOME=str(self.root), **env)
        self.assertEqual(self.calls("wineserver"), [["-k"]])
        return result

    def test_wine_success_cleanup_failure_not_primary(self):
        result = self.wine_run(CLEANUP_EXIT="9")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls("wine")), 2)
        self.assertTrue((self.root / "t/wineboot.log").is_file())
        self.assertTrue((self.root / "t/dm.log").is_file())
        self.assertTrue((self.root / "t/dc.log").is_file())

    def test_wine_initialization_failure(self):
        result = self.wine_run(INIT_EXIT="17", CLEANUP_EXIT="9")
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertEqual(self.calls("wine"), [])
        self.assertIn("wineboot exit=17", result.stdout)

    def test_wine_first_test_failure(self):
        result = self.wine_run(DM_EXIT="18", CLEANUP_EXIT="9")
        self.assertEqual(result.returncode, 18, result.stderr)
        self.assertEqual(len(self.calls("wine")), 2)

    def test_wine_second_test_failure(self):
        result = self.wine_run(DC_EXIT="19")
        self.assertEqual(result.returncode, 19, result.stderr)

    def test_wine_init_timeout(self):
        result = self.wine_run(TIMEOUT_COMMAND="wineboot", CLEANUP_EXIT="9")
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertEqual(self.calls("wine"), [])

    def test_wine_test_timeout(self):
        result = self.wine_run(TIMEOUT_COMMAND="wine", CLEANUP_EXIT="9")
        self.assertEqual(result.returncode, 124, result.stderr)

    def test_wine_early_exit_cleanup(self):
        result = self.wine_run(make_test_dir=False)
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls("wineboot"), [])


if __name__ == "__main__":
    unittest.main()
