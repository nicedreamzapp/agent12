# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems.

Report them privately through GitHub: go to the **Security** tab of this repo and click **Report a vulnerability** ([direct link](https://github.com/nicedreamzapp/agent12/security/advisories/new)). Only the maintainer sees the report.

Helpful details: what you found, how to reproduce it, which commit, your OS and Python version, and the adapter and model you were running.

I aim to reply within 3 days and to ship a fix or a clear plan within 30 days, depending on severity. You will be credited in the advisory unless you ask not to be.

## Supported versions

Fixes go into the latest code on `main`. Please update before reporting if you are on an older commit.

## What matters most here

The parts where a mistake could hurt someone:

- the sandboxes in `runner.py`, which are plain folders under `sandboxes/`, while the agent under test can run commands with your user's permissions
- `adapters/command.py`, which builds a shell command from `AGENT12_CMD` and the task prompt
- the judges in `tasks/easy.py` and `tasks/hard.py`, which run model-written code in a subprocess
- the visual benches in `furball_bench.py` and `showdown.py`, which open model-written HTML in a headless Brave with a remote debugging port
