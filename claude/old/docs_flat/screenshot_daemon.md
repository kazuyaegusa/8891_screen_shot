# screenshot_daemon.py - メインデーモン

## 概要
3秒間隔でスクリーンショットを撮影→OpenAI Vision APIで解析→JSONL保存→クリーンアップを行うオーケストレーター。

## 関数

### `run_daemon()`
デーモンのメインループを開始する。

**インプット:** なし（設定は`config.py`の`get_config()`から取得）

**アウトプット:** なし（SIGTERM/SIGINTで停止するまで無限ループ）

**動作フロー:**
1. 設定読み込み・バリデーション
2. ディレクトリ作成
3. ログ設定（ファイル＋stdout）
4. シグナルハンドラ登録
5. メインループ開始:
   - スクリーンショット撮影（`capture_screenshot`）
   - Vision API解析（`ImageAnalyzer.analyze`） ※失敗しても継続
   - JSONL追記（`append_analysis`）
   - 10サイクルごとにクリーンアップ（`cleanup_old_screenshots`）
   - 自己調整間隔で`time.sleep`

---

### `setup_logging(log_file: Path)`
ロギングの設定。

**インプット:**
| パラメータ | 型 | 説明 |
|-----------|------|------|
| `log_file` | `Path` | ログファイルパス |

**アウトプット:** なし

## シグナル処理

| シグナル | 動作 |
|---------|------|
| `SIGTERM` | graceful shutdown（現在のサイクル完了後停止） |
| `SIGINT` | graceful shutdown（Ctrl+C） |

## ログ出力先
- ファイル: `claude/98_tmp/daemon.log`
- 標準出力: コンソール
