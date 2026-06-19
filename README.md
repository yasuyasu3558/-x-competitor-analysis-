# X競合分析 完全自動化システム（無料版）

副業ジャンルのX競合4アカウントを毎朝7:00 JSTに自動分析し、Telegramに配信。**月額¥0**。
さらに、**ローカルの「Xについて」フォルダを `x_reference/` に1日1回自動同期**し、その過去データを
**(1)毎朝の自動分析** と **(2)Claude Code スキル `x-post-writer`** の両方で参照して、
ネタの重複回避・文体の再現・過去投稿の再活用提案を行います。

---

## このパッケージの中身

```
competitor-x-analysis-free/
├── README.md                          ← このファイル
├── requirements.txt                   ← Python依存パッケージ
├── .gitignore                         ← Git管理から除外する設定
├── .claude/
│   └── skills/
│       └── x-post-writer/
│           ├── SKILL.md               ← ★X投稿作成スキル(手動で投稿を練る用)
│           └── reference_digest.md    ←   参考データのダイジェスト(1日1回自動更新)
├── .github/
│   └── workflows/
│       └── daily-analysis.yml         ← GitHub Actions定義(毎朝7時実行)
├── scripts/
│   ├── fetch_and_analyze.py           ← メインスクリプト(RSS+参考データ→Gemini→配信)
│   ├── reference.py                   ← x_reference/ 読み込み共通ローダー
│   ├── build_skill_digest.py          ← スキル用ダイジェスト生成(1日1回)
│   ├── local_daily_push.sh            ← ★ローカル→リポジトリ 1日1回自動push(mac/Linux)
│   └── local_daily_push.bat           ← ★同上(Windows)
├── prompts/
│   ├── system_prompt.txt              ← Geminiのシステムプロンプト
│   └── user_prompt_template.txt       ← ユーザープロンプト雛形
├── config/
│   └── competitors.json               ← 4アカウントの設定＋参考データ上限
├── x_reference/                       ← ★「Xについて」フォルダの同期先(過去データ)
│   └── README.md                      ←   入れ方の説明＋サンプル
└── reports/                           ← 毎日の分析結果が自動で蓄積
```

---

## ★ ローカルの「Xについて」フォルダを過去データとして自動連携する方法

ローカルPCの **「Xについて」フォルダ** の中身を、1日1回リポジトリの `x_reference/` に
自動 push します。同期後は次の2つが自動でその過去データを参照します。

- **毎朝の自動分析**：過去ネタと重複しない投稿案を生成（重複回避）／再活用提案
- **Claude Code スキル `x-post-writer`**：手動でX投稿を練るとき、過去データを踏まえて案出し

> ⚠️ クラウド（GitHub Actions / Claude Code on the web）は **あなたのローカルPCの
> 「Xについて」フォルダに直接アクセスできません。** そのため「ローカル → リポジトリへ push」
> が唯一の連携経路です。下記の自動 push を1日1回走らせて橋渡しします。

### セットアップ手順（1日1回 自動push）

1. このリポジトリをローカルにクローンする
   ```bash
   git clone <このリポジトリのURL>
   ```
2. 自動pushスクリプトの先頭2つのパスを自分の環境に合わせて書き換える
   - `scripts/local_daily_push.sh`（mac/Linux）または `scripts/local_daily_push.bat`（Windows）
   - `SRC_DIR` … ローカルの「Xについて」フォルダ
   - `REPO_DIR` … クローンしたこのリポジトリの場所
3. 1日1回スケジュール実行する

   **mac/Linux（cron, 毎日6:50に実行する例）**
   ```bash
   chmod +x scripts/local_daily_push.sh
   crontab -e
   # 次の1行を追加（パスは自分の環境に合わせる）
   50 6 * * * /bin/bash ~/-x-competitor-analysis-/scripts/local_daily_push.sh >> ~/x_push.log 2>&1
   ```

   **Windows（タスクスケジューラ）**
   - 「タスクの作成」→ トリガー：毎日 6:50 → 操作：プログラムの開始に
     `scripts\local_daily_push.bat` のフルパスを指定。

これで毎日「Xについて」フォルダの最新状態がリポジトリに同期され、
スキル用ダイジェスト（`.claude/skills/x-post-writer/reference_digest.md`）も**1日1回だけ**更新されます。

### スキルの使い方（手動でX投稿を練る）
Claude Code で「今日のX投稿を作って」「ツイート案を出して」等と頼むと、スキル
`x-post-writer` が `reference_digest.md`（＝Xについての過去データ）を読み込み、
重複を避けつつ本人の文体で投稿案＋一押し＋再活用案を出します。

> 同期は不要だがダイジェストだけ今すぐ作り直したいときは：
> `python scripts/build_skill_digest.py --force`

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
| 参考データの読み込み上限 | `config/competitors.json`(`max_reference_items` / `max_reference_chars`) |
| 過去データの置き場 | `x_reference/`（ローカル「Xについて」の同期先） |
| ローカル自動pushの設定 | `scripts/local_daily_push.sh` / `.bat`（先頭のパス） |
| スキルの挙動 | `.claude/skills/x-post-writer/SKILL.md` |
| プロンプト内容 | `prompts/system_prompt.txt` |
| 配信先 | GitHub Secretsの設定で切替 |

---

## 法的・倫理的な注意

- RSSHubは各国の規約遵守でグレーゾーン。商用利用やスクレイピング過多は避ける
- 競合アカウントの投稿を**そのまま転載**することは絶対NG。「構造を借りて自分の体験で書き直す」が原則

---

## ライセンス

個人利用・商用利用ともに自由。改変も自由。
