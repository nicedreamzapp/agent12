#!/usr/bin/env python3
"""Run the vision-read-text suite against a local MLX vision model.

Needs Apple Silicon and mlx-vlm. It downloads the item images once, pins them by sha256,
asks the model to read the text, scores exact matches after normalizing, and writes a
submission file that tools/validate_submissions.py accepts as is.

    python suites/vision-read-text/run.py --model mlx-community/Qwen3-VL-8B-Instruct-4bit
    python suites/vision-read-text/run.py --model <repo> --hardware "Apple M4 Pro, 48 GB unified memory"

Scoring is deliberately dumb: no model judges another model, so the number means the same
thing on your machine as on mine. A model that wraps the right text in a sentence scores
zero, because for a camera that speaks the answer out loud, the extra words are the bug.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(HERE, "images")
HASHES = os.path.join(HERE, "image-hashes.json")
UA = {"User-Agent": "agent12-vision-read-text/1.0"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def normalize(s):
    """Lowercase, collapse whitespace, drop punctuation that is not inside a number."""
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(?<!\d)[.,;:!?'\"()\[\]]+|[.,;:!?'\"()\[\]]+(?!\d)", "", s)
    return s.strip()


def fetch(item):
    os.makedirs(CACHE, exist_ok=True)
    ext = os.path.splitext(item["url"])[1].split("?")[0] or ".img"
    path = os.path.join(CACHE, item["id"] + ext)
    if not os.path.exists(path):
        req = urllib.request.Request(item["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
        print(f"  fetched {item['id']}")
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return path, digest


def check_hashes(seen):
    """Refuse to score if a pinned image changed. A moved URL would silently
    rewrite the test, and the number would stop being comparable."""
    if os.path.exists(HASHES):
        with io.open(HASHES, encoding="utf-8") as f:
            pinned = json.load(f)
        drift = {k: (pinned[k], seen[k]) for k in pinned if k in seen and pinned[k] != seen[k]}
        if drift:
            for k, (was, now) in drift.items():
                print(f"  CHANGED {k}: pinned {was[:12]} but got {now[:12]}")
            raise SystemExit("image set changed, not scoring. Delete the file's cache copy "
                             "and re-check the source before trusting a run.")
        return pinned
    with io.open(HASHES, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=1)
    print(f"  pinned {len(seen)} image hashes (first run)")
    return seen


def model_identity(arg):
    """What to call the model, and whether a Hugging Face link is honest.

    Passing a local directory used to produce "https://huggingface.co//Users/matt/..."
    which is a link to nothing. A row is only linked when the argument is a repo id,
    or a hub cache folder whose name still carries the org (models--org--name).
    """
    if os.path.isdir(arg):
        base = os.path.basename(os.path.normpath(arg))
        if base.startswith("models--"):
            repo = "/".join(base[len("models--"):].split("--"))
            return repo, f"https://huggingface.co/{repo}"
        return base + " (local build)", None
    return arg, f"https://huggingface.co/{arg}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="MLX vision model repo id")
    ap.add_argument("--hardware", default="", help='e.g. "Apple M4 Pro, 48 GB unified memory"')
    ap.add_argument("--who", default=os.environ.get("AGENT12_HANDLE", ""),
                    help="your handle, goes on the row")
    ap.add_argument("--max-tokens", type=int, default=48)
    ap.add_argument("--include-draft", action="store_true",
                    help="also run items marked draft in the manifest")
    args = ap.parse_args()

    with io.open(os.path.join(HERE, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    items = [i for i in man["items"]
             if args.include_draft or not str(i.get("status", "")).startswith("draft")]
    if not items:
        raise SystemExit("no runnable items")

    print(f"{len(items)} items, model {args.model}")
    seen = {}
    paths = {}
    for i in items:
        paths[i["id"]], seen[i["id"]] = fetch(i)
    check_hashes(seen)

    try:
        from mlx_vlm import generate, load
        from mlx_vlm.prompt_utils import apply_chat_template
    except ImportError:
        raise SystemExit("mlx-vlm is not installed. On Apple Silicon: pip install mlx-vlm")

    model_name, model_url = model_identity(args.model)
    if model_url is None:
        print(f"  note: {model_name} has no public repo to link, the row will say so")

    t0 = time.time()
    model, processor = load(args.model)
    load_s = round(time.time() - t0, 1)
    print(f"loaded in {load_s}s")

    correct, results, first_token_total = 0, [], 0.0
    for i in items:
        cfg = getattr(model, "config", None)
        prompt = apply_chat_template(processor, cfg, man["prompt"], num_images=1)
        t = time.time()
        raw = generate(model, processor, prompt, [paths[i["id"]]],
                       max_tokens=args.max_tokens, verbose=False)
        took = time.time() - t
        first_token_total += took
        answer = raw if isinstance(raw, str) else getattr(raw, "text", str(raw))
        got, want = normalize(answer), normalize(i["expected"])
        hit = got == want
        correct += hit
        results.append({"id": i["id"], "expected": i["expected"],
                        "got": answer.strip()[:200], "pass": hit,
                        "seconds": round(took, 2)})
        print(f"  {'PASS' if hit else 'FAIL'} {i['id']:22s} got: {answer.strip()[:60]!r}")

    acc = round(100 * correct / len(items), 1)
    out = {
        "suite": "vision-read-text",
        "model": model_name,
        "model_url": model_url,
        "hardware": args.hardware,
        "metrics": {"accuracy": acc,
                    "first_token_s": round(first_token_total / len(items), 2)},
        "n_items": len(items),
        "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submitted_by": args.who or "unnamed",
        "notes": f"load {load_s}s, max_tokens {args.max_tokens}, "
                 f"manifest v{man['version']}, exact-match scoring",
        "items": results,
    }
    slug = model_name.split("/")[-1].replace(" (local build)", "-local").lower()
    dest = os.path.join(ROOT, "submissions",
                        f"vision-read-text--{slug}--{(args.who or 'unnamed').lower()}.json")
    with io.open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print(f"\naccuracy {acc}% ({correct}/{len(items)})")
    print(f"wrote {dest}")
    if not args.hardware:
        print("WARNING: no --hardware given, and the validator rejects a row without the "
              "machine named. Add it before submitting.")


if __name__ == "__main__":
    main()
