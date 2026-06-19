#!/usr/bin/env bash
#
# ローカルの「Xについて」フォルダの中身を、このリポジトリの x_reference/ に同期し、
# スキル用ダイジェストを更新して、1日1回 git push する。
#
# 使い方:
#   1. 下の2つのパスを自分の環境に合わせて書き換える
#   2. 実行権限を付与:  chmod +x scripts/local_daily_push.sh
#   3. cron で1日1回実行（例は README.md 参照）
#
# mac/Linux 用。Windows は local_daily_push.bat を使う。

set -euo pipefail

# ===== 環境に合わせて書き換える =====
# ローカルの「Xについて」フォルダ（過去投稿・参考データの置き場）
SRC_DIR="${X_REFERENCE_SRC:-$HOME/Xについて}"
# このリポジトリのローカルクローンの場所
REPO_DIR="${X_REPO_DIR:-$HOME/-x-competitor-analysis-}"
# push 先ブランチ
BRANCH="${X_REPO_BRANCH:-main}"
# ====================================

DEST_DIR="$REPO_DIR/x_reference"

echo "[1/4] 同期: $SRC_DIR -> $DEST_DIR"
if [ ! -d "$SRC_DIR" ]; then
  echo "ERROR: 「Xについて」フォルダが見つかりません: $SRC_DIR" >&2
  exit 1
fi
mkdir -p "$DEST_DIR"
# README.md は残し、それ以外の既存ファイルを消してからコピー（ローカルをミラー）
find "$DEST_DIR" -type f ! -name 'README.md' -delete
cp -R "$SRC_DIR"/. "$DEST_DIR"/ 2>/dev/null || true

echo "[2/4] スキル用ダイジェストを更新（1日1回）"
cd "$REPO_DIR"
python3 scripts/build_skill_digest.py

echo "[3/4] 変更をコミット"
git add x_reference/ .claude/skills/
if git diff --staged --quiet; then
  echo "  変更なし。push をスキップします。"
  exit 0
fi
git commit -m "Sync x_reference: $(date +'%Y-%m-%d')"

echo "[4/4] push（失敗時は指数バックオフで最大4回リトライ）"
n=0
until git push origin "$BRANCH"; do
  n=$((n+1))
  if [ "$n" -ge 4 ]; then
    echo "ERROR: push に4回失敗しました。" >&2
    exit 1
  fi
  sleep $((2 ** n))
done
echo "完了。"
