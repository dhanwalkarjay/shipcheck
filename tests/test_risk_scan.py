import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "pr-trust-report", "scripts")
sys.path.insert(0, SCRIPT)
import risk_scan  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "risky.diff")


def ids(report):
    return {s["id"] for s in report["signals"]}


class RiskyDiffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8") as fh:
            cls.report = risk_scan.build_report(fh.read())

    def test_overall_is_high(self):
        self.assertEqual(self.report["risk"], "high")

    def test_expected_signals(self):
        expected = {
            "migration", "auth-path", "deleted-tests", "disabled-tests",
            "auth-bypass", "secret", "deps", "swallowed-errors",
            "debug-leftovers", "todo-markers",
        }
        self.assertTrue(expected <= ids(self.report), ids(self.report))

    def test_stats(self):
        self.assertEqual(self.report["stats"]["files_changed"], 6)
        self.assertEqual(self.report["stats"]["test_files_changed"], 2)

    def test_high_signals_sorted_first(self):
        sev = [s["severity"] for s in self.report["signals"]]
        self.assertEqual(sev[0], "high")
        self.assertEqual(sev[-1], "low")


class CleanDiffTests(unittest.TestCase):
    DIFF = (
        "diff --git a/src/util.py b/src/util.py\n"
        "--- a/src/util.py\n+++ b/src/util.py\n"
        "@@ -1,1 +1,2 @@\n def f():\n+    return 1\n"
        "diff --git a/tests/test_util.py b/tests/test_util.py\n"
        "--- a/tests/test_util.py\n+++ b/tests/test_util.py\n"
        "@@ -1,1 +1,2 @@\n def test_f():\n+    assert f() == 1\n"
    )

    def test_clean_change_is_low_risk(self):
        report = risk_scan.build_report(self.DIFF)
        self.assertEqual(report["risk"], "low")
        self.assertEqual(report["signals"], [])

    def test_source_without_tests_flagged(self):
        added = "".join(f"+x{i} = {i}\n" for i in range(60))
        diff = (
            "diff --git a/src/big.py b/src/big.py\n--- a/src/big.py\n+++ b/src/big.py\n"
            "@@ -0,0 +1,60 @@\n" + added
        )
        report = risk_scan.build_report(diff)
        self.assertIn("no-tests", ids(report))
        self.assertEqual(report["risk"], "medium")

    def test_doc_only_change_not_flagged_as_no_tests(self):
        added = "".join(f"+line {i}\n" for i in range(80))
        diff = (
            "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n"
            "@@ -0,0 +1,80 @@\n" + added
        )
        self.assertNotIn("no-tests", ids(risk_scan.build_report(diff)))

    def test_empty_diff(self):
        report = risk_scan.build_report("")
        self.assertEqual(report["risk"], "low")
        self.assertEqual(report["stats"]["files_changed"], 0)


class GitIntegrationTests(unittest.TestCase):
    def run_git(self, cwd, *args):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    def test_cli_against_real_repo(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_git(d, "init", "-q", "-b", "main")
            self.run_git(d, "config", "user.email", "t@t.t")
            self.run_git(d, "config", "user.name", "t")
            with open(os.path.join(d, "a.txt"), "w") as fh:
                fh.write("one\n")
            self.run_git(d, "add", "-A")
            self.run_git(d, "commit", "-qm", "base")
            self.run_git(d, "checkout", "-qb", "feat")
            os.makedirs(os.path.join(d, "migrations"))
            with open(os.path.join(d, "migrations", "001.sql"), "w") as fh:
                fh.write("ALTER TABLE t ADD COLUMN c INT;\n")
            self.run_git(d, "add", "-A")
            self.run_git(d, "commit", "-qm", "feat")

            proc = subprocess.run(
                [sys.executable, os.path.join(SCRIPT, "risk_scan.py"),
                 "--repo", d, "--base", "main", "--head", "feat", "--fail-on", "high"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 2, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["risk"], "high")
            self.assertIn("migration", ids(data))


if __name__ == "__main__":
    unittest.main()
