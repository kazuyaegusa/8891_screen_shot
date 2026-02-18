# ワークフロー再現性 監査レポート

実施日: 2026-02-18
対象: claude/src 配下のキャプチャ・ワークフロー・再生システム全体

---

## 結論（先に）

**現状のワークフロー再現性は不十分。53%のステップが座標依存で、ウィンドウ位置が変わると再生に失敗する。**

ただし改善の基盤は揃っている:
- スクリーンショットは全ステップに100%付いている
- Vision フォールバック（AIによる画像認識）のコードは実装済み
- 修正すべきバグが1件ある（ANTHROPIC_API_KEY 未対応）

---

## 1. 要素識別の仕組み（action_player.py）

再生時の要素検索は以下の優先順位で行われる:

```
1. identifier 一致     → 最も確実（アプリ固有の内部ID）
2. value 一致          → 確実（テキストフィールドの値など）
3. description 一致    → 確実（アクセシビリティの説明文）
4. title + role 一致   → やや確実（"再読み込み" + AXButton など）
5. アプリ全体検索      → ウィンドウ位置変更に対応（上記4条件で全要素再帰検索）
6. 座標フォールバック   → 再現性なし（記録時の生座標をそのまま使用）
7. Vision フォールバック → AIがスクリーンショットから要素位置を推定
```

## 2. キャプチャデータの品質（4,693件分析）

| 要素情報 | 件数 | 割合 |
|---------|------|------|
| 意味のある名前（"終了", "再読み込み" 等） | 1,494 | 31% |
| identifier あり | 149 | 3% |
| value あり | 810 | 17% |
| description あり | 433 | 9% |
| **汎用名のみ（AXGroup, AXImage 等）** | **2,780** | **59%** |

### 問題
- **59%のキャプチャは「AXGroup」「AXImage」としか記録されていない**
- これはmacOSのアクセシビリティAPIの限界。Chrome/Slack/Discord等のElectronアプリは内部要素をAXGroupとしてしか公開しない
- この59%は座標フォールバック（=再現性なし）になる

### 具体例

**再現可能な記録:**
```json
{
  "target.name": "再読み込み",
  "target.role": "AXButton",
  "target.description": "再読み込み"
}
→ アプリ内で「再読み込み」ボタンを名前で特定できる
```

**再現不可能な記録:**
```json
{
  "target.name": "AXGroup",
  "target.role": "AXGroup",
  "target.identifier": null,
  "target.value": null
}
→ 座標(1266, 1349)に頼るしかない
```

## 3. ワークフロー内ステップの再現性（2,276ステップ分析）

| 分類 | 件数 | 割合 | 再現方法 |
|------|------|------|---------|
| AXUIElementで特定可能 | 1,064 | **46%** | identifier/value/description/title+roleで検索 |
| 座標フォールバック必要 | 1,212 | **53%** | 記録時の生座標をそのまま使用 |
| スクリーンショット付き | 2,276 | **100%** | Vision AIによる画像認識が理論上可能 |
| スクリーンショット実在 | 2,276 | **100%** | ファイルが実際に存在する |

## 4. Vision フォールバックの現状

### 仕組み
座標フォールバックになった場合、action_player.py がスクリーンショットをAI（Vision API）に送信し、要素の現在位置を推定する。

```python
# action_player.py L574
if method == "coordinate_fallback":
    vision_coords = self._find_element_with_vision_fallback(step, step.screenshot_path)
    if vision_coords is not None:
        x, y = vision_coords
        result["method"] = "vision_fallback"
```

### バグ: ANTHROPIC_API_KEY 未対応

```python
# action_player.py L485（現在のコード）
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
```

**ANTHROPIC_API_KEY が含まれていない。** 現在のAIプロバイダーはAnthropicだが、Vision フォールバックがそれを認識しないため、53%の座標依存ステップに対してAI画像認識が発動しない。

### 修正案
```python
api_key = (os.environ.get("ANTHROPIC_API_KEY")
           or os.environ.get("GEMINI_API_KEY")
           or os.environ.get("OPENAI_API_KEY"))
```

さらに、AIClient初期化部分もAnthropicに対応させる必要がある:
```python
# 現在（L526）: gemini/openai のみ分岐
client = AIClient(provider=config.ai_provider,
    model=config.gemini_model if config.ai_provider == "gemini" else config.openai_model)

# 修正: anthropic も含める
model_map = {
    "anthropic": config.anthropic_model,
    "gemini": config.gemini_model,
    "openai": config.openai_model,
}
client = AIClient(provider=config.ai_provider,
    model=model_map.get(config.ai_provider))
```

## 5. OCR は使われているか？

**使われていない。** 現在のシステムは以下の2つの方法のみ:

1. **macOS Accessibility API（AXUIElement）** — UIツリーから要素名・ロール・ID等を取得
2. **AI Vision API** — スクリーンショットを画像として送信し、要素位置を推定（OCRではなく画像認識）

OCR（文字認識）は一切行われていない。AXUIElementが「AXGroup」としか返さない要素に対して、スクリーンショット上のテキストをOCRで読み取り、再現時に同じテキストを画面上で探す、という処理は未実装。

## 6. 再現性を高めるための改善案

### 即座に対応可能（バグ修正レベル）
1. **Vision フォールバックの ANTHROPIC_API_KEY 対応** — 上記のバグ修正
2. **AIClient初期化のprovider分岐修正** — anthropicモデルの正しい選択

### 短期的改善
3. **キャプチャ時にOCRを実行** — AXGroupしか取れない要素に対して、スクリーンショットから周辺テキストを抽出して記録。再生時に同じテキストを画面上で検索
4. **スクリーンショット差分マッチング** — 記録時のスクリーンショットの該当領域を切り出し、再生時に現在の画面でテンプレートマッチング

### 中期的改善
5. **Computer Use API の活用** — Anthropic の Computer Use 機能で、「このスクリーンショットの中で○○をクリックして」と直接指示
6. **要素のコンテキスト情報強化** — AXGroup の親要素・兄弟要素のtitle/valueも記録し、相対位置で特定

## 7. 現時点の再現性まとめ

```
全ステップ: 2,276件
├── AXUIElement で確実に再現可能: 1,064件 (46%)
├── 座標フォールバック（再現性なし）: 1,212件 (53%)
│   ├── Vision AI で救済可能（実装済み・バグあり）: 全件（スクショ100%完備）
│   └── バグ修正後に実質的に救済可能: 推定70-80%
└── テキスト入力（座標不問で再現可能）: 別途存在
```

**修正前の実効再現率: 約46%**
**Vision バグ修正後の推定再現率: 約80-90%**
