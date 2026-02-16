# Screen Action Recorder - 調査・実装サマリー

> 作成日: 2026-02-05
> 更新日: 2026-02-07
> 作成者: Claude Code

## 概要

画面上のクリック操作を記録し、UIElement情報とスクリーンショットを保存。記録したデータをもとに操作を再生する仕組みを構築した。macOS Accessibility APIを活用することで、座標ベースではなく要素の識別子ベースでの再生を実現。

---

## 背景・目的

### 課題
- 繰り返しのGUI操作を自動化したい
- 従来のマクロ記録は座標ベースのため、ウィンドウ位置が変わると失敗する
- 操作内容を後から確認・編集したい

### 目標
- クリック/入力操作を記録（座標 + UI要素情報 + スクリーンショット）
- 記録をJSON形式で保存し、再利用可能な「スキル」として組み替え
- 要素の識別子ベースで再生し、レイアウト変更に強い自動化を実現

---

## 既存プロダクト調査

### 類似ツール比較

| プロダクト | 概要 | 長所 | 短所 |
|-----------|------|------|------|
| **[Kairos](https://www.kairos.computer/)** | 画面録画からワークフロー学習するAI | 自然言語指示、50+アプリ連携 | クローズドソース、$37/月 |
| **[Ui.Vision](https://ui.vision/rpa)** | オープンソースRPA、Record & Replay | OCR/CV対応、Anthropic Computer Use統合 | Webブラウザ中心、ネイティブアプリ弱い |
| **[Skyvern](https://github.com/Skyvern-AI/skyvern)** | ブラウザ自動化AI | フォーム入力特化、高精度 | ブラウザ限定 |
| **[Anthropic Computer Use](https://docs.anthropic.com/en/docs/build-with-claude/computer-use)** | Claudeが画面を見て操作 | 汎用性高い | スクリーンショットベース、要素IDなし |
| **[Selenium IDE](https://www.selenium.dev/selenium-ide/)** | Web自動化の定番 | 複数ロケーター記録 | Web専用 |

### 本プロジェクトの差別化

- macOS Accessibility APIにより**実際のUI要素ID/識別子を取得**
- スクリーンショット + 要素情報の両方を保存
- 識別子ベースの再検索により、位置変更に耐性がある
- 将来的にAIによる画像認識フォールバックを追加可能

---

## 技術調査

### macOS Accessibility API

**使用フレームワーク:**
- `ApplicationServices` - AXUIElement操作
- `Quartz` - CGEvent（クリック実行、イベント監視）
- `AppKit` - NSWorkspace（アプリ情報取得）

**主要API:**
```python
# 指定座標のUI要素取得
AXUIElementCopyElementAtPosition(systemWide, x, y, None) -> (error, element)

# 要素の属性取得
AXUIElementCopyAttributeValue(element, "AXRole", None) -> (error, value)
AXUIElementCopyAttributeValue(element, "AXIdentifier", None) -> (error, value)
AXUIElementCopyAttributeValue(element, "AXPosition", None) -> (error, AXValueRef)
AXUIElementCopyAttributeValue(element, "AXSize", None) -> (error, AXValueRef)
```

**取得可能な属性:**
| 属性 | 用途 | 再検索での優先度 |
|------|------|----------------|
| `AXIdentifier` | 開発者が設定した一意ID | 最高 |
| `AXValue` | テキスト内容 | 高 |
| `AXDescription` | 要素の説明 | 高 |
| `AXTitle` | 表示タイトル | 中 |
| `AXRole` | 要素の種類（Button, Text等） | 低 |
| `AXPosition` | 位置 (CGPoint) | フォールバック |
| `AXSize` | サイズ (CGSize) | フォールバック |

**Frame取得の注意点:**

`AXPosition`/`AXSize`は`AXValueRef`型で返され、直接値を取り出せない。pyobjcでは文字列表現をパースする方法で対応：

```python
# AXValueRefの文字列表現
# Position: "<AXValue 0x... {value = x:100.0 y:200.0 type = kAXValueCGPointType}>"
# Size: "<AXValue 0x... {value = w:80.0 h:30.0 type = kAXValueCGSizeType}>"

import re
pos_match = re.search(r'x:([\d.]+)\s*y:([\d.]+)', str(position))
size_match = re.search(r'w:([\d.]+)\s*h:([\d.]+)', str(size))
```

### グローバルイベント監視

**CGEventTap:**
```python
from Quartz import (
    CGEventTapCreate,
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly,
    CGEventMaskBit,
    kCGEventLeftMouseDown,
)

# イベントタップ作成（リッスンのみ、イベントは変更しない）
tap = CGEventTapCreate(
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly,
    CGEventMaskBit(kCGEventLeftMouseDown) | CGEventMaskBit(kCGEventRightMouseDown),
    callback_function,
    None,
)
```

**必要な権限:**
- システム設定 > プライバシーとセキュリティ > アクセシビリティ
- 実行するアプリ（Terminal, Python等）を許可リストに追加

---

## 実装内容

### 1. レコーダー (`mvp_click_recorder.py`)

**機能:**
- グローバルなマウスクリックを監視
- クリック位置のUI要素情報を取得
- スクリーンショットを自動撮影
- セッションJSONとして保存

**出力データ構造:**
```json
{
  "session_id": "07af6ff8",
  "created_at": "2026-02-05T22:23:36",
  "total_actions": 6,
  "actions": [
    {
      "action_id": "f565a938",
      "timestamp": "2026-02-05T22:23:10",
      "action_type": "left_click",
      "coordinates": {"x": 571.47, "y": 67.75},
      "app": {
        "name": "システム設定",
        "bundle_id": "com.apple.systempreferences"
      },
      "element": {
        "role": "AXButton",
        "title": null,
        "description": "戻る",
        "identifier": "go back",
        "value": null,
        "frame": {"x": 380, "y": 60, "width": 32, "height": 28},
        "available_attributes": ["AXIdentifier", "AXEnabled", ...]
      },
      "screenshot_path": "/path/to/screenshots/f7ea17c7.png"
    }
  ]
}
```

### 2. プレイヤー (`mvp_action_player.py`)

**機能:**
- セッションJSONを読み込み
- 各アクションの要素を再検索
- 見つかった要素の中心座標をクリック
- アプリのアクティブ化も自動実行

**要素検索アルゴリズム:**
```
1. 記録座標の要素を取得
2. identifier一致 → その要素のframe中心をクリック
3. value一致 → その要素のframe中心をクリック
4. description一致 → その要素のframe中心をクリック
5. title + role一致 → その要素のframe中心をクリック
6. roleのみ一致 → 記録座標をクリック
7. フォールバック → 記録座標をクリック
```

**コマンドラインオプション:**
```bash
python3 mvp_action_player.py <session.json> [options]

Options:
  --dry-run    実際にクリックせずシミュレーション
  --delay N    アクション間の待機秒数（デフォルト: 1.0）
  --start N    N番目のアクションから開始（0始まり）
```

### 3. キーボード入力（統合）

**追加内容（2026-02-07）:**
- `mvp_click_recorder.py` が `kCGEventKeyDown` を記録
- 連続入力は `text_input` にまとめる
- ショートカットは `key_shortcut`、単発キーは `key_input`
- `flags` と `modifiers` を保存

**再生側:**
- `mvp_action_player.py` が `text_input` / `key_input` / `key_shortcut` を再生
- `BASE_FLAGS=0x100` を常に設定し、Shift固着を回避

---

## テスト結果

### テストシナリオ

システム設定アプリで以下の操作を記録：
1. ウィンドウ上部クリック
2. 「ディスプレイ」クリック
3. 「アクセシビリティ」クリック
4. 「VoiceOver」クリック
5. 「戻る」ボタンクリック
6. Cursorアプリに戻ってクリック

### 記録結果

| # | 要素 | 取得できた識別情報 |
|---|------|------------------|
| 1 | グループ領域 | role: AXGroup |
| 2 | ディスプレイ | value: "ディスプレイ" |
| 3 | アクセシビリティ | identifier: "com.apple.Accessibility-Settings.extension", value: "アクセシビリティ" |
| 4 | VoiceOver | identifier: "AX_FEATURE_VOICEOVER", description: "VoiceOver" |
| 5 | 戻るボタン | identifier: "go back", description: "戻る" |
| 6 | 画像 | role: AXImage |

**スクリーンショット:** 各クリック時点の画面を保存（約1.5-2MB/枚）

### 再生結果

```
[1/6] Target Role: AXGroup
      method: coordinate_fallback → ✓ Success

[2/6] Target Value: ディスプレイ
      method: role_match_at_position → ✓ Success

[3/6] Target ID: com.apple.Accessibility-Settings.extension
      method: identifier_match_at_position → ✓ Success

[4/6] Target ID: AX_FEATURE_VOICEOVER
      method: identifier_match_at_position → ✓ Success

[5/6] Target ID: go back
      method: identifier_match_at_position → ✓ Success

[6/6] Target Role: AXImage
      method: role_match_at_position → ✓ Success

Result: 6/6 actions successful
```

**特筆事項:**
- identifier付きの要素（3, 4, 5）は`identifier_match_at_position`で検索成功
- frame情報から中心座標を計算し、記録時とは異なる座標でクリック実行
- ウィンドウ位置が多少変わっても正しくクリックされることを確認

---

## ファイル構成

```
01_Homerow_auto/
├── mvp_click_recorder.py      # 記録ツール
├── mvp_action_player.py       # 再生ツール
├── mvp_output/
│   ├── session_*.json         # 記録セッション
│   └── screenshots/           # スクリーンショット
├── docs/
│   ├── SCREEN_ACTION_RECORDER_DESIGN.md    # 設計書
│   └── SCREEN_ACTION_RECORDER_SUMMARY.md   # 本ドキュメント
└── skills/                    # 既存のhomerowスキル（参考実装）
    ├── homerow/
    ├── app-automation/
    └── ...
```

---

## 今後の拡張案

### Phase 3: AI判断レイヤー
- 要素が見つからない場合、スクリーンショットをClaude Vision APIに送信
- 「このボタンはどこですか？」と問い合わせて座標を推測
- 信頼度スコアに基づいて実行判断

### Phase 4: ブラウザ対応
- Chrome Extension / Safari Extension でDOM要素を取得
- CSS Selector / XPath を記録
- Accessibility APIと併用したハイブリッド検索

### Phase 5: スキルエディタ
- 記録したアクションをGUIで編集・組み替え
- 条件分岐（if文）、ループ処理
- 変数・パラメータ化（動的な値の注入）

### その他
- キーボード入力の統合テスト（V6）
- 要素出現待機（Wait Until Visible）
- エラーハンドリング・リトライ機構

---

## 依存関係

```
Python 3.9+
pyobjc-framework-Cocoa
pyobjc-framework-Quartz
pyobjc-framework-ApplicationServices
```

**インストール:**
```bash
pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz pyobjc-framework-ApplicationServices
```

---

## 使用方法

### 記録
```bash
cd /path/to/01_Homerow_auto
python3 mvp_click_recorder.py

# 画面をクリックして操作を記録
# Ctrl+C で終了 → mvp_output/session_YYYYMMDD_HHMMSS.json に保存
```

### 再生
```bash
# Dry-run（シミュレーション）
python3 mvp_action_player.py mvp_output/session_xxx.json --dry-run

# 本番実行
python3 mvp_action_player.py mvp_output/session_xxx.json

# オプション付き
python3 mvp_action_player.py mvp_output/session_xxx.json --delay 2.0 --start 2
```

---

## 結論

macOS Accessibility APIを活用することで、座標ベースではなく要素識別子ベースでの操作記録・再生が可能であることを実証した。システム設定アプリでのテストでは、identifier付きの要素は100%の精度で再検索・クリックに成功。ウィンドウ位置の変化にも耐性があることを確認した。

今後、AI画像認識によるフォールバック、ブラウザ対応、スキルエディタの実装により、より汎用的な自動化プラットフォームへの発展が見込める。
