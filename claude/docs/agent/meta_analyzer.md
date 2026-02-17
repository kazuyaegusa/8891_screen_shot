# meta_analyzer.py

クロスセッション性能分析モジュール。kework-agi MetaAnalyzer準拠。フィードバックデータを集計し、アプリ別統計・失敗ランキング・回帰検出・改善提案を含むレポートを生成する。

## インプット

### `MetaAnalyzer.__init__(store: WorkflowStore, feedback: FeedbackStore)`
- `store: WorkflowStore` - ワークフロー永続化ストア
- `feedback: FeedbackStore` - フィードバックストア

### `MetaAnalyzer.generate_report(days: int = 7)`
- `days: int` - 集計対象期間（デフォルト7日間）

### `MetaAnalyzer.detect_regression(workflow_id: str)`
- `workflow_id: str` - 回帰検出対象のワークフローID

### `MetaAnalyzer.suggest_improvements()`
- 引数なし

## アウトプット

### `generate_report(days)` → Dict[str, Any]

```python
{
    "period_days": int,              # 集計期間（日数）
    "total_feedbacks": int,          # 期間内フィードバック総数
    "overall_success_rate": float,   # 全体成功率（0.0〜1.0）
    "app_stats": {                   # アプリ別統計
        "Safari": {
            "count": int,            # 実行回数
            "success_rate": float,   # 成功率
            "avg_duration": float,   # 平均実行時間（秒）
        }
    },
    "top_failures": [                # 失敗ランキング Top5
        {
            "workflow_id": str,
            "name": str,
            "failure_count": int,
            "success_rate": float,
        }
    ],
    "top_used": [                    # 使用頻度ランキング Top5
        {
            "workflow_id": str,
            "name": str,
            "execution_count": int,
            "success_rate": float,
        }
    ],
    "status_distribution": {         # ステータス分布
        "draft": int,
        "tested": int,
        "active": int,
        "deprecated": int,
    },
    "suggestions": [                 # 改善提案
        {
            "workflow_id": str,
            "name": str,
            "priority": str,        # "high" / "medium" / "low"
            "suggestion": str,
            "auto_applicable": bool,
        }
    ],
}
```

### `detect_regression(workflow_id)` → bool
- 直近10回 vs 前10回で成功率が0.2以上低下した場合 `True`
- フィードバック20件未満の場合は常に `False`

### `suggest_improvements()` → List[Dict[str, Any]]
- 改善提案リスト（以下のルールで生成）

## 改善提案ルール

| ルール | 条件 | 優先度 | 自動適用 |
|--------|------|--------|----------|
| 低成功率 | 実行3回以上 & 失敗率≥50% | high | Yes |
| 回帰検出 | 直近10回の成功率が前10回より0.2以上低下 | high | No |
| アプリ低成功率 | アプリ実行5回以上 & 成功率<30% | high | No |
| 非推奨 | ステータスがDEPRECATED | medium | No |

## 関数一覧

| 関数 | 説明 |
|------|------|
| `MetaAnalyzer.__init__(store, feedback)` | ストアとフィードバックを初期化 |
| `MetaAnalyzer.generate_report(days)` | 指定期間の性能レポートを生成 |
| `MetaAnalyzer.detect_regression(workflow_id)` | ワークフローの回帰を検出 |
| `MetaAnalyzer.suggest_improvements()` | 全ワークフローの改善提案を生成 |

## 依存

- `agent.models.Workflow`, `agent.models.WorkflowStatus`
- `agent.workflow_store.WorkflowStore`
- `agent.feedback_store.FeedbackStore`
