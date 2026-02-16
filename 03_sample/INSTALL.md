# Homerow Auto - Installation Guide

macOS GUI自動化ツール。Accessibility APIを使って、座標ではなくUI要素の識別子ベースで操作を記録・再生します。

## 動作環境

- macOS 12以降
- Python 3.9+
- アクセシビリティ権限

## セットアップ

### 1. 展開

```bash
unzip homerow-auto-skills.zip -d ~/homerow-auto
cd ~/homerow-auto
```

### 2. Python依存パッケージのインストール

```bash
pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz pyobjc-framework-ApplicationServices
```

### 3. macOS権限の設定

以下の権限を付与してください（システム設定 > プライバシーとセキュリティ）：

- **アクセシビリティ**: Terminal.app（またはお使いのターミナル）
- **入力監視**: Terminal.app（キーボード記録を使う場合）

## 含まれるスキル

| スキル | 説明 |
|--------|------|
| `homerow` | Vimium風のキーボードヒントでUI要素をナビゲート |
| `app-automation` | 任意のmacOSアプリを自動操作 |
| `line-scan` | LINEアプリのチャット抽出・操作 |
| `line-export` | LINEチャットリストから一括エクスポート |
| `discord` | Discordアプリの自動操作 |
| `slack-automation` | Slackアプリの情報取得・自動操作 |

## コアツール

| ファイル | 説明 |
|---------|------|
| `mvp_click_recorder.py` | クリック操作の記録 |
| `mvp_action_player.py` | 記録した操作の再生 |
| `scripts/utils/test_scan.py` | アプリのUI要素診断 |

## クイックスタート

```bash
# 1. 操作を記録（Ctrl+Cで終了）
python3 mvp_click_recorder.py

# 2. 記録を再生（ドライラン）
python3 mvp_action_player.py mvp_output/session_*.json --dry-run

# 3. LINEのチャットを抽出
python3 skills/line-scan/scripts/line_chat_all.py --count 5

# 4. 任意のアプリをスキャン
python3 skills/app-automation/scripts/auto_app.py Safari scan
```

## 詳細ドキュメント

- `docs/SCREEN_ACTION_RECORDER_DESIGN.md` - 設計書
- `docs/SCREEN_ACTION_RECORDER_SUMMARY.md` - 技術サマリー
- 各 `skills/*/SKILL.md` - スキルごとの詳細ドキュメント

## ライセンス

MIT
