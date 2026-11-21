#!/usr/bin/env python3
"""Build the Will it fit my Mac pages (docs/mac-fit/) from data/mac-fit-targets.json.

Memory needed = weights (summed safetensors) + KV cache (from config.json) + 1.2 GB runtime.
Each Mac is checked against two GPU wired limits:
  default: macOS lets the GPU wire about 75% of unified memory out of the box
  raised:  sudo sysctl iogpu.wired_limit_mb=<N>, leaving 8 GB for macOS
A model that ships an MTP head (speculative decoding) also gets a line without it,
since that head can be skipped or kept off the GPU.
"""
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "mac-fit-targets.json")
OUT = os.path.join(ROOT, "docs", "mac-fit")

GB = 1e9
RUNTIME_GB = 1.2
DEFAULT = 0.75
HEADROOM_GB = 8
MACS = [8, 16, 18, 24, 32, 36, 48, 64, 96, 128]
CONTEXTS = [(4096, "4k"), (8192, "8k"), (32768, "32k"), (131072, "128k")]
HF_QUANTS = 29

CSS = """:root{--bg:#0c0d10;--card:#15171c;--line:#23262e;--ink:#e8eaee;--dim:#9aa1ad;
--good:#4ade80;--bad:#f87171;--warn:#fbbf24;--accent:#7dd3fc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
.wrap{max-width:780px;margin:0 auto;padding:40px 22px 70px}
h1{font-size:25px;line-height:1.25;margin:0 0 6px;letter-spacing:-.2px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);
margin:34px 0 12px;font-weight:600}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.sub{color:var(--dim);margin:0 0 26px;font-size:15px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px 18px;margin:0 0 12px}
.pill{display:inline-block;background:#1c1f26;border:1px solid var(--line);
border-radius:999px;padding:2px 10px;font-size:12px;color:var(--dim);margin:0 6px 6px 0}
.big{font-size:30px;font-weight:650;letter-spacing:-.5px}
.row{display:flex;justify-content:space-between;gap:14px;padding:7px 0;
border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}
.row span:last-child{color:var(--dim);text-align:right}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--dim);font-weight:600;padding:7px 8px;
border-bottom:1px solid var(--line);font-size:12px;text-transform:uppercase;
letter-spacing:.06em}
td{padding:7px 8px;border-bottom:1px solid #1b1e25}
tr:last-child td{border-bottom:0}
.y{color:var(--good)}.n{color:var(--bad)}.t{color:var(--warn)}
code{background:#1b1e25;border:1px solid var(--line);border-radius:5px;
padding:1px 6px;font-size:12.5px}
pre{background:#1b1e25;border:1px solid var(--line);border-radius:9px;
padding:13px 15px;overflow-x:auto;font-size:12.5px;margin:0}
.note{color:var(--dim);font-size:12.5px;margin:9px 0 0}
.foot{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);
color:var(--dim);font-size:13px}
.tag{font-size:11px;text-transform:uppercase;letter-spacing:.07em;
padding:1px 7px;border-radius:4px;margin-right:7px}
.m{background:#14341f;color:var(--good)}
.c{background:#2d2410;color:var(--warn)}
.u{background:#2a1515;color:var(--bad)}"""


def default_limit(mac):
    return mac * DEFAULT


def raised_limit(mac):
    return max(mac * DEFAULT, mac - HEADROOM_GB)


def kv_gb(t, ctx):
    return 2 * t["layers"] * t["kv_heads"] * t["head_dim"] * 2 * ctx / GB


def need_gb(t, ctx, weights_gb):
    return kv_gb(t, ctx) + weights_gb + RUNTIME_GB


def fit(need):
    """(smallest Mac at the default limit, smallest Mac with the limit raised)."""
    d = next((m for m in MACS if need <= default_limit(m)), None)
    r = next((m for m in MACS if need <= raised_limit(m)), None)
    return d, r


def fit_text(need):
    d, r = fit(need)
    if d:
        return f"{d} GB Mac"
    if r:
        return f"{r} GB Mac with the GPU limit raised"
    return f"over {MACS[-1]} GB"


def cell(need, mac):
    if need <= default_limit(mac) - 2:
        return '<td class="y">yes</td>'
    if need <= default_limit(mac):
        return '<td class="t">tight</td>'
    if need <= raised_limit(mac):
        return '<td class="t">raised</td>'
    return '<td class="n">no</td>'


def page(t):
    name = t["model_id"].split("/", 1)[1]
    e = html.escape
    weights = t["stored_bytes"] / GB
    mtp = t.get("mtp_bytes", 0) / GB
    n8 = need_gb(t, 8192, weights)
    d8, r8 = fit(n8)
    if d8:
        headline, how = f"{d8} GB Mac", "at the default GPU limit"
    elif r8:
        headline, how = f"{r8} GB Mac", "with the GPU limit raised (see below)"
    else:
        headline, how = f"&gt;{MACS[-1]} GB Mac", "even with the GPU limit raised"
    default_also = ""
    if not d8 and r8:
        default_also = f" At the out-of-the-box limit it needs more than a {MACS[-1]} GB Mac."

    rows = "".join(
        f'<div class="row"><span>{lab} context</span><span>{kv_gb(t, c):.2f} GB KV + '
        f'{weights:.1f} GB weights + {RUNTIME_GB} GB runtime = <b style="color:var(--ink)">'
        f'{need_gb(t, c, weights):.1f} GB</b>, {fit_text(need_gb(t, c, weights))}</span></div>'
        for c, lab in CONTEXTS)

    mtp_card = ""
    if mtp:
        n8_nomtp = n8 - mtp
        mtp_card = f"""
<div class="card">
  <div class="big">{n8_nomtp:.1f} GB without the MTP head</div>
  <div class="note"><span class="tag m">measured</span>{mtp:.1f} GB of the {weights:.1f} GB
  is the MTP (multi-token prediction) head, summed from the <code>mtp.*</code> tensors in your
  safetensors headers. It only speeds up decoding, so a runtime that skips it or keeps it off
  the GPU needs {n8_nomtp:.1f} GB at 8k context: {fit_text(n8_nomtp)}.</div>
</div>
"""

    head = "".join(f"<th>{m}</th>" for m in MACS)
    body = "".join(
        f"<tr><td>{lab}</td><td>{need_gb(t, c, weights):.1f} GB</td>"
        + "".join(cell(need_gb(t, c, weights), m) for m in MACS) + "</tr>"
        for c, lab in CONTEXTS)
    m128 = MACS[-1]
    sysctl_mb = int(raised_limit(m128) * 1024)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(name)} on a Mac: what it needs</title>
<meta name="description" content="RAM needed to run {e(name)} with MLX on
Apple Silicon, worked out from the file list and config.">
<style>
{CSS}
</style></head><body><div class="wrap">

<h1>{e(name)}<br>on a Mac: what it actually needs</h1>
<p class="sub">For {e(t["fullname"])}. Worked out from your repo, no sign-up,
nothing to click.</p>

<div class="card">
  <div class="pill">{t["quant_bits"]}-bit</div>
  <div class="pill">{t["layers"]} layers</div>
  <div class="pill">{t["kv_heads"]} KV heads</div>
  <div class="pill">head dim {t["head_dim"]}</div>
  <div class="pill">{t["likes"]} likes</div>
  <div class="pill">{t["downloads"]:,} downloads</div>
  <div style="margin-top:10px">
    <div class="big">{weights:.1f} GB</div>
    <div class="note"><span class="tag m">measured</span>download size, summed from the
    {t["weight_files"]} safetensors {"file" if t["weight_files"] == 1 else "files"} in your repo</div>
  </div>
</div>

<div class="card">
  <div class="big">{headline}</div>
  <div class="note"><span class="tag c">computed</span>the smallest machine that holds it
  at 8k context, {how}.{default_also}</div>
</div>
{mtp_card}
<h2>What it needs as context grows</h2>
<div class="card">{rows}</div>
<p class="note">KV cache = 2 tensors x {t["layers"]} layers x {t["kv_heads"]} KV heads
x {t["head_dim"]} head dim x 2 bytes (fp16) x tokens. Read straight off your
<code>config.json</code>. Runtime overhead is the 1.2 GB I see for Python, MLX, the
tokenizer and activations on my own runs.</p>

<h2>Mac by Mac</h2>
<div class="card" style="overflow-x:auto">
<table><thead><tr><th>Context</th><th>Needs</th>{head}</tr></thead>
<tbody>{body}</tbody></table>
<p class="note">Columns are unified memory in GB. <span class="y">yes</span> fits at the
default GPU limit, about 75% of unified memory. <span class="t">tight</span> fits there but
leaves under 2 GB, so expect swap once a browser is open. <span class="t">raised</span> fits once the
limit is raised to leave 8 GB for macOS. <span class="n">no</span> does not fit either way.</p>
</div>

<h2>Raising the GPU limit</h2>
<div class="card">
<div class="note" style="margin-top:0">macOS caps how much unified memory the GPU can wire,
about 75% by default. That cap is a setting, not a hardware limit. On a {m128} GB Mac this
leaves 8 GB for macOS and hands the rest to MLX until the next reboot:</div>
<pre style="margin-top:10px">sudo sysctl iogpu.wired_limit_mb={sysctl_mb}</pre>
<div class="note">Swap in your own number: unified memory in GB, minus 8, times 1024.</div>
</div>

<h2>Run it</h2>
<pre>pip install mlx-lm
mlx_lm.generate --model {e(t["model_id"])} \\
  --prompt "hello" --max-tokens 100</pre>

<h2>What is not on this page</h2>
<div class="card">
  <div class="note"><span class="tag u">not measured</span>Tokens per second. That needs a
  real run on real silicon and I will not print a number I have not seen. If you want it,
  reply and I will run {e(name)} on an M5 and add the result here with the
  command I used.</div>
</div>

<div class="foot">
Speed, measured: this page is about memory. For how fast models actually run on Apple
Silicon, with the tasks and judging open, see the
<a href="../">Agent-12 local agent leaderboard</a>.<br><br>
Built by Matt Macosko, who publishes
<a href="https://huggingface.co/divinetribe">{HF_QUANTS} MLX quants</a> and wrote
<a href="https://github.com/nicedreamzapp/claude-code-local">claude-code-local</a>,
which runs Claude Code fully on-device on Apple Silicon.
Source for this page: your <a href="https://huggingface.co/{e(t["model_id"])}">model
repo</a> and its config.
</div>
</div></body></html>
"""


def index(targets):
    rows = "".join(
        f'<div class="row"><span><a href="{e_(t["author"])}.html">{e_(t["fullname"])}</a> '
        f'<span style="color:var(--dim)">{e_(t["model_id"].split("/", 1)[1])}</span></span>'
        f'<span>{need_gb(t, 8192, t["stored_bytes"] / GB):.1f} GB, '
        f'{fit_text(need_gb(t, 8192, t["stored_bytes"] / GB))}</span></div>'
        for t in targets)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Will it fit my Mac</title>
<style>
{CSS}
</style></head>
<body><div class="wrap"><h1>Will it fit my Mac</h1>
<p class="sub">RAM each of these MLX models needs at 8k context, worked out from the
repo file list and config. One page each. For measured speed instead of memory, see the
<a href="../">Agent-12 leaderboard</a>.</p>
<div class="card">{rows}</div>
<p class="note">The Mac named is the smallest that holds the model at the default GPU limit
(about 75% of unified memory), or with the limit raised to leave 8 GB for macOS where it says so.</p>
</div></body></html>
"""


def e_(s):
    return html.escape(s)


def main():
    targets = json.load(open(DATA))
    for t in targets:
        with open(os.path.join(OUT, f'{t["author"]}.html'), "w") as f:
            f.write(page(t))
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(index(targets))
    print(f"wrote {len(targets)} pages + index to {OUT}")


if __name__ == "__main__":
    main()
