# workflow_extractor.py

## 概要
記録済みJSON操作ログからワークフローを自動抽出するモジュール

## 主要クラス

### WorkflowExtractor(json_dir, workflow_dir, model, min_confidence)
- 入力:
  - json_dir: str - 操作ログJSONが格納されたディレクトリパス
  - workflow_dir: str - 抽出ワークフローの保存先ディレクトリ
  - model: str - 使用するLLMモデル名
  - min_confidence: float - 最小信頼度閾値（これ未満のワークフローは除外）

## 主要関数/メソッド

### extract_all()
- 入力: なし
- 出力: List[Workflow] - 抽出されたワークフローのリスト
- 説明: json_dir内の全操作ログを解析し、ワークフローを抽出・保存する

### build_segments()
- 入力: なし
- 出力: List[Dict] - 操作セグメントのリスト
- 説明: 操作ログを時間的・文脈的に意味のあるセグメントに分割する

## 依存
- models (Workflow, ActionStep)
- workflow_store (WorkflowStore)
- openai
- json (標準ライブラリ)

## 使用例
```python
from workflow_extractor import WorkflowExtractor

extractor = WorkflowExtractor(
    json_dir="./data/json",
    workflow_dir="./workflows",
    model="gpt-4o",
    min_confidence=0.7
)

# 全操作ログからワークフローを抽出
workflows = extractor.extract_all()
print(f"{len(workflows)}件のワークフローを抽出")

# セグメント分割のみ
segments = extractor.build_segments()
for seg in segments:
    print(seg)
```
