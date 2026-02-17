# state_observer.py

## 概要
現在のmacOS画面状態を観測するオブザーバーモジュール

## 主要クラス

### StateObserver(config)
- 入力: config: AgentConfig - エージェント設定

## 主要関数/メソッド

### observe_current_state()
- 入力: なし
- 出力: Dict - {"app": str, "screenshot_path": str}
- 説明: 現在のアクティブアプリとスクリーンショットを取得する

### observe_at_position(x, y)
- 入力:
  - x: int - X座標
  - y: int - Y座標
- 出力: Dict - {"app": str, "element": Dict, "coordinates": Tuple[int, int]}
- 説明: 指定座標のUI要素情報を取得する

### take_screenshot(prefix)
- 入力: prefix: str - ファイル名プレフィックス
- 出力: str - 保存されたスクリーンショットのファイルパス
- 説明: 現在の画面をスクリーンショットとして保存する

### get_visible_elements(pid)
- 入力: pid: int - プロセスID
- 出力: List[Dict] - 表示中のUI要素リスト
- 説明: 指定プロセスの可視UI要素一覧を取得する

## 依存
- config (AgentConfig)
- subprocess
- Quartz / AppKit

## 使用例
```python
from state_observer import StateObserver
from config import AgentConfig

observer = StateObserver(AgentConfig())
state = observer.observe_current_state()
print(state["app"])              # "Safari"
print(state["screenshot_path"])  # "/tmp/screenshot_xxx.png"

detail = observer.observe_at_position(500, 300)
print(detail["element"])  # {"role": "AXButton", "title": "OK"}
```
