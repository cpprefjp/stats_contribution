import json, sys, os, re
from collections import Counter, OrderedDict
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import stats_contribution as sc

rows = json.load(open(sys.argv[1]))
groups_path = sys.argv[2]
out_path = sys.argv[3]

byhash = {}
for r in rows:
    byhash.setdefault(r["hash"], []).append(r)

# merge same-hash rows across repos
merged = []
seen = set()
for r in rows:
    if r["hash"] in seen: continue
    seen.add(r["hash"])
    rs = byhash[r["hash"]]
    same = [x for x in rs if x["tags"] == rs[0]["tags"]]
    if len(same) != len(rs):
        # 7桁の短縮ハッシュが別リポジトリで衝突した場合は別行として扱う
        rs = [r]
        seen.discard(r["hash"])
    m = dict(rs[0])
    m["repos"] = [x["repo"] for x in rs]
    m["hashes"] = r.get("hashes", [r["hash"]])
    merged.append(m)

# apply explicit groups
grouped = {}
if os.path.exists(groups_path):
    for line in open(groups_path):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"): continue
        hs, tg, desc = line.split("\t")
        hl = [h.strip() for h in hs.split(",")]
        d = {}
        for part in tg.split(","):
            part = part.strip()
            if not part: continue
            k, v = part.rsplit(":", 1)
            d[k.strip()] = int(v)
        grouped[hl[0]] = (hl, d, desc)
        for h in hl[1:]:
            grouped[h] = None

final = []
for m in merged:
    g = grouped.get(m["hashes"][0], 0)
    if g is None:
        continue
    if g != 0:
        hl, d, desc = g
        m = dict(m); m["hashes"] = hl; m["tags"] = d; m["subject"] = desc
    final.append(m)

extra_path = sys.argv[4] if len(sys.argv) > 4 else None
if extra_path and os.path.exists(extra_path):
    for line in open(extra_path):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"): continue
        cols = line.split("\t")
        repo, hs, login, date, tg, desc = cols[:6]
        cos = [x.strip() for x in cols[6].split(",")] if len(cols) > 6 and cols[6].strip() else []
        d = {}
        for part in tg.split(","):
            part = part.strip()
            if not part: continue
            if ":" in part:
                k, v = part.rsplit(":", 1); d[k.strip()] = int(v)
            else:
                d[part] = 1
        final.append({"repos":[repo], "hashes":[h.strip() for h in hs.split(",")],
                      "login":login, "date":date, "tags":d, "subject":desc, "coauthors":cos})

def pt(tags):
    return sum(sc.point_dict.get(k, 0)*v for k, v in tags.items())

users = {}
for m in final:
    users.setdefault(m["login"], []).append((m, False))
    for co in set(m["coauthors"]):
        users.setdefault(co, []).append((m, True))

totals = {u: sum(pt(m["tags"]) for m, _ in rs) for u, rs in users.items()}
order = sorted(users.keys(), key=lambda u: (-totals[u], u.lower()))

TAGORDER = ["cpprefjp/typo","cpprefjp/link","cpprefjp/compiler","cpprefjp/fixs","cpprefjp/fixm","cpprefjp/fixl",
            "cpprefjp/addref","cpprefjp/addlang","cpprefjp/addpage",
            "boostjp/typo","boostjp/link","boostjp/fixs","boostjp/fixm","boostjp/releases","boostjp/releasem",
            "boostjp/releasel","boostjp/addrefs","boostjp/addrefm",
            "tool/improves","tool/improvem","tool/improvel","tool/fixbug","tool/updatelib","tool/updatelangs","tool/updatelangm","tool/updatelangl",
            "tool/security","tool/adds","tool/addm","tool/addl","ignore"]
def fmt_tags(tags):
    items = sorted(tags.items(), key=lambda kv: TAGORDER.index(kv[0]) if kv[0] in TAGORDER else 99)
    out = []
    for k, v in items:
        if k == "ignore":
            out.append("ignore" if v <= 1 else "ignore:%d" % v)
        else:
            out.append("%s:%d" % (k, v))
    return ", ".join(out)

lines = ["# 2026年 貢献ポイント",
         "2025年12月から2026年11月を対象期間として、貢献ポイントを集計する。",
         ""]
for u in order:
    if u == "dependabot[bot]":
        lines.append("")
        lines.append("## [dependabot](https://github.com/apps/dependabot)")
        lines.append("自動更新のため、貢献ポイントの対象外とする。")
    else:
        lines.append("")
        lines.append("## [%s](https://github.com/%s)" % (u, u))
    lines.append("")
    lines.append("| コミット | タグ | 説明 |")
    lines.append("|----------|------|------|")
    rs = sorted(users[u], key=lambda t: (t[0]["date"], t[0]["hashes"][0]))
    for m, isco in rs:
        refs = " ".join("[commit %s, %s]" % (repo, ", ".join(m["hashes"])) for repo in m["repos"])
        desc = m["subject"].replace("|", "\\|")
        if isco:
            desc += " (Co-author)"
        lines.append("| %s | %s | %s |" % (refs, fmt_tags(m["tags"]), desc))
    lines.append("")

open(out_path, "w").write("\n".join(lines) + "\n")
print("users:", len(order), "rows:", len(final))
for u in order:
    print("  %-20s %6d" % (u, totals[u]))
