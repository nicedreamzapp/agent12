"""Command adapter — run ANY agent CLI against the same tasks.

Set AGENT12_CMD to a shell command template; {prompt} is replaced with the
shell-quoted task prompt. The command runs with the sandbox as cwd and
must exit when the episode is done. Examples:

  AGENT12_CMD='my-agent --print {prompt}'
  AGENT12_CMD='claude -p {prompt} --dangerously-skip-permissions'   # comparison lane

Label the entry with AGENT12_MODEL_LABEL so results say what actually ran.
Note: if your CLI reloads model weights per invocation, load time lands in
every task's seconds — report it or keep a server warm.
"""
import os
import shlex
import subprocess


class CommandAdapter:
    def __init__(self):
        self.template = os.environ.get("AGENT12_CMD", "")
        if "{prompt}" not in self.template:
            raise SystemExit("AGENT12_CMD must contain {prompt}")
        self.timeout = int(os.environ.get("AGENT12_CMD_TIMEOUT", "600"))
        self.last_output = ""

    def load(self):
        pass

    def reset(self):
        pass

    def run(self, prompt):
        cmd = self.template.replace("{prompt}", shlex.quote(prompt))
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=self.timeout)
        self.last_output = r.stdout + ("\nSTDERR:\n" + r.stderr if r.stderr else "")

    def info(self):
        return {"model": os.environ.get("AGENT12_MODEL_LABEL", "unlabeled"),
                "dialect": "n/a",
                "backend": "command",
                "prompt_file": ""}

    def close(self):
        pass
