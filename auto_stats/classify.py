import os
import json, re, sys
from collections import Counter, OrderedDict

commits = json.load(open(sys.argv[1]))
feats = json.load(open(sys.argv[2]))

TYPO = re.compile(r"(?i)typo|誤字|脱字|スペル|misspell|誤記|表記ミス|綴り")
SPEC = re.compile(r"(?i)P\d{4}R\d|LWG|CWG|仕様|非推奨|constexpr対応|mailing|C\+\+2[0-9]対応|Working Draft|規格|deprecat")
IGNORE_PATH = re.compile(r"^(start_editing/contribution_stats_|sponsors|\.github/ISSUE|LICENSE|CODEOWNERS)")
TOOLPATH = re.compile(r"^(\.github/|.*\.py$|.*\.ya?ml$|.*\.json$|.*\.js$|.*\.rb$|.*\.sh$|Dockerfile|Makefile)")

def page_kind(path):
    if path.startswith("lang/"): return "addlang"
    if path.startswith("reference/"): return "addref"
    return "addpage"

import os
UNDONE = {}
up = os.environ.get("UNDONE")
if up and os.path.exists(up):
    UNDONE = json.load(open(up))

OV = {}
ovp = sys.argv[4] if len(sys.argv) > 4 else None
if ovp and os.path.exists(ovp):
    for line in open(ovp):
        line = line.split("#")[0].strip()
        if not line: continue
        add = line.startswith("+")
        if add: line = line[1:]
        h, tg = line.split(None, 1)
        d = {}
        for part in tg.split(","):
            part = part.strip()
            if not part: continue
            if ":" in part:
                k, v = part.rsplit(":", 1); d[k.strip()] = int(v)
            else:
                d[part] = 1
        OV[h] = (d, add)

FIXM_MAX = int(os.environ.get("FIXM_MAX", "20"))
LINKSUBJ = re.compile(r"(?i)リンク|関連項目|nolink|\blinks?\b|参照を")
SPONSOR = re.compile(r"(?i)スポンサー|sponsor")
REVERT  = re.compile(r"(?i)^revert|巻き戻|取り消")
rows = []
for c in commits:
    repo = c["repo"]
    key = repo + "@" + c["hash"]
    fe = feats.get(key, {})
    subj = c["subject"]
    tags = Counter()
    details = []
    manual = False
    added_pages = [f["path"] for f in c["files"]
                   if f.get("status") == "A" and f["path"].endswith(".md")]
    def is_add_support(path):
        stem = path[:-3]
        for a in added_pages:
            if a.startswith(stem + "/") or os.path.dirname(a) == os.path.dirname(path):
                return True
        return False
    for f in c["files"]:
        path = f["path"]
        if "=>" in path:
            tags["ignore"] += 1; details.append(path+":rename"); continue
        fd = fe.get(path, {"n": f["add"]+f["del"], "link":False, "ver":0})
        n = fd["n"]; link = fd["link"]; ver = fd["ver"]; subst = fd.get("subst", False); subst2 = fd.get("subst2", False); fmt = fd.get("fmt", False)
        st = f.get("status","M")
        if IGNORE_PATH.match(path) or path.startswith("image/"):
            tags["ignore"] += 1; details.append(path+":skip"); continue
        if repo not in ("cpprefjp/site","boostjp/site") or TOOLPATH.match(path):
            manual = True; details.append("%s:TOOL(+%d-%d)" % (path, f["add"], f["del"])); continue
        if not path.endswith(".md"):
            if path.endswith("GLOBAL_QUALIFY_LIST.txt") or path.endswith("PRIMARY_OVERLOAD_SPECIALIZATION_LIST.txt"):
                tags["cpprefjp/link"] += 1; details.append(path+":link"); continue
            if path.endswith("GLOBAL_DEFINED_WORDS.json"):
                tags["cpprefjp/fixm"] += 1; details.append(path+":fixm"); continue
            manual = True; details.append(path+":OTHER"); continue
        pfx = "cpprefjp/" if repo == "cpprefjp/site" else "boostjp/"
        if st == "A":
            t = page_kind(path) if pfx == "cpprefjp/" else "addrefs"
            tags[pfx.rstrip("/")+"/"+t if False else pfx+t] += 1
            details.append("%s:A(%d)" % (path, n)); continue
        if st == "D":
            tags["ignore"] += 1; details.append(path+":D"); continue
        if n == 0:
            tags["ignore"] += 1; details.append(path+":empty"); continue
        if path == "implementation-status.md":
            if re.search(r"(?i)link|リンク", subj):
                tags[pfx+"link"] += 1; details.append("%s:link(%d)" % (path, n))
            else:
                cnt = max(1, fd.get("rows", 1))
                tags[pfx+"compiler"] += cnt; details.append("%s:compiler(%d rows/%d)" % (path, cnt, n))
            continue
        if TYPO.search(subj) and (n <= 4 or subst or subst2):
            tags[pfx+"typo"] += 1; details.append("%s:typo(%d)" % (path, n)); continue
        if ver and ver == n and pfx == "cpprefjp/":
            tags[pfx+"compiler"] += 1; details.append("%s:compiler(%d)" % (path, n)); continue
        if link or (LINKSUBJ.search(subj) and fd.get("alllink")):
            tags[pfx+"link"] += 1; details.append("%s:link(%d)" % (path, n)); continue
        if added_pages and os.environ.get("ADDMODE","parent") == "parent" and is_add_support(path):
            tags[pfx+"link"] = max(tags.get(pfx+"link", 0), 1)
            details.append("%s:add-support(%d)" % (path, n)); continue
        if fmt:
            tags[pfx+"fixs"] += 1; details.append("%s:fixs(fmt,%d)" % (path, n)); continue
        if SPEC.search(subj):
            tags[pfx+"fixl"] += 1; details.append("%s:fixl*(%d)" % (path, n)); continue
        if subst:
            tags[pfx+"fixm"] += 1; details.append("%s:fixm~(%d)" % (path, n)); continue
        if n <= FIXM_MAX:
            tags[pfx+"fixm"] += 1; details.append("%s:fixm(%d)" % (path, n))
        else:
            tags[pfx+"fixl"] += 1; details.append("%s:fixl(%d)" % (path, n))
    if c["hash"] in OV:
        d, add = OV[c["hash"]]
        if add:
            tags.update(d); details.append("OVERRIDE+")
        else:
            tags = Counter(d); details = ["OVERRIDE"]
        manual = False
    # 新規ページ追加を伴うコミットでは、同じ作業に含まれる既存ページの修正は
    # addref/addlang/addpage に含めて数える (2025年の人手判断に合わせる)
    ADDMODE = os.environ.get("ADDMODE", "parent")
    if ADDMODE in ("drop", "link"):
        has_add = any(k.endswith(("/addref", "/addlang", "/addpage")) for k in tags)
        if has_add:
            moved = 0
            for k in list(tags):
                if k.endswith(("/fixs", "/fixm", "/fixl")):
                    moved += tags.pop(k)
            if moved and ADDMODE == "link":
                pfx2 = "cpprefjp/" if repo == "cpprefjp/site" else "boostjp/"
                tags[pfx2 + "link"] = max(tags.get(pfx2 + "link", 0), 1)
    und = UNDONE.get(repo + "@" + c["hash"])
    is_undone = bool(und and und["gone"] >= 0.8 and und["back"] >= 0.8)
    if SPONSOR.search(subj) or REVERT.search(subj) or is_undone:
        tags = Counter({"ignore": 1}); manual = False
        details = ["undone" if is_undone else "rule-ignore"]
    elif c["files"] and all(f["path"].endswith(("package-lock.json",)) for f in c["files"]):
        tags = Counter({"ignore": 1}); manual = False; details = ["package-lock"]
    if "boostjp/fixl" in tags:
        tags["boostjp/fixm"] += tags.pop("boostjp/fixl")
    if c["login"] in ("dependabot[bot]",):
        tags = Counter({"ignore": 1}); manual = False; details = ["bot"]
    cos = [x for x in c["coauthors"] if x not in ("Copilot","copilot","dependabot[bot]","github-actions[bot]")
           and not x.lower().startswith(("claude", "gpt", "gemini")) and x != c["login"]]
    rows.append({"repo":repo,"hash":c["hash"],"date":c["date"],"login":c["login"],
                 "subject":subj,"coauthors":cos,
                 "tags":dict(tags),"details":details,"manual":manual,
                 "pages":sorted(x["path"] for x in c["files"] if x["path"].endswith(".md")),
                 "nfiles":len(c["files"])})
json.dump(rows, open(sys.argv[3],"w"), ensure_ascii=False)

# summary
per = Counter()
for r in rows:
    pts = 0
    per[r["login"]] += 1
print("commits per login:")
for k,v in per.most_common(): print("  %-20s %d" % (k,v))
print("manual-needed rows:", sum(1 for r in rows if r["manual"]))
