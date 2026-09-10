"""Agent-12 easy suite — 12 machine-checkable everyday agent tasks.

Pass/fail is judged by the filesystem, never by the model's prose.
"""
import json
import subprocess
import sys

from . import Task, answer_text

ENV = {  # runner applies these as AGENT_* defaults for this suite
    "AGENT_MAX_TOKENS": "1024",
    "AGENT_MAX_STEPS": "15",
    "AGENT_BASH_TIMEOUT": "30",
}


def w(d, name, text):
    p = d / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def run_py(d, script, timeout=10):
    return subprocess.run([sys.executable, script], cwd=d, capture_output=True,
                          text=True, timeout=timeout)


# ─── t01 create & run ────────────────────────────────────────────────────────

def t01_setup(d):
    pass

def t01_check(d):
    p = d / "hello.py"
    if not p.exists():
        return False
    r = run_py(d, "hello.py")
    return r.stdout.strip() == "hello world"

def t01_good(d):
    w(d, "hello.py", 'print("hello world")\n')

def t01_bad(d):
    w(d, "hello.py", 'print("Hello World")\n')


# ─── t02 fix bug ─────────────────────────────────────────────────────────────

def t02_setup(d):
    w(d, "calc.py", "def total(items):\n    s = 0\n    for i in range(1, len(items)):\n        s += items[i]\n    return s\n")
    w(d, "test_calc.py", "from calc import total\nassert total([1, 2, 3, 4]) == 10\nprint('OK')\n")

def t02_check(d):
    r = run_py(d, "test_calc.py")
    return "OK" in r.stdout

def t02_good(d):
    w(d, "calc.py", "def total(items):\n    s = 0\n    for i in range(len(items)):\n        s += items[i]\n    return s\n")

def t02_bad(d):
    pass  # leaves the bug in place


# ─── t03 rename across files ─────────────────────────────────────────────────

def t03_setup(d):
    w(d, "shapes.py", "def calc_area(w, h):\n    return w * h\n\ndef report(w, h):\n    return f'area={calc_area(w, h)}'\n")
    w(d, "main.py", "from shapes import calc_area, report\nprint(calc_area(2, 3), report(2, 3))\n")

def t03_check(d):
    a, b = (d / "shapes.py").read_text(), (d / "main.py").read_text()
    if "calc_area" in a or "calc_area" in b:
        return False
    if "rect_area" not in a or "rect_area" not in b:
        return False
    r = run_py(d, "main.py")
    return "6" in r.stdout

def t03_good(d):
    for name in ("shapes.py", "main.py"):
        p = d / name
        p.write_text(p.read_text().replace("calc_area", "rect_area"))

def t03_bad(d):
    p = d / "shapes.py"  # renames in one file only
    p.write_text(p.read_text().replace("calc_area", "rect_area"))


# ─── t04 extract value ───────────────────────────────────────────────────────

def t04_setup(d):
    w(d, "config.ini", "[server]\nhost = 10.0.0.7\nport = 8443\n\n[auth]\ntoken = zx91-alpha\n")

def t04_check(d):
    p = d / "answer.txt"
    return p.exists() and answer_text(p).strip() == "zx91-alpha"

def t04_good(d):
    w(d, "answer.txt", "zx91-alpha\n")

def t04_bad(d):
    w(d, "answer.txt", "token = zx91-alpha\n")


# ─── t05 find marker ─────────────────────────────────────────────────────────

def t05_setup(d):
    for i, name in enumerate(["alpha.py", "beta.py", "gamma.py", "delta.py"]):
        w(d, name, f"# module {i}\nx = {i}\n" + ("# TODO: refactor this\n" if name == "gamma.py" else ""))

def t05_check(d):
    p = d / "found.txt"
    return p.exists() and answer_text(p).strip() == "gamma.py"

def t05_good(d):
    w(d, "found.txt", "gamma.py\n")

def t05_bad(d):
    w(d, "found.txt", "delta.py\n")


# ─── t06 precise append ──────────────────────────────────────────────────────

def t06_setup(d):
    w(d, "notes.md", "# Notes\n\n- first item\n- second item\n")

def t06_check(d):
    text = (d / "notes.md").read_text()
    return ("- first item" in text and "- second item" in text
            and "- third item" in text
            and text.index("- second item") < text.index("- third item"))

def t06_good(d):
    p = d / "notes.md"
    p.write_text(p.read_text() + "- third item\n")

def t06_bad(d):
    w(d, "notes.md", "# Notes\n\n- third item\n")  # clobbered the file


# ─── t07 write json ──────────────────────────────────────────────────────────

def t07_setup(d):
    pass

def t07_check(d):
    p = d / "config.json"
    if not p.exists():
        return False
    try:
        cfg = json.loads(answer_text(p))
    except json.JSONDecodeError:
        return False
    return (cfg.get("name") == "demo-app" and cfg.get("port") == 3000
            and cfg.get("debug") is False and cfg.get("tags") == ["web", "local"])

def t07_good(d):
    w(d, "config.json", json.dumps(
        {"name": "demo-app", "port": 3000, "debug": False, "tags": ["web", "local"]}, indent=2))

def t07_bad(d):
    w(d, "config.json", json.dumps(
        {"name": "demo-app", "port": "3000", "debug": False, "tags": ["web", "local"]}))


# ─── t08 tricky escapes ──────────────────────────────────────────────────────

TRICKY = 'print("she said \\"hi\\"")\npath = "C:\\\\temp\\\\new"\n'

def t08_setup(d):
    pass

def t08_check(d):
    p = d / "tricky.py"
    if not p.exists() or p.read_text().rstrip("\n") != TRICKY.rstrip("\n"):
        return False
    r = run_py(d, "tricky.py")
    return 'she said "hi"' in r.stdout

def t08_good(d):
    w(d, "tricky.py", TRICKY)

def t08_bad(d):
    w(d, "tricky.py", 'print("she said "hi"")\npath = "C:\\temp\\new"\n')  # mangled escapes


# ─── t09 count files ─────────────────────────────────────────────────────────

def t09_setup(d):
    (d / "src" / "deep").mkdir(parents=True)
    w(d, "src/a.py", "pass\n")
    w(d, "src/deep/b.py", "pass\n")
    w(d, "src/deep/c.py", "pass\n")
    w(d, "readme.txt", "hi\n")

def t09_check(d):
    p = d / "count.txt"
    return p.exists() and answer_text(p).strip() == "3"

def t09_good(d):
    w(d, "count.txt", "3\n")

def t09_bad(d):
    w(d, "count.txt", "4\n")


# ─── t10 extract constant ────────────────────────────────────────────────────

def t10_setup(d):
    w(d, "prices.py", "def price_with_tax(p):\n    return p * 1.0825\n\ndef receipt(p):\n    return round(p * 1.0825, 2)\n")
    w(d, "test_prices.py", "import prices\nassert prices.receipt(100) == 108.25\nassert prices.TAX_RATE == 1.0825\nsrc = open('prices.py').read()\nassert src.count('1.0825') == 1, 'literal should appear exactly once'\nprint('OK')\n")

def t10_check(d):
    r = run_py(d, "test_prices.py")
    return "OK" in r.stdout

def t10_good(d):
    w(d, "prices.py", "TAX_RATE = 1.0825\n\ndef price_with_tax(p):\n    return p * TAX_RATE\n\ndef receipt(p):\n    return round(p * TAX_RATE, 2)\n")

def t10_bad(d):
    w(d, "prices.py", "TAX_RATE = 1.0825\n\ndef price_with_tax(p):\n    return p * TAX_RATE\n\ndef receipt(p):\n    return round(p * 1.0825, 2)\n")  # literal still duplicated


# ─── t11 csv sum ─────────────────────────────────────────────────────────────

def t11_setup(d):
    w(d, "sales.csv", "day,units,revenue\nmon,3,30\ntue,5,55\nwed,2,18\n")

def t11_check(d):
    p = d / "revenue_total.txt"
    return p.exists() and answer_text(p).strip() in ("103", "103.0")

def t11_good(d):
    w(d, "revenue_total.txt", "103\n")

def t11_bad(d):
    w(d, "revenue_total.txt", "10\n")  # summed the units column


# ─── t12 delete the right file ───────────────────────────────────────────────

def t12_setup(d):
    w(d, "app.log", "keep\n")
    w(d, "app.log.bak", "junk\n")
    w(d, "app_final.log", "keep\n")
    w(d, "data.txt", "keep\n")

def t12_check(d):
    return ((d / "app.log").exists() and (d / "app_final.log").exists()
            and (d / "data.txt").exists() and not (d / "app.log.bak").exists())

def t12_good(d):
    (d / "app.log.bak").unlink()

def t12_bad(d):
    (d / "app.log.bak").unlink()
    (d / "app_final.log").unlink()  # overreached


TASKS = [
    Task("t01_create_run", "Create a file named hello.py that prints exactly: hello world",
         t01_setup, t01_check, t01_good, t01_bad),
    Task("t02_fix_bug", "test_calc.py fails. Find the bug in calc.py, fix it, and make sure the test passes.",
         t02_setup, t02_check, t02_good, t02_bad),
    Task("t03_rename_across_files", "Rename the function calc_area to rect_area everywhere it appears in this project, and verify main.py still runs.",
         t03_setup, t03_check, t03_good, t03_bad),
    Task("t04_extract_value", "Read config.ini and write ONLY the auth token value to a new file named answer.txt.",
         t04_setup, t04_check, t04_good, t04_bad),
    Task("t05_find_marker", "One .py file in this directory contains a TODO comment. Write just that filename to found.txt.",
         t05_setup, t05_check, t05_good, t05_bad),
    Task("t06_precise_append", "Add '- third item' to the list in notes.md, after the existing items. Do not change anything else in the file.",
         t06_setup, t06_check, t06_good, t06_bad),
    Task("t07_write_json", 'Create config.json containing exactly these settings: name "demo-app", port 3000, debug false, tags ["web", "local"].',
         t07_setup, t07_check, t07_good, t07_bad),
    Task("t08_tricky_escapes",
         "Create tricky.py with exactly these two lines:\n"
         'print("she said \\"hi\\"")\n'
         'path = "C:\\\\temp\\\\new"\n'
         "Then run it to confirm it prints: she said \"hi\"",
         t08_setup, t08_check, t08_good, t08_bad),
    Task("t09_count_files", "Count how many .py files exist anywhere under this directory (recursively) and write just that number to count.txt.",
         t09_setup, t09_check, t09_good, t09_bad),
    Task("t10_extract_constant", "In prices.py, the tax multiplier 1.0825 is duplicated. Extract it into a module-level constant named TAX_RATE (defined once, used everywhere), then make sure test_prices.py passes.",
         t10_setup, t10_check, t10_good, t10_bad),
    Task("t11_csv_sum", "Sum the revenue column in sales.csv and write the total to revenue_total.txt.",
         t11_setup, t11_check, t11_good, t11_bad),
    Task("t12_delete_right_file", "Delete the stale backup file app.log.bak from this directory. Do not touch any other file.",
         t12_setup, t12_check, t12_good, t12_bad),
]
