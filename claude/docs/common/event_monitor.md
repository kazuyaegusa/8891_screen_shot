# event_monitor.py ドキュメント

対応ソース: `claude/src/common/event_monitor.py`

## 概要

macOS CGEventTapを使って、マウスクリック・キーボード入力イベントをリアルタイムに監視するモジュール。
`capture_loop.py` のeventモードから利用される。

## クラス: EventMonitor

### コンストラクタ

```python
monitor = EventMonitor(
    on_click=callback_fn,        # クリック時コールバック
    on_text_input=callback_fn,   # テキスト入力フラッシュ時コールバック
    click_debounce=0.5,          # クリックデバウンス秒
    text_flush_sec=1.0,          # テキストフラッシュ秒
)
```

### メソッド

#### `start()`

イベント監視を開始する（メインスレッドでブロッキング）。

- **入力**: なし
- **出力**: なし（ブロッキング、stop()で終了）
- CGEventTapを作成しCFRunLoopで待機する

#### `stop()`

イベント監視を停止する。別スレッドから呼び出す。

- **入力**: なし
- **出力**: なし
- テキストバッファをフラッシュしてからCFRunLoopを停止する

### コールバック

#### on_click(data)

```python
{"button": "left" | "right", "x": float, "y": float}
```

#### on_text_input(data)

```python
{"text": str}  # バッファに蓄積されたキー入力をフラッシュした結果
```

## 依存ライブラリ

- `pyobjc-framework-Quartz`

## 必要な権限

- アクセシビリティ権限
- 入力監視権限（キーボード記録時）
