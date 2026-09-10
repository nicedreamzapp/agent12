#!/usr/bin/env python3
"""Smoke-test every judge before it judges anything real.

For each task in each suite:
  known-good reference solution  -> the judge MUST pass it
  known-bad plausible attempt    -> the judge MUST fail it

A judge that fails either direction is broken, and a broken judge is worse
than no judge: it silently converts model skill into noise. This gate is
how we caught the original h3 probe demanding an eviction order that
contradicted its own spec.

Refuses to run below the interpreter floor in envcheck.py: the judges
execute solutions with sys.executable, so validating them on 3.9 says
nothing about how they behave on the 3.10+ syntax models actually write.

Also re-runs every known-good answer with a UTF-8 BOM prepended to the
answer file. The reference solutions are written by the same hand as the
judges, so plain agreement cannot show a judge grading form instead of
meaning; a BOM is the case where it clearly is, since "\ufeff" is not
whitespace and survives .strip(). A judge that fails a correct answer over
an invisible character is converting the agent's editor into its score.

Run: python3 validate_judges.py    (exits non-zero on any mismatch)
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from envcheck import require_min_python  # noqa: E402
from tasks import load_suite  # noqa: E402


BOM = b"\xef\xbb\xbf"


def _snapshot(d):
    return {p: p.read_bytes() for p in d.rglob("*") if p.is_file()}


def outcome(task, solver, root, bom=False):
    """Run one solver against one judge. With bom=True, prepend a UTF-8 BOM
    to every .txt/.json answer file the solver wrote, and return None if it
    wrote none (nothing to say about a task with no answer file)."""
    d = Path(tempfile.mkdtemp(dir=root))
    task.setup(d)
    if task.pin:
        task.pin(d)
    before = _snapshot(d)
    solver(d)
    if bom:
        answers = [p for p in d.rglob("*")
                   if p.is_file() and p.suffix in (".txt", ".json")
                   and before.get(p) != p.read_bytes()]
        if not answers:
            shutil.rmtree(d, ignore_errors=True)
            return None, ""
        for p in answers:
            p.write_bytes(BOM + p.read_bytes())
    try:
        res = task.check(d)
        ok, detail = res if isinstance(res, tuple) else (bool(res), "")
    except Exception as e:  # noqa: BLE001
        ok, detail = False, f"checker crashed: {type(e).__name__}: {e}"
    shutil.rmtree(d, ignore_errors=True)
    return ok, detail


def main():
    # a judge validated under the wrong interpreter proves nothing
    require_min_python()
    root = tempfile.mkdtemp(prefix="agent12-judgeval-")
    bad_judges = 0
    for suite_name in ("easy", "hard"):
        suite = load_suite(suite_name)
        print(f"── {suite_name} ──")
        for task in suite.TASKS:
            good_ok, gd = outcome(task, task.good, root)
            bad_ok, _ = outcome(task, task.bad, root)
            bom_ok, bd = outcome(task, task.good, root, bom=True)
            broken = (not good_ok) or bad_ok or (bom_ok is False)
            if broken:
                bad_judges += 1
            bom_col = "" if bom_ok is None else f" good+BOM={'PASS' if bom_ok else 'FAIL'}"
            detail = gd if (gd and not good_ok) else (bd if bom_ok is False else "")
            print(f"  {'BROKEN' if broken else 'OK':6s} {task.name:26s}"
                  f" good={'PASS' if good_ok else 'FAIL'}"
                  f" bad={'PASS' if bad_ok else 'FAIL'}{bom_col}"
                  + (f"  [{detail}]" if detail else ""))
    shutil.rmtree(root, ignore_errors=True)
    if bad_judges:
        print(f"\n{bad_judges} BROKEN judge(s) — do not run the benchmark.")
        sys.exit(1)
    print("\nAll judges validated: every known-good passes (with or without a BOM),"
          " every known-bad fails.")


if __name__ == "__main__":
    main()
