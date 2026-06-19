#!/usr/bin/env python3
"""
x_reference/（ローカルの「Xについて」フォルダの同期先）から、
過去のX投稿・参考データを読み込む共通ローダー。標準ライブラリのみで動作する。

fetch_and_analyze.py（毎朝の自動分析）と build_skill_digest.py（スキル用ダイジェスト生成）
の両方から利用される。
"""

import csv
import json
import re
from pathlib import Path


def load_reference_posts(ref_dir: Path, max_items: int = 500, max_chars: int = 800) -> list[dict]:
    """
    参考データフォルダ内のファイルを読み込み、{"text","posted_at","source"} のリストにする。

    対応形式:
      - .txt / .md : 1ファイル1投稿。複数入れる場合は「---」だけの行で区切る
      - .json      : ["本文", ...] / [{"text","posted_at"}] / {"posts": [...]}
      - .csv       : text / tweet / 本文 のいずれかの列を含む（posted_at/date/日付は任意）
    README.md と「.」始まりのファイルは無視。
    """
    if not ref_dir.exists():
        print(f"  参考フォルダが無いためスキップ: {ref_dir}")
        return []

    posts: list[dict] = []
    for path in sorted(ref_dir.glob("**/*")):
        if path.is_dir():
            continue
        if path.name.startswith(".") or path.name.lower() == "readme.md":
            continue

        suffix = path.suffix.lower()
        try:
            if suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                items = data if isinstance(data, list) else data.get("posts", [])
                for it in items:
                    if isinstance(it, dict):
                        text = str(it.get("text", "")).strip()
                        posted_at = str(it.get("posted_at", ""))
                    else:
                        text, posted_at = str(it).strip(), ""
                    if text:
                        posts.append({"text": text[:max_chars], "posted_at": posted_at, "source": path.name})

            elif suffix == ".csv":
                with open(path, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        text = (row.get("text") or row.get("tweet") or row.get("本文") or "").strip()
                        posted_at = (row.get("posted_at") or row.get("date") or row.get("日付") or "")
                        if text:
                            posts.append({"text": text[:max_chars], "posted_at": posted_at, "source": path.name})

            else:  # .txt / .md / その他テキスト
                raw = path.read_text(encoding="utf-8")
                for chunk in re.split(r"\n-{3,}\n", raw):
                    text = chunk.strip()
                    if text:
                        posts.append({"text": text[:max_chars], "posted_at": "", "source": path.name})

        except Exception as e:
            print(f"  Skip {path.name}: {e}")

        if len(posts) >= max_items:
            break

    return posts[:max_items]
