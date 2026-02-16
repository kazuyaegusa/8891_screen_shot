# screenshot_daemon.py - メインデーモン

対応ソース: `claude/src/daemon/screenshot_daemon.py`

## 概要

3秒間隔でスクリーンショットを撮影→OpenAI Vision APIで解析→JSONL保存→クリーンアップを行うオーケストレーター。各サイクルでマウス位置と最前面アプリ情報を`context`フィールドとしてJSONLに追加する。

## 関数

### `run_daemon()`
デーモンのメインループを開始する。

**インプット:** なし（設定は`common.config.get_config()`から取得）

**アウトプット:** なし（SIGTERM/SIGINTで停止するまで無限ループ）

**動作フロー:**
1. 設定読み込み・バリデーション
2. ディレクトリ作成
3. ログ設定（ファイル＋stdout）
4. シグナルハンドラ登録
5. マウストラッカー＆アプリインスペクタ初期化（graceful degradation対応）
6. メインループ開始:
   - スクリーンショット撮影（`capture_screenshot`）
   - マウス位置＋最前面アプリ情報を取得（`_get_context`）
   - Vision API解析（`ImageAnalyzer.analyze`） ※失敗しても継続
   - `context`フィールドを解析結果に追加
   - JSONL追記（`append_analysis`）
   - 10サイクルごとにクリーンアップ（`cleanup_old_screenshots`）
   - 自己調整間隔で`time.sleep`
7. shutdown時にマウストラッカーを停止

---

### `setup_logging(log_file: Path)`
ロギングの設定。

**インプット:**
| パラメータ | 型 | 説明 |
|-----------|------|------|
| `log_file` | `Path` | ログファイルパス |

**アウトプット:** なし

## JSONL出力形式

```json
{
  "timestamp": "2026-02-14 15:30:45",
  "filename": "screenshot_20260214_153045_123456.png",
  "description": "画面にはVSCodeが表示されており...",
  "model": "gpt-5",
  "context": {
    "mouse_position": {"x": 512.0, "y": 384.0},
    "frontmost_app": {"name": "VSCode", "bundle_id": "com.microsoft.VSCode"}
  }
}
```

### contextフィールド

| フィールド | 型 | 説明 |
|-----------|------|------|
| `mouse_position` | `{"x": float, "y": float}` | 撮影時のマウス座標 |
| `frontmost_app` | `{"name": str, "bundle_id": str}` | 最前面のアプリ情報 |

**注意:** Quartzが未インストールの場合やマウストラッキングが無効の場合、`context`フィールドは空dictまたは省略される（graceful degradation）。

## シグナル処理

| シグナル | 動作 |
|---------|------|
| `SIGTERM` | graceful shutdown（現在のサイクル完了後停止、マウストラッカー停止） |
| `SIGINT` | graceful shutdown（Ctrl+C） |

## 環境変数（コンテキスト関連）

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `ENABLE_MOUSE_TRACKING` | `true` | マウストラッキングの有効/無効 |
| `MOUSE_POLL_INTERVAL` | `0.5` | マウス位置のポーリング間隔（秒） |

## ログ出力先
- ファイル: `claude/98_tmp/daemon.log`
- 標準出力: コンソール
