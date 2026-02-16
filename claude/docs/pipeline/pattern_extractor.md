# pattern_extractor.py ドキュメント

対応ソース: `claude/src/pipeline/pattern_extractor.py`

## 概要

セッションから操作パターン（スキル）を抽出するモジュール。
AIClient を経由してスキル抽出を行い、confidence 閾値でフィルタリングする。

## クラス

### `PatternExtractor`

#### コンストラクタ

```python
PatternExtractor(ai_client: AIClient, min_confidence: float = 0.6)
```

| 項目 | 内容 |
|------|------|
| **入力** | `ai_client`: AIClient インスタンス, `min_confidence`: 最低確信度（デフォルト 0.6） |

#### `extract(session: Session) -> List[ExtractedSkill]`

セッションからスキルを抽出し、confidence フィルタを適用して返す。

| 項目 | 内容 |
|------|------|
| **入力** | `session`: Session オブジェクト |
| **出力** | `List[ExtractedSkill]`（条件を満たすスキルのリスト） |

処理フロー:
1. セッションのレコードが空の場合は空リストを返す
2. `AIClient.extract_skill()` でスキル抽出を実行
3. 抽出結果が `None` の場合は空リストを返す
4. `skill.confidence < min_confidence` の場合は空リストを返す（デバッグログ出力）
5. 条件を満たすスキルをリストで返す

## 依存ライブラリ

- pipeline.ai_client (AIClient)
- pipeline.models (Session, ExtractedSkill)
