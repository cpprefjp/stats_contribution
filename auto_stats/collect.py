import json, re, subprocess, sys, os

REPOS = ["cpprefjp/site","cpprefjp/site_generator","cpprefjp/kunai",
         "cpprefjp/kunai_config","cpprefjp/crsearch", "boostjp/site"]
import os
SINCE = os.environ.get("SINCE","2025-12-01")
UNTIL = os.environ.get("UNTIL","2026-12-01")
REV = os.environ.get("REV","origin/master")
S1 = "\x1e"  # record sep
S2 = "\x1d"  # field sep

EMAIL2LOGIN = {
 "faithandbrave@gmail.com":"faithandbrave",
 "haruka.sao@gmail.com":"h-sao",
 "keito.tottori@gmail.com":"K10-K10",
 "kaitomotake@gmail.com":"KaiTomotake",
 "kazuya2002uk@gmail.com":"pipapo-888",
 "matsumura.t.lab@gmail.com":"tetsurom",
 "yuki18425@gmail.com":"yknishidate",
 "t_toshi2006@yahoo.co.jp":"komori-n",
 "eng.equall2@gmail.com":"equal-l2",
 "iKonnyaku40@gmail.com":"Gumichocopengin8",
 "shawn316michaels@gmail.com":"suomesta",
 "raclamusi@gmail.com":"Raclamusi",
 "s.goto2050@gmail.com":"rotarymars",
 "kawasaki.liamg@gmail.com":"yohhoy",
 "myoga.murase@gmail.com":"akinomyoga",
 "takechi101010@gmail.com":"take-cheeze",
 "take-cheeze@users.noreply.github.com":"take-cheeze",
 "git@ryoga.dev":"Ryoga-exe",
 "yume-wikijp@live.jp":"yumetodo",
}
def login(name, email):
    if email in EMAIL2LOGIN: return EMAIL2LOGIN[email]
    m = re.fullmatch(r"\d+\+(.*)@users\.noreply\.github\.com", email)
    if m: return m.group(1)
    m = re.fullmatch(r"(.*)@users\.noreply\.github\.com", email)
    if m: return m.group(1)
    return name

def run(repo, args):
    return subprocess.run(["git"]+args, cwd=repo, capture_output=True, text=True).stdout

out = []
for repo in REPOS:
    fmt = S1 + S2.join(["%h","%ad","%an","%ae","%s","%b"]) + S2
    log = run(repo, ["log","--no-merges","--since",SINCE,"--until",UNTIL,
                     "--date=short","--pretty="+fmt,"--numstat",REV])
    for rec in log.split(S1):
        if not rec.strip(): continue
        parts = rec.split(S2)
        h, date, an, ae, subject, body = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        rest = parts[6] if len(parts) > 6 else ""
        files = []
        for line in rest.split("\n"):
            m = re.fullmatch(r"(\d+|-)\t(\d+|-)\t(.*)", line.strip())
            if m:
                a = 0 if m.group(1)=="-" else int(m.group(1))
                d = 0 if m.group(2)=="-" else int(m.group(2))
                files.append({"add":a,"del":d,"path":m.group(3)})
        cos = []
        for m in re.finditer(r"(?i)co-authored-by:\s*(.*?)\s*<(.*?)>", body):
            cos.append(login(m.group(1), m.group(2)))
        # file statuses
        st = run(repo, ["show","--pretty=","--name-status",h])
        status = {}
        for line in st.split("\n"):
            c = line.split("\t")
            if len(c) >= 2:
                status[c[-1]] = c[0][0]
        for f in files:
            f["status"] = status.get(f["path"], "M")
        # dependabotのコミットは、動作確認してマージした人の貢献として扱うため、
        # そのコミットをmasterへ取り込んだマージコミットの作者を記録する
        merged_by = None
        if login(an, ae) == "dependabot[bot]":
            ml = run(repo, ["log","--ancestry-path","--merges","--format=%an|%ae",
                            h + ".." + REV]).strip().split("\n")
            if ml and ml[-1]:
                man, mae = ml[-1].split("|")
                merged_by = login(man, mae)
        # dependabotの更新で、実際に更新された「直接使用のライブラリ」の名前を集める。
        # package-lock.json 以外のファイルの差分に現れる依存の名前が直接使用のもの。
        dep_names = []
        if merged_by:
            diff = run(repo, ["show", "-U0", "--pretty=", "--no-color", h])
            cur = None
            for line in diff.split("\n"):
                if line.startswith("diff --git "):
                    m2 = re.match(r"diff --git a/(.*) b/(.*)", line)
                    cur = m2.group(2) if m2 else None
                    continue
                if not cur or cur.endswith("package-lock.json"):
                    continue
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                body = line[1:]
                m2 = re.search(r'"([^"]+)"\s*:\s*"[~^>=<0-9]', body)        # package.json
                if m2 and m2.group(1) in ("version", "name", "node", "npm",
                                          "engines", "main", "module"):
                    m2 = None
                if not m2:
                    m2 = re.search(r"uses:\s*([\w.-]+/[\w.-]+)@", body)      # ワークフロー
                if not m2:
                    m2 = re.match(r"\s*([A-Za-z][\w.-]*)\s*[=~><]=", body)  # requirements.txt
                if m2 and m2.group(1) not in dep_names:
                    dep_names.append(m2.group(1))
        out.append({"repo":repo,"hash":h[:7],"date":date,"login":login(an,ae),
                    "merged_by":merged_by,"dep_names":dep_names,
                    "author":an,"email":ae,"subject":subject.strip(),
                    "coauthors":[c for c in cos if c],"files":files})
json.dump(out, open(sys.argv[1],"w"), ensure_ascii=False, indent=None)
print("commits:", len(out))
