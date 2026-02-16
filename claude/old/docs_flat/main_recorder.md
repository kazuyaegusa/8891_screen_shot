# main_recorder.py ドキュメント

対応ソース: `claude/src/main_recorder.py`

## 概要

マウス移動追跡 + スクリーンショット撮影 + アプリ情報取得を統合し、画面操作の完全な記録を残すメインスクリプト。

## 使用方法

```bash
# デフォルト: 300枚、1秒間隔
python3 claude/src/main_recorder.py

# カスタム設定
python3 claude/src/main_recorder.py --count 100 --interval 0.5

# マウス移動記録の間隔を変更
python3 claude/src/main_recorder.py --move-interval 0.1

# 出力先を指定
python3 claude/src/main_recorder.py --output ./my_session
```

## コマンドライン引数

| 引数 | 型 | デフォルト | 説明 |
|------|------|-----------|------|
| `--count` | int | 300 | スクリーンショット撮影枚数 |
| `--interval` | float | 1.0 | スクリーンショット撮影間隔(秒) |
| `--move-interval` | float | 0.05 | マウス移動記録間隔(秒) |
| `--output` | str | auto | 出力先ディレクトリ |

## 出力ファイル構成

```
output_YYYYMMDD_HHMMSS/
├── session.json          # メインセッションデータ
├── screenshots/          # スクリーンショット画像
│   ├── shot_0000.png
│   ├── shot_0001.png
│   └── ...
└── mouse_trail.json      # マウス移動ログ(詳細)
```

## session.json の構造

```json
{
  "session_id": "a1b2c3d4",
  "created_at": "2026-02-14T10:30:00",
  "config": {
    "screenshot_count": 300,
    "screenshot_interval": 1.0,
    "move_interval": 0.05
  },
  "summary": {
    "total_screenshots": 300,
    "total_mouse_moves": 5000,
    "total_clicks": 25,
    "duration_seconds": 300.5
  },
  "screenshots": [
    {
      "index": 0,
      "filepath": "screenshots/shot_0000.png",
      "timestamp": "2026-02-14T10:30:00.123",
      "elapsed": 0.456,
      "extra": {
        "mouse_position": {"x": 500, "y": 300},
        "app": {"name": "Safari", "bundle_id": "com.apple.Safari"},
        "element": {
          "role": "AXButton",
          "title": "Downloads",
          "identifier": "downloads-button",
          "frame": {"x": 480, "y": 290, "width": 40, "height": 20}
        }
      }
    }
  ],
  "clicks": [
    {
      "x": 500, "y": 300,
      "timestamp": "...", "elapsed": 5.0, "button": "left",
      "app": {"name": "Safari", ...},
      "element": {"role": "AXButton", ...}
    }
  ]
}
```

## mouse_trail.json の構造

```json
{
  "session_id": "a1b2c3d4",
  "move_log": [
    {"x": 100, "y": 200, "timestamp": "...", "elapsed": 0.05},
    {"x": 102, "y": 201, "timestamp": "...", "elapsed": 0.10}
  ],
  "click_log": [
    {"x": 500, "y": 300, "timestamp": "...", "elapsed": 5.0, "button": "left"}
  ],
  "stats": {
    "total_moves": 5000,
    "total_clicks": 25,
    "duration": 300.5
  }
}
```

## クラス: MainRecorder

### コンストラクタ

```python
recorder = MainRecorder(
    output_base=None,           # 出力先 (None=自動生成)
    screenshot_count=300,       # 撮影枚数
    screenshot_interval=1.0,    # 撮影間隔(秒)
    move_interval=0.05,         # マウス移動記録間隔(秒)
)
```

### メソッド

#### `run()`

記録を開始する。Ctrl+Cで途中停止しても記録済みデータは保存される。

- **入力**: なし
- **出力**: `session.json` と `mouse_trail.json` をファイル出力

## 処理フロー

1. `MouseTracker` をバックグラウンドスレッドで起動
2. `ScreenshotRecorder.take_batch()` で連続撮影開始
3. 各撮影時に `AppInspector.get_full_info()` でアプリ・UI要素情報を取得
4. クリック発生時も `AppInspector` でアプリ情報を記録
5. 完了後(またはCtrl+C時)にJSON保存

## 必要な権限

- アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ
- 画面収録: システム設定 > プライバシーとセキュリティ > 画面収録
