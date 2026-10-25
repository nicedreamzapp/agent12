# Contributing

Thanks for taking a look. Independent runs are what make the board worth trusting, so a result
from your own hardware is useful even if you never send code.

## Reporting a problem

Open an [issue](https://github.com/nicedreamzapp/agent12/issues/new/choose). The things that make
it quick to act on:

- your chip, RAM and OS
- your Python version (runs need 3.10 or later)
- the serving stack, model and quantization you ran
- the exact `runner.py` command, and the score
- for a judge you think is wrong, the task name and the files the model left in its sandbox

## Running it locally

```bash
# 1. validate the judges (required, the runner assumes this passed)
python3 validate_judges.py

# 2. run a configured model through the reference engine (needs Anvil)
python3 runner.py --suite easy --model qwen3-coder-30b --run qwen30_easy

# 3. or plug in any agent CLI
AGENT12_CMD='your-agent --print {prompt}' AGENT12_MODEL_LABEL='your-model' \
  python3 runner.py --suite easy --adapter command --run yours_easy
```

Step 1 works from a fresh clone with no installs. Step 2 needs the Anvil engine, which is not in
this repo (see the README). `run_task.sh`, `glimmer_night.sh` and `lyric_ab.py` hard-code paths on
my machine and will not run elsewhere as-is.

## Tests

`python3 validate_judges.py` is the test. It runs a known-good solution (must pass) and a
known-bad one (must fail) against every task's judge, and exits non-zero if any judge gets either
wrong. Run it after any change to `tasks/`.

## Pull requests

Small and focused is easiest to review. For big changes, like a new task or a scoring change,
open an issue first so we can talk it through. A new task needs a judge plus known-good and
known-bad solutions, and must pass `validate_judges.py`. Result files should say what hardware
produced them.

Please follow the [code of conduct](CODE_OF_CONDUCT.md).
