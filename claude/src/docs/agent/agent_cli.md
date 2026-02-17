# agent_cli.py

## 概要
エージェントシステムのCLIエントリーポイント

## サブコマンド

### learn
- 入力: --json-dir: str - 操作ログJSONディレクトリパス
- 出力: 抽出されたワークフロー一覧（標準出力）
- 説明: JSON操作ログからワークフローを自動抽出して保存する

### list
- 入力: なし
- 出力: 保存済みワークフロー一覧（標準出力）
- 説明: 保存されている全ワークフローを一覧表示する

### run
- 入力:
  - --goal: str - 達成目標テキスト
  - --dry-run: bool - ドライラン実行フラグ
  - --max-steps: int - 最大ステップ数
- 出力: 実行結果（標準出力）
- 説明: 目標を指定して自律実行ループを開始する

### play
- 入力:
  - --workflow-id: str - 再生するワークフローID
  - --dry-run: bool - ドライランフラグ
  - --delay: float - ステップ間の待機秒数
- 出力: 再生結果（標準出力）
- 説明: 保存済みワークフローを再生する

## 依存
- argparse (標準ライブラリ)
- config (AgentConfig)
- autonomous_loop (AutonomousLoop)
- workflow_extractor (WorkflowExtractor)
- workflow_store (WorkflowStore)
- models (ExecutionContext)

## 使用例
```python
# ワークフロー学習
python agent_cli.py learn --json-dir ./data/json

# ワークフロー一覧
python agent_cli.py list

# 自律実行
python agent_cli.py run --goal "Safariでgoogle.comを開く" --max-steps 20

# ワークフロー再生（ドライラン）
python agent_cli.py play --workflow-id wf_001 --dry-run --delay 1.0
```
