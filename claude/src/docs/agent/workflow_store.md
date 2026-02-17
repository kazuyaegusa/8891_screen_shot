# workflow_store.py

## 概要
ワークフローの永続化・検索・管理を行うストアモジュール

## 主要クラス

### WorkflowStore(workflow_dir)
- 入力: workflow_dir: str - ワークフロー保存ディレクトリパス

## 主要関数/メソッド

### save(workflow)
- 入力: workflow: Workflow - 保存するワークフロー
- 出力: str - 保存先ファイルパス
- 説明: ワークフローをJSON形式でファイルに保存する

### get(workflow_id)
- 入力: workflow_id: str - ワークフローID
- 出力: Workflow | None - 見つかった場合Workflow、なければNone
- 説明: IDでワークフローを取得する

### list_all()
- 入力: なし
- 出力: List[Workflow] - 全ワークフローのリスト
- 説明: 保存されている全ワークフローを一覧取得する

### search(query)
- 入力: query: str - 検索クエリ文字列
- 出力: List[Workflow] - マッチしたワークフローのリスト
- 説明: ワークフロー名やステップ内容でキーワード検索する

### delete(workflow_id)
- 入力: workflow_id: str - 削除対象ワークフローID
- 出力: bool - 削除成功ならTrue
- 説明: 指定IDのワークフローを削除する

## 依存
- models (Workflow)
- json (標準ライブラリ)
- os (標準ライブラリ)

## 使用例
```python
from workflow_store import WorkflowStore
from models import Workflow, ActionStep

store = WorkflowStore("./workflows")

# 保存
step = ActionStep(action_type="click", x=100, y=200)
wf = Workflow(workflow_id="wf_001", name="テスト操作", steps=[step], confidence=0.9)
path = store.save(wf)

# 取得
wf = store.get("wf_001")

# 一覧
all_wf = store.list_all()

# 検索
results = store.search("テスト")

# 削除
store.delete("wf_001")
```
