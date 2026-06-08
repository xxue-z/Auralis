"""Auralis Agent 配置管理"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class Config:
    WS_HOST: str = os.getenv("WS_HOST", "127.0.0.1")
    WS_PORT: int = int(os.getenv("WS_PORT", "9527"))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    MIMO_API_KEY: str = os.getenv("MIMO_API_KEY", "")
    LOCAL_MODEL_ENABLED: bool = os.getenv("LOCAL_MODEL_ENABLED", "false").lower() == "true"
    LOCAL_MODEL_PATH: str = os.getenv("LOCAL_MODEL_PATH", "")
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data"))
    MEMORY_DIR: Path = DATA_DIR / "memory"
    LOGS_DIR: Path = DATA_DIR / "logs"

    @classmethod
    def ensure_dirs(cls):
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)


config = Config()
