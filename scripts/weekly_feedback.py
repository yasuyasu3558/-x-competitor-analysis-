#!/usr/bin/env python3
"""
Weekly X Competitor Feedback - Free Version
GitHub Actions上で毎週月曜7:00 JSTに実行される。
直近1週間分の日次レポートを集約 → Gemini APIで週次トレンドを総括 → メール(SMTP)で配信。

日次システム(fetch_and_analyze.py)が生成した reports/YYYY-MM-DD.md を入力に使う。
日次レポートが1件も無い場合は、フォールバックとして1週間分の競合RSSを直接取得する。
"""

import json
import os
import re
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

import google.generativeai as genai

# 日次スクリプトの取得ロジックを再利用(フォールバック用)
from fetch_and_analyze import fetch_rss_with_fallback

# プロジェクトルート
ROOT = Path(__file__).parent.parent

# JST タイムゾーン
JST = timezone(timedelta(hours=9))

# 週次の遡及日数
LOOKBACK_DAYS = 7


def load_config() -> dict:
    """設定ファイルを読み込み"""
    with open(ROOT / "config" / "competitors.json", encoding="utf-8") as f:
        return json.load(f)


def collect_daily_reports(lookback_days: int = LOOKBACK_DAYS) -> list[dict]:
    """
    直近 lookback_days 日分の日次レポート(reports/YYYY-MM-DD.md)を新しい順→古い順で集める。
    ファイル名の日付で対象期間を判定する。
    """
    report_dir = ROOT / "reports"
    if not report_dir.exists():
        return []

    today = datetime.now(JST).date()
    cutoff = today - timedelta(days=lookback_days)

    collected = []
    for path in report_dir.glob("*.md"):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", path.stem)
        if not m:
            continue
        try:
            file_date = datetime(int(m[1]), int(m[2]), int(m[3])).date()
        except ValueError:
            continue
        if cutoff <= file_date <= today:
            collected.append({"date": file_date, "text": path.read_text(encoding="utf-8")})

    # 日付昇順(古い→新しい)で返す
    collected.sort(key=lambda r: r["date"])
    return collected


def build_input_from_reports(reports: list[dict]) -> str:
    """日次レポート群を1本のテキストに連結"""
    chunks = []
    for r in reports:
        chunks.append(f"\n\n===== {r['date'].isoformat()} の日次レポート =====\n\n{r['text']}")
    return "".join(chunks).strip()


def build_input_from_rss(config: dict) -> str:
    """
    フォールバック: 日次レポートが無い場合に1週間分の競合RSSを直接取得し、JSON文字列で返す。
    """
    settings = config["settings"]
    result = []
    for competitor in config["competitors"]:
        print(f"  [fallback] Fetching {competitor['id']}...")
        posts = fetch_rss_with_fallback(
            competitor["rss_endpoints"],
            LOOKBACK_DAYS * 24,  # 1週間分
            settings["max_posts_per_account"] * 7,
        )
        result.append({
            "account": competitor["id"],
            "label": competitor["label"],
            "position": competitor["position"],
            "posts": posts,
        })
    return json.dumps(
        {"posts_data": result, "generated_at": datetime.now(JST).isoformat()},
        ensure_ascii=False,
        indent=2,
    )


def period_label() -> str:
    """対象期間の表示用ラベル(例: 2026年06月09日〜06月15日)"""
    today = datetime.now(JST).date()
    start = today - timedelta(days=LOOKBACK_DAYS - 1)
    return f"{start.strftime('%Y年%m月%d日')}〜{today.strftime('%m月%d日')}"


def analyze_with_gemini(weekly_data: str, source_kind: str) -> str:
    """Gemini APIで週次総括レポートを生成"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY が設定されていません")

    genai.configure(api_key=api_key)

    system_prompt = (ROOT / "prompts" / "weekly_system_prompt.txt").read_text(encoding="utf-8")
    user_prompt_template = (ROOT / "prompts" / "weekly_user_prompt_template.txt").read_text(encoding="utf-8")

    period_jp = period_label()
    user_prompt = (
        user_prompt_template
        .replace("{WEEKLY_DATA}", weekly_data)
        .replace("{PERIOD_JP}", period_jp)
        .replace("{SOURCE_KIND}", source_kind)
    )
    system_prompt = system_prompt.replace("{PERIOD_JP}", period_jp)

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system_prompt,
    )

    print("Calling Gemini API (weekly)...")
    response = model.generate_content(
        user_prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 4000,
        },
    )
    return response.text


def save_report(markdown: str) -> Path:
    """週次レポートをファイルに保存"""
    today = datetime.now(JST).strftime("%Y-%m-%d")
    report_dir = ROOT / "weekly_reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"{today}.md"
    report_path.write_text(markdown, encoding="utf-8")
    print(f"Weekly report saved: {report_path}")
    return report_path


def markdown_to_basic_html(markdown: str) -> str:
    """
    依存ライブラリを増やさないための簡易Markdown→HTML変換。
    見出し・箇条書き・段落のみ対応(週次レポートはこの範囲で十分)。
    """
    html_lines = ["<div style=\"font-family:-apple-system,Segoe UI,Roboto,Hiragino Sans,sans-serif;"
                  "line-height:1.7;color:#1a1a1a;max-width:680px;margin:0 auto;\">"]
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close_list()
            continue
        if line.startswith("# "):
            close_list()
            html_lines.append(f"<h1 style=\"font-size:20px;border-bottom:2px solid #eee;padding-bottom:6px;\">{line[2:].strip()}</h1>")
        elif line.startswith("## "):
            close_list()
            html_lines.append(f"<h2 style=\"font-size:17px;margin-top:22px;\">{line[3:].strip()}</h2>")
        elif line.startswith("### "):
            close_list()
            html_lines.append(f"<h3 style=\"font-size:15px;\">{line[4:].strip()}</h3>")
        elif line.lstrip().startswith(("- ", "* ")):
            if not in_list:
                html_lines.append("<ul style=\"padding-left:20px;\">")
                in_list = True
            html_lines.append(f"<li>{line.lstrip()[2:].strip()}</li>")
        else:
            close_list()
            html_lines.append(f"<p>{line.strip()}</p>")

    close_list()
    html_lines.append("</div>")
    return "\n".join(html_lines)


def send_email(markdown: str) -> bool:
    """SMTP経由でメール配信(Gmailを想定。stdlibのみで実装)"""
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    mail_to = os.environ.get("MAIL_TO")
    mail_from = os.environ.get("MAIL_FROM", user)
    from_name = os.environ.get("MAIL_FROM_NAME", "X競合分析Bot")

    if not user or not password or not mail_to:
        print("SMTP credentials (SMTP_USER / SMTP_PASS / MAIL_TO) not set, skipping email")
        return False

    period_jp = period_label()
    subject = f"📊 競合X週次トレンド総括（{period_jp}）"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, mail_from))
    msg["To"] = mail_to

    # プレーンテキスト(Markdownそのまま) + HTML の2パート
    msg.attach(MIMEText(markdown, "plain", "utf-8"))
    msg.attach(MIMEText(markdown_to_basic_html(markdown), "html", "utf-8"))

    # 複数宛先(カンマ区切り)対応
    recipients = [addr.strip() for addr in mail_to.split(",") if addr.strip()]

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.starttls()
        with server:
            server.login(user, password)
            server.sendmail(mail_from, recipients, msg.as_string())
        print(f"Email sent successfully to {mail_to}")
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def main():
    print("=" * 50)
    print(f"Weekly X Competitor Feedback - {datetime.now(JST)}")
    print("=" * 50)

    config = load_config()

    # 1. 直近1週間の日次レポートを集約
    print("\n[1/3] Collecting daily reports...")
    reports = collect_daily_reports()
    if reports:
        print(f"  {len(reports)} daily reports found ({reports[0]['date']} 〜 {reports[-1]['date']})")
        weekly_data = build_input_from_reports(reports)
        source_kind = "(A) 日次レポートの連結"
    else:
        print("  No daily reports found. Falling back to weekly RSS fetch...")
        weekly_data = build_input_from_rss(config)
        source_kind = "(B) 1週間分の競合RSS(フォールバック)"

    # 2. Gemini で週次総括
    print("\n[2/3] Calling Gemini API...")
    markdown_report = analyze_with_gemini(weekly_data, source_kind)
    save_report(markdown_report)

    # 3. メール配信
    print("\n[3/3] Sending email...")
    if not send_email(markdown_report):
        print("WARNING: Email delivery did not succeed")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("Done.")
    print("=" * 50)


if __name__ == "__main__":
    main()
