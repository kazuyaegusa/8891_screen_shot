# action_player.py

ActionStep モデル対応のアクション再生モジュール。

## インプット

### `ActionPlayer.play_action_step(step, dry_run)`
- `step: ActionStep` - 実行する操作ステップ
- `dry_run: bool` - True で実際の操作をスキップ

### `ActionPlayer.play_steps(steps, dry_run, delay)`
- `steps: List[ActionStep]` - 実行するステップのリスト
- `dry_run: bool` - True で実際の操作をスキップ
- `delay: float` - 各ステップ間の待機秒数（デフォルト: 1.0）

### `ActionPlayer.play_action(action, dry_run)` (レガシー)
- `action: Dict[str, Any]` - mvp 形式のアクション辞書
- `dry_run: bool` - True で実際の操作をスキップ

## アウトプット

### 実行結果 `Dict[str, Any]`
```python
{
    "action_id": str,          # アクション識別子
    "success": bool,           # 成功/失敗
    "method": str,             # 要素検索方法 (identifier_match_at_position, value_match_at_position, etc.)
    "coordinates_used": {      # 実際にクリックした座標
        "x": float,
        "y": float,
    },
    "error": Optional[str],    # エラーメッセージ
    "dry_run": Optional[bool], # dry_run 時に True
}
```

## 関数一覧

| 関数 | 説明 |
|------|------|
| `ActionPlayer.__init__()` | プレイヤー初期化 |
| `ActionPlayer.play_action_step(step, dry_run)` | ActionStep を再生 |
| `ActionPlayer.play_steps(steps, dry_run, delay)` | ステップリストを順次再生 |
| `ActionPlayer._action_step_to_legacy_action(step)` | ActionStep を mvp Dict 形式に変換 |
| `ActionPlayer._find_element_with_vision_fallback(step, screenshot_path)` | Vision フォールバック（Phase 4 スタブ） |
| `get_ax_attribute(element, attr)` | AX属性を取得 |
| `get_element_frame(element)` | 要素のフレーム取得 |
| `activate_app(bundle_id)` | アプリをアクティブ化 |
| `click_at(x, y, button)` | 指定座標をクリック |
| `normalize_flags(flags)` | キーフラグを正規化 |
| `type_key(keycode, flags, delay)` | キー入力 |
| `play_key_action(action, dry_run)` | キー系アクションを再生 |
| `search_all_elements(app_element, max_depth)` | アプリ内全要素を再帰検索 |
| `find_element_by_criteria(target, tolerance)` | 要素を属性で検索 |
| `play_action(action, dry_run)` | レガシー Dict 形式のアクション再生 |

## 依存

- `agent.models.ActionStep`
- macOS: Quartz, ApplicationServices, AppKit
