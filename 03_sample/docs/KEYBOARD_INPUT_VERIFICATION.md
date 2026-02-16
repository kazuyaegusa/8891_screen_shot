# キーボード入力機能 - 検証計画と結果

> 作成日: 2026-02-06
> 検証実施日: 2026-02-06
> 更新日: 2026-02-07
> 前提: MVP Click Recorder (Phase 1-2) 完了済み

---

## 目的

`mvp_click_recorder.py` にキーボード入力の記録機能を追加し、`mvp_action_player.py` で再生できるようにする。これにより、テスト計画のB2(LINE入力), C1(Safari URL), D1(Numbers), E4(ショートカットキー)が実行可能になる。

---

## 検証結果サマリ

| Step | 内容 | 結果 |
|------|------|------|
| Step 1 | キーイベント基本取得 | **成功** - 全キーでkeycode+char取得 |
| Step 2 | 修飾キー取得 | **成功** - Cmd/Shift/Option/Control判別OK |
| Step 3 | 日本語入力(IME) | **パターンB** - ローマ字で取得（ひらがなではない） |
| Step 4 | キーイベント再生 | **バグあり→修正済** - Shiftフラグ固着（再テスト未実施） |
| Step 5 | レコーダー/プレイヤー統合 | **実装済み** - 記録/再生に統合（V6テスト待ち） |

### 判明した重要事項

1. **日本語入力はkeycodeベースで記録・再生可能** (IME状態が同じなら同じ結果)
2. **CGEventSetFlagsは毎回明示的に設定が必要** (flags=0x100をベースに)
3. **かなキー=keycode 104、英数切替=keycode 109** で入力ソース切替を検知可能

---

## 検証の全体像

```
Step 1: キーイベント取得の基本確認    → 成功
  ↓
Step 2: 修飾キーの取得確認            → 成功
  ↓
Step 3: 日本語入力(IME)の挙動確認     → パターンB（ローマ字取得）
  ↓
Step 4: キーイベント再生の確認         → バグ修正済、再テスト未実施
  ↓
Step 5: レコーダー/プレイヤー統合       → 実装済み（V6テスト待ち）
```

---

## Step 1: キーイベント取得の基本確認

### やること

`CGEventTap` でキーボードイベントを捕捉できるか確認する。

### 検証スクリプト

```python
#!/usr/bin/env python3
"""Step 1: キーイベント取得の基本テスト"""

from Quartz import (
    CGEventTapCreate, CGEventTapEnable,
    CFMachPortCreateRunLoopSource,
    CFRunLoopGetCurrent, CFRunLoopAddSource, CFRunLoopRun,
    CGEventGetIntegerValueField,
    CGEventKeyboardGetUnicodeString,
    kCGSessionEventTap, kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly,
    CGEventMaskBit,
    kCGEventKeyDown, kCGEventKeyUp, kCGEventFlagsChanged,
    kCGKeyboardEventKeycode,
    kCFRunLoopCommonModes,
)

def callback(proxy, event_type, event, refcon):
    if event_type == kCGEventKeyDown:
        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        # Unicode文字を取得
        length, chars = CGEventKeyboardGetUnicodeString(event, 10, None, None)
        char_str = chars if chars else ""
        print(f"KEY DOWN: keycode={keycode}, char='{char_str}', length={length}")
    elif event_type == kCGEventKeyUp:
        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        print(f"KEY UP:   keycode={keycode}")
    return event

mask = (CGEventMaskBit(kCGEventKeyDown) |
        CGEventMaskBit(kCGEventKeyUp))

tap = CGEventTapCreate(
    kCGSessionEventTap, kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly, mask, callback, None)

if tap is None:
    print("ERROR: Event tap作成失敗。Accessibility権限を確認")
    exit(1)

print("=== Step 1: キーイベント基本テスト ===")
print("キーボードを押してください。Ctrl+C で終了。")
print()

src = CFMachPortCreateRunLoopSource(None, tap, 0)
CFRunLoopAddSource(CFRunLoopGetCurrent(), src, kCFRunLoopCommonModes)
CGEventTapEnable(tap, True)

try:
    CFRunLoopRun()
except KeyboardInterrupt:
    print("\n終了")
```

### 確認ポイント

| # | 確認事項 | 期待結果 |
|---|----------|----------|
| 1-1 | 英字キー (a, b, c...) を押す | keycode と char が表示される |
| 1-2 | 数字キー (1, 2, 3...) を押す | keycode と char が表示される |
| 1-3 | Enterキーを押す | keycode=36 が表示される |
| 1-4 | Tabキーを押す | keycode=48 が表示される |
| 1-5 | Deleteキーを押す | keycode=51 が表示される |
| 1-6 | 矢印キーを押す | keycodeが表示される (上=126,下=125,左=123,右=124) |
| 1-7 | KEY DOWN と KEY UP が対で出る | 各キーで2行表示される |

### 成功基準

全ての英数字キー、Enter、Tab、矢印キーで `keycode` と `char` が取得できること。

### 実測結果 (2026-02-06 13:00)

**判定: 成功**

- 英字 a(keycode=0), b(11), c(8): char取得OK
- Enter(36), Tab(48), ForwardDelete(117): 全てOK
- 矢印 Up(126), Down(125), Left(123), Right(124): 全てOK
- Space(49): OK
- KEY_DOWN / KEY_UP が全て対で出力
- 合計23イベント検出（Ctrl+C含む）

---

## Step 2: 修飾キーの取得確認

### やること

Cmd, Shift, Option, Control キーの状態を取得できるか確認する。

### 検証スクリプト

```python
#!/usr/bin/env python3
"""Step 2: 修飾キーテスト"""

from Quartz import (
    CGEventTapCreate, CGEventTapEnable,
    CFMachPortCreateRunLoopSource,
    CFRunLoopGetCurrent, CFRunLoopAddSource, CFRunLoopRun,
    CGEventGetIntegerValueField, CGEventGetFlags,
    CGEventKeyboardGetUnicodeString,
    kCGSessionEventTap, kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly,
    CGEventMaskBit,
    kCGEventKeyDown, kCGEventFlagsChanged,
    kCGKeyboardEventKeycode,
    kCFRunLoopCommonModes,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
)

def get_modifiers(event):
    """修飾キーのフラグを解析"""
    flags = CGEventGetFlags(event)
    mods = []
    if flags & kCGEventFlagMaskCommand:
        mods.append("Cmd")
    if flags & kCGEventFlagMaskShift:
        mods.append("Shift")
    if flags & kCGEventFlagMaskAlternate:
        mods.append("Option")
    if flags & kCGEventFlagMaskControl:
        mods.append("Control")
    return mods

def callback(proxy, event_type, event, refcon):
    if event_type == kCGEventKeyDown:
        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        length, chars = CGEventKeyboardGetUnicodeString(event, 10, None, None)
        mods = get_modifiers(event)
        flags = CGEventGetFlags(event)
        mod_str = "+".join(mods) if mods else "(none)"
        char_str = chars if chars else ""
        print(f"KEY: {mod_str}+keycode={keycode} char='{char_str}' flags=0x{flags:x}")
    elif event_type == kCGEventFlagsChanged:
        mods = get_modifiers(event)
        flags = CGEventGetFlags(event)
        print(f"FLAGS CHANGED: {mods} flags=0x{flags:x}")
    return event

mask = (CGEventMaskBit(kCGEventKeyDown) |
        CGEventMaskBit(kCGEventFlagsChanged))

tap = CGEventTapCreate(
    kCGSessionEventTap, kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly, mask, callback, None)

if tap is None:
    print("ERROR: Event tap作成失敗")
    exit(1)

print("=== Step 2: 修飾キーテスト ===")
print("以下を試してください:")
print("  1. Cmd+C (コピー)")
print("  2. Cmd+V (ペースト)")
print("  3. Cmd+Shift+S (別名保存)")
print("  4. Cmd+Tab (アプリ切替)")
print("Ctrl+C で終了。")
print()

src = CFMachPortCreateRunLoopSource(None, tap, 0)
CFRunLoopAddSource(CFRunLoopGetCurrent(), src, kCFRunLoopCommonModes)
CGEventTapEnable(tap, True)

try:
    CFRunLoopRun()
except KeyboardInterrupt:
    print("\n終了")
```

### 確認ポイント

| # | 確認事項 | 期待結果 |
|---|----------|----------|
| 2-1 | Cmd+C を押す | `Cmd+keycode=8 char='c'` |
| 2-2 | Cmd+V を押す | `Cmd+keycode=9 char='v'` |
| 2-3 | Cmd+Shift+S を押す | `Cmd+Shift+keycode=1` |
| 2-4 | Cmd単体を押す | `FLAGS CHANGED: ['Cmd']` (押下時) + `FLAGS CHANGED: []` (離した時) |
| 2-5 | Shift+A を押す | `Shift+keycode=0 char='A'` |
| 2-6 | Option+数字 を押す | `Option+keycode=... char='特殊文字'` |

### 成功基準

- 修飾キーの組み合わせが正しく判別できること
- `kCGEventFlagsChanged` で修飾キー単体の押下/離しが検知できること

### 実測結果 (2026-02-06 13:01)

**判定: 成功**

| 操作 | 検出結果 |
|------|----------|
| Cmd+C | `modifiers=[Cmd] keycode=8 char='c' flags=0x00100108` |
| Cmd+V | `modifiers=[Cmd] keycode=9 char='v' flags=0x00100108` |
| Cmd+A | `modifiers=[Cmd] keycode=0 char='a' flags=0x00100108` |
| Cmd+Shift+S | `modifiers=[Cmd+Shift] keycode=1 char='s' flags=0x0012010a` |
| Cmd単体 | FLAGS `[Cmd] 0x00100108` → FLAGS `[(none)] 0x00000100` (対で検出) |
| Shift+A | `modifiers=[Shift] keycode=0 char='A' flags=0x00020102` |
| Option+J | `modifiers=[Option] keycode=38 char='∆' flags=0x00080120` |
| Control+C | `modifiers=[Control] keycode=8 char='\x03' flags=0x00040101` |

- 合計37イベント検出
- 全修飾キー（Cmd/Shift/Option/Control）が正しく判別可能
- FLAGS_CHANGED イベントで修飾キー単体の押下/離しも検知可能
- flags の数値からビット演算で修飾キーを復元可能

---

## Step 3: 日本語入力(IME)の挙動確認

### やること

日本語IMEがONの状態でのキーイベントの挙動を確認する。

### 確認ポイント

| # | 確認事項 | 確認内容 |
|---|----------|----------|
| 3-1 | ひらがなモードで「あ」を入力 | keycodeとcharがどう出るか |
| 3-2 | 「にほんご」と入力（変換前） | イベントが各キーごとに出るか |
| 3-3 | スペースキーで変換 | 変換候補選択時のイベント |
| 3-4 | Enterで確定 | 確定時のイベント |
| 3-5 | 直接入力(英数)と日本語入力の切替 | flagsの変化 |

### 想定される3つのパターン

**パターンA: keycode + IME変換後テキスト取得可能**
→ 最も望ましい。keycode記録 + テキスト記録の両方が可能。

**パターンB: keycodeのみ取得、変換後テキストは取得不可**
→ keycode再生で対応可能だが、変換結果が環境依存になる。

**パターンC: IME変換中はキーイベントが来ない**
→ テキスト入力は別アプローチ（直接テキスト注入）が必要。

### 判断基準

- パターンAの場合 → そのまま実装に進む
- パターンB/Cの場合 → Step 3b（テキスト注入方式の検討）を追加

### 実測結果 (2026-02-06 13:03)

**判定: パターンB（keycodeのみ取得、ひらがなは取得不可）**

| 操作 | 検出結果 |
|------|----------|
| かなキー押下 | `keycode=104 (Kana) char=' '` |
| 「あ」入力 (IME ON) | `keycode=0 char='a'` (**ひらがなではなくローマ字**) |
| Enter (確定) | `keycode=36 char='\r'` |
| 「にほん」入力 | `n(45), i(34), h(4), o(31), n(45)` 全てローマ字 |
| Space (変換) | `keycode=49 char=' '` |
| Enter (確定) | `keycode=36 char='\r'` |
| 英数切替 | `keycode=109 char='\x10' flags=0x00800100` |
| 英語「hello」入力 | `h(4), e(14), l(37), l(37), o(31)` 正常 |

**重要な発見:**
- CGEventTapはIME処理前の**生キーコード（ローマ字）**を捕捉する
- ひらがなや変換後のテキストはcharには入らない
- しかし、keycodeをそのまま再生すれば**IMEが同じ状態なら同じ日本語が入力される**
- かなキー(104)と英数切替キー(109)で入力ソースの切替を記録・再現可能
- 合計52イベント検出

**実装方針:** keycodeベースの記録・再生で十分対応可能。入力ソース切替キーも記録する。

---

## Step 4: キーイベント再生の確認

### やること

`CGEventCreateKeyboardEvent` でキーボード入力を再現できるか確認する。

### 検証スクリプト

```python
#!/usr/bin/env python3
"""Step 4: キー再生テスト
実行前にテキストエディットを開いてフォーカスしてください
"""

import time
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGHIDEventTap,
    kCGEventFlagMaskCommand,
)

def type_key(keycode, flags=0):
    """1つのキーを押して離す"""
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    if flags:
        CGEventSetFlags(down, flags)
        CGEventSetFlags(up, flags)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)
    time.sleep(0.05)

def type_string_via_keys(text):
    """文字列をキーコードで入力（英数のみ）"""
    # 基本的な文字→keycode マッピング
    keymap = {
        'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3,
        'g': 5, 'h': 4, 'i': 34, 'j': 38, 'k': 40, 'l': 37,
        'm': 46, 'n': 45, 'o': 31, 'p': 35, 'q': 12, 'r': 15,
        's': 1, 't': 17, 'u': 32, 'v': 9, 'w': 13, 'x': 7,
        'y': 16, 'z': 6,
        '1': 18, '2': 19, '3': 20, '4': 21, '5': 23,
        '6': 22, '7': 26, '8': 28, '9': 25, '0': 29,
        ' ': 49, '\n': 36, '\t': 48,
        '.': 47, ',': 43, '/': 44, '-': 27, '=': 24,
    }
    for ch in text:
        lower = ch.lower()
        if lower in keymap:
            flags = kCGEventFlagMaskCommand if False else 0
            if ch.isupper():
                # Shift + key
                type_key(keymap[lower], 0x20002)  # kCGEventFlagMaskShift
            else:
                type_key(keymap[lower])
        else:
            print(f"  [skip] unmapped char: '{ch}'")

print("=== Step 4: キー再生テスト ===")
print("3秒後にテキストエディットに「Hello World」を入力します。")
print("テキストエディットを開いてフォーカスしてください。")
time.sleep(3)

# テスト1: 英字入力
print("テスト1: 'Hello World' を入力...")
type_string_via_keys("Hello World")
print("  完了")
time.sleep(1)

# テスト2: Enter
print("テスト2: Enterキー...")
type_key(36)  # Enter
print("  完了")
time.sleep(1)

# テスト3: Cmd+A (全選択)
print("テスト3: Cmd+A (全選択)...")
type_key(0, kCGEventFlagMaskCommand)
print("  完了")
time.sleep(1)

print("\n=== テスト完了 ===")
print("テキストエディットに 'Hello World' が入力され、全選択されたか確認してください。")
```

### 確認ポイント

| # | 確認事項 | 期待結果 |
|---|----------|----------|
| 4-1 | 英字 "Hello World" が入力される | テキストエディットに表示 |
| 4-2 | Enterキーが機能する | 改行される |
| 4-3 | Cmd+A で全選択される | テキスト全体がハイライト |
| 4-4 | 入力速度は自然か | 各キー間0.05秒で問題ないか |
| 4-5 | 大文字(Shift+key)が正しく入力される | 'H'と'W'が大文字 |

### 成功基準

英数字テキストの入力と修飾キー付きショートカットが正しく再生されること。

### 実測結果 (2026-02-06 13:03)

**判定: バグあり → 修正済み**

実行結果:
- 期待: `Hello World` → 実際: `HELLO WORLD` (全て大文字)
- 期待: `12345.67` → 実際: `!@#$%>^&` (全てShift付き記号)

**原因:** `CGEventSetFlags` を `flags=0` の場合に呼ばなかったため、
'H' 入力時に設定した Shift フラグが後続の全キーに固着した。

**修正内容:** `scripts/keyboard/keyboard_test_step4.py` を修正
- `flags` のデフォルト値を `0x100`（ベースフラグ）に変更
- `CGEventSetFlags` を毎回必ず呼び出すように変更
- Shift付きキーは `kCGEventFlagMaskShift | 0x100` を設定

```python
# 修正前（バグ）
def type_key(keycode, flags=0, delay=0.03):
    ...
    if flags:  # flags=0 だと呼ばれない！
        CGEventSetFlags(down, flags)

# 修正後
BASE_FLAGS = 0x100
def type_key(keycode, flags=None, delay=0.03):
    if flags is None:
        flags = BASE_FLAGS
    ...
    CGEventSetFlags(down, flags)  # 常に呼ぶ
```

**ステータス: 修正済み、再テスト待ち**

---

## Step 5: 統合実装（2026-02-07）

Step 1〜4の結果をもとに、レコーダー・プレイヤーへの統合を実装した。

### 実装内容（要点）

- `mvp_click_recorder.py`
  - `kCGEventKeyDown` を記録対象に追加
  - 連続入力は `text_input` にまとめる
  - `key_shortcut` / `key_input` を追加
  - `flags` と `modifiers` を保存
  - かな/英数キーも記録（keycodeベース）
- `mvp_action_player.py`
  - `text_input` / `key_input` / `key_shortcut` 再生を追加
  - `BASE_FLAGS=0x100` を常にセットしてShift固着を防止

### 記録データフォーマット案

```json
{
  "action_id": "abc12345",
  "timestamp": "2026-02-06T12:30:00",
  "action_type": "key_input",
  "app": {
    "name": "テキストエディット",
    "bundle_id": "com.apple.TextEdit"
  },
  "key_event": {
    "event_type": "key_down",
    "keycode": 0,
    "character": "a",
    "modifiers": [],
    "flags": 256
  }
}
```

### ショートカットの記録フォーマット案

```json
{
  "action_type": "key_shortcut",
  "key_event": {
    "keycode": 8,
    "character": "c",
    "modifiers": ["Cmd"],
    "flags": 1048840
  }
}
```

### テキスト入力の最適化案

連続キー入力をまとめて1アクションにする:

```json
{
  "action_type": "text_input",
  "text": "Hello World",
  "key_events": [
    {"keycode": 4, "character": "H", "modifiers": ["Shift"]},
    {"keycode": 14, "character": "e", "modifiers": []},
    ...
  ]
}
```

### 判断項目（検証結果に基づく決定）

| # | 判断事項 | 決定 | 根拠 |
|---|----------|------|------|
| 5-1 | 日本語入力方式 | **keycode方式** | Step 3: ローマ字keycodeを再生すればIMEが変換 |
| 5-2 | 連続入力のまとめ | **まとめる** | Step 1: イベント頻度が高く、個別記録だとJSONが膨大 |
| 5-3 | flagsの保存形式 | **数値(flags) + 修飾キー名の両方** | Step 2: 数値は再生用、名前は可読性用 |
| 5-4 | KEY_UPの記録 | **記録しない（KEY_DOWNのみ）** | Step 1: UPは再生時に自動生成すれば十分 |

### 決定した記録データフォーマット

```json
{
  "action_id": "abc12345",
  "timestamp": "2026-02-06T12:30:00",
  "action_type": "key_input",
  "app": {
    "name": "テキストエディット",
    "bundle_id": "com.apple.TextEdit"
  },
  "key_event": {
    "keycode": 0,
    "character": "a",
    "modifiers": [],
    "flags": 256
  }
}
```

### 連続テキスト入力（最適化形式）

```json
{
  "action_id": "def67890",
  "timestamp": "2026-02-06T12:30:01",
  "action_type": "text_input",
  "app": {
    "name": "テキストエディット",
    "bundle_id": "com.apple.TextEdit"
  },
  "text": "Hello World",
  "key_events": [
    {"keycode": 4, "character": "H", "modifiers": ["Shift"], "flags": 131330},
    {"keycode": 14, "character": "e", "modifiers": [], "flags": 256},
    {"keycode": 37, "character": "l", "modifiers": [], "flags": 256}
  ]
}
```

### ショートカットキー

```json
{
  "action_id": "ghi11111",
  "timestamp": "2026-02-06T12:30:05",
  "action_type": "key_shortcut",
  "app": {
    "name": "テキストエディット",
    "bundle_id": "com.apple.TextEdit"
  },
  "key_event": {
    "keycode": 8,
    "character": "c",
    "modifiers": ["Cmd"],
    "flags": 1048840
  }
}
```

---

## 実行手順まとめ

```
検証 Step 1  →  scripts/keyboard/keyboard_test_step1.py を実行
  所要時間: 5分
  判定: keycodeとcharが取れるか

検証 Step 2  →  scripts/keyboard/keyboard_test_step2.py を実行
  所要時間: 5分
  判定: 修飾キーが判別できるか

検証 Step 3  →  Step 1のスクリプトで日本語入力を試す
  所要時間: 10分
  判定: IME挙動パターン A/B/C のどれか

検証 Step 4  →  scripts/keyboard/keyboard_test_step4.py を実行
  所要時間: 5分
  判定: キー再生が正しく動くか
  ※テキストエディットを開いて待機する

結果まとめ  →  Step 5 の判断項目を埋める
  所要時間: 10分
```

**総所要時間: 約35分**

---

## 検証後のアクション（確定）

### 結果: Step 1-3 成功、Step 4 バグ修正済み → 実装に進む

**実装計画（完了）:**

1. **`mvp_click_recorder.py` への統合** ✅
   - `event_mask` に `kCGEventKeyDown`, `kCGEventFlagsChanged` を追加
   - `event_callback` にキーイベント処理を追加（KEY_DOWNのみ記録）
   - 連続入力を `text_input` アクションにまとめる最適化
   - ショートカットキー（修飾キー付き）は `key_shortcut` として記録
   - 入力ソース切替キー（かな=104, 英数=109）も記録

2. **`mvp_action_player.py` への統合** ✅
   - `type_key()` 関数の追加（BASE_FLAGS=0x100 を常に設定）
   - `text_input` アクションの再生（キーコード順次入力）
   - `key_shortcut` アクションの再生（修飾キー付きキー入力）

3. **再テスト: Step 4 修正版の確認**
   - `scripts/keyboard/keyboard_test_step4.py` を再実行し、Shiftフラグ固着が解消されたことを確認

### 日本語入力について

- **パターンBで対応可能**: keycodeベースの記録・再生で、IMEが同じ状態なら同じ日本語が入力される
- 入力ソース切替（かなキー/英数キー）も記録されるため、再生時に自動でIME状態を復元可能
- 辞書学習の差異による変換結果の違いは許容（Phase 3のAI補完で対応予定）
