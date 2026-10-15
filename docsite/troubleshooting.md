---
title: Agent-12 troubleshooting, error messages and fixes
description: Fixes for Agent-12 errors, built from the code's own error messages and real GitHub issues. Python 3.9 failing correct code, broken judges, AGENT12_CMD, missing Anvil engine, timeouts and harness differences.
---

# Troubleshooting

Each entry starts with the message you see. Messages are quoted from the
code; the linked issues are real reports on this repo.

## `Python 3.x is below the required 3.10.`

Full message from `envcheck.py`:

```text
Python 3.9.6 is below the required 3.10.
  interpreter: /usr/bin/python3
Judges execute the agent's solution with this interpreter, so a
correct answer using 3.10+ syntax (PEP 604 `X | None`, match, ...)
would be scored as a failure. System python3 on macOS is 3.9.
```

`validate_judges.py` exits with this. `runner.py` prints it as a `WARNING`
and keeps going, but the run's `interpreter.meets_min_python` will be
`false`.

Fix: run with Python 3.10 or newer. On macOS the system `python3` is 3.9, so
use a Homebrew, pyenv or uv interpreter. Only lower the floor with
`AGENT12_MIN_PYTHON` if you mean to grade against an older Python.

Background: [issue #1](https://github.com/nicedreamzapp/agent12/issues/1)
found a correct `h5_topo_lex` answer annotated `list[str] | None` scored as
a failure on 3.9.

## `AGENT12_MIN_PYTHON='…' is not a X.Y version`

The variable must be two numbers, such as `3.11`. Anything else exits
instead of silently falling back to the default.

## `N BROKEN judge(s) — do not run the benchmark.`

`validate_judges.py` found a judge that fails its known-good solution,
passes its known-bad one, or fails the known-good answer once a UTF-8 BOM is
added. The row marked `BROKEN` shows which. Do not trust runs until it is
green. If you changed a task, the bracketed detail on that row is the
judge's own reason.

## A correct answer fails because of an invisible character

Fixed in [#4](https://github.com/nicedreamzapp/agent12/pull/4) after
[issue #3](https://github.com/nicedreamzapp/agent12/issues/3). Some editors
write a UTF-8 BOM at the start of a file; `.strip()` does not remove it and
`json.loads` rejects it. Judges now read answers with `tasks.answer_text()`,
which drops a leading BOM. If you are on an older checkout, pull `main`.

Code fences (```` ```json ````) and prefixes like `Answer:` in an answer file
are still graded as content on purpose.

## `AGENT12_CMD must contain {prompt}`

The `command` adapter needs a template with the literal `{prompt}`, which it
replaces with the shell-quoted task prompt:

```bash
AGENT12_CMD='your-agent --print {prompt}' python3 runner.py --suite easy --adapter command --run test
```

## `ModuleNotFoundError: No module named 'agent'`

You ran the `anvil` or `anvil_dflash` adapter (the default adapter is
`anvil`, and every `--model` entry in `configs/models.json` uses one of
them) without the Anvil engine. Anvil is not in this repo. Either point
`AGENT12_ENGINE_DIR` at a directory with its `agent.py`, or use
`--adapter command` with your own agent.

## `model 'KEY' not in configs/models.json`

The `--model` key does not exist in the config file (or in the file given
with `--config`). Keys are listed on the
[Configuration](configuration.md#configsmodelsjson) page.

## `unknown adapter` / `unknown suite`

`--adapter` must be `anvil`, `anvil_dflash` or `command`; `--suite` must be
`easy` or `hard`. An `adapter` field inside a config entry overrides
`--adapter`.

## Every task fails in under a second

A whole suite failing almost instantly is almost always the environment, not
the model. In [issue #1](https://github.com/nicedreamzapp/agent12/issues/1)
one suite was lost to a CLI flag that silently disabled login (every task
failed in 0.8 s with zero input tokens), and another to an agent CLI stuck in
an approval mode that cannot work headless. Check `logs/<run>/<task>.log`
for the agent's actual output, and the `error` field in the result file.

## `TimeoutExpired: … timed out after 600 seconds`

The `command` adapter killed your CLI after `AGENT12_CMD_TIMEOUT` seconds
(default 600). The error is stored in that task's `error` field and the judge
still runs on whatever files exist. On a timeout the adapter does not update
its captured output, so that task's log can show the previous task's output
followed by the error line.

## `checker: SomeError` in a task's detail

The judge itself raised an exception while inspecting the sandbox, which is
scored as a fail. This usually means the agent left files in a shape the
judge could not read. The sandbox is kept at `sandboxes/<run>/<task>/` until
the next run with the same name, so you can look at it.

## `test file was modified`

The task pinned its test file's SHA-256 and the agent changed it. That
scores zero by design. Related judge messages in the hard suite:
`used the banned csv module` (`h4_csv_no_csv`) and
`memoization was removed` (`h8_cache_collision`).

## Scores differ from the board

Things that change scores, all documented in the repo:

- **Harness.** Board rows use the Anvil engine. Issue #1 measured the same
  model and weights at 8/8 hard in Anvil and 6/8 inside Claude Code as
  installed with MCP servers connected.
- **Caps.** A shell `AGENT_MAX_TOKENS` or `AGENT_MAX_STEPS` overrides the
  suite caps (see [Configuration](configuration.md#runnerpy)). Qwen3.8-27B
  8-bit scored 6/8 and 7/8 at the default hard caps and 8/8 at 8000 tokens and 40
  steps (`writeups/qwen38_vs_qwen36.md`).
- **Repeat variance.** Repeat runs of the same config can differ by one task;
  compare the `_s2` to `_s4` files in `results/`.
- **Interpreter.** See the Python section above.

## Running out of memory with the DFlash adapter

On 2026-09-19 the DFlash path re-prefilled the full transcript every turn and
the process grew past 100 GB, putting the machine into swap
(`writeups/qwen38_dflash_rerun.md`). The adapter now calls
`mx.set_cache_limit(2 * 1024 ** 3)` and clears the cache after every turn.
If you write your own MLX adapter, do the same.

## Visual benches

| Message | Cause |
|---|---|
| `ModuleNotFoundError: No module named 'websocket'` | `python3 -m pip install websocket-client` |
| `<key>: server never came up` | `furball_bench.py generate` waited 900 s for the model server's `/v1/models` and gave up. Check the server command in `MODELS`. |
| `page never opened` / `headless page never opened` | Brave did not start or did not expose DevTools on the port. Brave must be at `/Applications/Brave Browser.app/...`; try another `--port`. |
| `FileNotFoundError: ... 'ffmpeg'` | `ffmpeg` is not on `PATH`; the pixel statistics are read through it. |
| A DNF score file | The model request raised (often the timeout). Recorded as `dnf: true`. |

## Still stuck

Open an [issue](https://github.com/nicedreamzapp/agent12/issues/new) with
your chip, RAM, Python version, the command you ran, and the relevant part
of the result file or log.
