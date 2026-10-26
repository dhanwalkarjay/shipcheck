#!/usr/bin/env python3
"""ShipCheck risk scanner.

Reads a unified git diff and reports deterministic risk signals (migrations,
auth changes, dependency changes, deleted/disabled tests, leaked secrets, ...).
No network, no model calls, standard library only.

Usage:
  risk_scan.py --base main --head HEAD            # git diff base...head
  risk_scan.py --diff-file change.diff            # a saved diff
  git diff main...HEAD | risk_scan.py -           # stdin
  risk_scan.py --base main --format md            # markdown instead of JSON
  risk_scan.py --base main --fail-on high         # exit 2 in CI if risk >= high
"""
import argparse
import json
import re
import subprocess
import sys

LEVELS = {"low": 1, "medium": 2, "high": 3}

TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|e2e|cypress)/"
    r"|\.(test|spec)\.[cm]?[jt]sx?$"
    r"|_test\.(py|go|rb)$"
    r"|(^|/)test_[^/]+\.py$"
    r"|Test\.(java|kt)$"
)
MIGRATION_PATH = re.compile(
    r"(^|/)(migrations?|alembic|db/migrate|prisma/migrations)/"
    r"|\.sql$|(^|/)schema\.(prisma|rb)$"
)
AUTH_PATH = re.compile(
    r"(?i)(auth|login|logout|session|permission|rbac|acl|oauth|jwt|password|"
    r"crypto|security|credential|token)"
)
DEPS_PATH = re.compile(
    r"(^|/)(package(-lock)?\.json|yarn\.lock|pnpm-lock\.yaml|requirements[^/]*\.txt|"
    r"pyproject\.toml|poetry\.lock|Pipfile(\.lock)?|go\.(mod|sum)|Cargo\.(toml|lock)|"
    r"Gemfile(\.lock)?|pom\.xml|build\.gradle(\.kts)?|composer\.(json|lock))$"
)
INFRA_PATH = re.compile(
    r"(^|/)(\.github/workflows/|Dockerfile[^/]*|docker-compose[^/]*|Jenkinsfile|"
    r"\.gitlab-ci\.yml|k8s/|helm/|terraform/)|\.tf$|(^|/)\.env[^/]*$"
)
DOC_PATH = re.compile(r"(?i)\.(md|rst|txt)$|(^|/)docs?/")

SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"), "private key"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (
        re.compile(
            r"(?i)(api[_-]?key|secret|passwd|password|token)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
        ),
        "hard-coded credential",
    ),
]
DISABLED_TEST = re.compile(
    r"\.only\(|\b(xit|xdescribe|xtest)\(|\b(it|test|describe)\.skip\(|"
    r"@pytest\.mark\.(skip|xfail)|@unittest\.skip|\bt\.Skip\(|@Disabled|@Ignore"
)
ASSERTION = re.compile(r"\b(assert|expect|should|assertEqual|assertTrue|assertThat)\b")
DEBUG_LEFTOVER = re.compile(
    r"\bconsole\.(log|debug)\(|\bdebugger\b|\bpdb\.set_trace\(|\bbreakpoint\(\)|"
    r"^\s*print\("
)
TODO_MARK = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
SWALLOWED_ERROR = re.compile(
    r"except\b[^:]*:\s*pass\b|catch\s*\([^)]*\)\s*\{\s*\}"
)
EXCEPT_LINE = re.compile(r"^\s*except\b[^:]*:\s*$")
PASS_LINE = re.compile(r"^\s*pass\s*$")
LINT_BYPASS = re.compile(
    r"eslint-disable|# noqa|# type:\s*ignore|@ts-ignore|@ts-nocheck|# pylint: disable"
)
AUTH_BYPASS = re.compile(
    r"(?i)verify\s*=\s*False|rejectUnauthorized\s*:\s*false|"
    r"(skip|disable|bypass)[_ -]?(auth|authentication|permission|csrf)"
)


def parse_diff(text):
    """Parse a unified diff into {path: file_info}."""
    files = {}
    cur = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*?) b/(.*)$", line)
            path = m.group(2) if m else line.split(" b/")[-1]
            cur = {
                "path": path,
                "status": "modified",
                "added": 0,
                "removed": 0,
                "added_lines": [],
                "removed_lines": [],
                "binary": False,
            }
            files[path] = cur
        elif cur is None:
            continue
        elif line.startswith("new file mode"):
            cur["status"] = "added"
        elif line.startswith("deleted file mode"):
            cur["status"] = "deleted"
        elif line.startswith("rename to "):
            cur["status"] = "renamed"
        elif line.startswith("Binary files") or line.startswith("GIT binary patch"):
            cur["binary"] = True
        elif line.startswith("+++") or line.startswith("---"):
            continue
        elif line.startswith("+"):
            cur["added"] += 1
            cur["added_lines"].append(line[1:])
        elif line.startswith("-"):
            cur["removed"] += 1
            cur["removed_lines"].append(line[1:])
    return files


def is_test(path):
    return bool(TEST_PATH.search(path))


def scan(files):
    signals = []

    def add(sid, severity, message, paths):
        if paths:
            signals.append(
                {
                    "id": sid,
                    "severity": severity,
                    "message": message,
                    "files": sorted(set(paths))[:15],
                    "count": len(set(paths)),
                }
            )

    all_paths = list(files)
    src_files = [
        p for p in all_paths if not is_test(p) and not DOC_PATH.search(p)
    ]

    add("migration", "high", "Database schema or migration files changed",
        [p for p in all_paths if MIGRATION_PATH.search(p)])
    add("auth-path", "high", "Files in auth/security-sensitive paths changed",
        [p for p in src_files if AUTH_PATH.search(p)])
    add("deps", "medium", "Dependency manifest or lockfile changed",
        [p for p in all_paths if DEPS_PATH.search(p)])
    add("infra", "medium", "CI, container, infra or env config changed",
        [p for p in all_paths if INFRA_PATH.search(p)])

    deleted_tests = [p for p in all_paths if is_test(p) and files[p]["status"] == "deleted"]
    add("deleted-tests", "high", "Test files were deleted", deleted_tests)

    weakened = []
    for p in all_paths:
        f = files[p]
        if is_test(p) and f["status"] != "deleted":
            rem = sum(1 for l in f["removed_lines"] if ASSERTION.search(l))
            add_ = sum(1 for l in f["added_lines"] if ASSERTION.search(l))
            if rem > add_ and rem >= 2:
                weakened.append(p)
    add("weakened-tests", "medium", "Tests lost more assertions than they gained", weakened)

    def hits(regex, only_src=False, only_tests=False):
        out = []
        for p, f in files.items():
            if only_src and (is_test(p) or DOC_PATH.search(p)):
                continue
            if only_tests and not is_test(p):
                continue
            if any(regex.search(l) for l in f["added_lines"]):
                out.append(p)
        return out

    add("disabled-tests", "high", "Tests were skipped, focused (.only) or disabled",
        hits(DISABLED_TEST))
    add("auth-bypass", "high", "Added code that disables TLS verification or auth checks",
        hits(AUTH_BYPASS, only_src=True))

    for pat, label in SECRET_PATTERNS:
        add("secret", "high", "Possible secret added (" + label + ")",
            hits(pat))

    swallowed = hits(SWALLOWED_ERROR, only_src=True)
    for p_, f_ in files.items():
        if is_test(p_) or DOC_PATH.search(p_):
            continue
        ls = f_["added_lines"]
        if any(EXCEPT_LINE.match(a) and PASS_LINE.match(b) for a, b in zip(ls, ls[1:])):
            swallowed.append(p_)
    add("swallowed-errors", "medium", "Errors are caught and silently ignored", swallowed)
    add("lint-bypass", "low", "Linter/type-checker suppressions added", hits(LINT_BYPASS))
    add("debug-leftovers", "low", "Debug statements left in non-test code",
        hits(DEBUG_LEFTOVER, only_src=True))
    add("todo-markers", "low", "New TODO/FIXME/HACK markers", hits(TODO_MARK))

    src_changed = sum(files[p]["added"] + files[p]["removed"] for p in src_files)
    tests_touched = [p for p in all_paths if is_test(p)]
    if src_changed >= 40 and not tests_touched:
        add("no-tests", "medium",
            f"{src_changed} source lines changed but no test files were touched",
            src_files)

    total = sum(f["added"] + f["removed"] for f in files.values())
    if total > 800 or len(files) > 30:
        signals.append(
            {"id": "large-diff", "severity": "medium",
             "message": f"Large change ({total} lines across {len(files)} files): hard to review",
             "files": [], "count": len(files)}
        )
    elif total > 400:
        signals.append(
            {"id": "large-diff", "severity": "low",
             "message": f"Sizeable change ({total} lines across {len(files)} files)",
             "files": [], "count": len(files)}
        )
    return signals


def overall(signals):
    lv = [LEVELS[s["severity"]] for s in signals]
    if any(v == 3 for v in lv):
        return "high"
    if any(v == 2 for v in lv) or sum(1 for v in lv if v == 1) >= 3:
        return "medium"
    return "low"


def build_report(diff_text):
    files = parse_diff(diff_text)
    signals = scan(files)
    signals.sort(key=lambda s: -LEVELS[s["severity"]])
    tests = [p for p in files if is_test(p)]
    return {
        "risk": overall(signals),
        "stats": {
            "files_changed": len(files),
            "lines_added": sum(f["added"] for f in files.values()),
            "lines_removed": sum(f["removed"] for f in files.values()),
            "test_files_changed": len(tests),
            "source_files_changed": len(files) - len(tests),
        },
        "signals": signals,
        "files": [
            {"path": p, "status": f["status"], "added": f["added"],
             "removed": f["removed"], "is_test": is_test(p)}
            for p, f in files.items()
        ],
    }


def to_markdown(report):
    s = report["stats"]
    out = [
        f"**Overall risk: {report['risk'].upper()}**  ",
        f"{s['files_changed']} files (+{s['lines_added']} / -{s['lines_removed']}), "
        f"{s['test_files_changed']} test file(s) touched.",
        "",
    ]
    if not report["signals"]:
        out.append("No risk signals detected.")
    else:
        out += ["| Severity | Signal | Files |", "|---|---|---|"]
        for sig in report["signals"]:
            files = ", ".join(f"`{p}`" for p in sig["files"][:5]) or "-"
            if sig["count"] > 5:
                files += f" (+{sig['count'] - 5} more)"
            out.append(f"| {sig['severity']} | {sig['message']} | {files} |")
    return "\n".join(out)


def get_diff(args):
    if args.diff_file:
        if args.diff_file == "-":
            return sys.stdin.read()
        with open(args.diff_file, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    cmd = ["git", "-C", args.repo, "diff", "--no-color", "-U0",
           f"{args.base}...{args.head}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        # fall back to a plain two-dot diff (e.g. unrelated histories, shallow clone)
        cmd[-1] = f"{args.base}..{args.head}"
        res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit("git diff failed: " + res.stderr.strip())
    return res.stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description="ShipCheck deterministic risk scan")
    ap.add_argument("source", nargs="?", help="use '-' to read a diff from stdin")
    ap.add_argument("--repo", default=".", help="path to the git repository")
    ap.add_argument("--base", default="main", help="base branch/commit")
    ap.add_argument("--head", default="HEAD", help="head branch/commit")
    ap.add_argument("--diff-file", help="read a saved unified diff instead of running git")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    ap.add_argument("--fail-on", choices=list(LEVELS), help="exit 2 if risk >= level")
    args = ap.parse_args(argv)
    if args.source == "-":
        args.diff_file = "-"

    report = build_report(get_diff(args))
    print(json.dumps(report, indent=2) if args.format == "json" else to_markdown(report))
    if args.fail_on and LEVELS[report["risk"]] >= LEVELS[args.fail_on]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
