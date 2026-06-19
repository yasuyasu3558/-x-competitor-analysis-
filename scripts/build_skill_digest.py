#!/usr/bin/env python3
"""
x_reference/（ローカルの「Xについて」フォルダの同期先）の内容を、
Claude Code スキル `x-post-writer` が参照するダイジェストに変換する。

「1日1回だけ更新」する想定。当日分が既に生成済みなら何もしない。
--force を付けると当日でも強制的に再生成する。
標準ライブラリのみで動作（pip 不要）。
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reference import load_reference_posts

ROOT = Path(__file__).parent.parent
X_REFERENCE_DIR = ROOT / "x_reference"
SKILL_DIR = ROOT / ".claude" / "skills" / "x-post-writer"
DIGEST_PATH = SKILL_DIR / "reference_digest.md"
JST = timezone(timedelta(hours=9))

UPDATED_PREFIX = "最終更新: "


def today_str() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d")


def already_updated_today() -> bool:
    if not DIGEST_PATH.exists():
        return False
    head = DIGEST_PATH.read_text(encoding="utf-8")[:300]
    return f"{UPDATED_PREFIX}{today_str()}" in head


def build_digest(items: list[dict]) -> str:
    lines = [
        "# X参考データ ダイジェスト（スキル x-post-writer 用）",
        "",
        f"{UPDATED_PREFIX}{today_str()}",
        f"件数: {len(items)}",
        "",
        "> このファイルは scripts/build_skill_digest.py が x_reference/ から自動生成します。",
        "> 1日1回のみ更新されます。手動編集しても次回の更新で上書きされます。",
        "",
        "---",
        "",
    ]
    for i, it in enumerate(items, 1):
        meta_parts = [it.get("source", "")]
        if it.get("posted_at"):
            meta_parts.append(it["posted_at"])
        meta = " / ".join(p for p in meta_parts if p)
        lines.append(f"## 参考 {i}（{meta}）")
        lines.append(it["text"])
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    force = "--force" in sys.argv

    if already_updated_today() and not force:
        print(f"スキル用ダイジェストは本日({today_str()})分が更新済みのためスキップ。"
              f"（強制更新は --force）")
        return

    items = load_reference_posts(X_REFERENCE_DIR)
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    DIGEST_PATH.write_text(build_digest(items), encoding="utf-8")
    print(f"スキル用ダイジェストを更新: {DIGEST_PATH} （{len(items)}件）")


if __name__ == "__main__":
    main()
