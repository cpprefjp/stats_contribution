# 各コミットの変更が、期間終了時点のファイルに残っているかを判定する。
# 追加行がほぼ残らず、削除行がほぼ復活している場合、その変更は取り消されたとみなす。
import json, os, re, subprocess, sys
REPOS = ["cpprefjp/site","cpprefjp/site_generator","cpprefjp/kunai",
         "cpprefjp/kunai_config","cpprefjp/crsearch", "boostjp/site"]
S1 = "\x1e"
SINCE = os.environ.get("SINCE","2025-12-01")
UNTIL = os.environ.get("UNTIL","2026-12-01")
ENDREV_DEFAULT = os.environ.get("ENDREV","")
def end_rev(repo):
    if ENDREV_DEFAULT:
        return ENDREV_DEFAULT
    r = subprocess.run(["git","rev-list","-1","--before",UNTIL,"origin/master"],
                       cwd=repo, capture_output=True, text=True)
    return r.stdout.strip() or "origin/master"

cache = {}
def final_content(repo, path):
    key = (repo, path)
    if key not in cache:
        r = subprocess.run(["git","show","%s:%s" % (end_rev(repo), path)], cwd=repo,
                           capture_output=True, text=True)
        cache[key] = None if r.returncode else set(l.strip() for l in r.stdout.split("\n") if l.strip())
    return cache[key]

out = {}
for repo in REPOS:
    log = subprocess.run(["git","log","--no-merges","--since",SINCE,"--until",UNTIL,
        "-U0","--pretty="+S1+"%h","-p","--no-color",end_rev(repo)], cwd=repo,
        capture_output=True, text=True).stdout
    for rec in log.split(S1):
        if not rec.strip(): continue
        lines = rec.split("\n")
        h = lines[0].strip()[:7]
        cur = None; d = {}
        for line in lines[1:]:
            if line.startswith("diff --git "):
                m = re.match(r"diff --git a/(.*) b/(.*)", line)
                cur = m.group(2) if m else None
                if cur: d.setdefault(cur, ([], []))
                continue
            if cur is None: continue
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"): continue
            if line.startswith("+"): d[cur][0].append(line[1:].strip())
            elif line.startswith("-"): d[cur][1].append(line[1:].strip())
        tot_add = tot_add_gone = tot_rem = tot_rem_back = 0
        for path, (add, rem) in d.items():
            if not path.endswith(".md"): continue
            fin = final_content(repo, path)
            if fin is None:   # ファイル自体が消えている
                continue
            add = [l for l in add if l]; rem = [l for l in rem if l]
            tot_add += len(add); tot_rem += len(rem)
            tot_add_gone += sum(1 for l in add if l not in fin)
            tot_rem_back += sum(1 for l in rem if l in fin)
        if tot_add + tot_rem == 0: continue
        gone = tot_add_gone / tot_add if tot_add else 1.0
        back = tot_rem_back / tot_rem if tot_rem else 1.0
        out[repo + "@" + h] = {"add": tot_add, "rem": tot_rem,
                               "gone": round(gone, 3), "back": round(back, 3)}
json.dump(out, open(sys.argv[1], "w"))
undone = [k for k, v in out.items()
          if v["gone"] >= 0.8 and v["back"] >= 0.8 and v["add"] > 0 and v["rem"] > 0]
print("analyzed:", len(out), " undone candidates:", len(undone))
