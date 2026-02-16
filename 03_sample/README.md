# Screen Action Recorder

macOSの画面操作を記録・再生するツール。Accessibility APIを活用し、座標ベースではなく**要素識別子ベース**で再生することで、ウィンドウ位置の変化にも対応。

## 特徴

- **スマートな再生**: ボタンの位置が変わっても、名前(identifier)で探して正しくクリック
- **スクリーンショット付き記録**: 各クリック時点の画面を自動保存
- **JSON形式**: 記録データは編集・組み替え可能

## クイックスタート

### 必要条件

- macOS
- Python 3.9+
- アクセシビリティ権限（システム設定 > プライバシーとセキュリティ > アクセシビリティ）
- 入力監視権限（キーボード記録時）

### インストール

```bash
pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz pyobjc-framework-ApplicationServices
```

### 使い方

**1. 操作を記録**

```bash
python3 mvp_click_recorder.py
# 画面をクリックして操作 → Ctrl+C で終了
# → mvp_output/session_YYYYMMDD_HHMMSS.json に保存
```

**2. 記録を再生**

```bash
# シミュレーション（実際にはクリックしない）
python3 mvp_action_player.py mvp_output/session_xxx.json --dry-run

# 本番実行
python3 mvp_action_player.py mvp_output/session_xxx.json

# オプション
python3 mvp_action_player.py session.json --delay 2.0  # 待機時間を2秒に
python3 mvp_action_player.py session.json --start 3    # 4番目から開始
```

## 記録されるデータ

```json
{
  "action_id": "f565a938",
  "action_type": "left_click",
  "coordinates": {"x": 571.47, "y": 67.75},
  "app": {
    "name": "システム設定",
    "bundle_id": "com.apple.systempreferences"
  },
  "element": {
    "role": "AXButton",
    "identifier": "go back",
    "description": "戻る",
    "frame": {"x": 380, "y": 60, "width": 32, "height": 28}
  },
  "screenshot_path": "screenshots/xxx.png"
}
```

## 要素検索の優先順位

再生時、以下の順序で要素を探します：

1. `identifier` 一致 → frame中心をクリック
2. `value` 一致 → frame中心をクリック
3. `description` 一致 → frame中心をクリック
4. `title` + `role` 一致 → frame中心をクリック
5. `role` のみ一致 → 記録座標をクリック
6. フォールバック → 記録座標をクリック

## プロジェクト構成

```
├── mvp_click_recorder.py   # 記録ツール
├── mvp_action_player.py    # 再生ツール
├── docs/
│   ├── SCREEN_ACTION_RECORDER_DESIGN.md   # 設計書
│   └── SCREEN_ACTION_RECORDER_SUMMARY.md  # 技術サマリー
├── skills/                 # 既存のhomerowスキル群
│   ├── homerow/
│   ├── app-automation/
│   ├── line-scan/
│   ├── line-export/
│   ├── discord/
│   └── slack-automation/
└── mvp_output/             # 記録出力先
    ├── *.json              # セッションデータ
    └── screenshots/        # スクリーンショット（.gitignore）
```

## 技術詳細

- **イベント監視**: `CGEventTap` (Quartz)
- **UI要素取得**: `AXUIElement` (Accessibility API)
- **クリック実行**: `CGEventCreateMouseEvent`

詳細は [docs/SCREEN_ACTION_RECORDER_SUMMARY.md](docs/SCREEN_ACTION_RECORDER_SUMMARY.md) を参照。

## 今後の予定

- [ ] キーボード入力の統合テスト（V6）
- [ ] 要素出現待機（Wait Until Visible）
- [ ] AI画像認識によるフォールバック
- [ ] ブラウザ内要素対応
- [ ] スキルエディタ（GUI）

## ライセンス

MIT
