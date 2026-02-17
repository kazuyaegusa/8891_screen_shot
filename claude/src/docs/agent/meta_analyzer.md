# meta_analyzer.py

## 概要
クロスセッション性能分析モジュール。ワークフローの実行フィードバックを集計し、性能レポート生成・回帰検出・改善提案を行う（kework-agi MetaAnalyzer準拠）

## 主要クラス

### MetaAnalyzer(store, feedback)
- 入力: store: WorkflowStore - ワークフローストア, feedback: FeedbackStore - フィードバックストア

## 主要関数/メソッド

### generate_report(days=7)
- 入力: days: int - 集計対象期間（日数、デフォルト7）
- 出力: Dict[str, Any] - 性能レポート辞書
  - period_days: int - 集計期間
  - total_feedbacks: int - 期間内フィードバック総数
  - overall_success_rate: float - 全体成功率
  - app_stats: Dict - アプリ別統計（count, success_rate, avg_duration）
  - top_failures: List[Dict] - 失敗回数上位5ワークフロー
  - top_used: List[Dict] - 使用頻度上位5ワークフロー
  - status_distribution: Dict - ステータス別ワークフロー数
  - suggestions: List[Dict] - 改善提案リスト
- 説明: 指定期間のフィードバックを集計し、多角的な性能レポートを生成する

### detect_regression(workflow_id)
- 入力: workflow_id: str - ワークフローID
- 出力: bool - 回帰検出ならTrue
- 説明: 直近10回と前10回の成功率を比較し、0.2以上の低下があれば回帰として検出する。20回未満の実行ではFalseを返す

### suggest_improvements()
- 入力: なし
- 出力: List[Dict[str, Any]] - 改善提案リスト
  - workflow_id: str - 対象ワークフローID
  - name: str - ワークフロー名
  - priority: "high" | "medium" | "low" - 優先度
  - suggestion: str - 改善提案メッセージ
  - auto_applicable: bool - 自動適用可能か
- 説明: 全ワークフローを走査し、失敗率・回帰・アプリ成功率・非推奨ステータスに基づく改善提案を生成する

## 依存
- agent.models (Workflow, WorkflowStatus)
- agent.workflow_store (WorkflowStore)
- agent.feedback_store (FeedbackStore)
- datetime, logging (標準ライブラリ)

## 使用例
```python
from agent.meta_analyzer import MetaAnalyzer
from agent.workflow_store import WorkflowStore
from agent.feedback_store import FeedbackStore

store = WorkflowStore("./workflows")
feedback = FeedbackStore("./feedback")
analyzer = MetaAnalyzer(store, feedback)

# 週次レポート
report = analyzer.generate_report(days=7)
print(f"成功率: {report['overall_success_rate']:.1%}")
print(f"改善提案: {len(report['suggestions'])}件")

# 回帰検出
if analyzer.detect_regression("wf-001"):
    print("回帰検出!")

# 改善提案一覧
for s in analyzer.suggest_improvements():
    print(f"[{s['priority']}] {s['name']}: {s['suggestion']}")
```
