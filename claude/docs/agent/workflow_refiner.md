# workflow_refiner.py

ワークフロー改善モジュール（kework-agi準拠）。フィードバックに基づくステータス自動昇降格、confidence更新、失敗ステップ除去、バリアント生成、類似ワークフローマージを行う。

## インプット

### `WorkflowRefiner.__init__(store: WorkflowStore, feedback: FeedbackStore)`
- `store: WorkflowStore` - ワークフロー永続化ストア
- `feedback: FeedbackStore` - フィードバックストア

### `WorkflowRefiner.refine_all()`
- 引数なし
- 全ワークフローに対して改善処理を実行

### `WorkflowRefiner.select_best_variant(original_id: str)`
- `original_id: str` - 元ワークフローID

## アウトプット

### `refine_all()` → Dict[str, Any]

```python
{
    "updated": int,    # confidence更新されたワークフロー数
    "pruned": int,     # 失敗ステップが除去された数
    "merged": int,     # マージされたワークフロー数
    "promoted": int,   # ステータス昇格されたワークフロー数
    "demoted": int,    # ステータス降格されたワークフロー数
    "variants": int,   # 生成されたバリアント数
}
```

### `select_best_variant(original_id)` → str
- 元ワークフローとバリアントの中で最も成功率の高いワークフローIDを返却

## 改善ロジック

### 1. ステータス自動昇降格（kework-agi LearningEngine準拠）

| 遷移 | 条件 |
|------|------|
| DRAFT → TESTED | 実行1回以上 & 成功あり |
| TESTED → ACTIVE | 実行5回以上 & 成功率70%以上 |
| ANY → DEPRECATED | 実行3回以上 & 成功率20%未満 |

### 2. confidence更新
- 計算式: `新confidence = 既存confidence * 0.7 + 成功率 * 0.3`
- フィードバックが存在するワークフローが対象

### 3. 失敗ステップ除去
- 条件: 失敗率 ≥ 80% **かつ** フィードバック件数 ≥ 3件
- 該当ステップをワークフローから除去

### 4. バリアント生成（kework-agi SkillOptimizer準拠）
- 条件: 失敗フィードバック3件以上 & 既存バリアント3未満
- エラーパターンからステップ修正を自動生成
- `{元ワークフロー名}_v{N}` として保存（parent_id で関連付け）

エラー→修正マッピング:

| エラーコード | 修正タイプ | 説明 |
|-------------|-----------|------|
| HINT_NOT_FOUND (5回以上) | change_to_click_xy | 座標クリックに変更 |
| HINT_NOT_FOUND (5回未満) | insert_wait | 待機時間追加（0.5秒） |
| TIMEOUT | increase_timeout | タイムアウト1.5倍延長 |
| INPUT_FAILED | insert_focus_check | フォーカス確認挿入 |

### 5. 類似ワークフローマージ
- マージ条件（全て満たす必要あり）:
  - 同一アプリケーション
  - ワークフロー名の編集距離 ≤ 3
  - タグの重複率 ≥ 50%（Jaccard係数）
- マージ時: ステップ数が多い方をベースに、confidenceは平均

## 関数一覧

| 関数 | 説明 |
|------|------|
| `WorkflowRefiner.__init__(store, feedback)` | ストアとフィードバックを初期化 |
| `WorkflowRefiner.refine_all()` | 全ワークフローの改善を実行、統計を返却 |
| `WorkflowRefiner.select_best_variant(original_id)` | 最適バリアントのIDを返却 |

## 依存

- `agent.models.Workflow`, `agent.models.WorkflowStatus`
- `agent.workflow_store.WorkflowStore`
- `agent.feedback_store.FeedbackStore`
