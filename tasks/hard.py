"""Agent-12 hard suite — 8 reasoning-heavy coding tasks.

Same contract as the easy suite: fresh sandbox per task, filesystem and
subprocess judged, model prose never trusted. Anti-cheat: tasks that ship
a test file pin its hash at setup; a modified test file scores zero.

Judge provenance: the h3 probe in the original private harness demanded an
eviction order that contradicted the task's own spec (a spec-perfect
solution failed it — caught by validate_judges.py on 2026-08-10). The probe
below is the corrected, reference-validated version.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import Task, answer_text

ENV = {
    "AGENT_MAX_TOKENS": "3000",
    "AGENT_MAX_STEPS": "25",
    "AGENT_BASH_TIMEOUT": "45",
}

PINS = {}  # task name -> sha256 of the pristine shipped test file


def w(d, name, text):
    p = d / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_py(d, script, timeout=20):
    return subprocess.run([sys.executable, script], cwd=d, capture_output=True,
                          text=True, timeout=timeout)


# ─── H1: interval merge with touching/unsorted/negative edges ────────────────

def h1_setup(d):
    pass

def h1_check(d):
    p = d / "intervals.py"
    if not p.exists():
        return False
    probe = (
        "from intervals import merge\n"
        "assert merge([]) == []\n"
        "assert merge([[1,2]]) == [[1,2]]\n"
        "assert merge([[1,2],[2,3]]) == [[1,3]]\n"
        "assert merge([[5,7],[1,3]]) == [[1,3],[5,7]]\n"
        "assert merge([[1,4],[2,3]]) == [[1,4]]\n"
        "assert merge([[-5,-3],[-4,0],[1,1]]) == [[-5,0],[1,1]]\n"
        "assert merge([[1,4],[6,7]]) == [[1,4],[6,7]]\n"
        "assert merge([[3,3],[1,5]]) == [[1,5]]\n"
        "assert merge([[1,2],[3,4],[2,3]]) == [[1,4]]\n"
        "print('H1OK')\n")
    w(d, "_probe1.py", probe)
    r = run_py(d, "_probe1.py")
    return "H1OK" in r.stdout

def h1_good(d):
    w(d, "intervals.py",
      "def merge(intervals):\n"
      "    out = []\n"
      "    for s, e in sorted(intervals):\n"
      "        if out and s <= out[-1][1]:\n"
      "            out[-1][1] = max(out[-1][1], e)\n"
      "        else:\n"
      "            out.append([s, e])\n"
      "    return out\n")

def h1_bad(d):
    w(d, "intervals.py",  # forgets that touching intervals merge
      "def merge(intervals):\n"
      "    out = []\n"
      "    for s, e in sorted(intervals):\n"
      "        if out and s < out[-1][1]:\n"
      "            out[-1][1] = max(out[-1][1], e)\n"
      "        else:\n"
      "            out.append([s, e])\n"
      "    return out\n")


# ─── H2: debugging — mutation during iteration + boundary off-by-one ─────────

def h2_setup(d):
    w(d, "inventory.py",
      'def remove_expired(items, today):\n'
      '    """Return the items that have NOT expired. An item is expired when\n'
      '    its expires date is strictly before today. Must not modify the\n'
      '    input list."""\n'
      '    for it in items:\n'
      '        if it["expires"] <= today:\n'
      '            items.remove(it)\n'
      '    return items\n')
    w(d, "test_inventory.py",
      "from inventory import remove_expired\n"
      "items = [\n"
      "    {'name': 'a', 'expires': '2026-01-01'},\n"
      "    {'name': 'b', 'expires': '2026-01-02'},\n"
      "    {'name': 'c', 'expires': '2026-08-09'},\n"
      "    {'name': 'd', 'expires': '2026-12-31'},\n"
      "]\n"
      "snapshot = [dict(x) for x in items]\n"
      "out = remove_expired(items, '2026-08-09')\n"
      "assert [x['name'] for x in out] == ['c', 'd'], out\n"
      "assert items == snapshot, 'input list was modified'\n"
      "assert remove_expired([], '2026-08-09') == []\n"
      "keep = [{'name': 'x', 'expires': '2027-01-01'}]\n"
      "assert [x['name'] for x in remove_expired(keep, '2026-08-09')] == ['x']\n"
      "print('H2OK')\n")

def h2_pin(d):
    PINS["h2_fix_iteration_bug"] = sha(d / "test_inventory.py")

def h2_check(d):
    if sha(d / "test_inventory.py") != PINS["h2_fix_iteration_bug"]:
        return False, "test file was modified"
    r = run_py(d, "test_inventory.py")
    return "H2OK" in r.stdout

def h2_good(d):
    w(d, "inventory.py",
      'def remove_expired(items, today):\n'
      '    """Return the items that have NOT expired. An item is expired when\n'
      '    its expires date is strictly before today. Must not modify the\n'
      '    input list."""\n'
      '    return [it for it in items if it["expires"] >= today]\n')

def h2_bad(d):
    w(d, "inventory.py",  # fixed the mutation, kept the boundary bug
      'def remove_expired(items, today):\n'
      '    return [it for it in items if it["expires"] > today]\n')


# ─── H3: LRU cache with TTL and expired-first eviction ───────────────────────

def h3_setup(d):
    pass

def h3_check(d):
    p = d / "cache.py"
    if not p.exists():
        return False
    probe = (
        "from cache import Cache\n"
        "c = Cache(2)\n"
        "c.put('a', 1, ttl=10, now=0)\n"
        "c.put('b', 2, ttl=10, now=1)\n"
        "assert c.get('a', now=2) == 1\n"
        "c.put('c', 3, ttl=10, now=3)\n"        # full, none expired -> evict LRU 'b'
        "assert c.get('b', now=4) is None\n"
        "assert c.get('c', now=4) == 3\n"
        "assert c.get('a', now=4) == 1\n"        # recency now: c, then a
        "c.put('d', 4, ttl=1, now=5)\n"          # none expired -> evict LRU 'c'
        "assert c.get('c', now=5) is None\n"
        "assert c.get('a', now=5) == 1\n"
        "assert c.get('d', now=5) == 4\n"
        "assert c.get('d', now=6) is None\n"     # expired: 6 >= 5+1
        "c2 = Cache(2)\n"
        "c2.put('x', 7, ttl=100, now=0)\n"
        "c2.put('y', 8, ttl=2, now=1)\n"         # y expires at 3
        "assert c2.get('y', now=2) == 8\n"       # y is MRU, x is LRU
        "c2.put('z', 9, ttl=10, now=4)\n"        # y expired -> evict y, keep LRU x
        "assert c2.get('x', now=4) == 7\n"
        "assert c2.get('y', now=4) is None\n"
        "assert c2.get('z', now=4) == 9\n"
        "c3 = Cache(1)\n"
        "c3.put('k', 1, ttl=5, now=0)\n"
        "assert c3.get('k', now=4) == 1\n"
        "assert c3.get('k', now=5) is None\n"    # >= boundary, exactly at expiry
        "print('H3OK')\n")
    w(d, "_probe3.py", probe)
    r = run_py(d, "_probe3.py")
    return "H3OK" in r.stdout

def h3_good(d):
    w(d, "cache.py",
      "class Cache:\n"
      "    def __init__(self, capacity):\n"
      "        self.cap = capacity\n"
      "        self.d = {}  # key -> [value, expires_at]; dict order = recency\n"
      "\n"
      "    def get(self, key, now):\n"
      "        item = self.d.get(key)\n"
      "        if item is None:\n"
      "            return None\n"
      "        if now >= item[1]:\n"
      "            del self.d[key]\n"
      "            return None\n"
      "        self.d[key] = self.d.pop(key)\n"
      "        return item[0]\n"
      "\n"
      "    def put(self, key, value, ttl, now):\n"
      "        if key in self.d:\n"
      "            self.d.pop(key)\n"
      "        elif len(self.d) >= self.cap:\n"
      "            expired = [k for k, (_, exp) in self.d.items() if now >= exp]\n"
      "            if expired:\n"
      "                self.d.pop(expired[0])\n"
      "            else:\n"
      "                self.d.pop(next(iter(self.d)))\n"
      "        self.d[key] = [value, now + ttl]\n")

def h3_bad(d):
    w(d, "cache.py",  # plain LRU, ignores TTL entirely
      "class Cache:\n"
      "    def __init__(self, capacity):\n"
      "        self.cap = capacity\n"
      "        self.d = {}\n"
      "\n"
      "    def get(self, key, now):\n"
      "        if key not in self.d:\n"
      "            return None\n"
      "        self.d[key] = self.d.pop(key)\n"
      "        return self.d[key][0]\n"
      "\n"
      "    def put(self, key, value, ttl, now):\n"
      "        if key in self.d:\n"
      "            self.d.pop(key)\n"
      "        elif len(self.d) >= self.cap:\n"
      "            self.d.pop(next(iter(self.d)))\n"
      "        self.d[key] = [value, now + ttl]\n")


# ─── H4: CSV parser, csv module banned ───────────────────────────────────────

H4_DATA = ('name,quote,notes\n'
           'alice,"hello, world",simple\n'
           'bob,"she said ""hi""","line1\nline2"\n'
           'carol,plain,"trailing"\n')
H4_EXPECT = [["name", "quote", "notes"],
             ["alice", "hello, world", "simple"],
             ["bob", 'she said "hi"', "line1\nline2"],
             ["carol", "plain", "trailing"]]

def h4_setup(d):
    w(d, "data.csv", H4_DATA)

def h4_check(d):
    p = d / "out.json"
    src = d / "parse.py"
    if not p.exists() or not src.exists():
        return False
    body = src.read_text()
    if "import csv" in body or "from csv" in body:
        return False, "used the banned csv module"
    try:
        got = json.loads(answer_text(p))
    except json.JSONDecodeError:
        return False
    return got == H4_EXPECT

H4_PARSER = (
    "import json\n"
    "\n"
    "def parse(text):\n"
    "    rows, field, row = [], [], []\n"
    "    i, n, in_q = 0, len(text), False\n"
    "    while i < n:\n"
    "        ch = text[i]\n"
    "        if in_q:\n"
    "            if ch == '\"':\n"
    "                if i + 1 < n and text[i+1] == '\"':\n"
    "                    field.append('\"'); i += 1\n"
    "                else:\n"
    "                    in_q = False\n"
    "            else:\n"
    "                field.append(ch)\n"
    "        elif ch == '\"':\n"
    "            in_q = True\n"
    "        elif ch == ',':\n"
    "            row.append(''.join(field)); field = []\n"
    "        elif ch == '\\n':\n"
    "            row.append(''.join(field)); field = []\n"
    "            rows.append(row); row = []\n"
    "        else:\n"
    "            field.append(ch)\n"
    "        i += 1\n"
    "    if field or row:\n"
    "        row.append(''.join(field)); rows.append(row)\n"
    "    return rows\n"
    "\n"
    "rows = parse(open('data.csv').read())\n"
    "json.dump(rows, open('out.json', 'w'))\n")

def h4_good(d):
    w(d, "parse.py", H4_PARSER)
    subprocess.run([sys.executable, "parse.py"], cwd=d, timeout=20)

def h4_bad(d):
    w(d, "parse.py",  # correct output, but reaches for the banned module
      "import csv, json\n"
      "rows = list(csv.reader(open('data.csv')))\n"
      "json.dump(rows, open('out.json', 'w'))\n")
    subprocess.run([sys.executable, "parse.py"], cwd=d, timeout=20)


# ─── H5: lexicographically-smallest topological sort, cycles -> None ─────────

def h5_setup(d):
    pass

def _ref_topo(nodes, edges):
    import heapq
    indeg = {n: 0 for n in nodes}
    out = {n: [] for n in nodes}
    for a, b in edges:
        out[a].append(b)
        indeg[b] += 1
    heap = [n for n in nodes if indeg[n] == 0]
    heapq.heapify(heap)
    res = []
    while heap:
        n = heapq.heappop(heap)
        res.append(n)
        for m in out[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                heapq.heappush(heap, m)
    return res if len(res) == len(nodes) else None

H5_CASES = [
    (["b", "a"], []),
    (["a", "b", "c", "d"], [["d", "a"], ["d", "b"], ["a", "c"], ["b", "c"]]),
    (["x", "y"], [["x", "y"], ["y", "x"]]),
    (["m", "k", "z", "q"], [["z", "m"]]),
    (["a", "b", "c", "d", "e"], [["c", "a"], ["c", "b"], ["e", "d"], ["a", "d"]]),
]

def h5_check(d):
    p = d / "toposort.py"
    if not p.exists():
        return False
    lines = ["from toposort import topo"]
    for i, (nodes, edges) in enumerate(H5_CASES):
        exp = _ref_topo(nodes, edges)
        lines.append(f"assert topo({nodes!r}, {edges!r}) == {exp!r}, 'case {i}'")
    lines.append("print('H5OK')")
    w(d, "_probe5.py", "\n".join(lines) + "\n")
    r = run_py(d, "_probe5.py")
    return "H5OK" in r.stdout

def h5_good(d):
    w(d, "toposort.py",
      "import heapq\n"
      "\n"
      "def topo(nodes, edges):\n"
      "    indeg = {n: 0 for n in nodes}\n"
      "    out = {n: [] for n in nodes}\n"
      "    for a, b in edges:\n"
      "        out[a].append(b)\n"
      "        indeg[b] += 1\n"
      "    heap = [n for n in nodes if indeg[n] == 0]\n"
      "    heapq.heapify(heap)\n"
      "    res = []\n"
      "    while heap:\n"
      "        n = heapq.heappop(heap)\n"
      "        res.append(n)\n"
      "        for m in out[n]:\n"
      "            indeg[m] -= 1\n"
      "            if indeg[m] == 0:\n"
      "                heapq.heappush(heap, m)\n"
      "    return res if len(res) == len(nodes) else None\n")

def h5_bad(d):
    w(d, "toposort.py",  # valid topo order, but not the lexicographically smallest
      "def topo(nodes, edges):\n"
      "    indeg = {n: 0 for n in nodes}\n"
      "    out = {n: [] for n in nodes}\n"
      "    for a, b in edges:\n"
      "        out[a].append(b)\n"
      "        indeg[b] += 1\n"
      "    queue = [n for n in nodes if indeg[n] == 0]\n"
      "    res = []\n"
      "    while queue:\n"
      "        n = queue.pop(0)\n"
      "        res.append(n)\n"
      "        for m in out[n]:\n"
      "            indeg[m] -= 1\n"
      "            if indeg[m] == 0:\n"
      "                queue.append(m)\n"
      "    return res if len(res) == len(nodes) else None\n")


# ─── H6: normalize mixed-format log timestamps to UTC, sorted ────────────────

def _h6_lines():
    rows = [
        ("2026-08-09 14:30:00 -0700 | deploy started", datetime(2026, 8, 9, 21, 30, tzinfo=timezone.utc), "deploy started"),
        ("2026-08-09T20:15:00Z cache warmed", datetime(2026, 8, 9, 20, 15, tzinfo=timezone.utc), "cache warmed"),
        ("2026-08-10 05:00:00 +0900 | backup finished", datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc), "backup finished"),
        (None, datetime(2026, 8, 9, 22, 45, tzinfo=timezone.utc), "queue drained"),
        ("2026-08-09T19:05:30Z first ping", datetime(2026, 8, 9, 19, 5, 30, tzinfo=timezone.utc), "first ping"),
        (None, datetime(2026, 8, 9, 19, 30, tzinfo=timezone.utc), "worker online"),
    ]
    out = []
    for raw, dt, msg in rows:
        if raw is None:
            raw = f"epoch={int(dt.timestamp())} msg={msg}"
        out.append((raw, dt, msg))
    return out

def h6_setup(d):
    w(d, "logs.txt", "\n".join(r for r, _, _ in _h6_lines()) + "\n")

def h6_check(d):
    p = d / "normalized.txt"
    if not p.exists():
        return False
    exp = sorted(((dt, msg) for _, dt, msg in _h6_lines()))
    want = [f"{dt.strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}" for dt, msg in exp]
    got = [ln.rstrip() for ln in answer_text(p).strip().splitlines()]
    return got == want

def _h6_solve(d, do_sort):
    lines = (d / "logs.txt").read_text().strip().splitlines()
    out = []
    for ln in lines:
        if ln.startswith("epoch="):
            secs, msg = ln.split(" msg=", 1)
            dt = datetime.fromtimestamp(int(secs[6:]), tz=timezone.utc)
        elif " | " in ln:
            stamp, msg = ln.split(" | ", 1)
            dt = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc)
        else:
            stamp, msg = ln.split(" ", 1)
            dt = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        out.append((dt, msg))
    if do_sort:
        out.sort()
    w(d, "normalized.txt",
      "".join(f"{dt.strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}\n" for dt, msg in out))

def h6_good(d):
    _h6_solve(d, do_sort=True)

def h6_bad(d):
    _h6_solve(d, do_sort=False)  # converted correctly but forgot to sort


# ─── H7: 10-rule spec gauntlet (graded) ──────────────────────────────────────

def h7_setup(d):
    pass

H7_PROBES = [
    ("r01_typeerror", "try:\n    validate_username(42)\n    raise SystemExit(1)\nexcept TypeError as e:\n    assert str(e) == 'username must be a string'"),
    ("r02_short", "try:\n    validate_username('ab')\n    raise SystemExit(1)\nexcept ValueError as e:\n    assert str(e) == 'too short'"),
    ("r03_long", "try:\n    validate_username('a' * 17)\n    raise SystemExit(1)\nexcept ValueError as e:\n    assert str(e) == 'too long'"),
    ("r04_charset", "try:\n    validate_username('abc$def')\n    raise SystemExit(1)\nexcept ValueError as e:\n    assert str(e) == 'invalid character'"),
    ("r05_digit", "try:\n    validate_username('9abc')\n    raise SystemExit(1)\nexcept ValueError as e:\n    assert str(e) == 'cannot start with a digit'"),
    ("r06_edge", "for bad in ('_abc', 'abc_', '.abc', 'abc.'):\n    try:\n        validate_username(bad)\n        raise SystemExit(1)\n    except ValueError as e:\n        assert str(e) == 'invalid edge character'"),
    ("r07_repeat", "for bad in ('ab__cd', 'ab..cd'):\n    try:\n        validate_username(bad)\n        raise SystemExit(1)\n    except ValueError as e:\n        assert str(e) == 'repeated separator'"),
    ("r08_reserved", "for bad in ('admin', 'Root', 'ADMIN'):\n    try:\n        validate_username(bad)\n        raise SystemExit(1)\n    except ValueError as e:\n        assert str(e) == 'reserved'"),
    ("r09_lower", "assert validate_username('John_Doe99') == 'john_doe99'"),
    ("r10_valid", "assert validate_username('abc.def_9') == 'abc.def_9'\nassert validate_username('xyz') == 'xyz'"),
]

def h7_check(d):
    p = d / "validators.py"
    if not p.exists():
        return False, "0/10"
    ok = 0
    for name, body in H7_PROBES:
        w(d, f"_p7_{name}.py", "from validators import validate_username\n" + body + "\nprint('RULEOK')\n")
        try:
            r = run_py(d, f"_p7_{name}.py")
            ok += "RULEOK" in r.stdout
        except Exception:  # noqa: BLE001
            pass
    return ok == 10, f"{ok}/10"

H7_SOLUTION = (
    "import re\n"
    "\n"
    "def validate_username(s):\n"
    "    if not isinstance(s, str):\n"
    "        raise TypeError('username must be a string')\n"
    "    if len(s) < 3:\n"
    "        raise ValueError('too short')\n"
    "    if len(s) > 16:\n"
    "        raise ValueError('too long')\n"
    "    if not re.fullmatch(r'[A-Za-z0-9_.]+', s):\n"
    "        raise ValueError('invalid character')\n"
    "    if s[0].isdigit():\n"
    "        raise ValueError('cannot start with a digit')\n"
    "    if s[0] in '_.' or s[-1] in '_.':\n"
    "        raise ValueError('invalid edge character')\n"
    "    if '__' in s or '..' in s:\n"
    "        raise ValueError('repeated separator')\n"
    "    if s.lower() in ('admin', 'root'):\n"
    "        raise ValueError('reserved')\n"
    "    return s.lower()\n")

def h7_good(d):
    w(d, "validators.py", H7_SOLUTION)

def h7_bad(d):
    w(d, "validators.py", H7_SOLUTION.replace("return s.lower()", "return s"))  # rule 9 missed


# ─── H8: cache key collision in a bigger module, with a red herring ──────────

def h8_setup(d):
    w(d, "orders.py",
      '"""Order totaling with memoization."""\n'
      "_cache = {}\n"
      "\n"
      "def _round_money(x):\n"
      "    # banker's rounding is intentional here; do not change\n"
      "    return round(x + 0.0, 2)\n"
      "\n"
      "def _line_total(qty, price):\n"
      "    if qty < 0:\n"
      "        raise ValueError('negative qty')\n"
      "    return qty * price\n"
      "\n"
      "def order_total(customer_id, order_id, lines):\n"
      "    \"\"\"Total for one order. Results are memoized per (customer, order).\"\"\"\n"
      "    key = customer_id + str(order_id)\n"
      "    if key in _cache:\n"
      "        return _cache[key]\n"
      "    total = 0.0\n"
      "    for qty, price in lines:\n"
      "        total += _line_total(qty, price)\n"
      "    total = _round_money(total)\n"
      "    _cache[key] = total\n"
      "    return total\n"
      "\n"
      "def customer_grand_total(customer_id, orders):\n"
      "    return _round_money(sum(order_total(customer_id, oid, ls)\n"
      "                            for oid, ls in orders.items()))\n")
    w(d, "test_orders.py",
      "from orders import order_total\n"
      "assert order_total('a', 'b1', [(1, 10.0)]) == 10.0\n"
      "assert order_total('ab', '1', [(3, 5.0)]) == 15.0\n"
      "assert order_total('a', 'b1', [(1, 10.0)]) == 10.0\n"
      "assert order_total('c', 7, [(2, 2.5)]) == 5.0\n"
      "print('H8OK')\n")

def h8_pin(d):
    PINS["h8_cache_collision"] = sha(d / "test_orders.py")

def h8_check(d):
    if sha(d / "test_orders.py") != PINS["h8_cache_collision"]:
        return False, "test file was modified"
    body = (d / "orders.py").read_text()
    if body.count("_cache") < 2:
        return False, "memoization was removed"
    r = run_py(d, "test_orders.py")
    return "H8OK" in r.stdout

def h8_good(d):
    p = d / "orders.py"
    p.write_text(p.read_text().replace(
        "key = customer_id + str(order_id)",
        "key = (customer_id, str(order_id))"))

def h8_bad(d):
    p = d / "orders.py"  # "fixes" the failure by deleting the cache
    body = p.read_text().replace("    if key in _cache:\n        return _cache[key]\n", "")
    body = body.replace("    _cache[key] = total\n", "")
    body = body.replace("_cache = {}\n", "")
    p.write_text(body)


TASKS = [
    Task("h1_interval_merge",
         "Create intervals.py with a function merge(intervals) that merges a list of\n"
         "[start, end] integer intervals. Rules: overlapping OR touching intervals\n"
         "(e.g. [1,2] and [2,3]) merge into one; the input may be unsorted and may\n"
         "contain negative numbers and single-point intervals like [3,3]; return the\n"
         "merged intervals sorted by start; merge([]) returns []. Test it yourself\n"
         "on edge cases before finishing.",
         h1_setup, h1_check, h1_good, h1_bad),
    Task("h2_fix_iteration_bug",
         "test_inventory.py fails. Find ALL the bugs in inventory.py and fix them so\n"
         "the tests pass. Do not modify test_inventory.py. Read the docstring\n"
         "carefully — it is the spec.",
         h2_setup, h2_check, h2_good, h2_bad, pin=h2_pin),
    Task("h3_lru_ttl_cache",
         "Create cache.py with a class Cache(capacity) implementing an LRU cache\n"
         "with per-item TTL and an explicit clock:\n"
         "  put(key, value, ttl, now) — store value; the item expires when\n"
         "      now >= put_time + ttl (compare with >=).\n"
         "  get(key, now) — return the value, or None if missing or expired.\n"
         "      A successful get makes that key most-recently-used.\n"
         "When putting into a full cache, first evict any expired item; only if\n"
         "none is expired evict the least-recently-used one. Expired items count\n"
         "as absent for get. Test the eviction order yourself before finishing.",
         h3_setup, h3_check, h3_good, h3_bad),
    Task("h4_csv_no_csv",
         "data.csv uses standard CSV quoting: fields may be wrapped in double\n"
         'quotes, quoted fields may contain commas and real newlines, and "" inside\n'
         "a quoted field means one literal double-quote. WITHOUT using Python's csv\n"
         "module (banned — parse it yourself), write parse.py that reads data.csv\n"
         "and writes out.json: a JSON array of rows, each row an array of field\n"
         "strings. Run it to produce out.json.",
         h4_setup, h4_check, h4_good, h4_bad),
    Task("h5_topo_lex",
         "Create toposort.py with a function topo(nodes, edges) where nodes is a\n"
         "list of strings and edges is a list of [a, b] pairs meaning a must come\n"
         "before b. Return a topological ordering as a list. When several nodes are\n"
         "available, always pick the alphabetically smallest next (the result is\n"
         "the lexicographically smallest valid ordering). If the graph has a cycle,\n"
         "return None. Include nodes with no edges.",
         h5_setup, h5_check, h5_good, h5_bad),
    Task("h6_log_normalize",
         "logs.txt mixes three timestamp formats, one per line:\n"
         "  A) 'YYYY-MM-DD HH:MM:SS +HHMM | MESSAGE'  (numeric UTC offset)\n"
         "  B) 'epoch=SECONDS msg=MESSAGE'            (unix seconds, UTC)\n"
         "  C) 'YYYY-MM-DDTHH:MM:SSZ MESSAGE'         (already UTC)\n"
         "Convert every line to UTC and write normalized.txt where each line is\n"
         "'YYYY-MM-DDTHH:MM:SSZ MESSAGE', sorted ascending by time. Use only the\n"
         "standard library, and run your script to produce the file.",
         h6_setup, h6_check, h6_good, h6_bad),
    Task("h7_spec_gauntlet",
         "Create validators.py with ONE function validate_username(s) implementing\n"
         "ALL of these rules exactly:\n"
         " 1. if s is not a str: raise TypeError('username must be a string')\n"
         " 2. length < 3: raise ValueError('too short')\n"
         " 3. length > 16: raise ValueError('too long')\n"
         " 4. only letters, digits, underscore and dot are allowed; on any other\n"
         "    character: raise ValueError('invalid character')\n"
         " 5. if it starts with a digit: raise ValueError('cannot start with a digit')\n"
         " 6. if it starts or ends with '_' or '.': raise ValueError('invalid edge character')\n"
         " 7. if it contains '__' or '..': raise ValueError('repeated separator')\n"
         " 8. if it equals 'admin' or 'root' ignoring case: raise ValueError('reserved')\n"
         " 9. on success return the username lowercased\n"
         "10. valid examples must pass: 'John_Doe99' -> 'john_doe99'\n"
         "Apply the checks in an order that makes every rule reachable exactly as\n"
         "specified (think about which rule wins when several could fire).",
         h7_setup, h7_check, h7_good, h7_bad),
    Task("h8_cache_collision",
         "test_orders.py fails. Diagnose the ROOT CAUSE in orders.py and fix it\n"
         "properly. Keep the memoization (do not just delete the cache), do not\n"
         "modify test_orders.py, and leave _round_money alone — its comment is\n"
         "accurate.",
         h8_setup, h8_check, h8_good, h8_bad, pin=h8_pin),
]
