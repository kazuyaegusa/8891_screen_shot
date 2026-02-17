"""
エージェントシステムの設定（.envからロード）

【使用方法】
from agent.config import AgentConfig

config = AgentConfig()
print(config.openai_api_key)
print(config.workflow_dir)

# カスタム設定
config = AgentConfig(max_steps=30, dry_run=True)

【処理内容】
.envファイルから環境変数をロードし、エージェント設定を提供する。
デフォルト値が設定されているため、.envがなくても動作する（API呼び出しは除く）。

【依存】
python-dotenv, os
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# プロジェクトルートの .env をロード
_project_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class AgentConfig:
    """エージェント設定"""
    # OpenAI API
    openai_api_key: str = ""
    openai_model: str = "gpt-5"

    # ワークフロー保存先
    workflow_dir: str = ""

    # 実行制限
    max_steps: int = 50
    max_consecutive_failures: int = 5
    step_delay: float = 1.0

    # 安全機構
    dry_run: bool = False
    confirm_dangerous: bool = True
    dangerous_apps: List[str] = field(default_factory=lambda: [
        "Mail", "メール", "Slack", "Discord", "Messages", "メッセージ",
        "LINE", "Telegram", "WhatsApp",
    ])

    # AI設定
    reasoning_effort: str = "medium"
    max_output_tokens: int = 2000

    # スクリーンショット
    screenshot_dir: str = ""

    def __post_init__(self):
        if not self.openai_api_key:
            self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")

        src_dir = Path(__file__).resolve().parent.parent
        if not self.workflow_dir:
            self.workflow_dir = str(src_dir / "workflows")
        if not self.screenshot_dir:
            self.screenshot_dir = str(src_dir.parent.parent / "screenshots")

    def is_dangerous_app(self, app_name: str) -> bool:
        """送信系アプリかどうか判定"""
        return any(d.lower() in app_name.lower() for d in self.dangerous_apps)
