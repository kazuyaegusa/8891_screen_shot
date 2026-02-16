"""
スクリーンショット自動撮影＆画像解析システム - OpenAI Vision画像解析モジュール

処理内容:
  スクリーンショット画像をbase64エンコードし、OpenAI GPT-5 Vision APIに送信。
  画面に表示されている内容を日本語で簡潔に解説する。
  100_IMPORT/OPENAIGPT5.md のパターン（client.responses.create）に従う。

使用方法:
  from image_analyzer import ImageAnalyzer
  analyzer = ImageAnalyzer(api_key="sk-...")
  result = analyzer.analyze(Path("screenshot.png"))
  print(result["description"])
"""

import base64
from datetime import datetime
from pathlib import Path

from openai import OpenAI


class ImageAnalyzer:
    """OpenAI Vision APIを使用した画像解析クラス"""

    PROMPT = (
        "このスクリーンショットに表示されている画面内容を日本語で簡潔に説明してください。"
        "どのアプリケーションが表示されているか、画面上の主要な要素やテキストを含めてください。"
    )

    def __init__(self, api_key: str, model: str = "gpt-5"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze(self, image_path: Path) -> dict:
        """
        画像ファイルを解析し、画面内容の説明を返す。

        Args:
            image_path: 解析対象の画像ファイルパス

        Returns:
            dict: {
                "timestamp": "2026-02-14 15:30:45",
                "filename": "screenshot_...",
                "description": "画面にはVSCodeが...",
                "model": "gpt-5"
            }

        Raises:
            FileNotFoundError: 画像ファイルが存在しない場合
            Exception: API呼び出しに失敗した場合
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image_b64 = self._encode_image(image_path)
        suffix = image_path.suffix.lstrip(".")
        data_url = f"data:image/{suffix};base64,{image_b64}"

        res = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": self.PROMPT},
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            reasoning={"effort": "low"},
            max_output_tokens=800,
        )

        description = res.output_text

        # reasoningモデルが空テキストを返す場合のリトライ（1回）
        if not description.strip():
            res = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": self.PROMPT},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
                reasoning={"effort": "low"},
                max_output_tokens=800,
            )
            description = res.output_text

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": image_path.name,
            "description": description,
            "model": self.model,
        }

    @staticmethod
    def _encode_image(image_path: Path) -> str:
        """画像ファイルをbase64文字列にエンコードする"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
