# window_detector.py

マウスカーソル位置のウィンドウを検出するモジュール

## 概要

X11環境で `xdotool` を使い、マウスカーソル位置にあるウィンドウのID・名前・位置・サイズを取得する。

## 必要環境

- Linux + X11ディスプレイサーバー（+ ウィンドウマネージャー）
- `xdotool` コマンド (`sudo apt install xdotool`)
- DISPLAY環境変数が設定されていること

## クラス: WindowDetector

### get_mouse_position() -> Tuple[int, int]

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | `(x, y)` マウス座標のタプル |

### get_window_id_at_position(x, y) -> str

| 項目 | 内容 |
|------|------|
| Input | `x: int` X座標, `y: int` Y座標 |
| Output | `str` ウィンドウID |

### get_window_geometry(window_id) -> Dict[str, int]

| 項目 | 内容 |
|------|------|
| Input | `window_id: str` ウィンドウID |
| Output | `{"x": int, "y": int, "width": int, "height": int}` |

### get_window_name(window_id) -> str

| 項目 | 内容 |
|------|------|
| Input | `window_id: str` ウィンドウID |
| Output | `str` ウィンドウ名（タイトルバーのテキスト） |

### get_window_at_cursor() -> Optional[Dict]

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | `{"window_id": str, "name": str, "x": int, "y": int, "width": int, "height": int, "mouse_x": int, "mouse_y": int}` or `None` |

### get_window_at_position(x, y) -> Optional[Dict]

| 項目 | 内容 |
|------|------|
| Input | `x: int` X座標, `y: int` Y座標 |
| Output | `get_window_at_cursor()` と同じ形式 or `None` |
