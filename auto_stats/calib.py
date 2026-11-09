import json, re, sys
from collections import Counter
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import stats_contribution as sc

md = open(os.environ.get("TRUTH_MD", "cpprefjp/site/start_editing/contribution_stats_2025.md")).read()
truth = {}   # hash7 -> (tags, repo, desc)  only single-commit single-repo rows
for line in md.split("\n"):
    if not line.startswith("| ["): continue
    cols = line.split("|")
    refs = re.findall(r"\[commit ([\w/]+), ([^\]]+)\]", cols[1])
    if len(refs) != 1: continue
    repo, ids = refs[0]
    ids = [x.strip() for x in ids.split(",") if x.strip()]
    if len(ids) != 1: continue
    tg = {}
    ok = True
    for part in cols[2].split(","):
        part = part.strip()
        if not part: continue
        if ":" in part:
            k,v = part.rsplit(":",1)
            try: tg[k.strip()] = int(v)
            except: ok = False
        else:
            tg[part] = 1
    if not ok: continue
    truth[ids[0][:7]] = (tg, repo, cols[3].strip())

rows = json.load(open(sys.argv[1]))
pred = {r["hash"]: r for r in rows if r["repo"] in ("cpprefjp/site","boostjp/site")}

def pt(t): return sum(sc.point_dict.get(k,0)*v for k,v in t.items())

common = [h for h in truth if h in pred]
print("ground-truth single rows:", len(truth), " / matched with prediction:", len(common))
exact = 0; ptsum_t = 0; ptsum_p = 0
confusion = Counter()
diffs = []
for h in common:
    t, repo, desc = truth[h]
    p = pred[h]["tags"]
    ptsum_t += pt(t); ptsum_p += pt(p)
    if t == p: exact += 1
    else:
        diffs.append((pt(p)-pt(t), h, desc, t, p))
    # tag-level confusion for single-tag rows
    if len(t) == 1 and len(p) == 1:
        confusion[(list(t)[0], list(p)[0])] += 1
print("exact tag-set match: %d/%d = %.1f%%" % (exact, len(common), exact/len(common)*100))
print("total points: truth=%d pred=%d (ratio %.2f)" % (ptsum_t, ptsum_p, ptsum_p/ptsum_t))
print("\nsingle-tag confusion (truth -> pred), top 25:")
for (a,b),n in confusion.most_common(25):
    mark = "  OK" if a==b else "  <-- mismatch"
    print("  %-22s -> %-22s %4d%s" % (a,b,n,mark))
print("\nlargest point overestimates:")
diffs.sort(key=lambda x:-x[0])
for d,h,desc,t,p in diffs[:12]:
    print("  %+6d %s %s | truth=%s pred=%s" % (d,h,desc[:52],t,p))
print("\nlargest point underestimates:")
for d,h,desc,t,p in diffs[-12:]:
    print("  %+6d %s %s | truth=%s pred=%s" % (d,h,desc[:52],t,p))
