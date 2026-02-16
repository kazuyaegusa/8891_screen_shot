# models.py ドキュメント

対応ソース: `claude/src/pipeline/models.py`

## 概要

パイプライン全体で共有するデータモデル定義。キャプチャ結果・セッション・抽出スキルを表す3つの dataclass を提供する。

## データクラス

### `CaptureRecord`

1回のキャプチャ結果を表すデータクラス。`json_saver.py` が出力するJSONの内容を構造化して保持する。

| フィールド | 型 | 説明 |
|---|---|---|
| `capture_id` | `str` | キャプチャの一意識別子（UUID） |
| `timestamp` | `str` | キャプチャ日時（ISO8601形式） |
| `session` | `Dict` | セッション情報 `{"session_id": str, "sequence": int}` |
| `user_action` | `Dict` | ユーザー操作情報 `{"type": "click"/"text_input"/"shortcut"/"timer", ...}` |
| `target` | `Dict` | 検出されたUI要素/ウィンドウの情報（名前・ロール・座標・サイズ等） |
| `app` | `Dict` | アプリ情報 `{"name": str, "bundle_id": str, "pid": int}` |
| `browser` | `Dict` | ブラウザ情報 `{"is_browser": bool, "url": str, "page_title": str}` |
| `window` | `Dict` | ウィンドウ情報 `{"window_id": int, "name": str, "owner": str, ...}` |
| `screenshots` | `Dict` | スクリーンショットパス `{"full": str, "cropped": str}` |
| `json_path` | `str` | 元のJSONファイルの絶対パス |

### `Session`

同一アプリでの連続操作をグループ化したセッション。`SessionBuilder` によって生成される。

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `session_id` | `str` | (必須) | セッションの一意識別子（UUID） |
| `app_name` | `str` | (必須) | セッション中の主要アプリ名 |
| `records` | `List[CaptureRecord]` | `[]` | セッションに含まれるキャプチャレコードのリスト |
| `start_time` | `str` | `""` | セッション開始時刻（ISO8601形式） |
| `end_time` | `str` | `""` | セッション終了時刻（ISO8601形式） |

### `ExtractedSkill`

AIが抽出したスキル（操作パターン）。セッション分析の結果として生成される。

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `name` | `str` | (必須) | スキル名（例: 「ファイル整理」） |
| `description` | `str` | (必須) | スキルの説明文 |
| `steps` | `List[str]` | `[]` | 操作手順のリスト |
| `app` | `str` | `""` | 対象アプリ名 |
| `triggers` | `List[str]` | `[]` | スキルを発動するトリガーキーワード |
| `confidence` | `float` | `0.0` | AI抽出の信頼度（0.0〜1.0） |

## 依存ライブラリ

- Python標準ライブラリのみ (dataclasses, typing)
