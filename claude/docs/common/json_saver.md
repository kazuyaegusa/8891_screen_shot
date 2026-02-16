# json_saver.py ドキュメント

対応ソース: `claude/src/common/json_saver.py`

## 概要

スクリーンショットキャプチャ結果を包括的なJSONファイルとして保存する疎結合ユーティリティモジュール。
`window_screenshot.py`から呼び出されるが、単体でも利用可能。

## 関数

### `build_capture_payload(capture_result, monitors, all_windows, browser_info, user_action, session) -> Dict`

キャプチャ結果を包括的なJSONペイロードに構築する。

| 項目 | 内容 |
|------|------|
| **入力** | `capture_result`: WindowScreenshot.capture_window_at_cursor()の戻り値 |
| | `monitors`: mss.monitorsの全モニター情報リスト |
| | `all_windows`: detector.get_all_windows()の戻り値 |
| | `browser_info`: inspector.get_browser_info()の戻り値（オプション） |
| | `user_action`: ユーザー操作情報（click/text_input/shortcut/timer等） |
| | `session`: セッション情報 {"session_id": str, "sequence": int} |
| **出力** | 包括的キャプチャ情報Dict |

出力JSON構造:

```json
{
  "capture_id": "uuid",
  "timestamp": "ISO8601",
  "session": {
    "session_id": "uuid",
    "sequence": 42
  },
  "user_action": {
    "type": "click",
    "button": "left",
    "x": 500.0,
    "y": 300.0,
    "modifiers": [],
    "timestamp": 1234567890.123
  },
  "detection_mode": "element/window",
  "mouse": { "x": 100, "y": 200 },
  "target": {
    "detection_type": "element/window",
    "x": 100, "y": 200, "width": 80, "height": 30,
    "name": "検索", "role": "AXTextField", "title": "検索",
    "description": null, "identifier": "search-field",
    "value": "入力テキスト全文",
    "placeholder": "検索...",
    "focused": true, "enabled": true,
    "role_description": "テキストフィールド"
  },
  "app": {
    "name": "Safari", "bundle_id": "com.apple.Safari", "pid": 1234
  },
  "browser": {
    "is_browser": true,
    "url": "https://example.com",
    "page_title": "Example Page"
  },
  "window": {
    "window_id": 5678, "name": "Example Page",
    "owner": "Safari",
    "x": 0, "y": 25, "width": 1920, "height": 1055
  },
  "all_windows": [
    { "window_id": 5678, "name": "Example Page", "owner": "Safari",
      "owner_pid": 1234, "x": 0, "y": 25, "width": 1920, "height": 1055 }
  ],
  "monitors": [
    { "index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080 },
    { "index": 2, "left": 1920, "top": 0, "width": 1920, "height": 1080 }
  ],
  "screenshots": {
    "full": "/path/to/full_screenshot.png",
    "cropped": "/path/to/cropped_screenshot.png"
  }
}
```

### `save_capture_json(payload, output_path) -> str`

ペイロードをJSONファイルに保存する。

| 項目 | 内容 |
|------|------|
| **入力** | `payload`: build_capture_payload()の戻り値, `output_path`: 保存先パス |
| **出力** | 保存したJSONファイルの絶対パス (str) |

- 親ディレクトリが存在しない場合は自動作成
- エンコーディング: UTF-8, ensure_ascii=False（日本語そのまま保存）
- インデント: 2スペース

## 依存ライブラリ

- Python標準ライブラリのみ (json, uuid, datetime, pathlib)
