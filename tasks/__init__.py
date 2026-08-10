"""Task registry for Agent-12.

A task is four things:
  setup(d)   — build the starting filesystem state in sandbox dir d
  prompt     — what the agent is told (nothing else)
  check(d)   — filesystem/subprocess judge; returns bool or (bool, detail)
  good/bad   — reference solutions used by validate_judges.py: good must
               PASS the judge, bad is a plausible wrong attempt that must
               FAIL it. A task without a validated judge does not ship.
"""
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Task:
    name: str
    prompt: str
    setup: Callable
    check: Callable
    good: Callable
    bad: Callable
    pin: Optional[Callable] = None  # runs after setup (e.g. hash-pin test files)


def load_suite(name):
    if name == "easy":
        from . import easy
        return easy
    if name == "hard":
        from . import hard
        return hard
    raise SystemExit(f"unknown suite: {name!r} (expected easy|hard)")
