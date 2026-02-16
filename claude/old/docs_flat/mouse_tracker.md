# mouse_tracker.py ドキュメント

対応ソース: `claude/src/mouse_tracker.py`

## 概要

ポーリング方式(`CGEventCreate`+`CGEventGetLocation`)でマウスの移動・クリックをリアルタイムで追跡するモジュール。コールバック関数でイベントデータを外部に通知する。バックグラウンドスレッドでも確実に動作する。

## クラス: MouseTracker

### コンストラクタ

```python
tracker = MouseTracker(
    on_move=callback_fn,      # マウス移動時コールバック(Optional)
    on_click=callback_fn,     # クリック時コールバック(Optional)
    move_interval=0.05,       # 移動記録間隔(秒)
)
```

### メソッド

#### `start()`

マウス追跡を開始する(ブロッキング)。Ctrl+Cまたは`stop()`で停止。

- **入力**: なし
- **出力**: なし(コールバック経由でデータ通知)

#### `start_background()`

マウス追跡をバックグラウンドスレッド(daemon)で開始する。`stop()`で停止。

- **入力**: なし
- **出力**: なし

#### `stop()`

マウス追跡を停止する。別スレッドから呼び出し可能。

#### `get_move_log() -> List[Dict]`

記録されたマウス移動ログを取得。

- **出力**:
  ```python
  [
      {"x": 100.5, "y": 200.3, "timestamp": "2026-02-14T...", "elapsed": 1.234},
      ...
  ]
  ```

#### `get_click_log() -> List[Dict]`

記録されたクリックログを取得。

- **出力**:
  ```python
  [
      {"x": 300, "y": 400, "timestamp": "...", "elapsed": 5.678, "button": "left"},
      ...
  ]
  ```

#### `get_stats() -> Dict`

記録統計を取得。

- **出力**:
  ```python
  {"total_moves": 1500, "total_clicks": 12, "duration": 300.5}
  ```

### コールバック引数

#### on_move

```python
{"x": float, "y": float, "timestamp": str, "elapsed": float}
```

#### on_click

```python
{"x": float, "y": float, "timestamp": str, "elapsed": float, "button": "left"|"right"}
```

## 依存ライブラリ

- `pyobjc-framework-Quartz`
