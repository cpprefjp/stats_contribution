import json, sys
from collections import Counter
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import stats_contribution as sc
rows = json.load(open(sys.argv[1]))
per = Counter(); tagcnt = Counter()
for r in rows:
    p = 0
    for k,v in r["tags"].items():
        if k not in sc.point_dict: 
            print("unknown tag", k); continue
        p += sc.point_dict[k]*v
        tagcnt[k] += v
    per[r["login"]] += p
    for co in set(r["coauthors"]):
        if co != r["login"]: per[co] += p
tot = sum(per.values())
print("%-20s %8s %7s %7s" % ("user","point","comp","rate"))
comp = {k: int(pow(v,0.36)) if v>0 else 0 for k,v in per.items()}
ctot = sum(comp.values())
for k,v in per.most_common():
    print("%-20s %8d %7d %6.2f%%" % (k, v, comp[k], comp[k]/ctot*100 if ctot else 0))
print("total raw:", tot, "compressed total:", ctot)
print("\ntag usage:")
for k,v in tagcnt.most_common(): print("  %-22s %d" % (k,v))
