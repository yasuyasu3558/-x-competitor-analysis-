@echo off
REM ===========================================================================
REM  ローカルの「Xについて」フォルダの中身を、このリポジトリの x_reference\ に
REM  同期し、スキル用ダイジェストを更新して、1日1回 git push する（Windows用）。
REM
REM  使い方:
REM   1. 下の SRC_DIR / REPO_DIR を自分の環境に合わせて書き換える
REM   2. タスクスケジューラで1日1回このバッチを実行（手順は README.md 参照）
REM ===========================================================================

setlocal

REM ===== 環境に合わせて書き換える =====
set "SRC_DIR=%USERPROFILE%\Xについて"
set "REPO_DIR=%USERPROFILE%\-x-competitor-analysis-"
set "BRANCH=main"
REM ====================================

set "DEST_DIR=%REPO_DIR%\x_reference"

echo [1/4] 同期: %SRC_DIR% -^> %DEST_DIR%
if not exist "%SRC_DIR%" (
  echo ERROR: 「Xについて」フォルダが見つかりません: %SRC_DIR%
  exit /b 1
)
if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"

REM README.md を残し、それ以外をミラー同期（/XF で README.md を除外）
robocopy "%SRC_DIR%" "%DEST_DIR%" /MIR /XF README.md >nul
REM robocopy は成功でも 0〜7 を返すため、8 以上のみエラー扱い
if %ERRORLEVEL% GEQ 8 (
  echo ERROR: robocopy に失敗しました（code %ERRORLEVEL%）
  exit /b 1
)

echo [2/4] スキル用ダイジェストを更新（1日1回）
cd /d "%REPO_DIR%"
python scripts\build_skill_digest.py
if errorlevel 1 exit /b 1

echo [3/4] 変更をコミット
git add x_reference/ .claude/skills/
git diff --staged --quiet
if %ERRORLEVEL%==0 (
  echo   変更なし。push をスキップします。
  exit /b 0
)
for /f "tokens=2 delims==" %%d in ('wmic os get localdatetime /value') do set "DT=%%d"
git commit -m "Sync x_reference: %DT:~0,4%-%DT:~4,2%-%DT:~6,2%"

echo [4/4] push
git push origin %BRANCH%
if errorlevel 1 (
  echo ERROR: push に失敗しました。
  exit /b 1
)
echo 完了。
endlocal
