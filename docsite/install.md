---
title: Install Agent-12 (Python 3.10+, optional MLX and Anvil engine)
description: What you need to install to run the Agent-12 local LLM agent benchmark, from judge validation with plain Python to the MLX reference engine and the visual benches.
---

# Install

Agent-12 is a set of Python scripts with no package to install. What you need
depends on which part you run.

## 1. Clone the repo

```bash
git clone https://github.com/nicedreamzapp/agent12.git
cd agent12
```

## 2. Python 3.10 or newer

The judges run the agent's code with the same interpreter that runs the
harness (`sys.executable`). On Python 3.9, a correct answer that uses 3.10
syntax such as `list[str] | None` fails at import and is scored as wrong.
The system `python3` on a clean macOS install is 3.9, so check first:

```bash
python3 --version
```

`validate_judges.py` refuses to run below 3.10. `runner.py` still runs but
prints a warning on stderr and records the interpreter in the result file.
The floor can be changed with `AGENT12_MIN_PYTHON` (see
[Configuration](configuration.md#environment-variables-read-by-agent-12)).

## What each part needs

| You want to | Needs |
|---|---|
| Validate the judges (`validate_judges.py`) | Python 3.10+, standard library only |
| Score any agent CLI (`runner.py --adapter command`) | Python 3.10+ and your agent CLI on `PATH` |
| Reproduce the board rows (`--adapter anvil`) | The Anvil engine (`agent.py`), MLX on Apple silicon, and the model weights listed in `configs/models.json` |
| The DFlash row (`--adapter anvil_dflash`) | Anvil, plus `mlx-dspark` (the config note says 0.14 with mlx 0.32) and the drafter weights |
| Rebuild the leaderboard page (`build_site.py`) | Python, standard library only |
| Visual benches (`furball_bench.py`, `showdown.py`) | `websocket-client`, `ffmpeg` on `PATH`, Brave at its macOS path, and an OpenAI-compatible model server |

### About the Anvil engine

The board rows were produced by the Anvil reference engine, which is **not
in this repo**. `adapters/anvil.py` adds the directory in
`AGENT12_ENGINE_DIR` to `sys.path` and runs `import agent`. Without it, only
judge validation and the `command` adapter work from a fresh clone. This is
listed as a known limit in the README.

### Visual bench dependencies

```bash
python3 -m pip install websocket-client
```

`furball_bench.py` reads screenshots through `ffmpeg` (so it needs no image
library) and launches `/Applications/Brave Browser.app/Contents/MacOS/Brave Browser`.
That path is hard-coded, so these benches run on macOS with Brave installed.

### Scripts that only run on the author's machine

`run_task.sh`, `run_furball_bench.sh`, `finish_furball.sh`, `sweep.sh`,
`glimmer_night.sh`, `run_qwen38_dflash.sh`, `showdown_gen.py` and
`lyric_ab.py` hard-code paths and services on the author's Mac (venvs under
`~/.local/`, a local memory guard, other local apps). They are kept as a
record of how runs were made and will not run elsewhere as they are.

## Building these docs locally

```bash
python3 -m pip install -r requirements-docs.txt
mkdocs serve           # preview at http://127.0.0.1:8000
mkdocs build --strict  # what CI runs
```

The social card plugin needs the Cairo system library (`libcairo2` on
Ubuntu, `brew install cairo` on macOS).
