#!/usr/bin/env python3
"""Smoke-test every judge before it judges anything real.

For each task in each suite:
  known-good reference solution  -> the judge MUST pass it
  known-bad plausible attempt    -> the judge MUST fail it

A judge that fails either direction is broken, and a broken judge is worse
than no judge: it silently converts model skill into noise. This gate is
how we caught the original h3 probe demanding an eviction order that
contradicted its own spec.

Run: python3 validate_judges.py    (exits non-zero on any mismatch)
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tasks import load_suite  # noqa: E402


def outcome(task, solver, root):
    d = Path(tempfile.mkdtemp(dir=root))
    task.setup(d)
    if task.pin:
        task.pin(d)
    solver(d)
    try:
        res = task.check(d)
        ok, detail = res if isinstance(res, tuple) else (bool(res), "")
    except Exception as e:  # noqa: BLE001
        ok, detail = False, f"checker crashed: {type(e).__name__}: {e}"
    shutil.rmtree(d, ignore_errors=True)
    return ok, detail


def main():
    root = tempfile.mkdtemp(prefix="agent12-judgeval-")
    bad_judges = 0
    for suite_name in ("easy", "hard"):
        suite = load_suite(suite_name)
        print(f"── {suite_name} ──")
        for task in suite.TASKS:
            good_ok, gd = outcome(task, task.good, root)
            bad_ok, _ = outcome(task, task.bad, root)
            verdict = "OK" if (good_ok and not bad_ok) else "BROKEN"
            if verdict == "BROKEN":
                bad_judges += 1
            print(f"  {verdict:6s} {task.name:26s} good={'PASS' if good_ok else 'FAIL'}"
                  f" bad={'PASS' if bad_ok else 'FAIL'}"
                  + (f"  [{gd}]" if gd and not good_ok else ""))
    shutil.rmtree(root, ignore_errors=True)
    if bad_judges:
        print(f"\n{bad_judges} BROKEN judge(s) — do not run the benchmark.")
        sys.exit(1)
    print("\nAll judges validated: every known-good passes, every known-bad fails.")


if __name__ == "__main__":
    main()
