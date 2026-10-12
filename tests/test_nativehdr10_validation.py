"""Source-bound batch runner regressions; execute only after full-batch review."""

from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/nativehdr10_validation.py"
SPEC = importlib.util.spec_from_file_location("nativehdr10_validation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / "source"
        self.source.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Validation Fixture")
        self.git("config", "user.email", "validation@invalid")
        (self.source / "affected.txt").write_text("initial\n")
        (self.source / "unrelated.txt").write_text("unrelated\n")
        self.commit()
        self.path = self.root / "manifest.json"
        self.ledger = self.root / "receipts.json"
        self.counter = self.root / "runs.txt"
        self.data = {"schema": 1, "sources": {"source": "source"},
                     "checks": [self.check("one")]}
        self.write_manifest()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.source), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "fixture")

    def check(self, name, code=None, sources=None):
        if code is None:
            code = ("from pathlib import Path; "
                    f"p=Path({str(self.counter)!r}); "
                    f"p.open('a').write({name + chr(10)!r}); print('actual check output')")
        return {"id": name, "sources": sources or ["source"],
                "argv": [sys.executable, "-c", code], "cwd": "source",
                "env": {}, "timeout_seconds": 10}

    def write_manifest(self):
        self.path.write_text(json.dumps(self.data))

    def run_batch(self, invalidate=(), reason=None):
        self.write_manifest()
        with redirect_stdout(io.StringIO()):
            return validation.run_batch(self.path, self.ledger, invalidate, reason)

    def receipts(self, name="one"):
        return json.loads(self.ledger.read_text())["checks"][name]

    def runs(self):
        return self.counter.read_text().splitlines() if self.counter.exists() else []

    def test_success_is_executed_once_and_receipt_is_exact(self):
        self.assertEqual(self.run_batch(), 0)
        receipt = self.receipts()[-1]
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["returncode"], 0)
        self.assertEqual(receipt["sources"]["source"]["tree"], self.git("rev-parse", "HEAD^{tree}"))
        self.assertEqual(receipt["sources"]["source"]["head"], self.git("rev-parse", "HEAD"))
        self.assertEqual(receipt["command"]["argv"], self.data["checks"][0]["argv"])
        self.assertIn("actual check output", Path(receipt["log"]).read_text())
        self.assertEqual(receipt["log_sha256"], validation.file_digest(Path(receipt["log"])))
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(self.runs(), ["one"])
        self.assertEqual(len(self.receipts()), 1)  # No synthetic pass for the skip.

    def test_failure_retries_without_repeating_success(self):
        marker = self.root / "failed-once"
        code = ("from pathlib import Path; import sys; "
                f"p=Path({str(marker)!r}); existed=p.exists(); p.touch(); "
                "print('attempt'); sys.exit(0 if existed else 7)")
        self.data["checks"].append(self.check("retry", code))
        self.assertEqual(self.run_batch(), 1)
        self.assertEqual(self.receipts("retry")[-1]["returncode"], 7)
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(self.runs(), ["one"])
        self.assertEqual([item["status"] for item in self.receipts("retry")], ["failed", "passed"])

    def test_changed_source_requires_explicit_invalidation(self):
        self.run_batch()
        (self.source / "affected.txt").write_text("changed\n")
        self.commit()
        with self.assertRaisesRegex(validation.ValidationError, "explicitly --invalidate"):
            self.run_batch()
        self.assertEqual(self.runs(), ["one"])
        self.assertEqual(self.run_batch(["one"], "affected code corrected"), 0)
        self.assertEqual(self.runs(), ["one", "one"])
        event = self.receipts()[-2]
        self.assertEqual(event["status"], "invalidated")
        self.assertEqual(event["reason"], "affected code corrected")
        self.assertNotEqual(event["fingerprint"], event["previous_fingerprint"])

    def test_scoped_unaffected_success_is_not_rerun(self):
        self.data["checks"][0]["paths"] = {"source": ["affected.txt"]}
        self.data["checks"].append({**self.check("other"), "paths": {"source": ["unrelated.txt"]}})
        self.run_batch()
        old_tree = self.receipts("other")[-1]["sources"]["source"]["tree"]
        (self.source / "affected.txt").write_text("fix\n")
        self.commit()
        self.assertEqual(self.run_batch(["one"], "affected input changed"), 0)
        self.assertEqual(self.runs(), ["one", "other", "one"])
        self.assertEqual(len(self.receipts("other")), 1)
        self.assertEqual(self.receipts("other")[-1]["sources"]["source"]["tree"], old_tree)
        self.assertIn("input_sha256", self.receipts("other")[-1]["sources"]["source"])

    def test_command_environment_timeout_and_scope_changes_need_invalidation(self):
        self.run_batch()
        original = copy.deepcopy(self.data)
        for field, value in (("argv", [sys.executable, "-c", "print('changed')"]),
                             ("env", {"LC_ALL": "C.UTF-8"}), ("timeout_seconds", 11),
                             ("paths", {"source": ["affected.txt"]})):
            with self.subTest(field=field):
                self.data = copy.deepcopy(original)
                self.data["checks"][0][field] = value
                with self.assertRaisesRegex(validation.ValidationError, "explicitly --invalidate"):
                    self.run_batch()
        self.assertEqual(self.runs(), ["one"])

    def test_identical_tree_new_commit_does_not_invalidate(self):
        self.run_batch()
        self.git("commit", "--allow-empty", "--quiet", "-m", "same code")
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(self.runs(), ["one"])

    def test_running_attempt_is_retried_not_counted_as_pass(self):
        self.run_batch()
        ledger = json.loads(self.ledger.read_text())
        ledger["checks"]["one"][-1]["status"] = "running"
        self.ledger.write_text(json.dumps(ledger))
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(self.runs(), ["one", "one"])

    def test_success_log_loss_requires_explicit_invalidation(self):
        self.run_batch()
        log = Path(self.receipts()[-1]["log"])
        log.write_text("not the original output")
        with self.assertRaisesRegex(validation.ValidationError, "log missing/changed"):
            self.run_batch()
        log.unlink()
        with self.assertRaisesRegex(validation.ValidationError, "log missing/changed"):
            self.run_batch()
        self.assertEqual(self.runs(), ["one"])
        self.assertEqual(self.run_batch(["one"], "original log lost"), 0)

    def test_dirty_tracked_or_untracked_source_is_rejected(self):
        for path in (self.source / "affected.txt", self.source / "untracked.txt"):
            with self.subTest(path=path):
                path.write_text("dirty\n")
                with self.assertRaisesRegex(validation.ValidationError, "is dirty"):
                    self.run_batch()
                self.assertEqual(self.runs(), [])
                self.assertFalse(self.ledger.exists())
                if path.name == "affected.txt":
                    self.git("restore", "affected.txt")
                else:
                    path.unlink()

    def test_source_mutation_during_zero_exit_never_passes_or_runs_next_check(self):
        code = "from pathlib import Path; Path('affected.txt').write_text('mutated')"
        self.data["checks"] = [self.check("mutates", code), self.check("later")]
        with self.assertRaisesRegex(validation.ValidationError, "batch stopped"):
            self.run_batch()
        attempt = self.receipts("mutates")[-1]
        self.assertEqual(attempt["returncode"], 0)
        self.assertEqual(attempt["status"], "failed")
        self.assertIn("dirty", attempt["error"])
        self.assertEqual(self.runs(), [])
        self.assertNotIn("later", json.loads(self.ledger.read_text())["checks"])

    def test_argv_is_literal_and_environment_not_inherited(self):
        sentinel = self.root / "must-not-exist"
        literal = f"$(touch {sentinel}); * 'quoted'"
        code = "import os, sys; print(sys.argv[1]); print(os.environ.get('LEDGER_TEST_SECRET', 'absent'))"
        self.data["checks"][0]["argv"] = [sys.executable, "-c", code, literal]
        with mock.patch.dict(os.environ, {"LEDGER_TEST_SECRET": "do-not-leak"}):
            self.assertEqual(self.run_batch(), 0)
        output = Path(self.receipts()[-1]["log"]).read_text()
        self.assertIn(literal, output)
        self.assertIn("absent", output)
        self.assertNotIn("do-not-leak", output)
        self.assertFalse(sentinel.exists())

    def test_missing_executable_and_timeout_are_failures(self):
        self.data["checks"] = [self.check("missing"), self.check("timeout")]
        self.data["checks"][0]["argv"] = [str(self.root / "no-executable")]
        self.data["checks"][1]["argv"] = [sys.executable, "-c", "import time; time.sleep(60)"]
        self.data["checks"][1]["timeout_seconds"] = 1
        self.assertEqual(self.run_batch(), 1)
        for name in ("missing", "timeout"):
            with self.subTest(name=name):
                attempt = self.receipts(name)[-1]
                self.assertEqual(attempt["status"], "failed")
                self.assertIsNone(attempt["returncode"])
                self.assertIn("RUNNER ERROR", Path(attempt["log"]).read_text())

    def test_full_preflight_prevents_partial_rerun(self):
        self.data["checks"].append(self.check("two"))
        self.run_batch()
        self.data["checks"][1]["env"] = {"CHANGED": "yes"}
        with self.assertRaisesRegex(validation.ValidationError, "explicitly --invalidate"):
            self.run_batch(["one"], "force one")
        self.assertEqual(self.runs(), ["one", "two"])
        self.assertEqual(len(self.receipts()), 1)

    def test_invalidations_require_reason_existing_receipt_and_known_id(self):
        for ids, reason in ((["one"], None), (["other"], "why"), (["one"], "why"),
                            (["one", "one"], "why"), ([], "why")):
            with self.subTest(ids=ids, reason=reason):
                with self.assertRaises(validation.ValidationError):
                    self.run_batch(ids, reason)
        self.assertEqual(self.runs(), [])

    def test_concurrent_ledger_use_is_rejected(self):
        with validation.locked(self.ledger):
            with self.assertRaisesRegex(validation.ValidationError, "already in use"):
                self.run_batch()
        self.assertEqual(self.runs(), [])

    def test_ledger_in_nonignored_source_path_is_rejected(self):
        self.ledger = self.source / "receipts.json"
        with self.assertRaisesRegex(validation.ValidationError, "must be Git-ignored"):
            self.run_batch()
        self.assertFalse(self.ledger.exists())

    def test_multiple_source_dependencies_and_cwd_dependency_are_checked(self):
        other = self.root / "other"
        subprocess.run(["git", "clone", "--quiet", str(self.source), str(other)], check=True)
        self.data["sources"]["other"] = "other"
        self.data["checks"][0]["sources"].append("other")
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(set(self.receipts()[-1]["sources"]), {"source", "other"})
        self.data["checks"][0]["sources"] = ["other"]
        with self.assertRaisesRegex(validation.ValidationError, "omits its cwd source"):
            self.run_batch()

    def test_ignored_output_directory_is_supported(self):
        (self.source / ".gitignore").write_text("/results/\n")
        self.commit()
        results = self.source / "results"
        results.mkdir()
        self.ledger = results / "receipts.json"
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(self.runs(), ["one"])

    def test_submodules_are_not_silently_hashed_as_plain_sources(self):
        head = self.git("rev-parse", "HEAD")
        self.git("update-index", "--add", "--cacheinfo", f"160000,{head},submodule")
        self.git("commit", "--quiet", "-m", "gitlink")
        with self.assertRaisesRegex(validation.ValidationError, "Submodules unsupported"):
            self.run_batch()
        self.assertEqual(self.runs(), [])

    def test_interrupt_preserves_nonpassing_attempt_for_retry(self):
        with mock.patch.object(validation, "execute", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_batch()
        self.assertEqual(self.receipts()[-1]["status"], "running")
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(self.runs(), ["one"])

    def test_sigterm_kills_check_and_descendant_before_retry(self):
        ready = self.root / "ready.json"
        child_code = "import time; time.sleep(60)"
        code = (
            "import json, os, subprocess, sys; from pathlib import Path\n"
            f"ready = Path({str(ready)!r})\n"
            "if ready.exists():\n"
            "    print('retry after cancellation'); sys.exit(0)\n"
            f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
            "ready.write_text(json.dumps([os.getpid(), child.pid]))\n"
            "child.wait()\n"
        )
        self.data["checks"] = [self.check("one", code)]
        self.write_manifest()
        pids = []
        with (self.root / "runner.log").open("wb") as log:
            runner = subprocess.Popen([sys.executable, str(SCRIPT), str(self.path),
                                       "--ledger", str(self.ledger)], stdout=log,
                                      stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if ready.exists():
                        try:
                            pids = json.loads(ready.read_text())
                            break
                        except ValueError:  # Wait for the complete readiness write.
                            pass
                    self.assertIsNone(runner.poll(), "runner exited before check readiness")
                    time.sleep(0.01)
                self.assertEqual(len(pids), 2, "check/descendant did not become ready")
                runner.send_signal(signal.SIGTERM)
                self.assertEqual(runner.wait(timeout=10), 128 + signal.SIGTERM)
                for pid in pids:
                    deadline = time.monotonic() + 5
                    while self.process_running(pid) and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertFalse(self.process_running(pid), f"orphaned process {pid}")
                self.assertNotEqual(self.receipts()[-1]["status"], "passed")
                self.assertEqual(self.run_batch(), 0)
                self.assertEqual(len(self.receipts()), 2)
                self.assertEqual(self.receipts()[-1]["status"], "passed")
            finally:
                if runner.poll() is None:
                    runner.kill()
                    runner.wait()
                for pid in pids:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    @staticmethod
    def process_running(pid):
        # Container init may retain adopted zombies: those cannot execute.
        result = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                                capture_output=True, text=True, timeout=5)
        state = result.stdout.strip()
        return bool(state) and not state.startswith("Z")

    def test_cancellation_during_launch_reaps_child_and_restores_handlers(self):
        original = {number: signal.getsignal(number)
                    for number in (signal.SIGTERM, signal.SIGINT)}
        popen = subprocess.Popen
        launched = []

        def cancel_launch(*args, **kwargs):
            process = popen(*args, **kwargs)
            launched.append(process)
            os.kill(os.getpid(), signal.SIGTERM)
            return process

        command = {"argv": [sys.executable, "-c", "import time; time.sleep(60)"],
                   "cwd": str(self.source), "env": {}, "timeout_seconds": 10}
        with (self.root / "launch.log").open("wb") as log:
            with validation.termination_handler():
                with mock.patch.object(validation.subprocess, "Popen", side_effect=cancel_launch):
                    with self.assertRaises(validation.TerminationRequested):
                        validation.execute(command, log)
        self.assertEqual(len(launched), 1)
        self.assertIsNotNone(launched[0].returncode)
        for number, handler in original.items():
            self.assertEqual(signal.getsignal(number), handler)

    def test_imported_batch_restores_sigterm_handler_on_success_and_error(self):
        handler = signal.getsignal(signal.SIGTERM)
        self.assertEqual(self.run_batch(), 0)
        self.assertEqual(signal.getsignal(signal.SIGTERM), handler)
        self.data["checks"][0]["timeout_seconds"] = 0
        with self.assertRaises(validation.ValidationError):
            self.run_batch()
        self.assertEqual(signal.getsignal(signal.SIGTERM), handler)

    def test_ledger_inside_source_must_not_overwrite_tracked_file(self):
        self.ledger = self.source / "affected.txt"
        with self.assertRaisesRegex(validation.ValidationError, "must be Git-ignored"):
            self.run_batch()
        self.assertEqual((self.source / "affected.txt").read_text(), "initial\n")

    def test_duplicate_keys_and_invalid_manifest_shapes_are_rejected(self):
        self.path.write_text('{"schema": 1, "schema": 1}')
        with self.assertRaisesRegex(validation.ValidationError, "duplicate JSON key"):
            validation.manifest(self.path)
        original = copy.deepcopy(self.data)
        for field, value in (("argv", "echo hello"), ("sources", []), ("env", {"BAD=KEY": "x"}),
                             ("timeout_seconds", True), ("paths", {"source": ["../escape"]}),
                             ("paths", {"source": []}), ("paths", {"unknown": ["affected.txt"]})):
            with self.subTest(field=field, value=value):
                self.data = copy.deepcopy(original)
                self.data["checks"][0][field] = value
                with self.assertRaises(validation.ValidationError):
                    self.run_batch()
        self.assertEqual(self.runs(), [])

    def test_missing_scoped_path_and_duplicate_check_are_rejected(self):
        self.data["checks"][0]["paths"] = {"source": ["missing.txt"]}
        with self.assertRaisesRegex(validation.ValidationError, "scoped path absent"):
            self.run_batch()
        self.data["checks"][0].pop("paths")
        self.data["checks"].append(copy.deepcopy(self.data["checks"][0]))
        with self.assertRaisesRegex(validation.ValidationError, "Duplicate check"):
            self.run_batch()
        self.assertEqual(self.runs(), [])

    def test_corrupt_receipt_is_not_an_imported_pass(self):
        self.ledger.write_text(json.dumps({"schema": 1, "checks": {"one": [
            {"status": "passed", "fingerprint": "incomplete", "returncode": 0}]}}))
        with self.assertRaisesRegex(validation.ValidationError, "Incomplete passing receipt"):
            self.run_batch()
        self.assertEqual(self.runs(), [])


if __name__ == "__main__":
    unittest.main()
