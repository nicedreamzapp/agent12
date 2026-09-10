#!/usr/bin/env python3
"""Interpreter facts, recorded and enforced.

Every judge runs the agent's solution with `sys.executable`, so the
interpreter that runs the harness is part of the grading conditions, not
a detail of the operator's machine. A solution annotated `list[str] | None`
(PEP 604, Python 3.10+) raises TypeError on 3.9 and is scored as a failure,
while a solution that skipped annotations altogether passes -- the modern
answer is punished for the environment it landed in.

System python3 on a clean macOS install is 3.9, so this is the default
outcome, not an exotic one.

Two consequences, one per entry point:
  runner.py         records `interpreter` in the results, so a run is
                    fully described by its own JSON.
  validate_judges.py refuses to run below MIN_PYTHON, because a judge
                    validated under the wrong interpreter proves nothing.

Override the floor with AGENT12_MIN_PYTHON=3.11 when a suite needs newer
syntax; setting it lower is allowed and recorded, never silent.
"""
import os
import platform
import sys

MIN_PYTHON = (3, 10)


def min_python():
    """The required floor, honouring AGENT12_MIN_PYTHON=X.Y."""
    raw = os.environ.get("AGENT12_MIN_PYTHON", "").strip()
    if not raw:
        return MIN_PYTHON
    try:
        parts = tuple(int(p) for p in raw.split(".")[:2])
    except ValueError:
        raise SystemExit(f"AGENT12_MIN_PYTHON={raw!r} is not a X.Y version")
    if len(parts) != 2:
        raise SystemExit(f"AGENT12_MIN_PYTHON={raw!r} is not a X.Y version")
    return parts


def interpreter_info():
    """What judged this run. Goes verbatim into results/*.json."""
    floor = min_python()
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "executable": sys.executable,
        "min_python_required": ".".join(str(p) for p in floor),
        "meets_min_python": sys.version_info[:2] >= floor,
    }


def _too_old_message(floor):
    want = ".".join(str(p) for p in floor)
    return (
        f"Python {platform.python_version()} is below the required {want}.\n"
        f"  interpreter: {sys.executable}\n"
        "Judges execute the agent's solution with this interpreter, so a\n"
        "correct answer using 3.10+ syntax (PEP 604 `X | None`, match, ...)\n"
        "would be scored as a failure. System python3 on macOS is 3.9.\n"
        f"Re-run with a {want}+ interpreter, or set AGENT12_MIN_PYTHON to\n"
        "the version you actually intend to grade against."
    )


def require_min_python():
    """Hard gate. Used where a wrong interpreter invalidates the result."""
    floor = min_python()
    if sys.version_info[:2] < floor:
        raise SystemExit(_too_old_message(floor))


def warn_min_python():
    """Soft gate: the run proceeds, but never claims the environment was fine."""
    floor = min_python()
    if sys.version_info[:2] < floor:
        print("WARNING: " + _too_old_message(floor).replace("\n", "\n         "),
              file=sys.stderr, flush=True)
