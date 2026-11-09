# auto_stats

`start_editing/contribution_stats_<年>.md` の下書きを機械的に生成するスクリプト群。
最終的な割り振りは人が確認して直すことを前提にしている。

## 使い方

対象リポジトリは親ディレクトリの `run.sh` がcloneしたものを使う。

```sh
sh auto_stats/run_2026.sh      # out/contribution_stats_2026.md を生成
```

生成したファイルを `cpprefjp/site/start_editing/` に置き、`sh run_2026.sh` で
ポイントを集計する。未集計コミットが報告されなくなるまで繰り返す。

## 処理の流れ

| スクリプト | 役割 |
|-----------|------|
| `collect.py`  | 対象期間のコミットのメタ情報・変更ファイル・Co-authorを集める |
| `feat.py`     | `git log -U0 -p` を1パス解析し、変更がリンク行だけか、処理系バージョン行だけか、文字単位で見て機械的な置換か、書式だけかを判定する |
| `undone.py`   | 追加行が期間終了時点のファイルに残っておらず、削除行が復活しているコミットを「巻き戻した変更」として検出する |
| `classify.py` | 上記の特徴からタグを割り振る。`data/overrides.txt` で個別に上書きできる |
| `group.py`    | 同一ページへの追随コミットと、同一Pull Request内の微調整コミットをひとつの行にまとめる |
| `gen_md.py`   | 集計ファイルのMarkdownを出力する。`data/groups.txt` で複数コミットを明示的に1行にでき、`data/extra.txt` で期間外のコミット (後からマージされたPull Requestなど) を足せる |

## 校正

前年の集計ファイルを正解として精度を測れる。

```sh
SINCE=2024-12-01 UNTIL=2025-12-01 python3 auto_stats/collect.py out/c25.json
SINCE=2024-12-01 UNTIL=2025-12-01 python3 auto_stats/feat.py    out/f25.json
SINCE=2024-12-01 UNTIL=2025-12-01 python3 auto_stats/undone.py  out/u25.json
UNDONE=out/u25.json ADDMODE=parent FIXM_MAX=40 \
  python3 auto_stats/classify.py out/c25.json out/f25.json out/r25.json /dev/null
WINDOW=30 PRWINDOW=60 python3 auto_stats/group.py out/r25.json out/r25g.json
python3 auto_stats/holdout.py cpprefjp/site/start_editing/contribution_stats_2025.md out/r25g.json
```

2026年時点での成績 (分配率の個別最大ズレ / 片側合計ズレ)：

- 2025年 (この年の判断に合わせて調整した): 1.7 / 5.3 ポイント
- 2024年 (調整に使っていない): 1.2 / 8.9 ポイント

`tool/*` タグは差分から判定できないため `data/overrides.txt` に手で書く。
校正時もツール系の行は対象から除いている。

## 圧縮境界の確認

分配率は `int(base^0.36)` の切り捨てで決まるため、境界の近くにいる人は1ポイントの
判定で分配率が1枠 (2026年は0.58%) 動く。上位は数百〜数千ポイントの誤差でも枠が
動かないのに、下位は1ポイントで動くという非対称がある。

```sh
python3 auto_stats/boundary.py 2026
```

「境界が近い」と出た人の行は、必ず差分を目視で確認する。

## 判定しきれないもの

- 作業者との個別合意で低く付ける場合 (2025年の「機械的作業ということで作業者からの希望で低めのポイント」など)
- 他のコミットとのポイント統合のうち、ページもPull Requestも共有しないもの

いずれも分配手順の「コントリビューターからの追加・修正の指摘を募集」で拾う前提。
