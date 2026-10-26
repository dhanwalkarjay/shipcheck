#!/usr/bin/env python3
"""ShipCheck claim checker.

Takes what an agent SAID it did (its final message or PR description) and the
diff of what it actually did, extracts checkable claims, and compares them.
Standard library only; no network, no model calls.

Verdicts per claim:
  supported     the diff backs the claim
  contradicted  the diff shows the opposite
  unverified    the diff alone cannot prove it (run something to find out)

Usage:
  claim_check.py --summary-file said.txt --base main --head HEAD
  claim_check.py --summary-file said.txt --diff-file change.diff --format md
  claim_check.py --summary-file said.txt --base main --fail-on-contradicted
"""
import argparse
import json
import re
import subprocess
import sys

TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|e2e)/|\.(test|spec)\.[cm]?[jt]sx?$"
    r"|_test\.(py|go|rb)$|(^|/)test_[^/]+\.py$"
)
DEPS_PATH = re.compile(
    r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|Pipfile|go\.mod|"
    r"Cargo\.toml|Gemfile|pom\.xml|build\.gradle(\.kts)?|composer\.json)$"
)
DEP_LINE = re.compile(
    r"\"[@\w/.-]+\"\s*:\s*\"[\^~>=<]*\d+(\.\d+)*[^\"]*\""   # package.json style
    r"|^[A-Za-z0-9_.-]+\s*(==|>=|<=|~=|>|<)\s*\d"             # requirements.txt style
    r"|^[A-Za-z0-9_.-]+\s*=\s*\"[\^~]?\d+(\.\d+)*\""         # Cargo/pyproject style
)
SECRET = re.compile(
    r"AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|(?i:(api[_-]?key|secret|passwd|password|token))\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
)
TEST_SIGNAL = re.compile(r"\b(assert|expect|should|assertEqual|assertTrue)\b|\b(def test_|it\(|test\()")
DISABLED = re.compile(r"\.skip\(|@pytest\.mark\.(skip|xfail)|\bxit\(|@unittest\.skip|\.only\(")
DEFINITION = re.compile(r"^\s*(def |class |function |export |public |async function )")


def parse_diff(text):
    files, cur = {}, None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*?) b/(.*)$", line)
            path = m.group(2) if m else line.split(" b/")[-1]
            cur = {"status": "modified", "added": [], "removed": []}
            files[path] = cur
        elif cur is None:
            continue
        elif line.startswith("new file mode"):
            cur["status"] = "added"
        elif line.startswith("deleted file mode"):
            cur["status"] = "deleted"
        elif line.startswith(("+++", "---")):
            continue
        elif line.startswith("+"):
            cur["added"].append(line[1:])
        elif line.startswith("-"):
            cur["removed"].append(line[1:])
    return files


def is_test(p):
    return bool(TEST_PATH.search(p))


def sentence_of(text, match):
    """Return the sentence containing the match. A '.' only ends a sentence
    when followed by whitespace or end of text, so 'api.js' stays intact."""
    bounds = [m.end() for m in re.finditer(r"[.!?](?=\s|$)|\n", text)]
    start = max([b for b in bounds if b <= match.start()] or [0])
    end = min([b for b in bounds if b >= match.end()] or [len(text)])
    return " ".join(text[start:end].split())[:200]


def claim(kind, text, verdict, evidence):
    return {"type": kind, "claim": text, "verdict": verdict, "evidence": evidence}


def check(summary, files):
    out = []
    paths = list(files)
    test_files = [p for p in paths if is_test(p)]

    # 1. "added/covered by tests"
    for m in re.finditer(r"(?i)\b(added|wrote|includes?|with|covered by)\s+(new\s+|unit\s+|regression\s+)?tests?\b", summary):
        real = [p for p in test_files if files[p]["status"] != "deleted"
                and any(TEST_SIGNAL.search(l) for l in files[p]["added"])
                and not all(DISABLED.search(l) or not l.strip() or l.strip() == "pass"
                            for l in files[p]["added"])]
        if real:
            out.append(claim("added-tests", sentence_of(summary, m), "supported",
                             "New test code with assertions in: " + ", ".join(real)))
        else:
            why = "no test file with new assertions in the diff"
            if any(files[p]["status"] == "deleted" for p in test_files):
                why += "; test files were deleted: " + ", ".join(
                    p for p in test_files if files[p]["status"] == "deleted")
            skipped = [p for p in test_files if any(DISABLED.search(l) for l in files[p]["added"])]
            if skipped:
                why += "; tests were skipped in: " + ", ".join(skipped)
            out.append(claim("added-tests", sentence_of(summary, m), "contradicted", why))
        break

    # 2. "N tests passing"
    m = re.search(
        r"(?i)\b\d+\s*/\s*\d+\s*(tests?\s*)?(are\s+)?(passing|passed|pass)\b"
        r"|\b(all\s+)?(\d+\s+)?(unit\s+|new\s+)?tests?\s+(are\s+)?(now\s+)?(all\s+)?(passing|passed|pass|green)\b",
        summary)
    if m:
        warn = []
        if any(files[p]["status"] == "deleted" for p in test_files):
            warn.append("test files were deleted in this change")
        if any(DISABLED.search(l) for p in test_files for l in files[p]["added"]):
            warn.append("tests were skipped or focused in this change")
        ev = "The diff cannot show test results. Run the test command and compare the count."
        if warn:
            ev += " Caution: " + "; ".join(warn) + ", so a green run may hide missing coverage."
        out.append(claim("tests-pass", sentence_of(summary, m), "unverified", ev))

    # 3. "no new dependencies"
    m = re.search(r"(?i)\b(no\s+(new\s+)?(dependenc(y|ies)|deps|packages?)|dependenc(y|ies)\s+(are\s+|is\s+)?(untouched|unchanged)|without\s+(adding|new)\s+dependenc)", summary)
    if m:
        added = [(p, l.strip()) for p in paths if DEPS_PATH.search(p)
                 for l in files[p]["added"] if DEP_LINE.search(l.strip())]
        if added:
            out.append(claim("no-new-deps", sentence_of(summary, m), "contradicted",
                             "Dependency-like lines added: " + "; ".join(f"{p}: {l[:80]}" for p, l in added[:4])))
        else:
            out.append(claim("no-new-deps", sentence_of(summary, m), "supported",
                             "No dependency lines added in manifest files."))

    # 4. "no hard-coded secrets"
    m = re.search(r"(?i)\bno\s+(hard-?coded\s+)?(secrets?|credentials?|api\s*keys?)\b|nothing\s+sensitive", summary)
    if m:
        hit = [p for p in paths if any(SECRET.search(l) for l in files[p]["added"])]
        if hit:
            out.append(claim("no-secrets", sentence_of(summary, m), "contradicted",
                             "Secret-like string added in: " + ", ".join(hit)))
        else:
            out.append(claim("no-secrets", sentence_of(summary, m), "supported",
                             "No secret-like strings found in added lines."))

    # 5. "only touched X"
    m = re.search(r"(?i)\bonly\s+(touch(es|ed)|chang(es|ed)|modif(y|ies|ied)|affect(s|ed))\s+`?([\w./@-]+)`?", summary)
    if m:
        target = m.group(6).rstrip(".,;:")
        others = [p for p in paths if target not in p]
        if others:
            out.append(claim("scope-only", sentence_of(summary, m), "contradicted",
                             f"Files outside `{target}` also changed: " + ", ".join(others[:6])))
        else:
            out.append(claim("scope-only", sentence_of(summary, m), "supported",
                             f"Every changed file matches `{target}`."))

    # 6. "no breaking changes / backwards compatible"
    m = re.search(r"(?i)\bno\s+breaking\s+changes?|backwards?[- ]compatible|non-breaking", summary)
    if m:
        removed_defs = [(p, l.strip()) for p in paths if not is_test(p)
                        for l in files[p]["removed"] if DEFINITION.match(l)]
        migr = [p for p in paths if p.endswith(".sql") or "migrations" in p]
        if removed_defs:
            out.append(claim("no-breaking", sentence_of(summary, m), "unverified",
                             "Definitions were removed or changed: " + "; ".join(
                                 f"{p}: {l[:60]}" for p, l in removed_defs[:4]) + ". Check callers."))
        elif migr:
            out.append(claim("no-breaking", sentence_of(summary, m), "unverified",
                             "A schema change is included (" + ", ".join(migr[:3]) + "); check it is backward compatible."))
        else:
            out.append(claim("no-breaking", sentence_of(summary, m), "unverified",
                             "No removed definitions found, but the diff cannot prove compatibility."))

    # 7. "removed debug/unused"
    m = re.search(r"(?i)\b(removed|deleted|cleaned up)\s+(the\s+)?(debug|console\.log|unused|dead)", summary)
    if m:
        left = [p for p in paths if not is_test(p) and any(
            re.search(r"console\.log\(|\bdebugger\b|pdb\.set_trace\(|breakpoint\(\)", l) for l in files[p]["added"])]
        out.append(claim("removed-debug", sentence_of(summary, m),
                         "contradicted" if left else "supported",
                         ("Debug statements still added in: " + ", ".join(left)) if left
                         else "No new debug statements in added lines."))
    return out


def get_diff(args):
    if args.diff_file:
        with open(args.diff_file, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    for rng in (f"{args.base}...{args.head}", f"{args.base}..{args.head}"):
        res = subprocess.run(["git", "-C", args.repo, "diff", "--no-color", "-U0", rng],
                             capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout
    sys.exit("git diff failed: " + res.stderr.strip())


def to_markdown(claims):
    if not claims:
        return "No checkable claims were found in the summary."
    order = {"contradicted": 0, "unverified": 1, "supported": 2}
    rows = sorted(claims, key=lambda c: order[c["verdict"]])
    out = ["| Verdict | Claim | Evidence |", "|---|---|---|"]
    for c in rows:
        out.append(f"| {c['verdict']} | {c['claim']} | {c['evidence']} |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify an agent's claims against its diff")
    ap.add_argument("--summary-file", required=True, help="text file ('-' for stdin) with what the agent said")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", default="main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--diff-file")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    ap.add_argument("--fail-on-contradicted", action="store_true")
    args = ap.parse_args(argv)

    summary = sys.stdin.read() if args.summary_file == "-" else open(
        args.summary_file, encoding="utf-8", errors="replace").read()
    claims = check(summary, parse_diff(get_diff(args)))
    counts = {k: sum(1 for c in claims if c["verdict"] == k)
              for k in ("supported", "contradicted", "unverified")}
    if args.format == "json":
        print(json.dumps({"counts": counts, "claims": claims}, indent=2))
    else:
        print(f"**{counts['contradicted']} contradicted · {counts['unverified']} unverified · "
              f"{counts['supported']} supported**\n")
        print(to_markdown(claims))
    return 2 if args.fail_on_contradicted and counts["contradicted"] else 0


if __name__ == "__main__":
    sys.exit(main())
