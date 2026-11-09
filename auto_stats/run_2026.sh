#!/bin/sh
# 2026年分の集計ファイルを生成する。
# cpprefjp/site などのリポジトリは ../run.sh でcloneされているものを使う。
set -e
cd "$(dirname "$0")/.."
OUT=${OUT:-auto_stats/out}
mkdir -p "$OUT"

export SINCE=2025-12-01
export UNTIL=2026-12-01
export ENDREV=origin/master

python3 auto_stats/collect.py "$OUT/commits.json"
python3 auto_stats/feat.py    "$OUT/feats.json"
python3 auto_stats/undone.py  "$OUT/undone.json"

UNDONE="$OUT/undone.json" ADDMODE=parent FIXM_MAX=40 \
  python3 auto_stats/classify.py "$OUT/commits.json" "$OUT/feats.json" "$OUT/rows.json" auto_stats/data/overrides.txt
WINDOW=30 PRWINDOW=60 \
  python3 auto_stats/group.py "$OUT/rows.json" "$OUT/rows_grouped.json" auto_stats/data/skip.txt auto_stats/data/merge.txt
python3 auto_stats/gen_md.py "$OUT/rows_grouped.json" auto_stats/data/groups.txt \
  "$OUT/contribution_stats_2026.md" auto_stats/data/extra.txt

echo "generated: $OUT/contribution_stats_2026.md"
