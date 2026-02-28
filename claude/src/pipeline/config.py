"""
パイプライン設定管理モジュール

【使用方法】
from pipeline.config import PipelineConfig

# .env + 環境変数からロード
config = PipelineConfig.from_env()

# デフォルト値で生成
config = PipelineConfig()

# 個別指定
config = PipelineConfig(session_gap=600, ai_model="gpt-5")

【処理内容】
1. python-dotenv で .env ファイルを読み込み
2. 環境変数からパイプライン設定値を取得（未設定ならデフォルト値）
3. PipelineConfig dataclass としてアクセス可能にする

【依存】
python-dotenv, pathlib
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class PipelineConfig:
    watch_dir: Path = Path("./screenshots")
    skills_dir: Path = Path.home() / ".claude" / "skills"
    session_gap: int = 300
    session_max: int = 50
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.0-flash"
    cpu_limit: int = 30
    mem_limit: int = 500
    poll_sec: float = 10.0
    min_confidence: float = 0.6

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        # プロジェクトルートの .env を明示的に探す
        src_dir = Path(__file__).resolve().parent.parent
        for candidate in [src_dir / ".env", src_dir.parent / ".env"]:
            if candidate.exists():
                load_dotenv(candidate)
                break
        else:
            load_dotenv()
        return cls(
            watch_dir=Path(os.getenv("PIPELINE_WATCH_DIR", "./screenshots")),
            skills_dir=Path(os.getenv("PIPELINE_SKILLS_DIR", str(Path.home() / ".claude" / "skills"))),
            session_gap=int(os.getenv("PIPELINE_SESSION_GAP", "300")),
            session_max=int(os.getenv("PIPELINE_SESSION_MAX", "50")),
            ai_provider=os.getenv("PIPELINE_AI_PROVIDER", "gemini"),
            ai_model=os.getenv("PIPELINE_AI_MODEL", "gemini-2.0-flash"),
            cpu_limit=int(os.getenv("PIPELINE_CPU_LIMIT", "30")),
            mem_limit=int(os.getenv("PIPELINE_MEM_LIMIT", "500")),
            poll_sec=float(os.getenv("PIPELINE_POLL_SEC", "10.0")),
            min_confidence=float(os.getenv("PIPELINE_MIN_CONFIDENCE", "0.6")),
        )
