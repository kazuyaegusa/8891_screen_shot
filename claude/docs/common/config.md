# config.py - 設定管理モジュール

対応ソース: `claude/src/common/config.py`

## 概要

`.env`ファイルからAPIキーを読み込み、システム全体の設定を一元管理する。マウストラッキング設定も管理。

## 関数

### `get_config() -> Config`
設定インスタンスを取得する（シングルトン）。

**インプット:** なし

**アウトプット:** `Config`インスタンス

## Configクラス属性

| 属性 | 型 | デフォルト | 説明 |
|------|------|-----------|------|
| `OPENAI_API_KEY` | str | `""` | OpenAI APIキー（.envから） |
| `OPENAI_MODEL` | str | `"gpt-5"` | 使用するモデル |
| `CAPTURE_INTERVAL` | float | `3.0` | 撮影間隔（秒） |
| `IMAGE_FORMAT` | str | `"png"` | 画像フォーマット |
| `RETENTION_SECONDS` | int | `3600` | 画像保持期間（秒） |
| `MAX_DISK_MB` | int | `500` | ディスク使用量上限（MB） |
| `ENABLE_MOUSE_TRACKING` | bool | `true` | マウストラッキング有効/無効 |
| `MOUSE_POLL_INTERVAL` | float | `0.5` | マウス位置のポーリング間隔（秒） |
| `SCREENSHOT_DIR` | Path | `claude/10_raw/screenshots` | 画像保存先 |
| `ANALYSIS_DIR` | Path | `claude/10_raw/analysis` | 解析結果保存先 |
| `LOG_FILE` | Path | `claude/98_tmp/daemon.log` | ログファイル |

## メソッド

### `Config.ensure_dirs()`
必要なディレクトリを作成する。

### `Config.validate() -> list[str]`
設定のバリデーション。エラーメッセージのリストを返す（空なら正常）。
