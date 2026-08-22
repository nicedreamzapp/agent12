#!/usr/bin/env python3
"""Fur-ball bench: can a local model write the furry-ball demo, and does it work?

Two halves:
  generate  — ask a model for a single self-contained HTML file
  score     — load it in headless Brave, look at it, and pet it

Scoring is mechanical, not vibes. We measure whether anything drew at all, whether
the surface has strand-scale detail (a smooth sphere fails this), and whether a
synthetic drag actually moves the hair — with the change staying local to the
stroke instead of the whole screen flipping.

  python3 furball_bench.py generate <model-key>
  python3 furball_bench.py score <html-file> [--label NAME]
  python3 furball_bench.py board
"""
import argparse, base64, json, os, re, shutil, signal, statistics, subprocess, sys, time, urllib.request

import websocket

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.environ.get("TASK", "furball")
PROMPT = open(os.path.join(HERE, f"tasks/{TASK}/prompt.md")).read()
OUT_DIR = os.path.join(HERE, f"results/{TASK}")
os.makedirs(OUT_DIR, exist_ok=True)

# what counts as a pass depends on the task. furball wants strand texture and a
# LOCAL response under the stroke; spin wants a shaded ball that turns, and a drag
# that changes the whole image faster than its own idle spin does.
def verdict(res):
    if TASK == "furball":
        res["drew"] = res.get("coverage", 0) > 0.06
        res["textured"] = res.get("detail", 0) > 6.0
        res["responds"] = (res.get("pet_band", 0) > 0.02 and res.get("pet_ratio", 0) > 1.6)
        res["pass"] = all([res["loaded"], res["drew"], res["textured"], res["responds"]])
    else:
        res["drew"] = res.get("coverage", 0) > 0.02
        res["shaded"] = res.get("shading", 0) > 12.0
        res["animates"] = res.get("idle_change", 0) > 0.004
        res["responds"] = res.get("pet_global", 0) > max(0.01, res.get("idle_change", 0) * 1.4)
        # note: a smooth untextured sphere looks identical while it rotates, so
        # "animates" is recorded but cannot be a pass condition on this task
        res["framed"] = not res.get("clipped", True)
        res["pass"] = all([res["loaded"], res["drew"], res["shaded"], res["framed"]])
    return res

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
MLX_PY = os.path.expanduser("~/.local/mlx-server/bin/python")
VLM_PY = os.path.expanduser("~/.local/mlx-vlm-latest/bin/python")

# Every contender that has weights on this box today.
MODELS = {
    "gemma-4-31b": {
        "display": "Gemma 4 31B abliterated (MLX 4-bit)",
        "serve": [MLX_PY, "-m", "mlx_lm.server", "--model",
                  "divinetribe/gemma-4-31b-it-abliterated-4bit-mlx",
                  "--host", "127.0.0.1", "--port", "9434"],
        "base": "http://127.0.0.1:9434",
        "name": "divinetribe/gemma-4-31b-it-abliterated-4bit-mlx",
    },
    "qwen3.6-35b": {
        "display": "Qwen3.6-35B-A3B (MLX 8-bit)",
        "serve": [MLX_PY, "-m", "mlx_lm.server", "--model",
                  "lmstudio-community/Qwen3.6-35B-A3B-MLX-8bit",
                  "--host", "127.0.0.1", "--port", "9431"],
        "base": "http://127.0.0.1:9431",
        "name": "lmstudio-community/Qwen3.6-35B-A3B-MLX-8bit",
    },
    "qwen3-vl-32b": {
        "display": "Qwen3-VL 32B abliterated (MLX 4-bit)",
        "serve": [MLX_PY, "-m", "mlx_vlm.server", "--model",
                  "divinetribe/Huihui-Qwen3-VL-32B-Instruct-abliterated-4bit-mlx",
                  "--port", "9432"],
        "base": "http://127.0.0.1:9432",
        "name": "divinetribe/Huihui-Qwen3-VL-32B-Instruct-abliterated-4bit-mlx",
    },
    "muse-glimmer-mm": {
        "display": "Muse Glimmer 30B Abliterated MM (MLX bf16)",
        "serve": [VLM_PY, "-m", "mlx_vlm.server", "--model",
                  os.path.expanduser("~/Muse-Glimmer-30B-Abliterated-MM-bf16"),
                  "--port", "9433"],
        "base": "http://127.0.0.1:9433",
        "name": "divinetribe/Muse-Glimmer-30B-Abliterated-MM-bf16",
    },
}


# ----------------------------------------------------------------- generation
def wait_for(base, timeout=900):
    for _ in range(int(timeout / 2)):
        try:
            urllib.request.urlopen(base + "/v1/models", timeout=3).read()
            return True
        except Exception:
            time.sleep(2)
    return False


def chat(base, model, prompt, max_tokens=24000, timeout=1200):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.load(r)
    return out["choices"][0]["message"]["content"]


def extract_html(text):
    m = re.search(r"```(?:html)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    i = text.find("<")
    return text[i:].strip() if i >= 0 else text.strip()


def generate(key):
    spec = MODELS[key]
    proc = None
    if spec["serve"]:
        print(f"starting {key} ...", flush=True)
        proc = subprocess.Popen(spec["serve"], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        if not wait_for(spec["base"]):
            proc.kill()
            raise SystemExit(f"{key}: server never came up")
    try:
        t0 = time.time()
        try:
            text = chat(spec["base"], spec["name"], PROMPT)
        except Exception as e:                      # slower than the cap = DNF
            secs = time.time() - t0
            meta = {"model": key, "dnf": True, "gen_seconds": round(secs, 1), "why": str(e)[:120]}
            json.dump({"label": key, "loaded": False, "dnf": True, "pass": False,
                       "gen_seconds": round(secs, 1)},
                      open(os.path.join(OUT_DIR, key + ".score.json"), "w"), indent=1)
            print(json.dumps(meta), flush=True)
            return meta
        secs = time.time() - t0
    finally:
        if proc:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()

    html = extract_html(text)
    path = os.path.join(OUT_DIR, f"{key}.html")
    open(path, "w").write(html)
    open(os.path.join(OUT_DIR, f"{key}.raw.txt"), "w").write(text)
    meta = {"model": key, "display": spec["display"], "gen_seconds": round(secs, 1),
            "chars": len(html), "html": path,
            "complete": "</html>" in html.lower()}
    print(json.dumps(meta), flush=True)
    return meta


# -------------------------------------------------------------------- scoring
def cdp(ws, method, params=None, _id=[0]):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": method, "params": params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == _id[0]:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {})


def ev(ws, expr):
    r = cdp(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                     "awaitPromise": True})
    return r.get("result", {}).get("value")


def shot(ws, path):
    data = cdp(ws, "Page.captureScreenshot", {"format": "png"})["data"]
    with open(path, "wb") as fh:
        fh.write(base64.b64decode(data))
    return path


def png_stats(path):
    """coverage + strand-scale detail, via ffmpeg so we need no image library."""
    import struct
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True).stdout
    n = len(raw)
    side = int(n ** 0.5)
    lit = sum(1 for b in raw if b > 18) / max(n, 1)
    # mean absolute horizontal gradient over lit pixels = strand-scale texture
    grad, cnt = 0, 0
    for y in range(0, side - 1, 3):
        row = raw[y * side:(y + 1) * side]
        for x in range(0, side - 1, 2):
            a, b = row[x], row[x + 1]
            if a > 18 or b > 18:
                grad += abs(a - b)
                cnt += 1
    vals = [b for b in raw[::5] if b > 18]
    if len(vals) > 30:
        mean = sum(vals) / len(vals)
        std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
    else:
        std = 0.0
    # bounding box of the lit pixels, to catch a ball drawn half off-screen
    xs0, xs1, ys0, ys1 = side, 0, side, 0
    for y in range(0, side, 4):
        row = raw[y * side:(y + 1) * side]
        for x in range(0, side, 4):
            if row[x] > 18:
                xs0, xs1 = min(xs0, x), max(xs1, x)
                ys0, ys1 = min(ys0, y), max(ys1, y)
    clipped = (xs0 <= 4 or ys0 <= 4 or xs1 >= side - 8 or ys1 >= side - 8) if xs1 else True
    return {"coverage": round(lit, 4), "detail": round(grad / max(cnt, 1), 3),
            "shading": round(std, 2), "clipped": bool(clipped), "px": n}


def gray(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                           "-pix_fmt", "gray", "-"], capture_output=True).stdout


def diff_region(ra, rb, side, x0, y0, x1, y1):
    changed = tot = 0
    for y in range(y0, y1):
        base = y * side
        for x in range(x0, x1, 2):
            i = base + x
            if i >= len(ra) or i >= len(rb):
                continue
            tot += 1
            if abs(ra[i] - rb[i]) > 10:
                changed += 1
    return changed / max(tot, 1)


def diff_png(a, b):
    ra = subprocess.run(["ffmpeg", "-v", "error", "-i", a, "-f", "rawvideo",
                         "-pix_fmt", "gray", "-"], capture_output=True).stdout
    rb = subprocess.run(["ffmpeg", "-v", "error", "-i", b, "-f", "rawvideo",
                         "-pix_fmt", "gray", "-"], capture_output=True).stdout
    n = min(len(ra), len(rb))
    changed = sum(1 for i in range(0, n, 7) if abs(ra[i] - rb[i]) > 10)
    return changed / max(n / 7, 1)


def score(html_path, label=None, port=9340, keep=True):
    label = label or os.path.splitext(os.path.basename(html_path))[0]
    shots = os.path.join(OUT_DIR, label + "_shots")
    shutil.rmtree(shots, ignore_errors=True)
    os.makedirs(shots)
    profile = f"/tmp/furball-score-{label}"
    shutil.rmtree(profile, ignore_errors=True)

    W = H = 900
    proc = subprocess.Popen([
        BRAVE, "--headless=new", f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}", f"--window-size={W},{H}",
        "--use-angle=metal", "--hide-scrollbars", "--force-device-scale-factor=1",
        "--no-first-run", "--disable-extensions", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    res = {"label": label, "errors": [], "loaded": False}
    try:
        target = None
        for _ in range(40):
            time.sleep(0.5)
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
            except Exception:
                continue
            for p in pages:
                if p.get("type") == "page":
                    target = p["webSocketDebuggerUrl"]
            if target:
                break
        if not target:
            res["errors"].append("page never opened")
            return res

        ws = websocket.create_connection(target, timeout=90, max_size=64 * 1024 * 1024,
                                         suppress_origin=True)
        cdp(ws, "Runtime.enable")
        cdp(ws, "Page.enable")
        cdp(ws, "Emulation.setDeviceMetricsOverride",
            {"width": W, "height": H, "deviceScaleFactor": 1, "mobile": False})
        # install the error collector BEFORE the page's own script runs, otherwise a
        # syntax error in their file is invisible and looks like "it just drew nothing"
        cdp(ws, "Page.addScriptToEvaluateOnNewDocument", {"source":
            "window.__errs=[];addEventListener('error',e=>window.__errs.push("
            "(e.message||'')+' @'+(e.filename||'')+':'+(e.lineno||0)));"
            "addEventListener('unhandledrejection',e=>window.__errs.push('promise: '+e.reason));"})
        cdp(ws, "Page.navigate", {"url": "file://" + os.path.abspath(html_path)})
        time.sleep(11)                                  # let it build strands + settle

        res["loaded"] = True
        res["webgl2"] = bool(ev(ws, "!!document.querySelector('canvas') && "
                                    "!!document.createElement('canvas').getContext('webgl2')"))
        res["errors"] = ev(ws, "window.__errs||[]") or []

        # frame rate over ~1.2s
        fps = ev(ws, """new Promise(r=>{let n=0,t0=performance.now();
            function f(){n++;(performance.now()-t0<1200)?requestAnimationFrame(f):r(n/((performance.now()-t0)/1000));}
            requestAnimationFrame(f);})""")
        res["fps"] = round(fps or 0, 1)

        base = shot(ws, os.path.join(shots, "rest.png"))
        res.update(png_stats(base))

        # control: how much the page changes on its own over the same window,
        # so an idle animation can't be mistaken for a response to the stroke
        time.sleep(1.5)
        idle = shot(ws, os.path.join(shots, "idle.png"))
        res["idle_change"] = round(diff_png(base, idle), 4)

        # pet it: press in the middle, drag right, and watch what moved
        cx, cy = W // 2, H // 2
        cdp(ws, "Input.dispatchMouseEvent", {"type": "mousePressed", "x": cx - 160,
                                             "y": cy, "button": "left", "clickCount": 1})
        for i in range(1, 17):
            cdp(ws, "Input.dispatchMouseEvent", {"type": "mouseMoved",
                                                 "x": cx - 160 + i * 20, "y": cy,
                                                 "button": "left", "buttons": 1})
            time.sleep(0.02)
        during = shot(ws, os.path.join(shots, "petted.png"))
        cdp(ws, "Input.dispatchMouseEvent", {"type": "mouseReleased", "x": cx + 160,
                                             "y": cy, "button": "left"})
        time.sleep(2.0)
        after = shot(ws, os.path.join(shots, "relaxed.png"))

        # the honest test: did the STROKE BAND change more than an untouched band
        # of the same size? both see the same ambient animation.
        gi, gd, gr = gray(idle), gray(during), gray(after)
        band = (cx - 180, cy - 70, cx + 180, cy + 70)
        ctrl = (cx - 180, 60, cx + 180, 200)
        res["pet_band"] = round(diff_region(gi, gd, W, *band), 4)
        res["pet_ctrl"] = round(diff_region(gi, gd, W, *ctrl), 4)
        res["pet_ratio"] = round(res["pet_band"] / max(res["pet_ctrl"], 0.004), 2)
        res["relax_change"] = round(diff_region(gd, gr, W, *band), 4)
        res["pet_global"] = round(diff_png(idle, during), 4)
        res["pet_change"] = res["pet_band"]
        ws.close()
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        if not keep:
            shutil.rmtree(shots, ignore_errors=True)

    # verdict: drew something furry, ran, and responded to the stroke
    res["drew"] = res.get("coverage", 0) > 0.06
    res["furry"] = res.get("detail", 0) > 6.0
    res["responds"] = (res.get("pet_band", 0) > 0.02 and res.get("pet_ratio", 0) > 1.6)
    res["springs_back"] = res.get("relax_change", 0) > 0.005
    res["pass"] = all([res["loaded"], res["drew"], res["furry"], res["responds"]])
    json.dump(res, open(os.path.join(OUT_DIR, label + ".score.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


def board():
    rows = []
    for f in sorted(os.listdir(OUT_DIR)):
        if f.endswith(".score.json"):
            rows.append(json.load(open(os.path.join(OUT_DIR, f))))
    if not rows:
        print("no scores yet")
        return
    hdr = (f"{'model':<22}{'pass':<6}{'fps':>7}{'cover':>8}{'detail':>8}"
           f"{'shade':>7}{'idle':>8}{'drag':>8}{'clip':>6}")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda r: (not r.get("pass"), -r.get("detail", 0))):
        tag = 'PASS' if r.get('pass') else ('DNF' if r.get('dnf') else 'fail')
        print(f"{r['label']:<22}{tag:<6}"
              f"{r.get('fps',0):>7}{r.get('coverage',0):>8}{r.get('detail',0):>8}"
              f"{r.get('shading',0):>7}{r.get('idle_change',0):>8}"
              f"{r.get('pet_global',0):>8}{('yes' if r.get('clipped') else 'no'):>6}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["generate", "score", "board"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--label")
    ap.add_argument("--port", type=int, default=9340)
    a = ap.parse_args()
    if a.cmd == "generate":
        generate(a.arg)
    elif a.cmd == "score":
        score(a.arg, a.label, a.port)
    else:
        board()
