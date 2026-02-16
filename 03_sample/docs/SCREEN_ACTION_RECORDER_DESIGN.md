# Screen Action Recorder - 設計ドキュメント

> 作成日: 2026-02-05
> 更新日: 2026-02-07
> ステータス: Phase 2 完了、キーボード入力統合済み（V6テスト待ち）

## 概要

画面操作を記録し、AIで再生・自動化するシステム。

### コアコンセプト

```
[記録フェーズ]                    [再生フェーズ]
ユーザー操作                      保存データ
    ↓                              ↓
クリック検知 ──→ スクリーンショット   AI が要素を再検索
    ↓              + 要素ID             ↓
JSON保存      + アプリ名          マッチング
    ↓              + タイムスタンプ     ↓
スキル化                          見つからない場合
                                     ↓
                                  画像認識で推測
```

## 類似プロダクト調査

| プロダクト | 特徴 | オープンソース | URL |
|-----------|------|---------------|-----|
| **Kairos** | 画面録画からワークフロー学習、自然言語で指示 | ❌ | https://www.kairos.computer/ |
| **Ui.Vision** | Record & Replay + OCR + AI、Anthropic Computer Use統合 | ✅ | https://ui.vision/rpa |
| **Skyvern** | ブラウザ自動化、フォーム入力特化 | ✅ | https://github.com/Skyvern-AI/skyvern |
| **Anthropic Computer Use** | Claude自身がスクリーンショットを見て操作 | API提供 | https://docs.anthropic.com/en/docs/build-with-claude/computer-use |
| **Selenium IDE** | 複数ロケーター記録、Web特化 | ✅ | https://www.selenium.dev/selenium-ide/ |

### 本プロジェクトの差別化ポイント

- macOS Accessibility API → **実際のUI要素IDを取得**
- 記録時点でスクリーンショット + 要素情報を保存
- 再利用可能な「スキル」として組み替え可能
- AIハイブリッド再生（要素検索 → 画像認識フォールバック）

## 対象範囲

- ✅ macOSネイティブアプリ
- ✅ ブラウザ内Webアプリ
- ✅ 画像認識による補完

## データ構造

### アクション記録フォーマット

```json
{
  "action_id": "uuid",
  "timestamp": "2026-02-05T10:30:00",
  "action_type": "click|type|scroll|drag",
  "app": {
    "name": "LINE",
    "bundle_id": "jp.naver.line.mac"
  },
  "element": {
    "role": "AXButton",
    "title": "送信",
    "identifier": "send_button",
    "frame": {"x": 100, "y": 200, "width": 80, "height": 30},
    "path": ["AXWindow", "AXGroup", "AXButton"]
  },
  "coordinates": {"x": 140, "y": 215},
  "screenshot_path": "screenshots/action_001.png",
  "input_value": "テキスト入力の場合の値",
  "context": {
    "window_title": "チャット - 田中",
    "visible_text_near": ["メッセージ", "送信", "スタンプ"]
  }
}
```

### セッション記録フォーマット

```json
{
  "session_id": "uuid",
  "name": "LINEメッセージ送信",
  "created_at": "2026-02-05T10:30:00",
  "actions": [
    { "action_id": "...", ... },
    { "action_id": "...", ... }
  ],
  "metadata": {
    "total_actions": 5,
    "duration_seconds": 30,
    "apps_used": ["LINE"]
  }
}
```

## 実装フェーズ

### Phase 1: レコーダー基盤 ✅ 完了

**目標:** クリック/入力を検知してJSON+スクリーンショット保存

| コンポーネント | 技術 | 難易度 | 状態 |
|---------------|------|--------|------|
| グローバルイベント監視 | CGEventTap (Quartz) | ★★☆ | ✅ 完了 |
| UI要素取得 | Accessibility API | ★☆☆ | ✅ 完了 |
| Frame取得 | AXPosition + AXSize | ★★☆ | ✅ 完了 |
| スクリーンショット | screencapture | ★☆☆ | ✅ 完了 |
| JSON出力 | Python json | ★☆☆ | ✅ 完了 |

**成果物:** `mvp_click_recorder.py`

### Phase 2: プレイヤー（再生機能） ✅ 完了

**目標:** 記録したJSONから操作を再実行

| コンポーネント | 技術 | 難易度 | 状態 |
|---------------|------|--------|------|
| 要素再検索 | Accessibility API | ★★☆ | ✅ 完了 |
| フォールバック座標クリック | CGEvent | ★☆☆ | ✅ 完了 |
| アプリアクティブ化 | NSRunningApplication | ★☆☆ | ✅ 完了 |
| テキスト入力 | CGEventKeyboard | ★★☆ | ✅ 統合済み（テスト待ち） |
| 待機/同期処理 | 要素出現待ち | ★★☆ | 未着手 |

**成果物:** `mvp_action_player.py`

**テスト結果:** 4セッション48アクションをテスト済み。権限正常時の要素取得率100%。
詳細は `docs/TEST_RESULTS.md` 参照。

**要素検索の優先順位:**
1. identifier一致 → frame中心をクリック
2. value一致 → frame中心をクリック
3. description一致 → frame中心をクリック
4. title + role一致 → frame中心をクリック
5. roleのみ一致 → 記録座標をクリック
6. フォールバック → 記録座標をクリック

### Phase 3: AI判断レイヤー

**目標:** 要素が見つからない場合、スクリーンショットからAIが推測

| コンポーネント | 技術 | 難易度 |
|---------------|------|--------|
| スクリーンショット比較 | Claude Vision API | ★★☆ |
| 要素マッチング | プロンプトエンジニアリング | ★★★ |
| 信頼度スコア | AI出力パース | ★★☆ |

### Phase 4: ブラウザ対応

**目標:** Safari/Chrome内のWeb要素も記録

| コンポーネント | 技術 | 難易度 |
|---------------|------|--------|
| ブラウザ拡張連携 | Chrome Extension API | ★★★ |
| DOM要素取得 | JavaScript injection | ★★★ |
| セレクター保存 | CSS/XPath | ★★☆ |

### Phase 5: スキルエディタ

**目標:** 記録を組み替えて新しいワークフロー作成

| コンポーネント | 技術 | 難易度 |
|---------------|------|--------|
| ビジュアルエディタ | Web UI (React等) | ★★★ |
| 条件分岐/ループ | JSONスキーマ拡張 | ★★☆ |
| 変数/パラメータ | テンプレート化 | ★★☆ |

## 技術詳細

### グローバルイベント監視

macOSでグローバルなクリック/キー入力を監視する方法：

1. **CGEventTap** - 最も低レベル、権限が必要
2. **NSEvent.addGlobalMonitorForEvents** - より高レベル

```python
# CGEventTap例
from Quartz import (
    CGEventTapCreate,
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly,
    CGEventMaskBit,
    kCGEventLeftMouseDown,
)
```

### 要素特定の堅牢性

同じ要素を再発見するための複数の識別子（優先順）：

1. `AXIdentifier` (あれば最優先)
2. `AXTitle` + `AXRole`
3. 親要素からのパス (AXPath)
4. 周辺テキストコンテキスト
5. スクリーンショット類似度（AIフォールバック）

### 既存資産の活用

現在の `homerow_executor.py` と `homerow_overlay.py` のコードを再利用可能：

- クリック実行: `click_at()` 関数
- 要素検索: Accessibility API呼び出し
- JSON出力: フォーマット参考

## ファイル構成（予定）

```
screen-action-recorder/
├── recorder/
│   ├── event_monitor.py      # グローバルイベント監視
│   ├── element_capture.py    # UI要素情報取得
│   ├── screenshot.py         # スクリーンショット撮影
│   └── session.py            # セッション管理
├── player/
│   ├── element_finder.py     # 要素再検索
│   ├── action_executor.py    # アクション実行
│   └── ai_fallback.py        # AI推測フォールバック
├── editor/
│   └── skill_editor.py       # スキル編集
├── output/
│   ├── sessions/             # 記録セッション
│   └── screenshots/          # スクリーンショット
└── main.py                   # エントリーポイント
```

## 必要な権限

- **アクセシビリティ**: システム環境設定 > セキュリティとプライバシー > アクセシビリティ
- **画面収録**: システム環境設定 > セキュリティとプライバシー > 画面収録

## 次のアクション

1. [x] 設計ドキュメント作成
2. [x] Phase 1 MVP: グローバルクリック監視テスト
3. [x] Phase 1: UI要素取得統合
4. [x] Phase 1: スクリーンショット自動保存
5. [x] Phase 2: 再生機能実装
6. [x] クロスアプリテスト (ターミナル/Cursor/Finder/テキストエディット)
7. [x] **キーボード入力の検証** → `docs/KEYBOARD_INPUT_VERIFICATION.md`
8. [x] キーボード入力の記録実装
9. [x] キーボード入力の再生実装
10. [ ] テスト計画 B2, C1, D1, E4 の実施
