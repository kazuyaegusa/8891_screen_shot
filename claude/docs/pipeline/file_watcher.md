# file_watcher.py ドキュメント

対応ソース: `claude/src/pipeline/file_watcher.py`

## 概要

ファイル監視モジュール（ポーリング方式）。監視ディレクトリ内の `cap_*.json` ファイルをスキャンし、未処理のファイルを検出して `CaptureRecord` に変換する。処理済みファイルは `_processed.txt` で管理する。

## クラス

### `FileWatcher`

#### コンストラクタ

```python
FileWatcher(watch_dir: Path, poll_interval: float = 10.0)
```

| 引数 | 型 | デフォルト | 説明 |
|---|---|---|---|
| `watch_dir` | `Path` | (必須) | 監視対象ディレクトリ（存在しない場合は自動作成） |
| `poll_interval` | `float` | `10.0` | ポーリング間隔（秒） |

- 初期化時に `watch_dir` を `mkdir(parents=True, exist_ok=True)` で自動作成
- `_processed.txt` から処理済みファイル一覧をメモリにロード

## メソッド

### `scan_new_files() -> List[Path]`

未処理の新規キャプチャファイルを検出する。

| 項目 | 内容 |
|------|------|
| **入力** | なし |
| **出力** | 未処理の `cap_*.json` ファイルパスのリスト（ファイル名順ソート済み） |

- `watch_dir` 内の `cap_*.json` パターンにマッチするファイルをスキャン
- `_processed.txt` に記録済みのファイルは除外

### `mark_processed(path: Path) -> None`

ファイルを処理済みとしてマークする。

| 項目 | 内容 |
|------|------|
| **入力** | `path`: 処理済みにするファイルの `Path` |
| **出力** | `None` |

- メモリ上の処理済みセットにファイル名を追加
- `_processed.txt` にファイル名を追記（永続化）

### `load_record(path: Path) -> CaptureRecord`

JSONファイルを読み込み、`CaptureRecord` に変換する。

| 項目 | 内容 |
|------|------|
| **入力** | `path`: キャプチャJSONファイルの `Path` |
| **出力** | `CaptureRecord` インスタンス |

- JSONのキーが存在しない場合はデフォルト値（空文字列・空Dict）を使用
- `json_path` にはファイルの絶対パス（`resolve()`）を格納

## プロパティ

### `poll_interval -> float`

ポーリング間隔（秒）を返す読み取り専用プロパティ。

## 内部ファイル

| ファイル | 説明 |
|---|---|
| `_processed.txt` | 処理済みファイル名を1行1ファイルで記録。`watch_dir` 直下に生成 |

## 依存ライブラリ

- Python標準ライブラリ (json, logging, pathlib)
- pipeline.models (`CaptureRecord`)
