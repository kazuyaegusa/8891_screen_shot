# screenshot_recorder.py ドキュメント

対応ソース: `claude/src/screenshot_recorder.py`

## 概要

macOS標準の`screencapture`コマンドを使い、指定回数のスクリーンショットを一定間隔で撮影するモジュール。

## クラス: ScreenshotRecorder

### コンストラクタ

```python
recorder = ScreenshotRecorder(
    output_dir="output/screenshots",  # 保存先
    total_count=300,                   # 撮影枚数
    interval=1.0,                      # 撮影間隔(秒)
)
```

### メソッド

#### `take_one(name: str) -> Optional[str]`

1枚スクリーンショットを撮影する。

- **入力**: `name` - ファイル名(拡張子なし)
- **出力**: 保存先ファイルパス。失敗時は`None`

#### `take_batch(on_capture, on_progress) -> List[Dict]`

バッチでスクリーンショットを撮影する。

- **入力**:
  - `on_capture(index, filepath) -> Dict` - 撮影ごとのコールバック(Optional)
  - `on_progress(current, total)` - 進捗コールバック(Optional)
- **出力**:
  ```python
  [
      {
          "index": 0,
          "filepath": "output/screenshots/shot_0000.png",
          "timestamp": "2026-02-14T10:30:00.123",
          "elapsed": 0.456,
          "extra": {  # on_captureの戻り値
              "mouse_position": {"x": 100, "y": 200},
              "app": {"name": "Safari", ...},
              "element": {"role": "AXButton", ...}
          }
      },
      ...
  ]
  ```

#### `get_output_dir() -> str`

出力ディレクトリパスを返す。

## 依存

- macOS `screencapture` コマンド (標準搭載)
