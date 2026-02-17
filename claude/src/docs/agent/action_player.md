# action_player.py

## 概要
ActionStepを実際のmacOS操作として実行するプレイヤーモジュール

## 主要クラス

### ActionPlayer
操作ステップを実行するクラス

## 主要関数/メソッド

### play_action_step(step, dry_run)
- 入力:
  - step: ActionStep - 実行する操作ステップ
  - dry_run: bool - Trueの場合、実際の操作を行わずログのみ出力
- 出力: Dict - 実行結果 {"success": bool, "action": str, "error": str}
- 説明: 1つのActionStepを実行する

### play_steps(steps, dry_run, delay)
- 入力:
  - steps: List[ActionStep] - 実行する操作ステップ一覧
  - dry_run: bool - ドライランフラグ
  - delay: float - ステップ間の待機秒数
- 出力: List[Dict] - 各ステップの実行結果リスト
- 説明: 複数ステップを順番に実行する

### play_action(action_dict, dry_run)
- 入力:
  - action_dict: Dict - アクション辞書 (legacy形式)
  - dry_run: bool - ドライランフラグ
- 出力: Dict - 実行結果
- 説明: レガシー辞書形式のアクションを実行する（後方互換用）

### find_element_by_criteria(criteria) [内部関数]
- 入力: criteria: Dict - UI要素の検索条件
- 出力: 要素の座標情報
- 説明: Accessibility APIで対象UI要素を検索する

### click_at(x, y) [内部関数]
- 入力: x: int, y: int - クリック座標
- 出力: なし
- 説明: 指定座標をクリックする

### type_key(keycode, modifiers) [内部関数]
- 入力: keycode: str, modifiers: List[str] - キーと修飾キー
- 出力: なし
- 説明: キー入力を実行する

### activate_app(app_name) [内部関数]
- 入力: app_name: str - アプリケーション名
- 出力: なし
- 説明: 指定アプリをアクティブにする

## 依存
- models (ActionStep)
- subprocess
- pyautogui

## 使用例
```python
from action_player import ActionPlayer
from models import ActionStep

player = ActionPlayer()
step = ActionStep(action_type="click", x=100, y=200)
result = player.play_action_step(step, dry_run=False)
print(result)  # {"success": True, "action": "click", "error": None}
```
