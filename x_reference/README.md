# x_reference/ — 「Xについて」フォルダの同期先（過去のX投稿・参考データ）

ローカルPCの **「Xについて」フォルダ**の中身を、ここ（リポジトリの `x_reference/`）に
**1日1回自動 push** して同期します。同期された内容は次の2つで参照されます。

1. **毎朝の自動分析パイプライン**（`scripts/fetch_and_analyze.py`）… 競合分析レポートの素材
2. **Claude Code スキル `x-post-writer`** … 手動でX投稿を練るときの過去データ参考

> スキル用のダイジェスト（`.claude/skills/x-post-writer/reference_digest.md`）は
> **1日1回だけ**更新されます（当日分が既にあれば再生成しません）。

## 同期のしくみ
ローカルの自動 push スクリプト（`scripts/local_daily_push.sh` / `local_daily_push.bat`）が、
ローカルの「Xについて」フォルダの中身をこのフォルダにコピー → ダイジェスト生成 → commit/push します。
cron（mac/Linux）やタスクスケジューラ（Windows）で1日1回実行してください。詳細はリポジトリ直下の `README.md`。

## 対応フォーマット
`README.md` と `.` で始まるファイルは無視されます。

### テキスト（`.txt` / `.md`）
1ファイル=1投稿が基本。1ファイルに複数入れる場合は **`---` だけの行**で区切る。

```
1つ目の投稿本文…
---
2つ目の投稿本文…
```

### JSON（`.json`）
```json
["1つ目の投稿本文", "2つ目の投稿本文"]
```
```json
{ "posts": [ { "text": "投稿本文", "posted_at": "2026-05-01" } ] }
```

### CSV（`.csv`）
`text`（または `tweet` / `本文`）列を含める。`posted_at` / `date` / `日付` 列は任意。

```csv
text,posted_at
"投稿本文1",2026-05-01
```

## 上限の調整
`config/competitors.json` の `settings`：
- `max_reference_items`：読み込む最大件数（デフォルト200）
- `max_reference_chars`：1件あたりの最大文字数（デフォルト500）

## サンプル
`sample_posts.txt` を同梱。動作確認後は削除・差し替えしてください。
