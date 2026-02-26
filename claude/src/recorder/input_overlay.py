"""
ビデオフレームにマウスクリック・キーボード操作のオーバーレイを描画するモジュール

使用方法:
    from recorder.input_overlay import InputOverlay

    overlay = InputOverlay()
    overlay.add_click(500, 300, "left")
    overlay.add_key("Cmd+C")

    # numpy配列のフレームにオーバーレイを描画
    frame = overlay.draw(frame)

処理内容:
    1. add_click/add_key でイベントを登録（スレッドセーフ）
    2. 各イベントは lifetime 秒後に自動消滅（フェードアウト）
    3. draw() で現在アクティブなイベントをフレーム上に描画
    4. クリック: 塗りつぶし円 + 拡大する波紋リング
    5. キーボード: 画面下部に背景付きテキストラベル（複数同時表示対応）
"""

import time
import threading
from dataclasses import dataclass, field
from typing import List, Tuple

import cv2
import numpy as np


@dataclass
class VisualEvent:
    """描画用イベントデータ"""
    event_type: str  # "click" or "key"
    x: int = 0
    y: int = 0
    button: str = ""  # "left" or "right"
    key_text: str = ""
    created_at: float = field(default_factory=time.time)
    lifetime: float = 1.0


class InputOverlay:
    """
    フレーム上にマウスクリック・キーボード入力のビジュアルフィードバックを描画する。

    Input:
        click_lifetime: クリックエフェクトの表示秒数（デフォルト: 0.8）
        key_lifetime: キーラベルの表示秒数（デフォルト: 1.5）
        max_keys: 同時表示するキーラベルの最大数（デフォルト: 5）

    Output:
        draw() がオーバーレイ描画済みの numpy 配列（BGR フレーム）を返す
    """

    def __init__(
        self,
        click_lifetime: float = 0.8,
        key_lifetime: float = 1.5,
        max_keys: int = 5,
    ):
        self._events: List[VisualEvent] = []
        self._lock = threading.Lock()
        self._click_lifetime = click_lifetime
        self._key_lifetime = key_lifetime
        self._max_keys = max_keys

    def add_click(self, x: int, y: int, button: str = "left"):
        """
        クリックイベントを追加する。

        Input:
            x: クリック位置 X座標（ピクセル）
            y: クリック位置 Y座標（ピクセル）
            button: "left" or "right"
        """
        with self._lock:
            self._events.append(VisualEvent(
                event_type="click", x=x, y=y, button=button,
                lifetime=self._click_lifetime,
            ))

    def add_key(self, key_text: str):
        """
        キーボードイベントを追加する。

        Input:
            key_text: 表示するキーテキスト（例: "a", "Cmd+C", "Enter"）
        """
        with self._lock:
            key_events = [e for e in self._events if e.event_type == "key"]
            if len(key_events) >= self._max_keys:
                for e in self._events:
                    if e.event_type == "key":
                        self._events.remove(e)
                        break
            self._events.append(VisualEvent(
                event_type="key", key_text=key_text,
                lifetime=self._key_lifetime,
            ))

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """
        フレームにアクティブなイベントのオーバーレイを描画して返す。

        Input:
            frame: BGR形式の numpy 配列（cv2フレーム）

        Output:
            オーバーレイ描画済みの numpy 配列（入力フレームを直接変更する）
        """
        now = time.time()

        with self._lock:
            self._events = [e for e in self._events if now - e.created_at < e.lifetime]
            active = list(self._events)

        if not active:
            return frame

        overlay = frame.copy()

        key_idx = 0
        for event in active:
            progress = (now - event.created_at) / event.lifetime  # 0.0 → 1.0
            alpha = max(0.0, 1.0 - progress)

            if event.event_type == "click":
                self._draw_click(overlay, event, progress)
            elif event.event_type == "key":
                self._draw_key(overlay, frame.shape, event, key_idx)
                key_idx += 1

        # オーバーレイをブレンド（全体を一度にブレンドして効率化）
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        return frame

    @staticmethod
    def _draw_click(overlay: np.ndarray, event: VisualEvent, progress: float):
        """クリックの円+波紋を描画"""
        # 左クリック=赤、右クリック=緑 (BGR)
        color = (0, 0, 255) if event.button == "left" else (0, 255, 0)
        center = (event.x, event.y)

        # メイン円（サイズ固定）
        cv2.circle(overlay, center, 16, color, -1)

        # 波紋リング（拡大していく）
        ripple_r = int(16 + 50 * progress)
        thickness = max(1, int(3 * (1.0 - progress)))
        cv2.circle(overlay, center, ripple_r, color, thickness)

    @staticmethod
    def _draw_key(
        overlay: np.ndarray,
        frame_shape: Tuple[int, ...],
        event: VisualEvent,
        idx: int,
    ):
        """キーテキストを画面下部に描画"""
        h, w = frame_shape[:2]
        text = event.key_text
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.9
        thickness = 2

        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)

        pad = 10
        y_pos = h - 50 - idx * (th + pad * 2 + 8)
        x_pos = w - tw - pad * 2 - 20

        # 背景矩形
        cv2.rectangle(
            overlay,
            (x_pos - pad, y_pos - th - pad),
            (x_pos + tw + pad, y_pos + baseline + pad),
            (30, 30, 30),
            -1,
        )
        cv2.rectangle(
            overlay,
            (x_pos - pad, y_pos - th - pad),
            (x_pos + tw + pad, y_pos + baseline + pad),
            (100, 100, 100),
            1,
        )

        # テキスト
        cv2.putText(overlay, text, (x_pos, y_pos), font, scale, (255, 255, 255), thickness)
