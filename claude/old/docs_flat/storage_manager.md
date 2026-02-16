# storage_manager.py - ストレージ管理モジュール

## 概要
古いスクリーンショットの自動削除、解析結果のJSONL追記、ディスク使用量監視を行う。

## 関数

### `cleanup_old_screenshots(screenshot_dir: Path, retention_seconds: int = 3600) -> list[str]`
指定時間より古いスクリーンショットを削除する。

**インプット:**
| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `screenshot_dir` | `Path` | - | スクリーンショット保存ディレクトリ |
| `retention_seconds` | `int` | `3600` | 保持期間（秒） |

**アウトプット:** `list[str]` - 削除されたファイル名のリスト

---

### `append_analysis(analysis_dir: Path, result: dict) -> Path`
解析結果をJSONLファイルに追記する。日別でファイルを分割。

**インプット:**
| パラメータ | 型 | 説明 |
|-----------|------|------|
| `analysis_dir` | `Path` | 解析結果の保存先ディレクトリ |
| `result` | `dict` | 解析結果の辞書 |

**アウトプット:** `Path` - 書き込み先のJSONLファイルパス

**ファイル名形式:** `analysis_YYYYMMDD.jsonl`

---

### `get_disk_usage_mb(directory: Path) -> float`
ディレクトリ内の全ファイルの合計サイズをMB単位で返す。

**インプット:**
| パラメータ | 型 | 説明 |
|-----------|------|------|
| `directory` | `Path` | 対象ディレクトリ |

**アウトプット:** `float` - 合計サイズ（MB）
