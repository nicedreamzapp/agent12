#!/usr/bin/env python3
"""Check every community submission before it reaches the site.

A submission is one JSON file in submissions/. This refuses anything that would put a
number on the board without a machine behind it, a metric the suite does not define, or
a value outside that metric's range. It never repairs a file; it says what is wrong and
exits non-zero so CI can block the merge.

    python tools/validate_submissions.py            check them all
    python tools/validate_submissions.py <file>     check one
"""
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ["suite", "model", "hardware", "metrics", "run_utc", "submitted_by"]
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def registry():
    with io.open(os.path.join(ROOT, "suites", "registry.json"), encoding="utf-8") as f:
        r = json.load(f)
    return r, {s["id"]: s for s in r["suites"]}


def check(path, reg, suites):
    """Return a list of problems with this file. Empty list means it is good."""
    name = os.path.basename(path)
    if name.startswith("EXAMPLE"):
        return []                      # the template is meant to stay unfilled
    bad = []
    try:
        with io.open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        return [f"not readable JSON: {e}"]

    for k in REQUIRED:
        if not d.get(k):
            bad.append(f"missing required field: {k}")
    if bad:
        return bad

    suite = suites.get(d["suite"])
    if not suite:
        return [f"unknown suite '{d['suite']}', see suites/registry.json"]

    if not UTC.match(str(d["run_utc"])):
        bad.append(f"run_utc must look like 2026-10-30T09:15:00Z, got '{d['run_utc']}'")

    if not re.search(r"\d+\s*GB", str(d["hardware"]), re.I):
        bad.append("hardware must name the memory, e.g. 'Apple M4 Pro, 48 GB unified memory'")

    if not isinstance(d["metrics"], dict) or not d["metrics"]:
        return bad + ["metrics must be an object with at least one value"]

    for k, v in d["metrics"].items():
        if k not in suite["metrics"]:
            bad.append(f"metric '{k}' is not defined for suite {suite['id']} "
                       f"(allowed: {', '.join(suite['metrics'])})")
            continue
        spec = reg["metrics"][k]
        if not isinstance(v, (int, float)):
            bad.append(f"metric '{k}' must be a number, got {type(v).__name__}")
            continue
        lo, hi = spec["range"]
        if not lo <= v <= hi:
            bad.append(f"metric '{k}' = {v} is outside {lo}..{hi} {spec['unit']}")

    if d.get("n_items") is not None and not isinstance(d["n_items"], int):
        bad.append("n_items must be a whole number of test items")
    return bad


def main():
    reg, suites = registry()
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "submissions", "*.json")))
    if not files:
        print("no submissions yet")
        return 0

    problems = 0
    for p in files:
        bad = check(p, reg, suites)
        tag = "ok  " if not bad else "FAIL"
        print(f"{tag} {os.path.basename(p)}")
        for b in bad:
            print(f"       {b}")
        problems += len(bad)

    print(f"\n{len(files)} file(s), {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
