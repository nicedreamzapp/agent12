"""Anvil adapter — runs tasks through the lean native agent engine.

The engine is the ~550-token-system-prompt terminal agent (Anvil). Point
AGENT12_ENGINE_DIR at the directory containing its agent.py; all AGENT_*
environment variables (model, dialect, backend, base URL, prompt file)
are honored exactly as the interactive CLI honors them, so a benchmark
run is the same code path a user types into.
"""
import contextlib
import io
import os
import sys

ENGINE_DIR = os.path.expanduser(
    os.environ.get("AGENT12_ENGINE_DIR", "~/Desktop/PROJECTS/Local AI Setup/agent"))


class AnvilAdapter:
    def __init__(self):
        self.agent = None
        self.engine = None
        self.last_output = ""

    def load(self):
        sys.path.insert(0, ENGINE_DIR)
        import agent  # env must already be set — agent.py reads it at import
        self.agent = agent
        if agent.BACKEND == "http":
            self.engine = agent.HTTPEngine(agent.MODEL_DEFAULT)
        else:
            agent.acquire_seat()
            self.engine = agent.MLXEngine(agent.MODEL_DEFAULT)

    def reset(self):
        self.engine.reset()

    def run(self, prompt):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.agent.agent_turn(self.engine, prompt, quiet=True)
        self.last_output = buf.getvalue()

    def info(self):
        return {"model": self.agent.MODEL_DEFAULT,
                "dialect": self.agent.DIALECT,
                "backend": self.agent.BACKEND,
                "prompt_file": self.agent.PROMPT_FILE}

    def close(self):
        with contextlib.suppress(Exception):
            self.agent.release_seat()
