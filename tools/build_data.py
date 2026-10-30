#!/usr/bin/env python3
"""Build docs/data/catalog.json: one machine-readable row per model per suite.

This is the file the picker reads. Keeping it generated means the picker can never
disagree with the site, and anyone can fetch it and build their own thing.

Memory figures reuse the mac-fit math exactly: weights from the repo file list, KV cache
from the model's config, 1.2 GB runtime, MLX able to wire 75% of unified memory.

    python tools/build_data.py
"""
import glob
import io
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "data", "catalog.json")
GB = 1e9
USABLE = 0.75
RUNTIME = 1.2 * GB
MACS = [8, 16, 18, 24, 32, 36, 48, 64, 96, 128]


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def kv_bytes(t, ctx):
    return 2 * t["layers"] * t["kv_heads"] * t["head_dim"] * 2 * ctx


def smallest_mac(need):
    for m in MACS:
        if need <= m * GB * USABLE:
            return m
    return None


def mac_fit_rows():
    p = os.path.join(ROOT, "data", "mac-fit-targets.json")
    if not os.path.exists(p):
        return []
    rows = []
    for t in load(p):
        if not t.get("layers") or not t.get("head_dim"):
            continue
        by_ctx = {}
        for ctx in (4096, 8192, 32768, 131072):
            if t["max_ctx"] and ctx > t["max_ctx"]:
                continue
            need = t["stored_bytes"] + kv_bytes(t, ctx) + RUNTIME
            by_ctx[str(ctx)] = {"needs_gb": round(need / GB, 1),
                                "smallest_mac_gb": smallest_mac(need)}
        rows.append({
            "suite": "mac-fit",
            "model": t["model_id"],
            "model_url": f"https://huggingface.co/{t['model_id']}",
            "weights_gb": round(t["stored_bytes"] / GB, 1),
            "quant_bits": t["quant_bits"],
            "layers": t["layers"], "kv_heads": t["kv_heads"],
            "head_dim": t["head_dim"], "max_ctx": t["max_ctx"],
            "by_context": by_ctx,
            "page": f"mac-fit/{t['author']}",
            "source": "measured here",
            "hardware": None,
        })
    return rows


def leaderboard_memory():
    """Memory for the models on the board, from tools/fetch_model_memory.py."""
    p = os.path.join(ROOT, "data", "leaderboard-memory.json")
    return load(p) if os.path.exists(p) else {}


def memory_block(mem):
    """Per-context memory need for one model, same math as the mac-fit pages."""
    by_ctx = {}
    for ctx in (4096, 8192, 32768, 131072):
        if mem.get("max_ctx") and ctx > mem["max_ctx"]:
            continue
        need = mem["stored_bytes"] + kv_bytes(mem, ctx) + RUNTIME
        by_ctx[str(ctx)] = {"needs_gb": round(need / GB, 1),
                            "smallest_mac_gb": smallest_mac(need)}
    return by_ctx


def agent_rows(meta):
    """One row per model per agent suite, keyed through site/meta.json."""
    mem_all = leaderboard_memory()
    rows = []
    for key, r in (meta.get("rows") or {}).items():
        for suite, run_key in (("agent-easy", r.get("easy")), ("agent-hard", r.get("hard"))):
            if not run_key:
                continue
            p = os.path.join(ROOT, "results", f"{run_key}.json")
            if not os.path.exists(p):
                continue
            run = load(p)
            tasks = run.get("tasks") or {}
            if not tasks:
                continue
            passed = sum(1 for t in tasks.values() if t.get("pass"))
            mem = mem_all.get(key)
            rows.append({
                "suite": suite,
                "model": r["display"],
                "model_key": key,
                "pass_rate": round(100 * passed / len(tasks), 1),
                "n_items": len(tasks),
                "wall_s": round(sum(t.get("seconds") or 0 for t in tasks.values()), 1),
                "tok_s": r.get("tok_s"),
                "kind": r.get("kind", "local"),
                "hardware": meta.get("hardware_default"),
                "source": "measured here",
                # a cloud row has no local memory story, so leave it absent
                **({"repo": mem["repo"], "weights_gb": round(mem["stored_bytes"] / GB, 1),
                    "layer_note": mem.get("layer_note"),
                    "by_context": memory_block(mem)} if mem else {}),
            })
    return rows


def community():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "submissions", "*.json"))):
        if os.path.basename(p).startswith("EXAMPLE"):
            continue
        d = load(p)
        rows.append({"suite": d["suite"], "model": d["model"],
                     "model_url": d.get("model_url"),
                     "hardware": d["hardware"], "runtime": d.get("runtime"),
                     "n_items": d.get("n_items"), "source": "community",
                     "submitted_by": d["submitted_by"],
                     "submitted_by_url": d.get("submitted_by_url"),
                     "log_url": d.get("log_url"), "notes": d.get("notes"),
                     **d["metrics"]})
    return rows


def main():
    reg = load(os.path.join(ROOT, "suites", "registry.json"))
    meta = load(os.path.join(ROOT, "site", "meta.json"))
    rows = agent_rows(meta) + mac_fit_rows() + community()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    payload = {
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hardware_default": meta.get("hardware_default"),
        "assumptions": {
            "usable_fraction_of_unified_memory": USABLE,
            "runtime_overhead_gb": RUNTIME / GB,
            "kv_cache": "2 x layers x kv_heads x head_dim x 2 bytes (fp16) x tokens",
        },
        "suites": [{k: s[k] for k in ("id", "title", "measures", "metrics", "status")}
                   for s in reg["suites"]],
        "metrics": reg["metrics"],
        "rows": rows,
    }
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    kinds = {}
    for r in rows:
        kinds[r["suite"]] = kinds.get(r["suite"], 0) + 1
    print(f"wrote {OUT}")
    print("  " + ", ".join(f"{v} {k}" for k, v in sorted(kinds.items())))


if __name__ == "__main__":
    main()
