# execution_verifier.py

## 概要
操作実行後の状態変化を検証するベリファイアモジュール。
AI検証が実行できない場合は `verified=False` を返し、偽の成功判定を防止する。

## 主要クラス

### ExecutionVerifier(config)
- 入力: config: AgentConfig - エージェント設定

## 主要関数/メソッド

### verify_step(before_ss, after_ss, expected_change, dry_run)
- 入力:
  - before_ss: str - 実行前スクリーンショットのパス
  - after_ss: str - 実行後スクリーンショットのパス
  - expected_change: str - 期待される状態変化の説明
  - dry_run: bool - ドライランの場合は検証をスキップ
- 出力: Dict
  - `verified=True` の場合: `{"success": bool, "confidence": float, "verified": True, "reasoning": str}`
    → AI検証が正常実行された。success の値を信頼してよい
  - `verified=False` の場合: `{"success": False, "confidence": 0.0, "verified": False, "reasoning": str}`
    → 検証不可。呼び出し側はアクション実行結果をそのまま使うべき
- 検証不可の原因:
  - dry-run モード
  - スクリーンショット未取得
  - OPENAI_API_KEY 未設定
  - AIClient 初期化失敗
  - API 呼び出しエラー

### check_goal(goal, state, history)
- 入力:
  - goal: str - 達成目標テキスト
  - state: Dict - 現在の画面状態
  - history: List[Dict] - 実行履歴
- 出力: Dict - {"achieved": bool, "confidence": float, "reasoning": str}
- 説明: 目標が達成されたかをLLMで判定する

## 設計方針

**旧設計の問題**: エラー時に `success=True` を返していたため、API未設定・SS未取得でも
「検証成功」としてフィードバックに記録され、再現性スコアが不正に高くなっていた。

**新設計**: `verified` フラグで「検証が実行されたか」と「検証結果」を分離。
呼び出し側（autonomous_loop）は `verified=True` の場合のみAI判定で成否を上書きする。

## 依存
- agent.config (AgentConfig)
- pipeline.ai_client (AIClient)
- 環境変数: OPENAI_API_KEY

## 使用例
```python
from agent.execution_verifier import ExecutionVerifier
from agent.config import AgentConfig

verifier = ExecutionVerifier(AgentConfig())

result = verifier.verify_step(
    before_screenshot="/tmp/before.png",
    after_screenshot="/tmp/after.png",
    expected_change="ゴミ箱ウィンドウが表示される",
)

if result["verified"]:
    # AI検証が実行された → AI判定を信頼
    print(f"AI判定: success={result['success']}")
else:
    # 検証不可 → アクション実行結果をそのまま使う
    print(f"検証スキップ: {result['reasoning']}")
```
