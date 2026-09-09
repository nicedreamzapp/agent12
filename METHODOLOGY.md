# Methodology

## The two rules everything else follows from

**1. Every judge is validated before it judges anything real.**
Each task ships with a known-good reference solution and a known-bad
plausible attempt. `validate_judges.py` asserts the judge passes the good and
fails the bad, for all tasks, before any model run counts. Both directions
matter: a judge that passes everything inflates scores; a judge that fails
correct work converts model skill into noise.

This is not theoretical. The original private version of the `h3_lru_ttl_cache`
probe asserted an eviction order that contradicted the task's own spec — a
spec-perfect implementation failed it, and two strong models were wrongly
scored down before the validation gate caught it (2026-08-10). The probe was
rewritten and re-validated; affected runs were re-scored. Judges are code,
and code has bugs — which is why the gate exists.

**2. One variable moves per comparison.**
A scoreboard row is (model, harness, quantization, hardware, suite). Two rows
are comparable when exactly one of those differs. Model face-offs hold the
engine, dialect discipline, temperature (0), step caps, and hardware fixed.
Harness face-offs hold the model fixed. We never present a two-variable delta
as a model result.

## How a run works

- Fresh sandbox directory and fresh conversation per task; same loaded model
  across the suite (load time reported separately).
- The agent gets the task prompt and a working directory. Nothing else.
- The judge inspects the filesystem afterwards: it reads the artifacts, runs
  them in a fresh subprocess, and compares outputs. The model's own claims
  about what it did are never consulted.
- Tasks that ship a test file pin the file's SHA-256 at setup; a modified
  test file scores zero ("test file was modified" appears in the public
  per-task detail).
- Caps: easy = 1024 max tokens / 15 steps / 30s per shell call; hard = 3000
  max tokens / 25 steps / 45s. A model that cannot finish under caps fails —
  an agent that needs an hour for a 30-second task is not a usable agent,
  and the caps are identical for every row.

## The interpreter is part of the grading conditions

Judges run the agent's solution with `sys.executable`, so the interpreter
that runs the harness grades the code. On Python 3.9 a correct solution
annotated `list[str] | None` (PEP 604) raises `TypeError` at import and
scores zero, while a solution that skipped annotations passes: the more
modern answer is punished for the machine it landed on. System `python3`
on a clean macOS install is 3.9, so this is the default outcome, not an
exotic one.

The judge-validation gate does not catch this on its own — the reference
solutions are written in 3.9-compatible style, so `validate_judges.py`
reports a clean 20/20 on 3.9 while live runs are still being mis-scored.
Hence two explicit measures:

- `validate_judges.py` **refuses to run** below the floor (3.10), because
  judges validated under an interpreter nobody grades with prove nothing.
- `runner.py` records `interpreter` (version, implementation, executable,
  the floor, and whether it was met) in every `results/*.json`, so a row
  is described by its own file rather than by the operator's memory. Below
  the floor it still runs, and says so on stderr.

`AGENT12_MIN_PYTHON=3.11` raises the floor for a suite that needs newer
syntax; setting it lower is allowed, recorded in the results, and never
silent.

## What a row reports

- **score** — tasks passed / tasks in suite
- **time** — total wall-clock seconds across the suite (excluding model load)
- **hardware** — the exact machine, because "runs great" means nothing
  without "on what"
- **harness** — reference engine (with dialect: native tool-calls or
  prompted-XML) or a named external CLI via the command adapter
- **quant/weights** — exact model file or repo revision
- **interpreter** — the Python that ran the judges, because it decides
  which syntax a correct answer is allowed to use

## Harness sensitivity (why the harness column exists)

Measured 2026-08-09 on an M5 (128 GB): the same Qwen3.6-35B that scores 12/12
on the easy suite inside the ~550-token reference engine spent an hour in a
32k-token thinking spiral inside a 7,800-token, 66-tool harness and produced
zero files. Ecosystem tooling is currently pointed the other way — plugging
local models into heavyweight cloud harnesses. Agent-12 treats the harness
as an experimental variable, not an assumption. External-harness rows
(including cloud-agent CLIs) run through the `command` adapter and are
labeled as such.

## Cloud reference rows

Cloud models appear only as clearly-labeled reference points, run through
the same engine, tasks, and judges. They exist to answer "how much am I
giving up by going local?" — not to compete for the local crown.

## Limitations we know about

- 20 public tasks is a small set; confidence intervals on a single suite run
  are wide. Held-out tasks and repeat-run policies are described in
  [CONTAMINATION.md](CONTAMINATION.md).
- Temp-0 single runs measure the deterministic path, not the distribution.
  Where sampling variance matters (speculative: some serving stacks are not
  bit-stable), we re-run and report the mode.
- Judges check outcomes, not elegance. A hideous-but-correct solution passes.
  That is intentional: the question is "did the agent do the job."
