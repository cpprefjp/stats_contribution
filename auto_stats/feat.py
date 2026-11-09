import json, re, subprocess, sys, difflib
REPOS = ["cpprefjp/site","cpprefjp/site_generator","cpprefjp/kunai",
         "cpprefjp/kunai_config","cpprefjp/crsearch","cpprefjp/markdown_to_html",
         "boostjp/site"]
import os
SINCE=os.environ.get("SINCE","2025-12-01"); UNTIL=os.environ.get("UNTIL","2026-12-01")
REV = os.environ.get("REV","origin/master")
S1="\x1e"
LINKLINE = re.compile(r"\]\(|\.nolink|\[link ")
LISTLINK = re.compile(r"^\s*([-*+]\s+|\|)")
VER_RE = re.compile(r"^-?\s*\[?(Clang|GCC|Visual C\+\+|ICC|ICX|Oracle|EDG)\]?")
URL_RE = re.compile(r"\]\([^)]*\)")

MDLINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
def norm(l):
    return URL_RE.sub("](URL)", l).strip()
def plain(l):
    t = MDLINK.sub(r"\1", l).replace(".nolink", "")
    t = t.replace("./", "")
    return re.sub(r"\s+", " ", t).strip()

feats = {}
for repo in REPOS:
    log = subprocess.run(["git","log","--no-merges","--since",SINCE,"--until",UNTIL,
        "-U0","--pretty="+S1+"%h","-p","--no-color",REV], cwd=repo, capture_output=True, text=True).stdout
    for rec in log.split(S1):
        if not rec.strip(): continue
        lines = rec.split("\n")
        h = lines[0].strip()[:7]
        cur = None
        d = {}
        for line in lines[1:]:
            if line.startswith("diff --git "):
                m = re.match(r"diff --git a/(.*) b/(.*)", line)
                cur = m.group(2) if m else None
                if cur: d.setdefault(cur, [])
                continue
            if cur is None: continue
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"): continue
            if line.startswith("+") or line.startswith("-"):
                d[cur].append(line)
        out = {}
        for path, chl in d.items():
            add = [l[1:] for l in chl if l.startswith("+") and l[1:].strip()]
            rem = [l[1:] for l in chl if l.startswith("-") and l[1:].strip()]
            body = add + rem
            n = len(body)
            # 参照・関連項目のリンクに付随する説明の箇条書き (字下げされた箇条書き) は、
            # リンク編集の一部として扱う。LWG Issueの追加などが該当する。
            SUBBULLET = re.compile(r"^(\s{2,}|\t)[-*+]\s")
            def split_link(ls):
                lk = [l for l in ls if LINKLINE.search(l)]
                other = [l for l in ls if not LINKLINE.search(l)
                         and not l.strip().startswith("#")
                         and not SUBBULLET.match(l)
                         and l.strip() not in ("", "-", "*")]
                return lk, other
            alk, aot = split_link(add)
            rlk, rot = split_link(rem)
            is_link = False
            if n and (alk or rlk) and sorted(plain(x) for x in add) == sorted(plain(x) for x in rem):
                is_link = True
            elif n and (alk or rlk) and not aot and not rot:
                pa = set(plain(x) for x in add)
                pr = set(plain(x) for x in rem)
                if len(alk) != len(rlk):
                    is_link = pr <= pa or pa <= pr
                else:
                    is_link = sorted(norm(x) for x in alk) == sorted(norm(x) for x in rlk)
            at = "\n".join(add); rt = "\n".join(rem)
            if len(at) + len(rt) > 6000 or not add or not rem:
                subst = subst2 = fmt_only = False
                out_skip = True
            else:
                out_skip = False
            sm = None if out_skip else difflib.SequenceMatcher(None, rt, at, autojunk=False)
            if sm is not None:
                changed = 0; pairs = set()
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag == "equal": continue
                    changed += (i2 - i1) + (j2 - j1)
                    pairs.add((rt[i1:i2].strip(), at[j1:j2].strip()))
                subst = changed <= 30
                subst2 = len(pairs) <= 2 and changed <= 400
                import unicodedata
                FMT = set(" \t#*|-\n")
                fmt_only = bool(pairs) and all(
                    set(a) <= FMT and set(b) <= FMT for a, b in pairs)
            META_RE = re.compile(r"^\s*\*\s.*\[meta ")
            INC_RE = re.compile(r"^\s*#include")
            meta_only = bool(body) and all(META_RE.match(l) for l in body)
            heading_only = bool(body) and all(
                l.strip().startswith("#") and not INC_RE.match(l) for l in body)
            # 見出しの変更のうち、見出しのレベル (#の数) だけが変わったものと、
            # 見出しの削除は見た目の修正。見出しの文言が変わる場合は、
            # 読者に伝わる情報が変わるので軽微な修正とはしない。
            def htext(ls):
                return sorted(l.strip().lstrip("#").strip() for l in ls)
            heading_level_only = heading_only and (not add or htext(add) == htext(rem))
            include_only = bool(body) and all(INC_RE.match(l) for l in body)
            ver = sum(1 for l in body if VER_RE.match(l.strip().lstrip("-* ")))
            rows_added = sum(1 for l in add if l.strip().startswith("|"))
            out[path] = {"n": n, "link": is_link, "ver": ver, "rows": rows_added,
                         "nadd": len(add), "nrem": len(rem), "subst": subst, "subst2": subst2, "fmt": fmt_only,
                         "meta_only": meta_only, "heading_only": heading_only,
                         "heading_level_only": heading_level_only,
                         "include_only": include_only, "nadd_": len(add),
                         "alllink": bool(body) and all(LINKLINE.search(l) for l in body)}
        feats[repo+"@"+h] = out
json.dump(feats, open(sys.argv[1],"w"), ensure_ascii=False)
print("commits with diffs:", len(feats))
