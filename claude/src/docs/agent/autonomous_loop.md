# autonomous_loop.py

## 概要
観測→判断→実行→検証のサイクルを自律的に繰り返すメインループモジュール

## 主要クラス

### AutonomousLoop(config)
- 入力: config: AgentConfig - エージェント設定

## 主要関数/メソッド

### run(ctx)
- 入力: ctx: ExecutionContext - 実行コンテキスト (goal, dry_run, max_steps)
- 出力: ExecutionResult - 実行結果 (success, steps_executed, goal_achieved)
- 説明: 目標達成まで observe → select → play → verify のループを繰り返す。max_steps到達またはゴール達成で終了。

### play_workflow(workflow_id, dry_run, delay, params)
- 入力:
  - workflow_id: str - 実行するワークフローID
  - dry_run: bool - ドライランフラグ
  - delay: float - ステップ間の待機秒数
  - params: Dict - 実行パラメータ
- 出力: ExecutionResult - 実行結果
- 説明: 保存済みワークフローをステップごとに再生する

## 依存
- models (ExecutionContext, ExecutionResult)
- config (AgentConfig)
- state_observer (StateObserver)
- action_selector (ActionSelector)
- action_player (ActionPlayer)
- execution_verifier (ExecutionVerifier)
- workflow_store (WorkflowStore)

## 使用例
```python
from autonomous_loop import AutonomousLoop
from models import ExecutionContext
from config import AgentConfig

loop = AutonomousLoop(AgentConfig())

# 自律実行
ctx = ExecutionContext(goal="Safariでgoogle.comを開く", dry_run=False, max_steps=20)
result = loop.run(ctx)
print(f"成功: {result.success}, ステップ数: {result.steps_executed}")

# ワークフロー再生
result = loop.play_workflow("wf_001", dry_run=True, delay=1.0, params={})
print(f"ゴール達成: {result.goal_achieved}")
```
