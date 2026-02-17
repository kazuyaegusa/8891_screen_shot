# models.py

## 概要
エージェントシステムで使用するデータモデル定義

## 主要クラス

### ActionStep
1操作ステップを表すデータクラス

- 入力フィールド:
  - action_type: str - 操作種別 (click, type_key, activate_app 等)
  - target_app: str - 対象アプリケーション名
  - target_element: str - 対象UI要素
  - x: int - X座標
  - y: int - Y座標
  - keycode: str - キーコード
  - modifiers: List[str] - 修飾キー
  - text: str - 入力テキスト
- 出力: なし（データ保持用）

### Workflow
ワークフロー定義

- 入力フィールド:
  - workflow_id: str - ワークフロー識別子
  - name: str - ワークフロー名
  - steps: List[ActionStep] - 操作ステップ一覧
  - confidence: float - 信頼度スコア
- 出力: なし（データ保持用）

### ExecutionContext
実行コンテキスト

- 入力フィールド:
  - goal: str - 達成目標
  - dry_run: bool - ドライラン実行フラグ
  - max_steps: int - 最大ステップ数
- 出力: なし（データ保持用）

### ExecutionResult
実行結果

- 入力フィールド:
  - success: bool - 成功フラグ
  - steps_executed: int - 実行ステップ数
  - goal_achieved: bool - 目標達成フラグ
  - error: str - エラーメッセージ
- 出力: なし（データ保持用）

## 依存
- dataclasses (標準ライブラリ)

## 使用例
```python
from models import ActionStep, Workflow, ExecutionContext, ExecutionResult

step = ActionStep(action_type="click", x=100, y=200, target_app="Safari")
workflow = Workflow(workflow_id="wf_001", name="ブラウザ操作", steps=[step], confidence=0.95)
ctx = ExecutionContext(goal="Safariでページを開く", dry_run=False, max_steps=10)
result = ExecutionResult(success=True, steps_executed=3, goal_achieved=True)
```
