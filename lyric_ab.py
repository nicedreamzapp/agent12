#!/usr/bin/env python3
"""Blind A/B: gemma (Song Forge's current lyric brain) vs Qwen3.6, same prompt,
same temperature, same everything. Matt judges the words without knowing which
model wrote them.
"""
import json, os, random, subprocess, signal, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results/lyrics")
os.makedirs(OUT, exist_ok=True)

# lifted verbatim from ~/SongForgeM5/forge_server.py so this tests the real thing
sys.path.insert(0, os.path.expanduser("~/SongForgeM5"))
SYSTEM_PROMPT = None
for line in open(os.path.expanduser("~/SongForgeM5/forge_server.py")):
    pass
src = open(os.path.expanduser("~/SongForgeM5/forge_server.py")).read()
i = src.index("SYSTEM_PROMPT = (")
j = src.index('\n)\n', i)
SYSTEM_PROMPT = eval(src[i + len("SYSTEM_PROMPT = "):j + 2])

IDEAS = [
    ("hip-hop", "a song about Humboldt County and the Native people of this area, the Yurok, Hupa, Karuk and Wiyot, their ceremonies and their history"),
]

# Qwen3.6 is a reasoning model: with thinking on it burns the whole budget
# thinking and never writes the song. Song Forge's lyric call would get nothing.
GEMMA = ("gemma-4-31b", "http://127.0.0.1:9420",
         "divinetribe/gemma-4-31b-it-abliterated-4bit-mlx", None,
         {"enable_thinking": False})
QWEN = ("qwen3.6-35b", "http://127.0.0.1:9435",
        "lmstudio-community/Qwen3.6-35B-A3B-MLX-8bit",
        [os.path.expanduser("~/.local/mlx-server/bin/python"), "-m", "mlx_lm.server",
         "--model", "lmstudio-community/Qwen3.6-35B-A3B-MLX-8bit",
         "--host", "127.0.0.1", "--port", "9435"],
        {"enable_thinking": False})


def ask(base, model, style, idea, kw=None):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Write a {style} song. {idea}"},
        ],
        "temperature": 0.95, "top_p": 0.95, "max_tokens": 3000,
    }
    if kw:
        payload["chat_template_kwargs"] = kw
    body = json.dumps(payload).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.load(r)
    msg = out["choices"][0].get("message", {})
    txt = msg.get("content") or ""
    if not txt.strip():
        txt = msg.get("reasoning") or msg.get("reasoning_content") or ""
    import re as _re
    txt = _re.sub(r"<think>.*?</think>", "", txt, flags=_re.S)
    txt = _re.sub(r"^.*?</think>", "", txt, flags=_re.S)
    if not txt.strip():
        txt = "(model returned nothing)"
    # drop any reasoning channel leak before the lyrics
    for tag in ("[verse]", "[Verse]", "[VERSE]"):
        if tag in txt:
            txt = txt[txt.index(tag):]
            break
    return txt.strip(), round(time.time() - t0, 1)


def wait_for(base, timeout=600):
    for _ in range(timeout // 2):
        try:
            urllib.request.urlopen(base + "/v1/models", timeout=3).read()
            return True
        except Exception:
            time.sleep(2)
    return False


results = {}
for key, base, model, serve, kw in (GEMMA, QWEN):
    proc = None
    if serve:
        print(f"loading {key} ...", flush=True)
        proc = subprocess.Popen(serve, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not wait_for(base):
            print(f"{key}: never came up"); continue
    try:
        for style, idea in IDEAS:
            txt, secs = ask(base, model, style, idea, kw)
            results.setdefault(idea, {})[key] = {"text": txt, "secs": secs}
            print(f"  {key} · {style} · {secs}s", flush=True)
    finally:
        if proc:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()

# blind labels, coin-flipped per song so A isn't always the same model
key_map = {}
lines = []
for n, (style, idea) in enumerate(IDEAS, 1):
    got = results.get(idea, {})
    if len(got) < 2:
        continue
    names = list(got)
    random.shuffle(names)
    key_map[f"song {n}"] = {"A": names[0], "B": names[1]}
    lines.append(f"\n{'='*70}\nSONG {n} — {style.upper()}: {idea}\n{'='*70}")
    for label, nm in zip("AB", names):
        lines.append(f"\n----- {label} ({got[nm]['secs']}s) -----\n{got[nm]['text']}")

open(os.path.join(OUT, "blind.txt"), "w").write("\n".join(lines))
json.dump(key_map, open(os.path.join(OUT, "key.json"), "w"), indent=1)
print("\n".join(lines))
print("\n(answer key written to results/lyrics/key.json — not shown)")
