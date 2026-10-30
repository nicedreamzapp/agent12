#!/usr/bin/env python3
"""Build docs/all/index.html: every suite Agent-12 logs, every row we hold, in one place.

Three kinds of row, never blended, each labelled where it stands:
  measured here   - a run from results/, on the stated hardware
  community       - a validated file from submissions/, with who ran it and on what
  reported        - a vendor's own published number, with the source, for reference only

The big benchmarks are covered everywhere. This page exists for the small ones: the test
that tells you whether a model reads a label, finds a fact at 128k, or emits a tool call
the runtime can execute.

    python tools/build_all.py
"""
import glob
import html
import io
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "all", "index.html")

CSS = """
:root{--bg:#0c0d10;--card:#15171c;--line:#23262e;--ink:#e8eaee;--dim:#9aa1ad;
--good:#4ade80;--warn:#fbbf24;--accent:#7dd3fc;--dead:#6b7280}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:40px 22px 80px}
h1{font-size:27px;margin:0 0 8px;letter-spacing:-.3px}
h2{font-size:17px;margin:34px 0 4px}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.sub{color:var(--dim);font-size:15px;margin:0 0 26px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:15px 17px;margin:0 0 14px}
.measures{color:var(--dim);font-size:13px;margin:0 0 11px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--dim);font-weight:600;padding:6px 8px;font-size:11.5px;
text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--line)}
td{padding:6px 8px;border-bottom:1px solid #1b1e25;vertical-align:top}
tr:last-child td{border-bottom:0}
.pill{display:inline-block;border-radius:999px;padding:1px 9px;font-size:11px;
border:1px solid var(--line);color:var(--dim)}
.live{color:var(--good);border-color:#1d4a30}
.draft{color:var(--warn);border-color:#4a3a10}
.tag{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;padding:1px 6px;
border-radius:4px;white-space:nowrap}
.t-mine{background:#14341f;color:var(--good)}
.t-comm{background:#102a3a;color:var(--accent)}
.t-rep{background:#2a2410;color:var(--warn)}
.empty{color:var(--dead);font-size:13px;padding:4px 0}
.foot{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);
color:var(--dim);font-size:13px}
.num{font-variant-numeric:tabular-nums}
"""


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def pass_rate(run):
    tasks = run.get("tasks") or {}
    if not tasks:
        return None, 0, None
    passed = sum(1 for t in tasks.values() if t.get("pass"))
    secs = sum(t.get("seconds") or 0 for t in tasks.values())
    return round(100 * passed / len(tasks), 1), len(tasks), round(secs, 1)


def mine_rows(suite, meta):
    """Rows from results/, named through site/meta.json so displays stay consistent."""
    if not suite.get("results_glob"):
        return []
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, suite["results_glob"]))):
        run = load(p)
        rate, n, secs = pass_rate(run)
        if rate is None:
            continue
        key = os.path.splitext(os.path.basename(p))[0]
        display, tok_s = key, None
        for _, r in (meta.get("rows") or {}).items():
            if r.get("easy") == key or r.get("hard") == key:
                display, tok_s = r["display"], r.get("tok_s")
                break
        rows.append({"kind": "mine", "model": display,
                     "hardware": meta.get("hardware_default", ""),
                     "metrics": {"pass_rate": rate, "wall_s": secs,
                                 **({"tok_s": tok_s} if tok_s else {})},
                     "n": n, "who": "Agent-12", "who_url": "", "run": key})
    rows.sort(key=lambda r: -(r["metrics"].get("pass_rate") or 0))
    return rows


def community_rows(suite_id):
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "submissions", "*.json"))):
        if os.path.basename(p).startswith("EXAMPLE"):
            continue
        d = load(p)
        if d.get("suite") != suite_id:
            continue
        rows.append({"kind": "community", "model": d["model"],
                     "hardware": d["hardware"], "metrics": d["metrics"],
                     "n": d.get("n_items"), "who": d["submitted_by"],
                     "who_url": d.get("submitted_by_url", ""),
                     "run": d.get("log_url", "")})
    return rows


def fmt(metrics, reg):
    out = []
    for k, v in metrics.items():
        if v is None:
            continue
        unit = (reg["metrics"].get(k) or {}).get("unit", "")
        out.append(f'{k.replace("_", " ")} <b class="num">{v}</b> {html.escape(unit)}')
    return ", ".join(out) or "<span class='empty'>no metrics</span>"


def suite_block(suite, meta, reg):
    rows = mine_rows(suite, meta) + community_rows(suite["id"])
    status = "live" if suite["status"] == "live" else "draft"
    head = (f'<h2>{html.escape(suite["title"])} '
            f'<span class="pill {status}">{status}</span></h2>'
            f'<p class="measures">{html.escape(suite["measures"])}</p>')

    if suite["id"] == "mac-fit":
        # This suite's results are a page per model, not rows, so point at them
        # instead of claiming nothing is logged.
        body = ('<div class="measures" style="margin:0">10 models worked out so far, '
                'one page each, memory by Mac from 8 GB to 128 GB: '
                '<a href="../mac-fit/">will it fit my Mac</a>.</div>')
    elif not rows:
        body = (f'<div class="empty">Nothing logged yet. '
                f'{html.escape(suite["how"])}</div>')
    else:
        trs = ""
        for r in rows:
            who = (f'<a href="{html.escape(r["who_url"])}">{html.escape(r["who"])}</a>'
                   if r["who_url"] else html.escape(r["who"]))
            tag = ('<span class="tag t-mine">measured here</span>'
                   if r["kind"] == "mine" else
                   '<span class="tag t-comm">community</span>')
            trs += (f'<tr><td>{tag}</td><td>{html.escape(r["model"])}</td>'
                    f'<td>{fmt(r["metrics"], reg)}</td>'
                    f'<td>{html.escape(r["hardware"])}</td>'
                    f'<td>{r["n"] or ""}</td><td>{who}</td></tr>')
        body = ('<table><thead><tr><th></th><th>Model</th><th>Result</th>'
                '<th>Hardware</th><th>Items</th><th>Ran it</th></tr></thead>'
                f'<tbody>{trs}</tbody></table>')
    return head + f'<div class="card">{body}</div>'


def reported_block(meta):
    rep = meta.get("reported") or []
    if not rep:
        return ""
    trs = ""
    for r in rep:
        trs += (f'<tr><td><span class="tag t-rep">reported</span></td>'
                f'<td>{html.escape(r["display"])}</td>'
                f'<td>{html.escape(r.get("scores", ""))}</td>'
                f'<td><a href="{html.escape(r.get("url", ""))}">'
                f'{html.escape(r.get("source", ""))}</a></td></tr>')
    return ('<h2>Published by the vendor, not run here</h2>'
            '<p class="measures">Their own numbers, their own hardware, kept separate '
            'on purpose. Useful context, not a result.</p>'
            '<div class="card"><table><thead><tr><th></th><th>Model</th>'
            '<th>Claimed</th><th>Source</th></tr></thead>'
            f'<tbody>{trs}</tbody></table></div>')


def main():
    reg = load(os.path.join(ROOT, "suites", "registry.json"))
    meta = load(os.path.join(ROOT, "site", "meta.json"))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    live = [s for s in reg["suites"] if s["status"] == "live"]
    draft = [s for s in reg["suites"] if s["status"] != "live"]
    blocks = "".join(suite_block(s, meta, reg) for s in live + draft)
    n_comm = len([p for p in glob.glob(os.path.join(ROOT, "submissions", "*.json"))
                  if not os.path.basename(p).startswith("EXAMPLE")])

    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Every local model test we log · Agent-12</title>
<meta name="description" content="Agent, vision, speech, long context and tool-call
results for local models, measured and community submitted, in one place.">
<style>{CSS}</style></head><body><div class="wrap">

<h1>Every test we log</h1>
<p class="sub">Everyone publishes the big benchmarks. Nobody logs the small ones, which
are the ones that decide whether a model is usable: does it read the label, find the fact
at 128k, emit a tool call that parses, fit the machine you own. {len(reg['suites'])} suites
here, {n_comm} community submission{'s' if n_comm != 1 else ''} so far, and every row says
who ran it and on what.</p>

<div class="card">
<b>Add yours.</b> Copy
<a href="https://github.com/nicedreamzapp/agent12/blob/main/submissions/EXAMPLE-fill-this-in.json">the
template</a>, fill it in, open a pull request, or
<a href="https://github.com/nicedreamzapp/agent12/issues/new?template=submit-result.yml">open
an issue</a> and it gets filed for you. A number with no machine named gets rejected by
<a href="https://github.com/nicedreamzapp/agent12/blob/main/tools/validate_submissions.py">the
validator</a>, not by an opinion. Suites marked draft have no harness written yet, so the
first submission defines the format.
</div>

{blocks}
{reported_block(meta)}

<div class="foot">
<a href="../">Agent-12 leaderboard</a> ·
<a href="../mac-fit/">will it fit my Mac</a> ·
<a href="https://github.com/nicedreamzapp/agent12">source</a> ·
<a href="https://github.com/nicedreamzapp/agent12/blob/main/METHODOLOGY.md">methodology</a><br><br>
Built {datetime.now(timezone.utc).strftime('%Y-%m-%d')}. Run
<code>python tools/build_all.py</code> to rebuild this page.
</div>
</div></body></html>""")
    print(f"wrote {OUT}")
    print(f"  {len(live)} live suites, {len(draft)} draft, {n_comm} community submissions")


if __name__ == "__main__":
    main()
