# input_overlay.py API仕様

ビデオフレーム（numpy配列）にマウスクリック・キーボード操作のオーバーレイを描画するモジュール。

## クラス: InputOverlay

### コンストラクタ

```python
InputOverlay(click_lifetime=0.8, key_lifetime=1.5, max_keys=5)
```

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| click_lifetime | float | 0.8 | クリックエフェクトの表示秒数 |
| key_lifetime | float | 1.5 | キーラベルの表示秒数 |
| max_keys | int | 5 | 同時表示するキーラベルの最大数 |

### メソッド

#### `add_click(x, y, button="left")`

クリックイベントを追加する（スレッドセーフ）。

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| x | int | クリック位置 X座標（ピクセル） |
| y | int | クリック位置 Y座標（ピクセル） |
| button | str | "left" or "right" |

**出力**: なし

#### `add_key(key_text)`

キーボードイベントを追加する（スレッドセーフ）。

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| key_text | str | 表示するキーテキスト（例: "a", "Cmd+C", "Enter"） |

**出力**: なし

#### `draw(frame) -> np.ndarray`

フレームにアクティブなイベントのオーバーレイを描画して返す。

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| frame | np.ndarray | BGR形式の numpy 配列（cv2フレーム） |

**出力**: オーバーレイ描画済みの numpy 配列

### 描画仕様

| イベント | 描画 | 色 |
|---------|------|-----|
| 左クリック | 塗りつぶし円(r=16) + 拡大波紋リング | 赤 (BGR: 0,0,255) |
| 右クリック | 塗りつぶし円(r=16) + 拡大波紋リング | 緑 (BGR: 0,255,0) |
| キー入力 | 画面右下に背景付きテキストラベル | 白文字 + 暗灰色背景 |

## データクラス: VisualEvent

```python
@dataclass
class VisualEvent:
    event_type: str   # "click" or "key"
    x: int = 0
    y: int = 0
    button: str = ""
    key_text: str = ""
    created_at: float = time.time()
    lifetime: float = 1.0
```

## 依存パッケージ

- `opencv-python` または `opencv-python-headless`
- `numpy`
