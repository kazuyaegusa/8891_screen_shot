# action_selector.py

## 概要
ワークフローまたは自律判断で次の操作を選択するセレクターモジュール

## 主要クラス

### ActionSelector(config)
- 入力: config: AgentConfig - エージェント設定

## 主要関数/メソッド

### select_from_workflow(workflow, step_index, state, params)
- 入力:
  - workflow: Workflow - 実行中のワークフロー
  - step_index: int - 現在のステップインデックス
  - state: Dict - 現在の画面状態
  - params: Dict - 実行パラメータ
- 出力: ActionStep | None - 次に実行するステップ、なければNone
- 説明: ワークフローから現在の状態に適合する次のステップを選択する

### select_autonomous(goal, state, history)
- 入力:
  - goal: str - 達成目標テキスト
  - state: Dict - 現在の画面状態
  - history: List[Dict] - これまでの実行履歴
- 出力: Dict | None - 次に実行するアクション辞書、なければNone
- 説明: LLMを使って目標達成のための次のアクションを自律的に決定する

### action_dict_to_step(action, app_info)
- 入力:
  - action: Dict - アクション辞書
  - app_info: Dict - アプリケーション情報
- 出力: ActionStep - 変換されたActionStep
- 説明: 辞書形式のアクションをActionStepオブジェクトに変換する

## 依存
- models (ActionStep, Workflow)
- config (AgentConfig)
- openai

## 使用例
```python
from action_selector import ActionSelector
from config import AgentConfig

selector = ActionSelector(AgentConfig())

# ワークフローからステップ選択
step = selector.select_from_workflow(workflow, step_index=0, state=current_state, params={})

# 自律的なアクション選択
action = selector.select_autonomous(
    goal="Safariで検索する",
    state=current_state,
    history=[]
)
```
