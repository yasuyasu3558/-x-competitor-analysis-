# X競合分析 完全自動化システム（無料版）

副業ジャンルのX競合4アカウントを毎朝7:00 JSTに自動分析し、Telegramに配信。**月額¥0**。
さらに、**自分の過去X投稿を `my_posts/` フォルダで管理しておくと、それを「過去記事情報」として毎回AIに渡し、ネタの重複回避・過去投稿の再活用提案ができます。**

---

## このパッケージの中身

```
competitor-x-analysis-free/
├── README.md                          ← このファイル
├── requirements.txt                   ← Python依存パッケージ
├── .gitignore                         ← Git管理から除外する設定
├── .github/
│   └── workflows/
│       └── daily-analysis.yml         ← GitHub Actions定義(毎朝7時実行)
├── scripts/
│   └── fetch_and_analyze.py           ← メインスクリプト(RSS+過去投稿→Gemini→配信)
├── prompts/
│   ├── system_prompt.txt              ← Geminiのシステムプロンプト
│   └── user_prompt_template.txt       ← ユーザープロンプト雛形
├── config/
│   └── competitors.json               ← 4アカウントの設定
├── my_posts/                          ← ★自分の過去X投稿を入れるフォルダ
│   └── README.md                      ←   入れ方の説明＋サンプル
└── reports/                           ← 毎日の分析結果が自動で蓄積
```

---

## ★ 過去のX投稿を「過去記事情報」として自動で取り込む方法

自分の過去投稿を `my_posts/` フォルダに入れて push するだけ。
次回以降の自動実行で、AIが過去投稿を読み込み、

- **重複ネタの回避**：過去に書いたテーマと被らない投稿案を生成
- **過去投稿の再活用**：再投稿・リライト・続編にすると効きそうな過去投稿を提案

を行います。

### 手順
1. ローカルで管理している過去投稿を、`my_posts/` フォルダにコピーする
   （対応形式：`.txt` / `.md` / `.json` / `.csv` — 詳しくは `my_posts/README.md`）
2. `git add my_posts/ && git commit -m "add past posts" && git push`
3. 翌朝の自動実行（または Actions の手動実行）から自動で反映される

> ローカルフォルダを直接クラウドへ自動連携はされません。
> 「ローカル → リポジトリへ push」が、過去投稿をクラウドへ上げる経路になります。
> push を自動化したい場合は、ローカルフォルダを `my_posts/` にして
> `git add/commit/push` を行うタスク（cron / タスクスケジューラ）を組むのが簡単です。

---

## なぜ無料で動くのか

すべて各サービスの無料枠内で完結する設計：

| サービス | 無料枠 | 本システムの使用量 |
|---------|--------|-----------------|
| GitHub Actions | Public repoは無制限 | 月60分 |
| Google Gemini API | 1日250リクエスト | 1日1回 |
| RSSHub公開インスタンス | 無料 | 1日4リクエスト |
| Telegram Bot API | 完全無料・無制限 | 1日1メッセージ |
| GitHubリポジトリ | Public無制限 | MDファイル蓄積 |

**合計：¥0/月**（永続的に）

---

## 起動までの最短ルート

1. **GitHubアカウントとリポジトリ作成**
2. **このパッケージをアップロード**
3. **Gemini APIキー取得**（https://aistudio.google.com/app/apikey）
4. **Telegramボット作成 + Chat ID取得**（@BotFather）
5. **GitHub Secretsに `GEMINI_API_KEY` / `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` を設定**
6. **Actions タブで「Run workflow」テスト実行**
7. **Telegramに通知が届いたら成功**

---

## カスタマイズ早見表

| 変えたいこと | 編集するファイル |
|------------|---------------|
| 配信時刻 | `.github/workflows/daily-analysis.yml`(cron式) |
| 競合アカウント | `config/competitors.json` |
| 過去投稿の読み込み上限 | `config/competitors.json`(`max_my_posts` / `max_my_post_chars`) |
| プロンプト内容 | `prompts/system_prompt.txt` |
| 投稿テンプレ | `prompts/system_prompt.txt` |
| 配信先 | GitHub Secretsの設定で切替 |

---

## 法的・倫理的な注意

- RSSHubは各国の規約遵守でグレーゾーン。商用利用やスクレイピング過多は避ける
- 競合アカウントの投稿を**そのまま転載**することは絶対NG。「構造を借りて自分の体験で書き直す」が原則

---

## ライセンス

個人利用・商用利用ともに自由。改変も自由。
