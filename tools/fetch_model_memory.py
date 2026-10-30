#!/usr/bin/env python3
"""Work out the memory every leaderboard model needs, the same way mac-fit does.

Without this the picker can score a model but cannot say whether it fits the machine the
person actually owns, which is the whole question. Reads the repo ids out of
configs/models.json, pulls each repo's file list and config from Hugging Face, and writes
data/leaderboard-memory.json.

Needs network. Rerun it when a row is added to configs/models.json.

    python tools/fetch_model_memory.py
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "leaderboard-memory.json")
UA = {"User-Agent": "agent12-memory/1.0 (matt@ineedhemp.com)"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                return None
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return None


def text_config(cfg):
    """The text model's own config. On VLMs the layer counts sit under text_config, and
    reading only the root is why these models looked unreadable at first."""
    for nest in ("text_config", "language_config", "llm_config"):
        sub = cfg.get(nest)
        if isinstance(sub, dict) and sub.get("num_hidden_layers"):
            return sub
    return cfg


def kv_layers(tc):
    """Layers that actually hold a KV cache.

    Hybrid models list a layer_types array: the linear or sliding layers do not keep a
    growing full-attention cache, so counting every layer overstates the memory. When the
    array is there, count the full-attention ones and say which was used.
    """
    types = tc.get("layer_types")
    total = tc.get("num_hidden_layers") or 0
    if isinstance(types, list) and types:
        full = sum(1 for t in types if "full" in str(t).lower())
        if full:
            return full, f"{full} of {len(types)} layers hold full attention"
    return total, f"all {total} layers"


def main():
    with io.open(os.path.join(ROOT, "configs", "models.json"), encoding="utf-8") as f:
        models = json.load(f)

    out = {}
    for key, m in models.items():
        repo = (m.get("env") or {}).get("AGENT_MODEL")
        if not repo or "/" not in repo:
            print(f"  skip {key}: no repo id")
            continue
        info = get(f"https://huggingface.co/api/models/{repo}?blobs=true")
        if not info:
            print(f"  skip {key}: {repo} not readable (gated or gone)")
            continue
        files = [s for s in (info.get("siblings") or [])
                 if s.get("rfilename", "").endswith(".safetensors")
                 and "/" not in s["rfilename"]]
        size = sum(s.get("size") or 0 for s in files)
        raw = get(f"https://huggingface.co/{repo}/resolve/main/config.json") or {}
        cfg = text_config(raw)
        heads = cfg.get("num_attention_heads") or 0
        hidden = cfg.get("hidden_size") or 0
        head_dim = cfg.get("head_dim") or (hidden // heads if heads else 0)
        layers, layer_note = kv_layers(cfg)
        if not size or not layers or not head_dim:
            print(f"  skip {key}: incomplete ({size/1e9:.1f} GB, "
                  f"layers={layers}, head_dim={head_dim})")
            continue
        out[key] = {
            "repo": repo,
            "display": m.get("display", key),
            "stored_bytes": size,
            "weight_files": len(files),
            "layers": layers,
            "layer_note": layer_note,
            "kv_heads": cfg.get("num_key_value_heads") or heads,
            "head_dim": head_dim,
            "max_ctx": cfg.get("max_position_embeddings"),
            "quant_bits": (raw.get("quantization") or cfg.get("quantization")
                           or {}).get("bits"),
            "multimodal": bool(raw.get("vision_config")),
        }
        print(f"  {key:22s} {repo[:40]:40s} {size/1e9:6.1f} GB  "
              f"kv{out[key]['kv_heads']} d{head_dim}  {layer_note}")
        time.sleep(0.3)

    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {len(out)} of {len(models)} models -> {OUT}")


if __name__ == "__main__":
    main()
