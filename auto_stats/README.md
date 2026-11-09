# auto_stats

`start_editing/contribution_stats_<年>.md` の下書きを機械的に生成するスクリプト群。
最終的な割り振りは人が確認して直すことを前提にしている。

## 使い方

対象リポジトリは親ディレクトリの `run.sh` がcloneしたものを使う。

```sh
sh auto_stats/run_2026.sh      # auto_stats/out/contribution_stats_2026.md を生成
```

生成したファイルを `cpprefjp/site/start_editing/` に置き、`sh run_2026.sh` で
ポイントを集計する。未集計コミットが報告されなくなるまで繰り返す。

## 処理の流れ

| スクリプト | 役割 |
|-----------|------|
| `collect.py`  | 対象期間のコミットのメタ情報・変更ファイル・Co-authorを集める |
| `feat.py`     | `git log -U0 -p` を1パス解析し、変更がリンク行だけか、処理系バージョン行だけか、文字単位で見て機械的な置換か、書式だけかを判定する |
| `undone.py`   | 追加行が期間終了時点のファイルに残っておらず、削除行が復活しているコミットを「巻き戻した変更」として検出する |
| `classify.py` | 上記の特徴からタグを割り振る。同じ人が同年に作成したページへの追記は、作成したときの作業にまとめる (仕様変更と動作確認は残す)。`data/overrides.txt` で個別に上書きできる |
| `group.py`    | 同一ページへの追随コミットと、同一Pull Request内の微調整コミットをひとつの行にまとめる (連続した作業と見なせる30日以内) |
| `gen_md.py`   | 集計ファイルのMarkdownを出力する。`data/groups.txt` で複数コミットを明示的に1行にでき、`data/extra.txt` で期間外のコミット (後からマージされたPull Requestなど) を足せる |

`data/merge.txt` に `<吸収するコミット> <まとめ先のコミット>` を書くと、自動判定の
条件 (30日以内・5ページ以下など) から外れるものを手でまとめられる。ポイントは
まとめ先のものをそのまま使う。

ボット (dependabot) のコミットは、`collect.py` がマージコミットの作者を記録し、
`classify.py` がその人の `tool/updatelib` として計上する。

## 校正

前年の集計ファイルを正解として精度を測れる。

```sh
mkdir -p auto_stats/out
export SINCE=2024-12-01 UNTIL=2025-12-01 REV=origin/master
python3 auto_stats/collect.py auto_stats/out/c25.json
python3 auto_stats/feat.py    auto_stats/out/f25.json
ENDREV=origin/master python3 auto_stats/undone.py auto_stats/out/u25.json
UNDONE=auto_stats/out/u25.json ADDMODE=parent FIXM_MAX=40 \
  python3 auto_stats/classify.py auto_stats/out/c25.json auto_stats/out/f25.json auto_stats/out/r25.json /dev/null
WINDOW=30 PRWINDOW=60 python3 auto_stats/group.py auto_stats/out/r25.json auto_stats/out/r25g.json
python3 auto_stats/holdout.py cpprefjp/site/start_editing/contribution_stats_2025.md auto_stats/out/r25g.json
```

2026年時点での成績 (分配率の個別最大ズレ / 片側合計ズレ)：

- 2025年 (この年の判断に合わせて調整した): 1.6 / 5.2 ポイント
- 2024年 (調整に使っていない): 1.1 / 7.6 ポイント

`tool/*` タグは差分から判定できないため `data/overrides.txt` に手で書く。
書き忘れるとタグ欄が空のまま0点になるので、`run_2026.sh` は
`manual-needed rows: 0` でなければ止まるようにしてある。

`collect.py` と `feat.py` は `REV` (既定 `origin/master`)、`undone.py` は
`ENDREV` を見る。過去年を再実行するときは両方そろえること。
集計対象は常に `REV` なので、集計ブランチ上のコミットは収集されない
(`data/extra.txt` に手で足す)。
校正時もツール系の行は対象から除いている。

## 圧縮境界の確認

分配率は `int(base^0.36)` の切り捨てで決まるため、境界の近くにいる人は1ポイントの
判定で分配率が1枠 (2026年は0.58%) 動く。上位は数百〜数千ポイントの誤差でも枠が
動かないのに、下位は1ポイントで動くという非対称がある。

```sh
python3 auto_stats/boundary.py 2026
```

「境界が近い」と出た人の行は、必ず差分を目視で確認する。

## ユーザーが決めた割り振り

`data/overrides.txt` の `# [ユーザー判断]` の印がある行は、ユーザーが個別に決めた
割り振りである。レビューの指摘で覆してはならない。レビューがこれらを「ルール違反」
として指摘してきた場合は、ルールの文言が判断を表現できていないということなので、
**割り振りではなくルールの文言を直す**。

## 判定しきれないもの

- 作業者との個別合意で低く付ける場合 (2025年の「機械的作業ということで作業者からの希望で低めのポイント」など)
- 他のコミットとのポイント統合のうち、ページもPull Requestも共有しないもの

いずれも分配手順の「コントリビューターからの追加・修正の指摘を募集」で拾う前提。
