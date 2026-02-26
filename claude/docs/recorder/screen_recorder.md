# screen_recorder.py API仕様

マウスクリック・キーボード操作を全て捕捉しながら画面を録画するプログラム（macOS専用）。

## クラス: ScreenRecorder

### コンストラクタ

```python
ScreenRecorder(fps=15, output_dir="./recordings", scale=1.0, overlay_enabled=True, monitor=1)
```

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| fps | int | 15 | フレームレート |
| output_dir | str | "./recordings" | 出力先ディレクトリ |
| scale | float | 1.0 | スケール倍率（Retina時は0.5推奨） |
| overlay_enabled | bool | True | オーバーレイ描画の有効/無効 |
| monitor | int | 1 | 録画対象モニター番号 |

### メソッド

#### `start()`

録画を開始する。メインスレッドでCGEventTapを実行し、バックグラウンドスレッドでスクリーンキャプチャを行う。

- メインスレッド: CGEventTap + CFRunLoop（マウス/キーボード監視）
- バックグラウンドスレッド: mss + cv2.VideoWriter（画面録画）
- Ctrl+C で停止

**入力**: なし
**出力**: .mp4動画 + .jsonイベントログ

#### `stop()`

録画を停止する。CFRunLoopを停止し、テキストバッファをフラッシュし、イベントログを保存する。

**入力**: なし
**出力**: なし

## CLI

```bash
python3 -m recorder.screen_recorder [OPTIONS]
# または
python3 -m recorder [OPTIONS]
```

| オプション | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| --fps | int | 15 | フレームレート |
| --output | str | ./recordings | 保存先ディレクトリ |
| --scale | float | 1.0 | スケール倍率 |
| --no-overlay | flag | - | オーバーレイ描画を無効化 |
| --monitor | int | 1 | 録画対象モニター番号 |

## 出力ファイル

### 動画ファイル (.mp4)

- コーデック: mp4v (MPEG-4)
- 解像度: モニター解像度 × scale
- フレームレート: --fps で指定

### イベントログ (.json)

```json
{
  "recording_id": "uuid",
  "started_at": "ISO8601",
  "ended_at": "ISO8601",
  "duration_sec": 123.45,
  "video_path": "rec_20260220_120000.mp4",
  "fps": 15,
  "scale": 1.0,
  "total_events": 42,
  "events": [
    {
      "type": "click",
      "button": "left",
      "x": 500.0,
      "y": 300.0,
      "modifiers": ["Cmd"],
      "timestamp": 1234567890.123,
      "relative_time": 5.678
    },
    {
      "type": "shortcut",
      "key": "c",
      "keycode": 8,
      "modifiers": ["Cmd"],
      "timestamp": 1234567890.456,
      "relative_time": 6.012
    },
    {
      "type": "key",
      "key": "a",
      "keycode": 0,
      "modifiers": [],
      "timestamp": 1234567890.789,
      "relative_time": 6.345
    }
  ]
}
```

### イベント type 一覧

| type | 説明 | 主要フィールド |
|------|------|--------------|
| click | マウスクリック | button, x, y, modifiers |
| shortcut | 修飾キー+キー（Cmd+C等） | key, keycode, modifiers |
| key | 通常キー入力/特殊キー | key, keycode, modifiers |

## スレッドモデル

```
メインスレッド (CFRunLoop)
├── CGEventTap → クリック/キーボード監視
│   ├── InputOverlay.add_click() (スレッドセーフ)
│   ├── InputOverlay.add_key() (スレッドセーフ)
│   └── event_log に記録 (スレッドセーフ)
└── CFRunLoopRun() でブロック

キャプチャスレッド (daemon)
├── mss.grab() → スクリーンキャプチャ
├── InputOverlay.draw() → オーバーレイ描画
├── cv2.VideoWriter.write() → 動画書き込み
└── FPS制御 (sleep)
```

## 必要な権限

| 権限 | 用途 | 設定場所 |
|------|------|---------|
| 画面収録 | スクリーンキャプチャ | システム設定 > プライバシーとセキュリティ > 画面収録 |
| アクセシビリティ | CGEventTap | システム設定 > プライバシーとセキュリティ > アクセシビリティ |
| 入力監視 | キーボード監視 | システム設定 > プライバシーとセキュリティ > 入力監視 |

## 依存パッケージ

- `mss` - スクリーンキャプチャ
- `opencv-python-headless` - 動画エンコード
- `numpy` - フレーム操作
- `pyobjc-framework-Quartz` - CGEventTap (macOS)
