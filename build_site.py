#!/usr/bin/env python3
"""Build site/index.html from results/*.json + site/meta.json.

site/meta.json maps a scoreboard row key to its display info and which
result runs feed it:

  {
    "hardware_default": "Apple M5, 128 GB unified memory",
    "rows": {
      "qwen3-coder-30b": {
        "display": "Qwen3-Coder-30B-A3B (MLX 8-bit)",
        "params": "30B MoE (3B active)",
        "tok_s": 68,
        "easy": "qwen30_easy_v1",
        "hard": "qwen30_hard_v1",
        "kind": "local"
      },
      ...
    }
  }

kind: "local" | "cloud" — cloud rows render in a labeled reference section.
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
SITE = HERE / "site"
OUT = HERE / "docs"


def load_run(name):
    p = RESULTS / f"{name}.json"
    if not name or not p.exists():
        return None
    d = json.loads(p.read_text())
    total = round(sum(t["seconds"] for t in d["tasks"].values()), 1)
    return {"score": d["score"], "seconds": total, "run": name,
            "version": d.get("harness_version", "pre-1.0")}


def cellpair(run):
    if not run:
        return '<td class="na">—</td><td class="na">—</td>'
    p, n = run["score"].split("/")
    cls = "gold" if p == n else ""
    return (f'<td class="score {cls}">{run["score"]}</td>'
            f'<td class="secs">{run["seconds"]}s</td>')


def build():
    meta = json.loads((SITE / "meta.json").read_text())
    hw = meta.get("hardware_default", "")
    local_rows, cloud_rows = [], []
    for key, row in meta["rows"].items():
        easy, hard = load_run(row.get("easy")), load_run(row.get("hard"))
        tok = row.get("tok_s")
        tr = (f'<tr><td class="model">{html.escape(row["display"])}'
              f'<span class="params">{html.escape(row.get("params", ""))}</span></td>'
              + cellpair(easy) + cellpair(hard)
              + f'<td class="secs">{tok if tok else "—"}</td>'
              + f'<td class="hw">{html.escape(row.get("hardware", hw))}</td></tr>')
        (cloud_rows if row.get("kind") == "cloud" else local_rows).append(tr)

    page = TEMPLATE.replace("{{LOCAL_ROWS}}", "\n".join(local_rows))
    page = page.replace("{{CLOUD_ROWS}}", "\n".join(cloud_rows))
    page = page.replace("{{UPDATED}}", meta.get("updated", ""))
    (OUT / "index.html").write_text(page)
    print(f"wrote {OUT / 'index.html'} ({len(local_rows)} local rows, {len(cloud_rows)} cloud)")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent-12 — the local agent leaderboard</title>
<style>
  :root {
    --bg: #f7f6f3; --panel: #ffffff; --ink: #1a1e24; --sub: #5b6472;
    --line: #e3e1db; --gold: #0b7a3e; --accent: #b4530a;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #12151a; --panel: #1a1f27; --ink: #e8e6e1; --sub: #97a0ad;
            --line: #2a313b; --gold: #4cc47e; --accent: #e88a3a; }
  }
  * { box-sizing: border-box; margin: 0; }
  body { background: var(--bg); color: var(--ink);
         font: 16px/1.55 -apple-system, "Segoe UI", Roboto, sans-serif;
         padding: 2.5rem 1rem 4rem; }
  main { max-width: 980px; margin: 0 auto; }
  h1 { font-size: 1.9rem; letter-spacing: -0.02em; }
  .tag { color: var(--sub); margin: .4rem 0 2rem; max-width: 46rem; }
  h2 { font-size: 1.05rem; margin: 2.2rem 0 .6rem; color: var(--sub);
       text-transform: uppercase; letter-spacing: .08em; font-weight: 600; }
  .tablewrap { overflow-x: auto; background: var(--panel); border: 1px solid var(--line);
               border-radius: 10px; }
  table { border-collapse: collapse; width: 100%; min-width: 780px; }
  th, td { padding: .65rem .9rem; text-align: left; border-top: 1px solid var(--line);
           white-space: nowrap; }
  thead th { border-top: none; color: var(--sub); font-size: .78rem;
             text-transform: uppercase; letter-spacing: .06em; }
  td.model { font-weight: 600; }
  .params { display: block; font-weight: 400; font-size: .78rem; color: var(--sub); }
  td.score { font-variant-numeric: tabular-nums; font-weight: 700; }
  td.score.gold { color: var(--gold); }
  td.secs { font-variant-numeric: tabular-nums; color: var(--sub); }
  td.hw { color: var(--sub); font-size: .85rem; white-space: normal; }
  td.na { color: var(--line); }
  .foot { margin-top: 2.2rem; color: var(--sub); font-size: .9rem; max-width: 46rem; }
  .foot a { color: var(--accent); }
  .rules { margin-top: 1rem; padding-left: 1.2rem; }
  .rules li { margin: .35rem 0; }
</style>
</head>
<body>
<main>
  <h1>Agent-12 <span style="color:var(--sub); font-weight:400;">— the local agent leaderboard</span></h1>
  <p class="tag">Which model can actually be your agent on your own hardware?
  Measured by doing real agent tasks in a sandboxed working directory —
  judged by the filesystem, never by the model's prose. Temperature 0, fixed
  caps, fresh sandbox per task, one variable moved per comparison.</p>

  <h2>Local models</h2>
  <div class="tablewrap">
  <table>
    <thead><tr>
      <th>Model</th>
      <th>Easy (12)</th><th>time</th>
      <th>Hard (8)</th><th>time</th>
      <th>tok/s</th>
      <th>Hardware</th>
    </tr></thead>
    <tbody>
{{LOCAL_ROWS}}
    </tbody>
  </table>
  </div>

  <h2>Cloud reference (not competing — context)</h2>
  <div class="tablewrap">
  <table>
    <thead><tr>
      <th>Model</th>
      <th>Easy (12)</th><th>time</th>
      <th>Hard (8)</th><th>time</th>
      <th>tok/s</th>
      <th>Where it runs</th>
    </tr></thead>
    <tbody>
{{CLOUD_ROWS}}
    </tbody>
  </table>
  </div>

  <div class="foot">
    <p><strong>How to trust a number here:</strong></p>
    <ul class="rules">
      <li>Every judge is smoke-tested on a known-good AND a known-bad
          reference solution before it judges anything real.</li>
      <li>Tasks that ship a test file pin its hash — editing the test scores zero.</li>
      <li>All rows run the same tasks, same caps, same judges, on the stated hardware.</li>
      <li>Cloud rows are labeled reference points, not contestants.</li>
    </ul>
    <p style="margin-top:1rem;">Tasks, judges, runner, and the validation gate are open:
    <a href="https://github.com/nicedreamzapp/agent12">github.com/nicedreamzapp/agent12</a>
    · <a href="https://github.com/nicedreamzapp/agent12/blob/main/METHODOLOGY.md">methodology</a>
    · <a href="https://github.com/nicedreamzapp/agent12/blob/main/CONTAMINATION.md">contamination policy</a>.
    Cloud reference times include network/API round-trips — that is the honest
    end-to-end experience. Updated {{UPDATED}}.</p>
  </div>
</main>
</body>
</html>
"""

if __name__ == "__main__":
    build()
