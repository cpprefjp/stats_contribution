import json, sys, os
rows = json.load(open(sys.argv[1]))
outdir = sys.argv[2]
byu = {}
for r in rows:
    byu.setdefault(r["login"], []).append(r)
for u, rs in byu.items():
    with open(os.path.join(outdir, "rev_"+u.replace("[","_").replace("]","_")+".txt"), "w") as f:
        for r in sorted(rs, key=lambda x: x["date"]):
            tg = ", ".join("%s:%d" % (k,v) for k,v in r["tags"].items())
            f.write("%s %s %s | %s | %s | %s%s\n" % (r["date"], r["repo"], r["hash"], r["subject"],
                    tg, ";".join(r["details"]), " [CO:"+",".join(r["coauthors"])+"]" if r["coauthors"] else ""))
    print(u, len(rs))
