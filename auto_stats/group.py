import json, os, re, sys, datetime
from collections import Counter
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import stats_contribution as sc

# 年間を通して何度も更新されるページ。これを「同じページ」の判定に使うと、
# 別々の時期の無関係な作業がつながってしまう
HUB = re.compile(r"^(implementation-status\.md|implementation\.md|lang/cpp\d\d\.md"
                 r"|.*/feature_test_macros\.md|reference\.md|index\.md)$")

rows = json.load(open(sys.argv[1]))
skip = set()
if len(sys.argv) > 3 and os.path.exists(sys.argv[3]):
    for line in open(sys.argv[3]):
        for h in line.replace("\t", " ").split():
            if len(h) == 7:
                skip.add(h)
# 「連続した作業が複数コミットになった場合」をまとめるための期間。
# 同年内に広げると、implementation-status.md のように年間を通して何度も
# 更新されるページで、別々の作業がまとまってしまう。
WINDOW = int(os.environ.get("WINDOW","30"))
PRWINDOW = int(os.environ.get("PRWINDOW","60"))
PAPER = re.compile(r"(?i)(P\d{4}R\d+|LWG\s?\d+|CWG\s?\d+|#\d+)")

def pt(t): return sum(sc.point_dict.get(k,0)*v for k,v in t.items())
def d(s): return datetime.date(*map(int, s.split("-")))

for r in rows:
    r["pages"] = tuple(p for p in r.get("pages", []) if not HUB.match(p))
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
PAGE_REPOS = ("cpprefjp/site", "boostjp/site")
for i in order:
    r = rows[i]
    if not r["pages"] or r["repo"] not in PAGE_REPOS:
        continue
    if len(r["pages"]) > 5:
        # 大量ページを触るコミットは原則まとめないが、
        # 直前の作業とページ集合が完全に一致する場合は続きの作業とみなす
        same = [j for j in set(owner.get((r["repo"], r["login"], pg)) for pg in r["pages"])
                if j is not None]
        if not (len(same) == 1 and set(rows[same[0]]["pages"]) == set(r["pages"])):
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
            if not (set(r["pages"]) & set(p["pages"])):
                continue
            # 微調整はその作業の行に吸収するだけで、ポイントは増やさない
            p["hashes"].append(r["hash"])
            p["coauthors"] = sorted(set(p["coauthors"]) | set(r["coauthors"]))
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
            p["coauthors"] = sorted(set(p["coauthors"]) | set(r["coauthors"]))
            p["papers"] |= r["papers"]
            p["pages"] = tuple(sorted(set(p["pages"]) | set(r["pages"])))
            p["date_last"] = r["date"]
            dropped.add(i)
            continue
    for k in keys:
        owner[k] = i

# data/merge.txt で、まとめ先を人が明示した分を適用する。
# 「同年内の当人による同ページへの複数の修正はまとめる場合がある」のうち、
# 自動判定の条件 (30日以内・5ページ以下など) から外れるものを手で指定する。
MERGE = []
mp = sys.argv[4] if len(sys.argv) > 4 else None
if mp and os.path.exists(mp):
    for line in open(mp):
        line = line.split("#")[0].strip()
        if not line:
            continue
        cols = line.split()
        if len(cols) >= 2:
            MERGE.append((cols[0], cols[1]))
if MERGE:
    pos = {}
    for i, r in enumerate(rows):
        if i in dropped:
            continue
        for h in r["hashes"]:
            pos[h] = i
    for absorbed, target in MERGE:
        i, j = pos.get(absorbed), pos.get(target)
        if i is None or j is None or i == j:
            print("WARNING: merge %s -> %s を適用できない" % (absorbed, target))
            continue
        rows[j]["hashes"].extend(rows[i]["hashes"])
        rows[j]["coauthors"] = sorted(set(rows[j]["coauthors"]) | set(rows[i]["coauthors"]))
        dropped.add(i)
        for h in rows[i]["hashes"]:
            pos[h] = j

# まとめた結果が1ページだけの行は、「同ページ内に対する複数の修正は、大きい
# 貢献ポイントにまとめる」というルールに従い、もっとも大きいタグだけを残す
for i, r in enumerate(rows):
    if i in dropped or len(r["hashes"]) < 2 or len(r["pages"]) != 1:
        continue
    cand = {k: v for k, v in r["tags"].items() if k != "ignore"}
    if len(cand) < 2:
        continue
    best = max(cand, key=lambda k: sc.point_dict.get(k, 0))
    r["tags"] = {best: cand[best]}

out = [r for i, r in enumerate(rows) if i not in dropped]
for r in out:
    r["pages"] = list(r["pages"]); r.pop("papers", None)
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
json.dump(sorted(rows[i]["hash"] for i in dropped), open(sys.argv[2]+".dropped", "w"))
print("rows: %d -> %d (merged %d)" % (len(rows), len(out), len(dropped)))
