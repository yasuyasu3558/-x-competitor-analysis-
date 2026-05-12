#!/usr/bin/env python3
"""
Daily X Competitor Analysis - Free Version
GitHub Actions上で毎朝7:00 JSTに実行される。
4アカウントのRSSを取得→Gemini APIで分析→Telegramに配信。
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import google.generativeai as genai
import requests

# プロジェクトルート
ROOT = Path(__file__).parent.parent

# JST タイムゾーン
JST = timezone(timedelta(hours=9))


def load_config() -> dict:
    """設定ファイルを読み込み"""
    with open(ROOT / "config" / "competitors.json", encoding="utf-8") as f:
        return json.load(f)


def fetch_rss_with_fallback(rss_endpoints: list[str], lookback_hours: int, max_posts: int) -> list[dict]:
    """
    複数のRSSエンドポイントを順に試して、最初に成功したものを使う。
    公開RSSHubは不安定なのでフォールバック必須。
    """
    cutoff = datetime.now(JST) - timedelta(hours=lookback_hours)

    for endpoint in rss_endpoints:
        try:
            print(f"  Trying: {endpoint}")
            response = requests.get(endpoint, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (X-Competitor-Analyzer/1.0)"
            })
            if response.status_code != 200:
                print(f"  HTTP {response.status_code}, trying next endpoint")
                continue

            feed = feedparser.parse(response.content)
            if not feed.entries:
                print(f"  Empty feed, trying next endpoint")
                continue

            posts = []
            for entry in feed.entries[:max_posts]:
                # 公開日をパース
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(JST)

                if pub_date and pub_date < cutoff:
                    continue

                # HTMLタグを除去
                text = re.sub(r"<[^>]+>", "", entry.get("summary", entry.get("title", "")))
                text = re.sub(r"\s+", " ", text).strip()[:500]

                posts.append({
                    "text": text,
                    "posted_at": pub_date.isoformat() if pub_date else "unknown",
                    "url": entry.get("link", "")
                })

            print(f"  Success: {len(posts)} posts retrieved")
            return posts

        except Exception as e:
            print(f"  Error: {e}, trying next endpoint")
            continue

    print(f"  All endpoints failed")
    return []


def gather_all_posts(config: dict) -> dict:
    """全競合の投稿を集約"""
    settings = config["settings"]
    result = []

    for competitor in config["competitors"]:
        print(f"Fetching {competitor['id']}...")
        posts = fetch_rss_with_fallback(
            competitor["rss_endpoints"],
            settings["lookback_hours"],
            settings["max_posts_per_account"]
        )
        result.append({
            "account": competitor["id"],
            "label": competitor["label"],
            "position": competitor["position"],
            "posts": posts
        })

    return {
        "posts_data": result,
        "generated_at": datetime.now(JST).isoformat()
    }


def analyze_with_gemini(posts_data: dict, system_prompt: str, user_prompt_template: str) -> str:
    """Gemini APIで分析レポートを生成"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY が設定されていません")

    genai.configure(api_key=api_key)

    # データを整形
    posts_text = json.dumps(posts_data, ensure_ascii=False, indent=2)
    today_jp = datetime.now(JST).strftime("%Y年%m月%d日")

    user_prompt = user_prompt_template \
        .replace("{POSTS_DATA}", posts_text) \
        .replace("{TODAY_JP}", today_jp)

    # gemini-2.5-flash は無料枠が大きい
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system_prompt
    )

    print("Calling Gemini API...")
    response = model.generate_content(
        user_prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 4000,
        }
    )

    return response.text


def save_report(markdown: str) -> Path:
    """レポートをファイルに保存"""
    today = datetime.now(JST).strftime("%Y-%m-%d")
    report_dir = ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"{today}.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Report saved: {report_path}")
    return report_path


def make_short_version(markdown: str, max_chars: int = 1500) -> str:
    """LINE/Telegram用の短縮版を生成"""
    # 「## 🎯」以降を切る
    short = markdown.split("## 🎯")[0]
    # 「## 📝」以降を切る
    short = short.split("## 📝")[0]
    return short[:max_chars]


def extract_one_push(markdown: str) -> str:
    """一押し投稿のセクションを抽出"""
    match = re.search(r"## 🎯[\s\S]*?(?=## 📝|$)", markdown)
    return match.group(0) if match else ""


def send_telegram(short_text: str, one_push: str, repo_url: str) -> bool:
    """Telegramに通知を送る"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram credentials not set, skipping")
        return False

    today = datetime.now(JST).strftime("%m/%d")
    message = f"📊 {today}朝の競合分析\n\n{short_text}\n\n━━━━━━━━━━━━\n\n{one_push}"

    # Telegramは4096文字上限
    message = message[:4000]

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            },
            timeout=20
        )
        if response.status_code == 200:
            print("Telegram message sent successfully")
            return True
        else:
            print(f"Telegram failed: {response.status_code} {response.text}")
            # parse_modeなしで再送
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": message,
                    "disable_web_page_preview": True
                },
                timeout=20
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def send_line(short_text: str, one_push: str) -> bool:
    """LINE Messaging APIに通知を送る（オプショナル）"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        return False

    today = datetime.now(JST).strftime("%m/%d")
    message = f"📊 {today}朝の競合分析\n\n{short_text}\n\n━━━━━━━━━━━━\n\n{one_push}"
    message = message[:4900]  # LINE上限5000

    try:
        response = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "to": user_id,
                "messages": [{"type": "text", "text": message}]
            },
            timeout=20
        )
        success = response.status_code == 200
        print(f"LINE: {'success' if success else 'failed'} ({response.status_code})")
        return success
    except Exception as e:
        print(f"LINE error: {e}")
        return False


def send_discord(short_text: str, one_push: str) -> bool:
    """Discord Webhookに通知（オプショナル）"""
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return False

    today = datetime.now(JST).strftime("%m/%d")
    content = f"**📊 {today}朝の競合分析**\n\n{short_text}\n\n━━━━━━━━━━━━\n\n{one_push}"
    content = content[:1900]  # Discord上限2000

    try:
        response = requests.post(webhook, json={"content": content}, timeout=20)
        success = response.status_code in (200, 204)
        print(f"Discord: {'success' if success else 'failed'}")
        return success
    except Exception as e:
        print(f"Discord error: {e}")
        return False


def main():
    print("=" * 50)
    print(f"Daily X Competitor Analysis - {datetime.now(JST)}")
    print("=" * 50)

    # 1. 設定読み込み
    config = load_config()

    # 2. RSS取得
    print("\n[1/4] Fetching RSS feeds...")
    posts_data = gather_all_posts(config)

    total_posts = sum(len(p["posts"]) for p in posts_data["posts_data"])
    print(f"\nTotal posts retrieved: {total_posts}")

    # 3. プロンプト読み込み
    system_prompt = (ROOT / "prompts" / "system_prompt.txt").read_text(encoding="utf-8")
    user_prompt_template = (ROOT / "prompts" / "user_prompt_template.txt").read_text(encoding="utf-8")

    # 4. Gemini分析
    print("\n[2/4] Calling Gemini API...")
    markdown_report = analyze_with_gemini(posts_data, system_prompt, user_prompt_template)

    # 5. 保存
    print("\n[3/4] Saving report...")
    report_path = save_report(markdown_report)

    # 6. 配信
    print("\n[4/4] Sending notifications...")
    short = make_short_version(markdown_report)
    one_push = extract_one_push(markdown_report)
    repo_url = os.environ.get("GITHUB_SERVER_URL", "") + "/" + os.environ.get("GITHUB_REPOSITORY", "")

    delivered = False
    if send_telegram(short, one_push, repo_url):
        delivered = True
    if send_line(short, one_push):
        delivered = True
    if send_discord(short, one_push):
        delivered = True

    if not delivered:
        print("WARNING: No delivery channel succeeded")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("Done.")
    print("=" * 50)


if __name__ == "__main__":
    main()
