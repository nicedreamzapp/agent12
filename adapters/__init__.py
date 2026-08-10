"""Agent adapters — the seam that keeps the benchmark harness-agnostic.

An adapter wraps one way of running an agent. The runner guarantees:
  - the process cwd is the task sandbox before run() is called
  - reset() is called between tasks (fresh conversation, same loaded model)

Adapter contract:
  load()            — load the model / start the engine (called once)
  reset()           — wipe conversation state between tasks
  run(prompt)       — run one agent episode to completion in cwd
  info() -> dict    — {"model": ..., "dialect": ..., "prompt_file": ...}
  close()           — release seats/leases
"""


def load_adapter(name):
    if name == "anvil":
        from .anvil import AnvilAdapter
        return AnvilAdapter()
    if name == "command":
        from .command import CommandAdapter
        return CommandAdapter()
    raise SystemExit(f"unknown adapter: {name!r} (expected anvil|command)")
