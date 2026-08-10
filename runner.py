#!/usr/bin/env python3
"""Agent-12 runner — one model, one suite, judged by the filesystem.

Usage:
  python3 runner.py --suite easy|hard --adapter anvil|command --run RUN_NAME
                    [--config configs/models.json --model KEY]

--model applies that entry's env block (AGENT_MODEL, AGENT_DIALECT, ...)
before the adapter loads, so a scoreboard row is fully described by one
config key. Results land in results/RUN_NAME.json, transcripts in
logs/RUN_NAME/.
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

HARNESS_VERSION = "1.0.0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True, choices=["easy", "hard"])
    ap.add_argument("--adapter", default="anvil", choices=["anvil", "command"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--config", default="")
    ap.add_argument("--model", default="")
    args = ap.parse_args()

    if args.model:
        cfg_path = Path(args.config or HERE / "configs" / "models.json")
        cfg = json.loads(cfg_path.read_text())
        if args.model not in cfg:
            raise SystemExit(f"model {args.model!r} not in {cfg_path}")
        entry = cfg[args.model]
        args.adapter = entry.get("adapter", args.adapter)
        for k, v in entry.get("env", {}).items():
            v = os.path.expanduser(v)
            if k == "AGENT_PROMPT_FILE" and v and not os.path.isabs(v):
                v = str(HERE / v)  # prompt files live in the repo; cwd moves per task
            os.environ[k] = v

    from tasks import load_suite
    suite = load_suite(args.suite)

    # suite discipline: temp 0, fixed caps — set BEFORE the adapter imports its engine
    os.environ.setdefault("AGENT_TEMP", "0.0")
    # "agent-" prefix required: the forge_guard memory policeman maps this
    # process to its lease by that prefix; other names get double-charged
    # and SIGSTOPped as an unregistered hog (learned 2026-08-10, 01:02)
    os.environ.setdefault("AGENT_LEASE_NAME", f"agent-12-{args.suite}")
    for k, v in suite.ENV.items():
        os.environ.setdefault(k, v)

    from adapters import load_adapter
    adapter = load_adapter(args.adapter)

    sandbox_root = HERE / "sandboxes" / args.run
    log_dir = HERE / "logs" / args.run
    results_dir = HERE / "results"
    for p in (sandbox_root, log_dir, results_dir):
        p.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    adapter.load()
    load_s = round(time.time() - t0, 1)

    results = {"run": args.run, "suite": args.suite, "adapter": args.adapter,
               "harness_version": HARNESS_VERSION,
               "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "load_s": load_s, "tasks": {}}
    results.update(adapter.info())

    passed = 0
    for task in suite.TASKS:
        d = sandbox_root / task.name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        task.setup(d)
        if task.pin:
            task.pin(d)
        os.chdir(d)
        adapter.reset()
        # the agent's system prompt embeds cwd at startup; tell it where it is
        task_prompt = f"(Working directory: {d})\n\n{task.prompt}"
        t1 = time.time()
        err = ""
        try:
            adapter.run(task_prompt)
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        took = round(time.time() - t1, 1)
        os.chdir(HERE)
        detail = ""
        try:
            res = task.check(d)
            ok, detail = res if isinstance(res, tuple) else (bool(res), "")
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"checker: {type(e).__name__}"
        passed += ok
        results["tasks"][task.name] = {"pass": ok, "seconds": took,
                                       "detail": detail, "error": err}
        (log_dir / f"{task.name}.log").write_text(
            adapter.last_output + (f"\nERROR: {err}\n" if err else ""))
        extra = f"  [{detail}]" if detail else ""
        print(f"  {'PASS' if ok else 'FAIL'}  {task.name}  ({took}s){extra}", flush=True)

    results["score"] = f"{passed}/{len(suite.TASKS)}"
    out = results_dir / f"{args.run}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"SCORE {passed}/{len(suite.TASKS)} -> {out}", flush=True)
    adapter.close()
    os._exit(0)  # MLX teardown can hang; results are already on disk


if __name__ == "__main__":
    main()
