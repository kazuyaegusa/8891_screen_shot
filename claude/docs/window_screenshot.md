# window_screenshot.py

マウスカーソル位置のウィンドウまたはUI要素を赤枠で囲ってスクリーンショットを撮るモジュール

## 概要

`window_detector` でマウス位置のウィンドウを検出し、`mss` で全画面キャプチャ、`Pillow` でターゲット領域に赤枠を描画して保存する。
macOSでは `AppInspector` (Accessibility API) によるUI要素レベルの検出にも対応。
キャプチャ結果は包括的なJSONファイルとしても保存される。

## 必要環境

- Linux + X11ディスプレイサーバー（+ ウィンドウマネージャー）+ `xdotool`
- macOS: `pyobjc-framework-Quartz`（スクリーン録画権限が必要）
  - elementモード: `pyobjc-framework-ApplicationServices` + アクセシビリティ権限
- `pip install mss Pillow`

## ファクトリ関数

### _create_detector() -> WindowDetector

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | OS対応のWindowDetectorインスタンス |

### _create_element_inspector() -> AppInspector or None

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | macOS: `AppInspector`インスタンス / macOS以外・失敗時: `None` |

## クラス: WindowScreenshot

### __init__(output_dir, detection_mode)

| 項目 | 内容 |
|------|------|
| Input | `output_dir: str` 保存先ディレクトリ（デフォルト: `./screenshots`）, `detection_mode: str` 検出モード（`"element"` or `"window"`、デフォルト: `"element"`） |

- `"element"`: UI要素レベルで赤枠検出（macOS専用、Accessibility API使用）。失敗時はwindowにフォールバック
- `"window"`: 従来のウィンドウレベル検出

### _normalize_element_info(element_info, mouse_x, mouse_y) -> Dict

AppInspectorの出力をwindow_info互換形式に変換する内部メソッド。拡張AX属性も含む。

| 項目 | 内容 |
|------|------|
| Input | `element_info: Dict` AppInspector出力, `mouse_x: int`, `mouse_y: int` |
| Output | `{"x", "y", "width", "height", "name", "role", "value", "placeholder", "focused", "enabled", "role_description", "detection_type": "element", "mouse_x", "mouse_y"}` |

### _detect_target() -> Optional[Dict]

detection_modeに応じたターゲット検出。elementモード失敗時はwindowにフォールバック。

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | ターゲット情報（window_info互換、`detection_type`, `app_pid`フィールド付き）or `None` |

**フォールバックフロー:**
1. elementモード: ウィンドウ情報取得(コンテキスト) → UI要素検出 → frame有効ならelement返却 → 無効ならwindow返却
2. windowモード: ウィンドウ情報をそのまま返却

### _collect_monitors() -> list

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | mss.monitorsの全モニター情報リスト |

### _collect_all_windows() -> list

| 項目 | 内容 |
|------|------|
| Input | なし |
| Output | detector.get_all_windows()の全ウィンドウ一覧 |

### _collect_browser_info(window_info) -> Dict

| 項目 | 内容 |
|------|------|
| Input | `window_info: Dict` ターゲット情報（app_pidを含む） |
| Output | `{"is_browser": bool, "url": str or None, "page_title": str or None}` |

### _find_monitor_at(x, y) -> Tuple[dict, int]

指定座標を含むモニターを返す。見つからない場合はプライマリモニターを返す。

| 項目 | 内容 |
|------|------|
| Input | `x: int` グローバルX座標, `y: int` グローバルY座標 |
| Output | `(mssモニター辞書, モニターインデックス1始まり)` |

### take_full_screenshot(monitor) -> Image.Image

| 項目 | 内容 |
|------|------|
| Input | `monitor: dict` mssモニター辞書（Noneならプライマリモニター） |
| Output | `PIL.Image.Image` 該当モニターのスクリーンショット |

**注意**: カーソル位置のモニターのみキャプチャする。マルチモニター環境で全画面結合はしない。

### draw_red_border(image, x, y, width, height, border_width) -> Image.Image

| 項目 | 内容 |
|------|------|
| Input | `image: Image.Image`, `x, y, width, height: int` 枠領域, `border_width: int` 枠線太さ（デフォルト3） |
| Output | `Image.Image` 赤枠描画済み画像（コピー） |

### crop_window_area(image, x, y, width, height, padding) -> Image.Image

| 項目 | 内容 |
|------|------|
| Input | `image: Image.Image`, `x, y, width, height: int` 領域, `padding: int` 余白（デフォルト5） |
| Output | `Image.Image` 切り出し画像 |

### add_window_info_label(image, window_info, position) -> Image.Image

detection_typeに応じてラベルを切り替え:
- `"element"`: `Element: <name> [<role>] | App: <owner> | Position | Size`
- `"window"`: `Window: <name> | Position | Size`

| 項目 | 内容 |
|------|------|
| Input | `image: Image.Image`, `window_info: Dict`, `position: str` ("top"/"bottom") |
| Output | `Image.Image` ラベル付き画像 |

### capture_window_at_cursor(crop_only, add_label, border_width, prefix) -> Optional[Dict]

メイン機能。マウスカーソル位置のターゲット（UI要素 or ウィンドウ）を赤枠で囲ってスクショ撮影 + JSON保存。

| 項目 | 内容 |
|------|------|
| Input | `crop_only: bool` ターゲット部分のみ, `add_label: bool` ラベル追加, `border_width: int` 枠太さ, `prefix: str` ファイル名接頭辞 |
| Output | `{"full_screenshot": str, "cropped_screenshot": str, "window_info": Dict, "detection_mode": str, "timestamp": str, "json_path": str}` or `None` |

**JSON出力**: `{prefix}_cap_{timestamp}.json` として出力ディレクトリに保存。
JSON構造の詳細は `docs/common/json_saver.md` を参照。

### capture_with_window_info(window_info, ...) -> Dict

外部から渡されたウィンドウ情報を使ってスクショ撮影（マウストラッカーとの連携用）。

| 項目 | 内容 |
|------|------|
| Input | `window_info: Dict` (`{"x", "y", "width", "height", "name"}`), その他 `capture_window_at_cursor` と同じ |
| Output | `capture_window_at_cursor` と同じ形式 |
