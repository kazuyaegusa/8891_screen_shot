# cleanup_manager.py ドキュメント

対応ソース: `claude/src/pipeline/cleanup_manager.py`

## 概要

セッション処理済みファイルおよび古いファイルを安全に削除するクリーンアップモジュール。
処理済みセッションの JSON・PNG ファイルを削除し、滞留ファイルの定期クリーンアップも行う。

## クラス

### `CleanupManager`

#### コンストラクタ

```python
CleanupManager(watch_dir: Path)
```

| 項目 | 内容 |
|------|------|
| **入力** | `watch_dir`: 監視対象ディレクトリ（キャプチャデータの保存先） |

#### `cleanup_session(session: Session) -> None`

セッション内の全レコードに紐づくファイルを削除する。

| 項目 | 内容 |
|------|------|
| **入力** | `session`: Session オブジェクト |
| **出力** | なし |

削除対象（レコードごと）:
- `record.json_path` — キャプチャ JSON ファイル
- `record.screenshots["full"]` — フルスクリーンショット PNG
- `record.screenshots["cropped"]` — クロップスクリーンショット PNG

#### `cleanup_old_files(retention_sec: int = 3600) -> List[str]`

watch_dir 内の古いキャプチャファイルを安全に削除する。

| 項目 | 内容 |
|------|------|
| **入力** | `retention_sec`: 保持期間（秒）。デフォルト 3600（1時間） |
| **出力** | 削除されたファイル名のリスト |

対象パターン:
- `cap_*.json`
- `full_*.png`
- `crop_*.png`

- 更新日時が `retention_sec` 以上前のファイルのみ削除
- watch_dir が存在しない場合は空リストを返す

### 内部メソッド

#### `_safe_delete(path: Path) -> None`

ファイルを安全に削除する。ファイルが存在しない場合は何もしない。削除失敗時は警告ログを出力する。

## 依存ライブラリ

- Python標準ライブラリ (pathlib, time, logging)
- pipeline.models (Session)
