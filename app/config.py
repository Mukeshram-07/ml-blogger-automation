"""
config.py
---------
Central configuration loader for ML Blogger Automation System.
All settings are read from environment variables via .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Blogger API credentials ──────────────────────────────────────────
    BLOGGER_API_KEY: str = os.getenv("BLOGGER_API_KEY", "")
    BLOGGER_BLOG_ID: str = os.getenv("BLOGGER_BLOG_ID", "")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REFRESH_TOKEN: str = os.getenv("GOOGLE_REFRESH_TOKEN", "")

    # ── Groq LLM (for expanding notes into polished articles) ────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    USE_LLM: bool = os.getenv("USE_LLM", "true").lower() == "true"

    # ── Publish behavior ─────────────────────────────────────────────────
    # DRY_RUN=true → runs everything but does NOT call Blogger API
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"
    # DRAFT_MODE=true → publishes to Blogger as draft (not live)
    DRAFT_MODE: bool = os.getenv("DRAFT_MODE", "false").lower() == "true"

    # ── File paths ────────────────────────────────────────────────────────
    TOPICS_FILE: str = os.getenv("TOPICS_FILE", "topics/topics.json")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_FILE: str = os.path.join(LOG_DIR, "automation.log")
    POST_LOG_FILE: str = os.path.join(LOG_DIR, "post_history.json")

    # ── Author ────────────────────────────────────────────────────────────
    AUTHOR_NAME: str = os.getenv("AUTHOR_NAME", "Mukesh")
    BLOG_LABELS: list = []  # populated per post from topic tags

    # ── Retry config ──────────────────────────────────────────────────────
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY_SECONDS: int = int(os.getenv("RETRY_DELAY_SECONDS", "5"))


config = Config()
