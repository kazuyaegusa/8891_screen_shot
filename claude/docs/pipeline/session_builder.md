# session_builder.py ドキュメント

対応ソース: `claude/src/pipeline/session_builder.py`

## 概要

セッションビルダーモジュール。`CaptureRecord` のストリームを受け取り、時間的・アプリ的な連続性に基づいて `Session` に区切る。ストリーミング処理に対応し、レコードを1件ずつ受け取るたびにセッション区切りを判定する。

## クラス

### `SessionBuilder`

#### コンストラクタ

```python
SessionBuilder(gap_seconds: int = 300, max_records: int = 50)
```

| 引数 | 型 | デフォルト | 説明 |
|---|---|---|---|
| `gap_seconds` | `int` | `300` | セッション区切りの時間間隔（秒） |
| `max_records` | `int` | `50` | 1セッションの最大レコード数 |

## メソッド

### `add_record(record: CaptureRecord) -> Optional[Session]`

レコードを追加し、セッション区切りを判定する。

| 項目 | 内容 |
|------|------|
| **入力** | `record`: 追加する `CaptureRecord` |
| **出力** | 区切り発生時は完了した `Session`、未発生時は `None` |

セッション区切り条件（いずれか1つでも該当すれば区切り）:

1. **時間gap**: 前回レコードから `gap_seconds` 以上経過
2. **アプリ変化**: `record.app["name"]` が前回と異なる
3. **最大件数**: バッファ内レコード数が `max_records` に到達

区切り発生時の動作:
- バッファ内の既存レコードで `Session` を生成して返す
- バッファをクリアし、新しいレコードを新バッファの先頭に格納

### `flush() -> Optional[Session]`

バッファに残っているレコードを `Session` にまとめて返す。

| 項目 | 内容 |
|------|------|
| **入力** | なし |
| **出力** | バッファにレコードがあれば `Session`、空なら `None` |

- ストリーム終了時に呼び出して残余レコードを回収する
- 呼び出し後、バッファと内部状態（`_last_app`）はリセットされる

## ヘルパー関数

### `_parse_timestamp(ts: str) -> datetime`（モジュール内部）

タイムスタンプ文字列を `datetime` にパースする。以下のフォーマットを順に試行:

1. `%Y-%m-%dT%H:%M:%S.%f`
2. `%Y-%m-%dT%H:%M:%S`
3. `%Y-%m-%d %H:%M:%S`
4. `datetime.fromisoformat()` にフォールバック

## 使用例

```python
builder = SessionBuilder(gap_seconds=300, max_records=50)
for record in records:
    session = builder.add_record(record)
    if session:
        process(session)
# 残りのバッファをフラッシュ
last = builder.flush()
if last:
    process(last)
```

## 依存ライブラリ

- Python標準ライブラリ (datetime, uuid)
- pipeline.models (`CaptureRecord`, `Session`)
