# event_monitor.py ドキュメント

対応ソース: `claude/src/common/event_monitor.py`

## 概要

macOS CGEventTapを使って、マウスクリック・キーボード入力・ショートカットキーイベントをリアルタイムに監視するモジュール。
`capture_loop.py` のeventモードから利用される。

## クラス: EventMonitor

### コンストラクタ

```python
monitor = EventMonitor(
    on_click=callback_fn,        # クリック時コールバック
    on_text_input=callback_fn,   # テキスト入力フラッシュ時コールバック
    on_shortcut=callback_fn,     # ショートカットキー時コールバック
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

### 内部メソッド

#### `_get_modifiers(event)` (staticmethod)

CGEventGetFlagsでアクティブな修飾キーのリストを返す。

- **入力**: CGEvent
- **出力**: `List[str]` (例: `["Cmd", "Shift"]`)
- 対応キー: Cmd, Shift, Option, Control

#### `_get_unicode_char(event)` (staticmethod)

CGEventKeyboardGetUnicodeStringで実際の入力文字を取得する。

- **入力**: CGEvent
- **出力**: `str` (取得失敗時は空文字)
- 旧 `_keycode_to_char` を置換（keycodeマッピング方式からOS API直接取得方式に変更）

### コールバック

#### on_click(data)

マウスクリック時に呼ばれる。デバウンス制御付き。

```python
{
    "button": "left" | "right",
    "x": float,
    "y": float,
    "modifiers": ["Cmd", ...],  # アクティブな修飾キーリスト
    "timestamp": float
}
```

#### on_text_input(data)

テキスト入力バッファがフラッシュされた時に呼ばれる（`text_flush_sec` 経過後）。

```python
{
    "text": str,                # バッファに蓄積されたキー入力をフラッシュした結果
    "key_events": [             # 個別キーイベントのリスト
        {
            "char": str,        # 入力文字
            "keycode": int,     # macOS keycode
            "timestamp": float
        },
        ...
    ]
}
```

#### on_shortcut(data)

Cmd/Control + 通常キーの組み合わせで発火する。

```python
{
    "modifiers": ["Cmd"],       # 修飾キーリスト
    "key": "c",                 # 入力キー（取得失敗時は "[key:keycode]"）
    "keycode": int,             # macOS keycode
    "timestamp": float
}
```

## 使用方法

```python
from common.event_monitor import EventMonitor

def on_click(data):
    print(f"Click: {data['button']} at ({data['x']}, {data['y']}) mods={data['modifiers']}")

def on_text(data):
    print(f"Text: {data['text']} ({len(data['key_events'])} keys)")

def on_shortcut(data):
    print(f"Shortcut: {'+'.join(data['modifiers'])}+{data['key']}")

monitor = EventMonitor(
    on_click=on_click,
    on_text_input=on_text,
    on_shortcut=on_shortcut,
    click_debounce=0.5,
    text_flush_sec=1.0,
)
monitor.start()   # メインスレッドでブロッキング（CFRunLoop）
# monitor.stop()  # 別スレッドから呼ぶ or SIGINTで停止
```

## 依存ライブラリ

- `pyobjc-framework-Quartz`

## 必要な権限

- アクセシビリティ権限
- 入力監視権限（キーボード記録時）
