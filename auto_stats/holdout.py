import json,re,sys
from collections import Counter
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import stats_contribution as sc
md=open(sys.argv[1]).read()
user=None; truth=Counter(); tool=Counter()
for line in md.split("\n"):
    m=re.fullmatch(r"## \[(.*?)\]\(.*?\)", line)
    if m: user=m.group(1); continue
    if not line.startswith("| ["): continue
    cols=line.split("|")
    for part in cols[2].split(","):
        part=part.strip()
        if not part: continue
        if ":" in part:
            k,v=part.rsplit(":",1); k=k.strip()
            try: p=sc.point_dict.get(k,0)*int(v)
            except: p=0
        else:
            k=part; p=sc.point_dict.get(part,0)
        truth[user]+=p
        if k.startswith("tool/"): tool[user]+=p
rows=json.load(open(sys.argv[2]))
pred=Counter()
for r in rows:
    if r["login"]=="dependabot[bot]": continue
    p=sum(sc.point_dict.get(k,0)*v for k,v in r["tags"].items() if not k.startswith("tool/"))
    pred[r["login"]]+=p
    for co in set(r["coauthors"]): pred[co]+=p
for u in set(list(pred)+list(tool)): pred[u]+=tool.get(u,0)
def comp(v): return int(pow(v,0.36)) if v>0 else 0
def shares(d):
    c={u:comp(v) for u,v in d.items() if v>0}; tot=sum(c.values()) or 1
    return {u:100*v/tot for u,v in c.items()}, c
st,ct=shares(truth); sp,cp=shares(pred)
tb=sum(v for v in truth.values() if v>0); pb=sum(pred.get(u,0) for u in truth if truth[u]>0)
print("base point 合計: 真=%d 予=%d (比 %.2f)" % (tb,pb,pb/tb))
print("%-18s %8s %8s | %6s %6s %7s" % ("user","base(真)","base(予)","share真","share予","差"))
for u,v in truth.most_common(10):
    if v<=0: continue
    print("%-18s %8d %8d | %5.1f%% %5.1f%% %+6.1fpt" % (u,v,pred.get(u,0),st.get(u,0),sp.get(u,0),sp.get(u,0)-st.get(u,0)))
print("分配率の総ズレ (片側合計): %.1f ポイント / 最大個別ズレ: %.1f ポイント" % (
    sum(abs(sp.get(u,0)-st.get(u,0)) for u in st)/2,
    max(abs(sp.get(u,0)-st.get(u,0)) for u in st)))
