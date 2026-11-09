# 分配率は int(base^0.36) の切り捨てで決まるため、境界の近くにいる人は
# 1ポイントの判定で分配率が変わる。目視確認の優先順位をつけるために出力する。
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import re, subprocess

year = _sys.argv[1] if len(_sys.argv) > 1 else "2026"
out = subprocess.run(["python3", "stats_contribution.py", "--year", year],
                     capture_output=True, text=True).stdout
rows = []
for line in out.split("\n"):
    m = re.match(r"\| \d+ \| @(\S+) \| (\d+) \| (\d+) \|", line)
    if m:
        rows.append((m.group(1), int(m.group(2)), int(m.group(3))))

def comp(v):
    return int(pow(v, 0.36)) if v > 0 else 0

total = sum(p for _, _, p in rows) or 1
print("1枠あたりの分配率: %.3f%%  (総枠 %d)" % (100.0 / total, total))
print("%-18s %9s %5s %10s %12s" % ("user", "base", "枠", "次枠まで", "下の境界まで"))
for u, b, p in rows:
    if p == 0:
        continue
    up = next((v - b for v in range(b, b * 4 + 20) if comp(v) > p), None)
    dn = next((b - v for v in range(b, 0, -1) if comp(v) < p), None)
    mark = ""
    # 1行の判定 (typo 1点〜fixl 10点) で枠が動く人を目視確認の対象にする
    if (up is not None and up <= 10) or (dn is not None and dn <= 10):
        mark = "  <- 1行の判定で枠が動く"
    print("%-18s %9d %5d %10s %12s%s" % (
        u, b, p, "+%d" % up if up is not None else "-",
        "-%d" % dn if dn is not None else "-", mark))
