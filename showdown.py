#!/usr/bin/env python3
"""Visual showdown, 2026-09-19: Qwen 3.8 27B vs Gemma 4 31B on three builds you can watch.

One variable moves: the model. Same prompt, temperature 0, 24k max tokens, one shot, no
retries. Each model writes a single HTML file and a script judges it in headless Brave.

  python3 showdown.py gen <task> <label> <base_url> <model_name>   # generate one file
  python3 showdown.py judge-breakout <html> <label>                 # score a breakout build
  python3 showdown.py clip <task> <html> <out.mp4> [seconds]         # record a watchable clip

Tasks: furball and spin reuse furball_bench.py's judge (TASK=... python3 furball_bench.py
score ...). breakout is judged here: it has to load with no errors, draw, keep moving
after the space bar, and the paddle has to follow the mouse.
"""
import base64, json, os, re, shutil, signal, subprocess, sys, time, urllib.request

import websocket

HERE = os.path.dirname(os.path.abspath(__file__))
BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"


def out_dir(task):
    d = os.path.join(HERE, "results", task)
    os.makedirs(d, exist_ok=True)
    return d


# ------------------------------------------------------------------ generation
def extract_html(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"```(?:html)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    i = text.find("<")
    return text[i:].strip() if i >= 0 else text.strip()


def gen(task, label, base, model, max_tokens=24000, timeout=3600):
    prompt = open(os.path.join(HERE, f"tasks/{task}/prompt.md")).read()
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0.0}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    meta = {"task": task, "label": label, "model": model, "max_tokens": max_tokens}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.load(r)
    except Exception as e:
        meta.update({"dnf": True, "gen_seconds": round(time.time() - t0, 1), "why": str(e)[:200]})
        json.dump(meta, open(os.path.join(out_dir(task), label + ".gen.json"), "w"), indent=1)
        print(json.dumps(meta), flush=True)
        return meta
    secs = time.time() - t0
    msg = out["choices"][0]["message"]
    text = msg.get("content") or ""
    usage = out.get("usage", {}) or {}
    toks = usage.get("completion_tokens")
    html = extract_html(text)
    path = os.path.join(out_dir(task), label + ".html")
    open(path, "w").write(html)
    open(os.path.join(out_dir(task), label + ".raw.txt"), "w").write(
        (msg.get("reasoning_content") or msg.get("reasoning") or "") + "\n=====\n" + text)
    meta.update({"gen_seconds": round(secs, 1), "completion_tokens": toks,
                 "tok_s": round(toks / secs, 1) if toks else None,
                 "finish_reason": out["choices"][0].get("finish_reason"),
                 "chars": len(html), "complete": "</html>" in html.lower(), "html": path})
    json.dump(meta, open(os.path.join(out_dir(task), label + ".gen.json"), "w"), indent=1)
    print(json.dumps(meta), flush=True)
    return meta


# -------------------------------------------------------------- headless brave
class Page:
    def __init__(self, port, W=960, H=720):
        self.W, self.H = W, H
        prof = f"/tmp/showdown-{port}"
        shutil.rmtree(prof, ignore_errors=True)
        self.proc = subprocess.Popen([
            BRAVE, "--headless=new", f"--remote-debugging-port={port}",
            f"--user-data-dir={prof}", f"--window-size={W},{H}", "--use-angle=metal",
            "--hide-scrollbars", "--force-device-scale-factor=1", "--no-first-run",
            "--disable-extensions", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        target = None
        for _ in range(40):
            time.sleep(0.5)
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
            except Exception:
                continue
            target = next((p["webSocketDebuggerUrl"] for p in pages if p.get("type") == "page"), None)
            if target:
                break
        if not target:
            raise RuntimeError("headless page never opened")
        self.ws = websocket.create_connection(target, timeout=90, max_size=64 * 1024 * 1024,
                                              suppress_origin=True)
        self._id = 0
        self.cdp("Runtime.enable")
        self.cdp("Page.enable")
        self.cdp("Emulation.setDeviceMetricsOverride",
                 {"width": W, "height": H, "deviceScaleFactor": 1, "mobile": False})
        # error collector goes in BEFORE navigation, or a syntax error is invisible
        self.cdp("Page.addScriptToEvaluateOnNewDocument", {"source":
            "window.__errs=[];addEventListener('error',e=>window.__errs.push("
            "(e.message||'')+' @'+(e.filename||'')+':'+(e.lineno||0)));"
            "addEventListener('unhandledrejection',e=>window.__errs.push('promise: '+e.reason));"})

    def cdp(self, method, params=None):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def ev(self, expr):
        r = self.cdp("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                          "awaitPromise": True})
        return r.get("result", {}).get("value")

    def go(self, path, settle=3):
        self.cdp("Page.navigate", {"url": "file://" + os.path.abspath(path)})
        time.sleep(settle)

    def shot(self, path, fmt="png"):
        data = self.cdp("Page.captureScreenshot", {"format": fmt, **({"quality": 90} if fmt == "jpeg" else {})})["data"]
        open(path, "wb").write(base64.b64decode(data))
        return path

    def mouse(self, typ, x, y, buttons=0):
        p = {"type": typ, "x": x, "y": y}
        if typ in ("mousePressed", "mouseReleased"):
            p.update({"button": "left", "clickCount": 1})
        if buttons:
            p.update({"button": "left", "buttons": buttons})
        self.cdp("Input.dispatchMouseEvent", p)

    def key(self, key, code, kc):
        for t in ("keyDown", "keyUp"):
            self.cdp("Input.dispatchKeyEvent", {"type": t, "key": key, "code": code,
                                                "windowsVirtualKeyCode": kc,
                                                "nativeVirtualKeyCode": kc,
                                                **({"text": " "} if key == " " and t == "keyDown" else {})})

    def canvas_rect(self):
        r = self.ev("(()=>{const c=[...document.querySelectorAll('canvas')].sort((a,b)=>"
                    "b.width*b.height-a.width*a.height)[0];if(!c)return null;const r=c.getBoundingClientRect();"
                    "return [r.left,r.top,r.right,r.bottom]})()")
        if not r:
            return (0, 0, self.W, self.H)
        x0, y0, x1, y1 = [int(v) for v in r]
        return (max(x0, 0), max(y0, 0), min(x1, self.W), min(y1, self.H))

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def gray(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                           "-pix_fmt", "gray", "-"], capture_output=True).stdout


def frac_changed(a, b, W, rows=None):
    y0, y1 = rows or (0, len(a) // W)
    ch = tot = 0
    for y in range(y0, y1, 2):
        for x in range(0, W, 3):
            i = y * W + x
            if i < len(a) and i < len(b):
                tot += 1
                ch += abs(a[i] - b[i]) > 12
    return ch / max(tot, 1)


def bright_x(a, W, H, y0=None, y1=None):
    """x centre of the longest bright horizontal run in the bottom of the play field,
    which is where every Breakout draws its paddle."""
    best = None
    for y in range(y0 if y0 is not None else int(H * 0.78), y1 if y1 is not None else H - 4, 2):
        row = a[y * W:(y + 1) * W]
        if len(row) < W:
            continue
        med = sorted(row[::8])[len(row[::8]) // 2]
        run = start = 0
        for x in range(W):
            if row[x] > med + 40:
                if run == 0:
                    start = x
                run += 1
                if run >= 40 and (best is None or run > best[0]):
                    best = (run, start + run // 2)
            else:
                run = 0
    return best[1] if best else None


def lit(a):
    return sum(1 for v in a[::7] if v > 18) / max(len(a[::7]), 1)


# --------------------------------------------------------------- breakout judge
def judge_breakout(html, label, port=9351):
    shots = os.path.join(out_dir("breakout"), label + "_shots")
    shutil.rmtree(shots, ignore_errors=True)
    os.makedirs(shots)
    W, H = 960, 720
    res = {"label": label, "loaded": False, "errors": []}
    pg = Page(port, W, H)
    try:
        pg.go(html, settle=3)
        res["loaded"] = True
        res["canvas"] = bool(pg.ev("!!document.querySelector('canvas')"))
        cx0, cy0, cx1, cy1 = pg.canvas_rect()
        MY = cy1 - max(20, (cy1 - cy0) // 12)          # mouse row: low in the play field
        pg.mouse("mouseMoved", W // 2, MY)
        a = gray(pg.shot(os.path.join(shots, "start.png")))
        res["coverage"] = round(lit(a), 4)
        # launch, then play: the frame keeps changing while the ball is in flight
        pg.mouse("mouseMoved", (cx0 + cx1) // 2, MY)
        pg.key(" ", "Space", 32)
        time.sleep(0.4)
        seq = []
        t0 = time.time()
        k = 0
        while time.time() - t0 < 4:
            # mouse held still, so every change between frames is the game moving on its own.
            # Space every second relaunches a ball that is waiting after a lost life (the
            # prompt says space launches); without it a game that correctly parks the ball
            # on the paddle looks frozen.
            if k % 4 == 3:
                pg.key(" ", "Space", 32)
            seq.append(gray(pg.shot(os.path.join(shots, f"play_{k:03d}.png"))))
            k += 1
            time.sleep(0.25)
        changes = [frac_changed(seq[i], seq[i + 1], W) for i in range(len(seq) - 1)]
        res["play_change_median"] = round(sorted(changes)[len(changes) // 2], 5) if changes else 0
        res["moving_frac"] = round(sum(c > 0.0002 for c in changes) / max(len(changes), 1), 3)
        # paddle follows the mouse: find the bright blob in the bottom band with the mouse
        # held far left, then far right. It has to travel most of the way across.
        xs = {}
        for side, mx in (("left", cx0 + 60), ("right", cx1 - 60)):
            for _ in range(6):
                pg.mouse("mouseMoved", mx, MY)
                time.sleep(0.1)
            xs[side] = bright_x(gray(pg.shot(os.path.join(shots, f"paddle_{side}.png"))), W, H,
                                cy0 + int((cy1 - cy0) * 0.72), cy1 - 2)
        res["paddle_left_x"], res["paddle_right_x"] = xs["left"], xs["right"]
        res["field_w"] = cx1 - cx0
        res["paddle_travel"] = (xs["right"] - xs["left"]) if None not in xs.values() else 0
        res["field_change"] = round(frac_changed(seq[0], seq[-1], W, (0, int(H * 0.5))), 4) if seq else 0
        res["errors"] = pg.ev("window.__errs||[]") or []
    finally:
        pg.close()
    res["drew"] = res.get("coverage", 0) > 0.03
    res["paddle_follows"] = res.get("paddle_travel", 0) > 0.4 * (res.get("field_w") or W)
    res["plays"] = res.get("moving_frac", 0) >= 0.5
    res["clean"] = len(res["errors"]) == 0
    res["pass"] = all([res["loaded"], res.get("canvas"), res["drew"], res["paddle_follows"],
                       res["plays"], res["clean"]])
    json.dump(res, open(os.path.join(out_dir("breakout"), label + ".score.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


# ------------------------------------------------------------------- clip maker
def clip(task, html, out_mp4, seconds=9, port=9361):
    """Screenshots as fast as CDP allows, then stitched at the measured rate so the clip
    plays back in real time. Interaction is scripted per task so both models get the
    same hand on the mouse."""
    import math
    W, H = (900, 900) if task in ("furball", "spin") else (960, 720)
    fdir = f"/tmp/clip_{os.path.basename(out_mp4)}"
    shutil.rmtree(fdir, ignore_errors=True)
    os.makedirs(fdir)
    pg = Page(port, W, H)
    n = 0
    try:
        pg.go(html, settle=10 if task == "furball" else 3)
        cx0, cy0, cx1, cy1 = pg.canvas_rect()
        MY = cy1 - max(20, (cy1 - cy0) // 12)
        if task == "breakout":
            pg.mouse("mouseMoved", (cx0 + cx1) // 2, MY)
            pg.key(" ", "Space", 32)
        t0 = time.time()
        pressed = False
        while time.time() - t0 < seconds:
            t = time.time() - t0
            if task in ("furball", "spin"):
                # rest for 2s, stroke across the middle for 3s, let go and watch
                if 2 <= t < 5:
                    x = int(W / 2 - 220 + (t - 2) / 3 * 440)
                    y = int(H / 2 + 40 * math.sin((t - 2) * 3))
                    if not pressed:
                        pg.mouse("mousePressed", x, y)
                        pressed = True
                    pg.mouse("mouseMoved", x, y, buttons=1)
                elif pressed:
                    pg.mouse("mouseReleased", W // 2 + 220, H // 2)
                    pressed = False
            else:
                x = int((cx0 + cx1) / 2 + ((cx1 - cx0) / 2 - 60) * math.sin(t * 1.6))
                pg.mouse("mouseMoved", x, MY)
                if int(t * 2) % 6 == 5:
                    pg.key(" ", "Space", 32)
            pg.shot(os.path.join(fdir, f"f_{n:04d}.jpg"), fmt="jpeg")
            n += 1
        secs = time.time() - t0
    finally:
        pg.close()
    fps = max(n / secs, 1)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", f"{fps:.2f}", "-i",
                    os.path.join(fdir, "f_%04d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-r", "30", out_mp4], check=True)
    shutil.rmtree(fdir, ignore_errors=True)
    print(f"clip {out_mp4}: {n} frames over {secs:.1f}s ({fps:.1f} captured fps)", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gen":
        gen(a[1], a[2], a[3], a[4])
    elif a[0] == "judge-breakout":
        judge_breakout(a[1], a[2])
    elif a[0] == "clip":
        clip(a[1], a[2], a[3], float(a[4]) if len(a) > 4 else 9)
