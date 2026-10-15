---
title: Agent-12 configuration, every flag, environment variable and config field
description: Reference for Agent-12's runner.py flags, AGENT12_* and AGENT_* environment variables, configs/models.json, site/meta.json, the result JSON, and the visual bench commands, read from the source.
---

# Configuration

Everything on this page was read from the source. Where a setting is only
passed through to the Anvil engine, which is not in this repo, the page says
what Agent-12 does with it and marks the engine's behavior **TODO-VERIFY**.

## `runner.py`

```text
python3 runner.py --suite easy|hard --run RUN_NAME
                  [--adapter anvil|anvil_dflash|command]
                  [--model KEY] [--config PATH]
```

| Flag | Required | Default | What the code does |
|---|---|---|---|
| `--suite` | yes | none | `easy` (12 tasks) or `hard` (8 tasks). |
| `--run` | yes | none | Name of the run. Output goes to `results/<run>.json`, `logs/<run>/` and `sandboxes/<run>/`. Reusing a name overwrites them. |
| `--adapter` | no | `anvil` | `anvil`, `anvil_dflash` or `command`. Ignored when `--model` is given and that entry has an `adapter` field. |
| `--model` | no | empty | A key in the config file. Its `env` block is applied before the adapter loads. Unknown keys exit with `model 'KEY' not in PATH`. |
| `--config` | no | `configs/models.json` | Only read when `--model` is set. |

Order of operations, which decides who wins when the same variable is set
twice:

1. Prints a warning on stderr if Python is below the floor.
2. If `--model` is set, every `env` entry is written into the environment,
   **overwriting** anything already set. Values go through
   `os.path.expanduser`, and a relative `AGENT_PROMPT_FILE` is resolved
   against the repo root.
3. Suite defaults are applied with `setdefault`, so they only fill in values
   that are **not already set**. A shell variable such as
   `AGENT_MAX_TOKENS=8000` therefore overrides the suite cap. The repo's
   "big budget" runs use exactly this
   (`AGENT_MAX_TOKENS=8000 AGENT_MAX_STEPS=40`, see `run_qwen38_dflash.sh`).
4. The adapter is imported and loaded once; each task then gets a fresh
   sandbox and `adapter.reset()`.

The prompt the agent receives is the task prompt prefixed with
`(Working directory: <sandbox path>)` and a blank line.

## Suite caps

Set by the runner with `setdefault`, so a value already in the environment
wins.

| Variable | easy | hard | Source |
|---|---|---|---|
| `AGENT_MAX_TOKENS` | `1024` | `3000` | `tasks/easy.py`, `tasks/hard.py` `ENV` |
| `AGENT_MAX_STEPS` | `15` | `25` | same |
| `AGENT_BASH_TIMEOUT` | `30` | `45` | same |
| `AGENT_TEMP` | `0.0` | `0.0` | `runner.py` |
| `AGENT_LEASE_NAME` | `agent-12-easy` | `agent-12-hard` | `runner.py` |

These are read by the Anvil engine, not by Agent-12. METHODOLOGY.md
describes them as max tokens, max steps and seconds per shell call.
**TODO-VERIFY** the exact semantics inside Anvil. The `command` adapter does
not pass them to your CLI in any special way; they are just in its
environment.

`AGENT_LEASE_NAME` exists for a memory guard on the author's machine; the
code comment says the name must start with `agent-`. **TODO-VERIFY** whether
it has any effect outside that machine.

## Environment variables read by Agent-12

| Variable | Read by | Default | What it does |
|---|---|---|---|
| `AGENT12_MIN_PYTHON` | `envcheck.py` | `3.10` | Python floor as `X.Y`. `validate_judges.py` exits below it; `runner.py` warns. A value that is not `X.Y` exits with `AGENT12_MIN_PYTHON='…' is not a X.Y version`. The floor and whether it was met are written to every result file. |
| `AGENT12_ENGINE_DIR` | `adapters/anvil.py`, `adapters/anvil_dflash.py` | `~/Desktop/PROJECTS/Local AI Setup/agent` | Directory holding Anvil's `agent.py`. Added to `sys.path` before `import agent`. The default is the author's own path. |
| `AGENT12_CMD` | `adapters/command.py` | none | Shell command template. Must contain `{prompt}`, which is replaced by the shell-quoted prompt. Runs with `shell=True` in the sandbox. |
| `AGENT12_CMD_TIMEOUT` | `adapters/command.py` | `600` | Seconds before the command is killed. A timeout is recorded in the task's `error` field and the judge still runs on whatever was written. |
| `AGENT12_MODEL_LABEL` | `adapters/command.py` | `unlabeled` | Written as `model` in the result file. |
| `AGENT_DFLASH_DRAFTER` | `adapters/anvil_dflash.py` | `incoai/Qwen3.8-27B-DFlash2` | Drafter model for DFlash speculative decoding. |
| `AGENT_CTX_LIMIT` | `adapters/anvil_dflash.py` | `131072` | Stored on the DFlash engine as `ctx_limit`. **TODO-VERIFY** how Anvil's loop uses it. |
| `TASK` | `furball_bench.py` | `furball` | Which visual task to use: reads `tasks/<TASK>/prompt.md`, writes to `results/<TASK>/`, and picks the pass rule (`furball` rule, or the spin rule for anything else). |

## Variables passed through to the Anvil engine

These appear in `configs/models.json` and are set by the runner, but only
Anvil reads them. Agent-12 records some of what Anvil reports back
(`model`, `dialect`, `backend`, `prompt_file`) in the result file.

| Variable | Values seen in the repo | Notes |
|---|---|---|
| `AGENT_MODEL` | Hugging Face repo ids, `deepseek-v4-flash`, `claude-sonnet-5` | The model to load or call. |
| `AGENT_DIALECT` | `native`, `prompted` | Tool-call format. The README describes these as native tool calls and prompted XML. |
| `AGENT_PROMPT_FILE` | `prompts/gemma4.md` | Extra prompt file; relative paths are resolved against the repo root by the runner. |
| `AGENT_BACKEND` | `http` | When Anvil reports `BACKEND == "http"`, the adapter builds `agent.HTTPEngine`; otherwise it takes a seat and builds `agent.MLXEngine`. |
| `AGENT_BASE_URL` | `http://127.0.0.1:8000`, `https://api.anthropic.com` | Server for the HTTP backend. |
| `AGENT_AUTH_TOKEN` | `dsv4-local` (local ds4 server entries) | Token for the HTTP backend. The Claude entry does not set one; its note says to set `AGENT_AUTH_TOKEN` to a real key before running. Since `--model` env overwrites the shell, export it in the shell only for entries that do not set it, and never commit a real key. |
| `AGENT_LEASE_GB` | `0`, `46` | Memory lease size for the author's memory guard. **TODO-VERIFY** |

**TODO-VERIFY** for all rows in this table: the behavior is defined in
Anvil's `agent.py`, which is not in this repo.

## `configs/models.json`

One object per model key:

```json
{
  "qwen3-coder-30b": {
    "adapter": "anvil",
    "display": "Qwen3-Coder-30B-A3B (MLX 8-bit)",
    "env": {
      "AGENT_MODEL": "lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-MLX-8bit",
      "AGENT_DIALECT": "native"
    }
  }
}
```

| Field | Used by the runner | Meaning |
|---|---|---|
| `adapter` | yes | Overrides `--adapter`. |
| `env` | yes | Environment variables applied before the adapter loads (overwrite). |
| `display` | no | Human-readable name. |
| `_note` | no | Free-text notes about the run history of that entry. |

Keys in the repo today: `qwen3-coder-30b`, `qwen3.6-35b`, `qwen3.8-27b`,
`qwen3.8-27b-8bit`, `gemma-4-31b`, `muse-glimmer-30b`,
`deepseek-v4-flash-0731`, `deepseek-v4-flash-orig`,
`claude-cloud-reference`, `qwen3.8-27b-8bit-dflash`.

## `site/meta.json` (the leaderboard)

`build_site.py` reads this file and the result files it names, and writes
`docs/index.html`. (Its docstring says `site/index.html`; the code writes to
`docs/`.)

| Field | Meaning |
|---|---|
| `hardware_default` | Hardware shown on every row without its own `hardware`. |
| `updated` | Date printed in the page footer. |
| `rows.<key>.display` / `params` | Name and the small grey line under it. |
| `rows.<key>.easy` / `hard` | Run names; the score and total seconds are read from `results/<name>.json`. A missing file shows a dash. |
| `rows.<key>.tok_s` | Tokens per second shown as entered; `null` shows a dash. Not computed by the script. |
| `rows.<key>.hardware` | Per-row hardware override. |
| `rows.<key>.kind` | `cloud` puts the row in the cloud reference table; anything else is local. |
| `reported[]` | Vendor-reported rows: `display`, `params`, `scores`, `source`, `url`, `status`. Shown in their own table and not mixed with Agent-12 scores. |

A score renders green when it is a full pass (for example `8/8`). The time
column is the sum of per-task `seconds`, rounded to one decimal.

## Result file (`results/<run>.json`)

| Field | Meaning |
|---|---|
| `run`, `suite`, `adapter` | As passed. |
| `harness_version` | `1.1.0` today; `1.0.0` before the interpreter was recorded. `build_site.py` falls back to `pre-1.0` internally when it is missing. |
| `interpreter` | `python_version`, `python_implementation`, `executable`, `min_python_required`, `meets_min_python`. Present from 1.1.0. |
| `started_utc` | Start time. |
| `load_s` | Seconds to load the model, not counted in task time. |
| `model`, `dialect`, `backend`, `prompt_file` | From the adapter's `info()`. The DFlash adapter adds `drafter`. |
| `tasks.<name>` | `pass`, `seconds`, `detail` (from the judge) and `error` (from the adapter). |
| `gen_stats` | DFlash adapter only: `gen_tokens`, `gen_seconds`, `tok_s_incl_prefill`, `mean_accept`, `generate_calls`. |
| `score` | `passed/total`. |

## Visual bench commands

These need Brave on macOS, `ffmpeg` and `websocket-client`; see
[Install](install.md#visual-bench-dependencies).

```text
python3 furball_bench.py generate <model-key>
python3 furball_bench.py score <html-file> [--label NAME] [--port 9340]
python3 furball_bench.py board
```

`generate` starts the model's server from the `MODELS` table inside
`furball_bench.py`, waits up to 900 seconds for `/v1/models`, asks once at
temperature 0 with `max_tokens` 24000, and writes `<key>.html` and
`<key>.raw.txt`. `score` loads the file at 900x900 in headless Brave, takes
`rest`, `idle`, `petted` and `relaxed` screenshots, and writes
`<label>.score.json`. `board` prints a table of all score files for the
current `TASK`.

Pass rules, from `verdict()`:

- **furball**: loaded, coverage > 0.06, detail > 6.0, and the drag band
  changed by more than 0.02 with a band-to-control ratio above 1.6.
- **spin** (any other `TASK`): loaded, coverage > 0.02, shading > 12.0, and
  the ball is not clipped by the frame. Idle animation is recorded but is not
  a pass condition.

```text
python3 showdown.py gen <task> <label> <base_url> <model_name>
python3 showdown.py judge-breakout <html> <label>
python3 showdown.py clip <task> <html> <out.mp4> [seconds]
```

`gen` sends one chat request (temperature 0, `max_tokens` 24000, 3600 s
timeout) to an OpenAI-compatible server. `judge-breakout` passes a game that
loads with a canvas, draws (coverage > 0.03), has the paddle travel more than
40% of the field when the mouse moves, keeps moving in at least half of the
sampled frames, and throws no page errors. `clip` records a video with
`ffmpeg` (default 9 seconds).

`showdown_gen.py` (`qwen`, `qwen-medium`, `gemma`) imports a memory client
from the author's machine and does not run elsewhere.

## `validate_judges.py` and `build_site.py`

Neither takes flags. `validate_judges.py` honors `AGENT12_MIN_PYTHON`.
