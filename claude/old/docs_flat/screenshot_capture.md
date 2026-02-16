# screenshot_capture.py - スクリーンショット撮影モジュール

## 概要
macOSの`screencapture`コマンドをsubprocessで呼び出し、画面全体のスクリーンショットを撮影する。

## 関数

### `capture_screenshot(output_dir: Path, fmt: str = "png") -> Path`
スクリーンショットを撮影し、指定ディレクトリに保存する。

**インプット:**
| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `output_dir` | `Path` | - | 画像の保存先ディレクトリ |
| `fmt` | `str` | `"png"` | 画像フォーマット（png, jpg, tiff等） |

**アウトプット:** `Path` - 保存されたファイルのパス

**ファイル名形式:** `screenshot_YYYYMMDD_HHMMSS_ffffff.{fmt}`

**例外:**
- `RuntimeError`: screencaptureコマンドの実行失敗、またはファイルが作成されなかった場合

**備考:**
- `-x`オプションでシャッター音を無効化
- `timeout=10`秒のタイムアウト設定
