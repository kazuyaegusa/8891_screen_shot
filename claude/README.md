# マウス位置 UI要素/ウィンドウ 赤枠スクリーンショット

マウスカーソル位置の**UI要素（検索窓、ボタン等）またはウィンドウ**を自動検出し、赤枠で囲んだスクリーンショットを撮影するツール。
Linux (X11) と macOS に対応。
キャプチャ結果は**包括的なJSON**（モニター情報、全ウィンドウ一覧、ブラウザURL/タイトル、入力テキスト等）として保存。

## 検出モード

| モード | 説明 | 対応OS |
|--------|------|--------|
| `element` (デフォルト) | Accessibility APIでUI要素レベル検出。失敗時はwindowにフォールバック | macOS |
| `window` | 従来のウィンドウレベル検出 | Linux, macOS |

### 動作イメージ

| シナリオ | windowモード | elementモード |
|---------|-------------|--------------|
| 検索窓をクリック | ブラウザ全体に赤枠 | 検索窓だけに赤枠 |
| ボタンをクリック | ウィンドウ全体に赤枠 | ボタンだけに赤枠 |
| Electron app (Discord等) | ウィンドウ全体に赤枠 | ウィンドウ（AX API非対応でフォールバック） |

## 構成

```
claude/
├── src/
│   ├── capture_loop.py            # 常駐キャプチャ（timer/eventモード対応、Ctrl+Cで停止）
│   ├── window_detector.py         # ウィンドウ検出 - Linux (xdotool)
│   ├── window_detector_mac.py     # ウィンドウ検出 - macOS (Quartz)
│   ├── window_screenshot.py       # 赤枠描画 + スクショ撮影 + JSON保存（OS自動判別、element/windowモード）
│   ├── common/
│   │   ├── app_inspector.py       # UI要素検出 + ブラウザ情報取得 - macOS (Accessibility API)
│   │   ├── event_monitor.py       # CGEventTapイベント監視 - macOS（クリック・キーボード）
│   │   └── json_saver.py          # JSON保存ユーティリティ（疎結合）
│   └── test_window_screenshot.py  # テストスクリプト（macOS/Linux自動分岐）
├── docs/
│   ├── capture_loop.md            # capture_loopのAPI仕様
│   ├── window_detector.md         # Linux版 API仕様
│   ├── window_detector_mac.md     # macOS版 API仕様
│   ├── window_screenshot.md       # window_screenshotのAPI仕様
│   └── common/
│       ├── app_inspector.md       # app_inspectorのAPI仕様
│       ├── event_monitor.md       # event_monitorのAPI仕様
│       └── json_saver.md          # json_saverのAPI仕様
└── README.md
```

## 必要環境

### Linux
- X11ディスプレイサーバー + ウィンドウマネージャー
- `sudo apt install xdotool`
- `pip install mss Pillow`

### macOS
- `pip install mss Pillow pyobjc-framework-Quartz`
- システム環境設定 > プライバシーとセキュリティ > スクリーン録画 で権限付与
- **elementモード追加要件**:
  - `pip install pyobjc-framework-ApplicationServices pyobjc-framework-Cocoa`
  - システム環境設定 > プライバシーとセキュリティ > アクセシビリティ で権限付与
- **eventモード追加要件**:
  - システム環境設定 > プライバシーとセキュリティ > 入力監視 で権限付与（キーボード記録時）

## 使い方

`window_screenshot.py` がOSを自動判別するので、使い方はLinux/Mac共通。

### 常駐キャプチャ（ずっと撮り続ける）

2つのトリガーモードから選択可能:

```bash
# === timerモード（デフォルト）: 一定間隔でキャプチャ ===

# デフォルト（3秒間隔、./screenshots に保存）
cd claude/src && python3 capture_loop.py

# 5秒間隔、出力先を指定
python3 capture_loop.py --trigger timer --interval 5 --output /tmp/capture

# ウィンドウモード + クロップのみ
python3 capture_loop.py --mode window --crop-only

# === eventモード: クリック・テキスト入力でキャプチャ（macOS専用） ===

# クリック・テキスト入力のたびにスクショ
python3 capture_loop.py --trigger event

# デバウンス・フラッシュ時間を調整
python3 capture_loop.py --trigger event --click-debounce 1.0 --text-flush 2.0

# 停止: Ctrl+C
```

| トリガー | 説明 | 用途 |
|---------|------|------|
| `timer` (デフォルト) | 一定間隔でキャプチャ | 定期監視、デモ録画 |
| `event` | クリック・テキスト入力でキャプチャ | 操作記録、UI検証 |

### UI要素レベルで赤枠スクショ + JSON保存（デフォルト）

```python
from window_screenshot import WindowScreenshot

# elementモード（デフォルト）: UI要素だけに赤枠
ws = WindowScreenshot(output_dir="./screenshots")

result = ws.capture_window_at_cursor()
print(result["detection_mode"])       # "element" or "window"（フォールバック時）
print(result["full_screenshot"])      # 全画面に赤枠
print(result["cropped_screenshot"])   # ターゲット部分のみ
print(result["json_path"])            # 包括的JSONファイルパス
print(result["window_info"])          # ターゲット情報
```

### JSON出力の内容

キャプチャ時に自動保存されるJSONには以下の情報が含まれる:

```json
{
  "capture_id": "uuid",
  "timestamp": "ISO8601",
  "detection_mode": "element",
  "mouse": { "x": 500, "y": 300 },
  "target": {
    "detection_type": "element",
    "name": "検索", "role": "AXTextField",
    "value": "入力テキスト全文（最大2000文字）",
    "placeholder": "検索...",
    "focused": true, "enabled": true,
    "role_description": "テキストフィールド"
  },
  "app": { "name": "Safari", "bundle_id": "com.apple.Safari", "pid": 1234 },
  "browser": { "is_browser": true, "url": "https://...", "page_title": "..." },
  "window": { "window_id": 5678, "name": "...", "owner": "Safari" },
  "all_windows": [ ... ],
  "monitors": [ { "index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080 }, ... ],
  "screenshots": { "full": "path/to/full.png", "cropped": "path/to/crop.png" }
}
```

### ウィンドウレベルで赤枠スクショ（従来動作）

```python
# windowモード: ウィンドウ全体に赤枠（従来と同じ）
ws = WindowScreenshot(output_dir="./screenshots", detection_mode="window")
result = ws.capture_window_at_cursor()
```

### ウィンドウ検出のみ

```python
# Linux
from window_detector import WindowDetector
detector = WindowDetector()

# macOS
from window_detector_mac import WindowDetectorMac
detector = WindowDetectorMac()

info = detector.get_window_at_cursor()
# => {"window_id": ..., "name": "Firefox", "owner_pid": 1234, "x": 100, "y": 50, ...}

# macOS: 最前面アプリのウィンドウを取得
focused = detector.get_focused_window()
```

### ブラウザ情報取得のみ

```python
from common.app_inspector import AppInspector

inspector = AppInspector()
app_info = inspector.get_frontmost_app()
browser_info = inspector.get_browser_info(app_info["pid"])
# => {"is_browser": True, "url": "https://...", "page_title": "..."}
```

### 外部のウィンドウ情報と連携

```python
# マウストラッカー等で取得した情報を渡す
window_info = {"x": 100, "y": 50, "width": 800, "height": 600, "name": "MyApp"}
result = ws.capture_with_window_info(window_info)
```

## テスト実行

```bash
# macOS（全テスト: 環境 + モニター + 全ウィンドウ + ブラウザ + element + window + JSON出力）
cd claude/src && python test_window_screenshot.py

# Linux 実環境（X11デスクトップ上）
cd claude/src && python test_window_screenshot.py

# JSON出力の目視確認
cat /tmp/test_*/cap_*.json | python3 -m json.tool
```

## フォールバックフロー

```
capture_window_at_cursor()
  ├─ _detect_target()
  │    ├─ detector.get_window_at_cursor() → window_info
  │    ├─ inspector.get_element_at_position(x, y) → element_info (拡張属性含む)
  │    └─ inspector.get_frontmost_app() → app_info (pid含む)
  ├─ _collect_monitors() → mss.monitors → 全モニター情報
  ├─ _collect_all_windows() → detector.get_all_windows() → 全ウィンドウ一覧
  ├─ _collect_browser_info(pid) → URL, タイトル
  ├─ スクショ撮影 + 赤枠描画 + 保存
  └─ json_saver.save_capture_json() → JSON保存
```

## 注意事項

- **Linux**: ウィンドウマネージャー必須。Wayland環境は非対応（xdotoolがX11依存）
- **macOS**: スクリーン録画の権限が必要。Retina対応はmssが自動で処理
- **macOS elementモード**: アクセシビリティ権限が必要。Electron系アプリ(Discord等)はAX API非対応のためwindowにフォールバック
- **共通**: DISPLAY環境変数（Linuxのみ）が必ず設定されている必要がある
- **JSON保存**: スクショ撮影が成功すればJSON保存失敗時でもスクショは正常に返却される
