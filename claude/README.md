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
│   │   ├── json_saver.py          # JSON保存ユーティリティ（疎結合）
│   │   └── privacy_guard.py       # プライバシー保護フィルタ（パスワード・機密情報マスク）
│   ├── pipeline/
│   │   ├── __init__.py              # パッケージ初期化
│   │   ├── __main__.py              # python -m pipeline 実行用エントリポイント
│   │   ├── models.py                # データモデル（CaptureRecord, Session, ExtractedSkill）
│   │   ├── config.py                # パイプライン設定（環境変数 + デフォルト値）
│   │   ├── resource_guard.py        # リソース監視・スロットリング（CPU/メモリ制限）
│   │   ├── file_watcher.py          # ファイル監視（cap_*.json ポーリング）
│   │   ├── session_builder.py       # セッション構築（操作まとまりへの区切り）
│   │   ├── ai_client.py             # AI API抽象化（OpenAI gpt-5）
│   │   ├── pattern_extractor.py     # パターン抽出（AIによるスキル抽出）
│   │   ├── skill_writer.py          # スキル書き込み（SKILL.md生成）
│   │   ├── cleanup_manager.py       # 処理済みデータ削除
│   │   └── learning_pipeline.py     # メインオーケストレータ + CLI
│   └── test_window_screenshot.py  # テストスクリプト（macOS/Linux自動分岐）
├── docs/
│   ├── capture_loop.md            # capture_loopのAPI仕様
│   ├── window_detector.md         # Linux版 API仕様
│   ├── window_detector_mac.md     # macOS版 API仕様
│   ├── window_screenshot.md       # window_screenshotのAPI仕様
│   ├── common/
│   │   ├── app_inspector.md       # app_inspectorのAPI仕様
│   │   ├── event_monitor.md       # event_monitorのAPI仕様
│   │   ├── json_saver.md          # json_saverのAPI仕様
│   │   └── privacy_guard.md       # privacy_guardのAPI仕様
│   └── pipeline/
│       ├── models.md              # データモデルのAPI仕様
│       ├── config.md              # パイプライン設定のAPI仕様
│       ├── resource_guard.md      # リソース監視のAPI仕様
│       ├── file_watcher.md        # ファイル監視のAPI仕様
│       ├── session_builder.md     # セッション構築のAPI仕様
│       ├── ai_client.md           # AIクライアントのAPI仕様
│       ├── pattern_extractor.md   # パターン抽出のAPI仕様
│       ├── skill_writer.md        # スキル書き出しのAPI仕様
│       ├── cleanup_manager.md     # クリーンアップのAPI仕様
│       └── learning_pipeline.md   # メインパイプラインのAPI仕様
└── README.md
```

## 必要環境

### Linux
- X11ディスプレイサーバー + ウィンドウマネージャー
- `sudo apt install xdotool`
- `pip install mss Pillow`

### macOS
- `pip install mss Pillow pyobjc-framework-Quartz psutil openai python-dotenv`
- システム環境設定 > プライバシーとセキュリティ > スクリーン録画 で権限付与
- **elementモード追加要件**:
  - `pip install pyobjc-framework-ApplicationServices pyobjc-framework-Cocoa`
  - システム環境設定 > プライバシーとセキュリティ > アクセシビリティ で権限付与
- **eventモード追加要件**:
  - システム環境設定 > プライバシーとセキュリティ > 入力監視 で権限付与（キーボード記録時）

## 使い方

`window_screenshot.py` がOSを自動判別するので、使い方はLinux/Mac共通。

### ワンコマンド運用（推奨）

キャプチャ + 学習パイプラインを1コマンドで同時起動:

```bash
cd claude/src && python3 capture_loop.py --trigger event --auto-learn
```

- イベント駆動（クリック・テキスト入力・ショートカット）でキャプチャ
- バックグラウンドで学習パイプラインが自動処理（JSON → セッション → スキル抽出 → SKILL.md生成）
- プライバシー保護: デフォルトで `standard` レベル（パスワードフィールド自動マスク）

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

# === eventモード: クリック・テキスト入力・ショートカットでキャプチャ（macOS専用） ===

# クリック・テキスト入力・ショートカットのたびにスクショ
python3 capture_loop.py --trigger event

# デバウンス・フラッシュ時間を調整
python3 capture_loop.py --trigger event --click-debounce 1.0 --text-flush 2.0

# プライバシーレベルを指定（standard/strict/off）
python3 capture_loop.py --trigger event --privacy-level strict

# 学習パイプラインを同時起動
python3 capture_loop.py --trigger event --auto-learn

# ショートカット例: Cmd+C, Cmd+V, Cmd+Z 等の修飾キー付き操作も自動検出
# 停止: Ctrl+C
```

| トリガー | 説明 | 用途 |
|---------|------|------|
| `timer` (デフォルト) | 一定間隔でキャプチャ | 定期監視、デモ録画 |
| `event` | クリック・テキスト入力・ショートカットでキャプチャ | 操作記録、UI検証 |

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
  "session": {
    "session_id": "uuid (起動ごとにユニーク)",
    "sequence": 42
  },
  "user_action": {
    "type": "click",
    "button": "left",
    "x": 500.0,
    "y": 300.0,
    "modifiers": ["Cmd"],
    "timestamp": 1234567890.123
  },
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

### user_action の type 一覧

| type | トリガー | 主要フィールド |
|------|---------|--------------|
| `click` | マウスクリック | button, x, y, modifiers, timestamp |
| `text_input` | テキスト入力 | text, key_events |
| `shortcut` | 修飾キー+キー | modifiers, key, keycode, timestamp |
| `timer` | タイマー | (なし) |

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
capture_window_at_cursor(user_action=..., session=...)
  ├─ _detect_target()
  │    ├─ detector.get_window_at_cursor() → window_info
  │    ├─ inspector.get_element_at_position(x, y) → element_info (拡張属性含む)
  │    └─ inspector.get_frontmost_app() → app_info (pid含む)
  ├─ _collect_monitors() → mss.monitors → 全モニター情報
  ├─ _collect_all_windows() → detector.get_all_windows() → 全ウィンドウ一覧
  ├─ _collect_browser_info(pid) → URL, タイトル
  ├─ スクショ撮影 + 赤枠描画 + 保存
  └─ json_saver.save_capture_json() → JSON保存（user_action + session 含む）
```

## プライバシー保護

`common/privacy_guard.py` により、キャプチャデータに機密情報が平文記録されるのを自動防止する。

### PrivacyLevel（3段階）

| レベル | 説明 | 用途 |
|--------|------|------|
| `standard` (デフォルト) | パスワードフィールド（AXSecureTextField）のみフィルタ。テキスト内のAPIキー・カード番号も除去 | 通常利用 |
| `strict` | 全テキスト入力をマスク。URLの全パラメータをマスク。AXValueを常にマスク | 社内デモ、共有環境 |
| `off` | フィルタなし（全データをそのまま記録） | デバッグ用 |

### フィルタ対象

| 対象 | standardモード | strictモード |
|------|---------------|-------------|
| パスワードフィールド（AXSecureTextField） | テキスト記録しない + AXValueマスク + スクショスキップ | 同左 |
| URLトークン・APIキーパラメータ | 該当パラメータのみマスク | 全パラメータマスク |
| テキスト内APIキー（OpenAI, GitHub, AWS等） | パターン除去 | 全テキストマスク |
| テキスト内クレジットカード番号 | パターン除去 | 全テキストマスク |
| Bearer トークン | パターン除去 | 全テキストマスク |

### 使用例

```python
from common.privacy_guard import PrivacyGuard, PrivacyLevel

guard = PrivacyGuard(PrivacyLevel.STANDARD)

guard.is_secure_field("AXSecureTextField")                  # True
guard.filter_text_input("password123", is_secure=True)      # None（記録しない）
guard.sanitize_url("https://x.com?token=abc&page=1")        # "https://x.com?token=[MASKED]&page=1"
guard.mask_value("secret", "AXSecureTextField")              # "[MASKED]"
guard.should_skip_capture("AXSecureTextField", focused=True) # True
guard.redact_sensitive_patterns("key: sk-abc123def456...")    # "key: [API_KEY]"
```

## 学習パイプライン（Phase 2）

capture_loop.py が生成するキャプチャデータ（JSON + PNG）をバックグラウンドで処理し、操作パターンをスキルとして `~/.claude/skills/` に自動保存する。

### 起動方法

```bash
# デフォルト起動（.env設定を使用）
cd claude/src && python -m pipeline.learning_pipeline

# 1回だけ実行（テスト用）
python -m pipeline.learning_pipeline --once

# カスタム設定
python -m pipeline.learning_pipeline --watch-dir ./screenshots --provider openai --model gpt-5
```

### 同時起動（capture_loop + pipeline）

```bash
# ターミナル1: キャプチャ
cd claude/src && python3 capture_loop.py --trigger event

# ターミナル2: パイプライン
cd claude/src && python -m pipeline.learning_pipeline
```

### パイプライン処理フロー

```
cap_*.json (FileWatcher)
  → CaptureRecord (models)
  → Session (SessionBuilder: 操作間隔・アプリ切替で区切り)
  → ExtractedSkill (PatternExtractor → AIClient → OpenAI gpt-5)
  → SKILL.md (SkillWriter → ~/.claude/skills/)
  → 処理済みファイル削除 (CleanupManager)
```

## 注意事項

- **Linux**: ウィンドウマネージャー必須。Wayland環境は非対応（xdotoolがX11依存）
- **macOS**: スクリーン録画の権限が必要。Retina対応はmssが自動で処理
- **macOS elementモード**: アクセシビリティ権限が必要。Electron系アプリ(Discord等)はAX API非対応のためwindowにフォールバック
- **共通**: DISPLAY環境変数（Linuxのみ）が必ず設定されている必要がある
- **JSON保存**: スクショ撮影が成功すればJSON保存失敗時でもスクショは正常に返却される
