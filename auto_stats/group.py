import json, os, re, sys, datetime
from collections import Counter
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import stats_contribution as sc

rows = json.load(open(sys.argv[1]))
skip = set()
if len(sys.argv) > 3 and os.path.exists(sys.argv[3]):
    for line in open(sys.argv[3]):
        for h in line.replace("\t", " ").split():
            if len(h) == 7:
                skip.add(h)
WINDOW = int(os.environ.get("WINDOW","7"))
PRWINDOW = int(os.environ.get("PRWINDOW","60"))
PAPER = re.compile(r"(?i)(P\d{4}R\d+|LWG\s?\d+|CWG\s?\d+|#\d+)")

def pt(t): return sum(sc.point_dict.get(k,0)*v for k,v in t.items())
def d(s): return datetime.date(*map(int, s.split("-")))

for r in rows:
    r["pages"] = tuple(r.get("pages", []))
    r["hashes"] = [r["hash"]]
    r["papers"] = set(m.group(1).replace(" ","").upper() for m in PAPER.finditer(r["subject"]))

PRNUM = re.compile(r"#(\d{3,5})")
def prs(r):
    return set(PRNUM.findall(r["subject"]))
def has_add(r):
    return any(k.endswith(("/addref","/addlang","/addpage")) for k in r["tags"])

owner = {}
pr_owner = {}
order = sorted(range(len(rows)), key=lambda i: (rows[i]["date"], rows[i]["hash"]))
dropped = set()
for i in order:
    r = rows[i]
    if not r["pages"] or len(r["pages"]) > 5:
        continue
    if r["tags"].get("ignore") and len(r["tags"]) == 1:
        continue
    if r["hash"] in skip:
        continue
    # 同一Pull Request内の微調整コミットは、その作業の行にまとめる。
    # 新規ページを追加しているコミットは独立した成果なのでまとめない。
    if not has_add(r):
        for pn in prs(r):
            k = (r["repo"], r["login"], "PR#" + pn)
            j = pr_owner.get(k)
            if j is None or j == i:
                continue
            p = rows[j]
            if (d(r["date"]) - d(p.get("date_last", p["date"]))).days > PRWINDOW:
                continue
            if pt(r["tags"]) > pt(p["tags"]):
                continue
            # 微調整はその作業の行に吸収するだけで、ポイントは増やさない
            p["hashes"].append(r["hash"])
            p["papers"] |= r["papers"]
            p["date_last"] = r["date"]
            dropped.add(i)
            break
        if i in dropped:
            continue
    for pn in prs(r):
        pr_owner.setdefault((r["repo"], r["login"], "PR#" + pn), i)
    keys = [(r["repo"], r["login"], pg) for pg in r["pages"]]
    owners = set(owner.get(k) for k in keys)
    if None not in owners and owners:
        g = max(owners, key=lambda j: (rows[j].get("date_last", rows[j]["date"]), j))
        p = rows[g]
        same_work = not (r["papers"] and p["papers"] and not (r["papers"] & p["papers"]))
        budget = sum(pt(rows[j]["tags"]) for j in owners)
        if (d(r["date"]) - d(p.get("date_last", p["date"]))).days <= WINDOW and pt(r["tags"]) <= budget and same_work:
            p["hashes"].append(r["hash"])
            merged = Counter(p["tags"])
            for k, v in r["tags"].items():
                if k == "ignore":
                    continue
                merged[k] = max(merged.get(k, 0), v)
            p["tags"] = dict(merged)
            p["papers"] |= r["papers"]
            p["date_last"] = r["date"]
            dropped.add(i)
            continue
    for k in keys:
        owner[k] = i

out = [r for i, r in enumerate(rows) if i not in dropped]
for r in out:
    r["pages"] = list(r["pages"]); r.pop("papers", None)
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
json.dump(sorted(rows[i]["hash"] for i in dropped), open(sys.argv[2]+".dropped", "w"))
print("rows: %d -> %d (merged %d)" % (len(rows), len(out), len(dropped)))
