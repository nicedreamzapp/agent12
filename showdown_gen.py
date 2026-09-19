#!/usr/bin/env python3
"""Generate the showdown builds in-process, one model load for all three tasks.

  ~/.local/qwen-fast/bin/python showdown_gen.py qwen     # Qwen3.8-27B 8-bit + DFlash 2
  ~/.local/mlx-vlm-latest/bin/python showdown_gen.py gemma  # Gemma 4 31B bf16 (mlx-vlm, text only)

Same prompt files, temperature 0, 32k new tokens, one shot. Every load is wrapped in a
forge_guard lease and waits for Song Forge to be idle first."""
import json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/SongForgeM5"))
from mem_client import reserve  # noqa: E402

TASKS = ["spin", "breakout", "furball"]
MAXTOK = 32768
QWEN = ("lmstudio-community/Qwen3.8-27B-MLX-8bit", "incoai/Qwen3.8-27B-DFlash2")
GEMMA = os.path.expanduser("~/.cache/huggingface/hub/gemma-4-31b-it-abliterated-VL-mlx-bf16")


def forge_idle():
    while True:
        try:
            j = json.load(urllib.request.urlopen("http://127.0.0.1:8767/api/status", timeout=5))
            if not j.get("jobs_running"):
                return
        except Exception:
            return
        print("song forge busy, waiting", flush=True)
        time.sleep(30)


def extract_html(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    if "</think>" in text:                       # template opened <think> in the prompt
        text = text.rsplit("</think>", 1)[1]
    text = re.sub(r"<\|channel\|?>thought.*?<channel\|>", "", text, flags=re.S)
    m = re.search(r"```(?:html)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    i = text.lower().find("<!doctype")
    if i < 0:
        i = text.find("<")
    return text[i:].strip() if i >= 0 else text.strip()


def save(task, label, text, secs, toks, extra):
    d = os.path.join(HERE, "results", task)
    os.makedirs(d, exist_ok=True)
    html = extract_html(text)
    open(os.path.join(d, label + ".html"), "w").write(html)
    open(os.path.join(d, label + ".raw.txt"), "w").write(text)
    meta = {"task": task, "label": label, "gen_seconds": round(secs, 1),
            "completion_tokens": toks, "tok_s": round(toks / secs, 1) if toks and secs else None,
            "max_tokens": MAXTOK, "chars": len(html), "complete": "</html>" in html.lower(), **extra}
    json.dump(meta, open(os.path.join(d, label + ".gen.json"), "w"), indent=1)
    print(json.dumps(meta), flush=True)


def run_qwen(effort=None):
    import mlx.core as mx
    from mlx_dspark.generate import dflash_generate
    from mlx_dspark.load import load_dflash_pair
    mx.set_cache_limit(2 * 1024 ** 3)
    forge_idle()
    with reserve("agent-12-showdown-qwen38", 38, ttl=7200):
        target, tok, drafter, _ = load_dflash_pair(QWEN[0], drafter=QWEN[1])
        for task in TASKS:
            prompt = open(os.path.join(HERE, f"tasks/{task}/prompt.md")).read()
            forge_idle()
            ids = tok.apply_chat_template([{"role": "user", "content": prompt}],
                                          add_generation_prompt=True, tokenize=True,
                                          **({"reasoning_effort": effort} if effort else {}))
            if isinstance(ids, dict):
                ids = ids["input_ids"]
            t0 = time.time()
            res = dflash_generate(target, tok, drafter, prompt_ids=list(ids),
                                  apply_chat_template=False, max_new_tokens=MAXTOK,
                                  temperature=0.0)
            secs = time.time() - t0
            label = "qwen3.8-27b-dflash" + (f"-{effort}" if effort else "")
            save(task, label, res.text, secs, res.num_tokens,
                 {"model": QWEN[0], "drafter": QWEN[1], "rounds": res.num_rounds,
                  "reasoning_effort": effort or "xhigh (template default)"})
            mx.clear_cache()


def run_gemma():
    import mlx.core as mx
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    mx.set_cache_limit(2 * 1024 ** 3)
    forge_idle()
    with reserve("showdown-gemma4-31b", 48, ttl=7200):
        model, processor = load(GEMMA)
        for task in TASKS:
            prompt = open(os.path.join(HERE, f"tasks/{task}/prompt.md")).read()
            formatted = apply_chat_template(processor, model.config, prompt, num_images=0)
            forge_idle()
            t0 = time.time()
            out = generate(model, processor, formatted, max_tokens=MAXTOK, temperature=0.0,
                           verbose=False)
            secs = time.time() - t0
            text = out if isinstance(out, str) else out.text
            toks = None if isinstance(out, str) else getattr(out, "generation_tokens", None)
            save(task, "gemma-4-31b", text, secs, toks, {"model": os.path.basename(GEMMA)})
            mx.clear_cache()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        TASKS[:] = sys.argv[2].split(",")   # argv[3], if any, is a forge_guard tag
    {"qwen": run_qwen, "qwen-medium": lambda: run_qwen("medium"),
     "gemma": run_gemma}[sys.argv[1]]()
