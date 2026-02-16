# window_detector_mac.py

macOS用: マウスカーソル位置のウィンドウを検出するモジュール

## 概要

macOSの `Quartz` API (`CGWindowListCopyWindowInfo`) を使い、マウスカーソル位置にあるウィンドウのID・名前・アプリ名・PID・位置・サイズを取得する。

## 必要環境

- macOS
- `pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa`
- システム環境設定 > プライバシーとセキュリティ > スクリーン録画 で対象アプリに権限付与

## クラス: WindowDetectorMac

### get_mouse_position() -> Tuple[int, int]

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | `(x, y)` マウス座標のタプル |

### get_all_windows() -> List[Dict]

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | Z-order順のウィンドウ情報リスト `[{"window_id": int, "name": str, "owner": str, "owner_pid": int, "x": int, "y": int, "width": int, "height": int, "layer": int}]` |

### get_focused_window() -> Optional[Dict]

NSWorkspaceで最前面アプリのPIDを取得し、そのPIDに対応するウィンドウを返却する。

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | `get_all_windows()` の要素と同じ形式 or `None` |

### get_window_at_cursor() -> Optional[Dict]

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | `{"window_id": int, "name": str, "owner": str, "owner_pid": int, "x": int, "y": int, "width": int, "height": int, "mouse_x": int, "mouse_y": int}` or `None` |

### get_window_at_position(x, y) -> Optional[Dict]

| 項目 | 内容 |
|------|------|
| Input | `x: int` X座標, `y: int` Y座標 |
| Output | `get_window_at_cursor()` と同じ形式 or `None` |

## Linux版 (window_detector.py) との違い

| 項目 | Linux版 | macOS版 |
|------|---------|---------|
| 依存 | xdotool (CLI) | pyobjc-framework-Quartz |
| 返却値の `owner` | なし | あり（アプリ名） |
| 返却値の `owner_pid` | なし | あり（プロセスID） |
| `get_focused_window()` | なし | あり |
| ウィンドウ検出方法 | xdotool getmouselocation | CGWindowListCopyWindowInfo + 座標マッチ |
