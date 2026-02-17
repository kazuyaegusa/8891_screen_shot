# feedback_store.py

実行フィードバック永続化モジュール。ワークフロー実行結果をJSON形式で保存し、成功率・ステップ別失敗率を算出する。

## インプット

### `FeedbackStore.__init__(feedback_dir: str)`
- `feedback_dir: str` - フィードバックJSON保存ディレクトリパス

### `FeedbackStore.record(feedback: ExecutionFeedback)`
- `feedback: ExecutionFeedback` - 保存するフィードバックデータ

### `FeedbackStore.get_by_workflow(workflow_id: str)`
- `workflow_id: str` - 対象ワークフローID

### `FeedbackStore.get_success_rate(workflow_id: str)`
- `workflow_id: str` - 対象ワークフローID

### `FeedbackStore.get_step_failure_rates(workflow_id: str)`
- `workflow_id: str` - 対象ワークフローID

### `FeedbackStore.list_all()`
- 引数なし

### `FeedbackStore.count()`
- 引数なし

## アウトプット

### `record(feedback)` → str
- 保存先ファイルパスを返却

### `get_by_workflow(workflow_id)` → List[ExecutionFeedback]
- 指定ワークフローのフィードバック一覧

### `get_success_rate(workflow_id)` → float
- 成功率（0.0〜1.0）

### `get_step_failure_rates(workflow_id)` → Dict[int, float]
- ステップインデックスをキー、失敗率（0.0〜1.0）を値とする辞書

### `list_all()` → List[ExecutionFeedback]
- 全フィードバック（timestamp降順）

### `count()` → int
- 保存済みフィードバック件数

## データモデル

### `ExecutionFeedback` (dataclass)

```python
@dataclass
class ExecutionFeedback:
    feedback_id: str          # フィードバック一意ID
    workflow_id: str          # 対象ワークフローID
    goal: str                 # 実行目標テキスト
    success: bool             # 全体成功/失敗
    steps_executed: int       # 実行したステップ数
    steps_succeeded: int      # 成功したステップ数
    failed_step_indices: List[int]  # 失敗したステップのインデックス
    error_details: List[Dict[str, str]]  # ステップ別エラー詳細 [{step_index, error_code, error_msg}]
    timestamp: str            # ISO8601タイムスタンプ
    execution_mode: str       # 実行モード（"workflow" / "autonomous"）
    duration_seconds: float   # 実行時間（秒）
    app_name: str             # 対象アプリケーション名
```

## 関数一覧

| 関数 | 説明 |
|------|------|
| `FeedbackStore.__init__(feedback_dir)` | フィードバック保存ディレクトリを初期化 |
| `FeedbackStore.record(feedback)` | フィードバックをJSONで保存、パスを返却 |
| `FeedbackStore.get_by_workflow(workflow_id)` | ワークフロー別にフィードバックを取得 |
| `FeedbackStore.get_success_rate(workflow_id)` | ワークフローの成功率を算出 |
| `FeedbackStore.get_step_failure_rates(workflow_id)` | ステップ別の失敗率を算出 |
| `FeedbackStore.list_all()` | 全フィードバックをtimestamp降順で取得 |
| `FeedbackStore.count()` | 保存済みフィードバック件数を返却 |

## ストレージ

- 保存先: `workflows/feedback/{feedback_id}.json`
- 形式: JSON（ExecutionFeedbackの全フィールドをシリアライズ）

## 依存

- `agent.models.ExecutionFeedback`
