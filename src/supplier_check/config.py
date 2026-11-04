"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RUNS_DIR = ROOT_DIR / "runs"

# Provider precedence is enforced in extract.get_client_and_model():
# LLM_BASE_URL -> GROQ_API_KEY -> OPENAI_API_KEY.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip() or None
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip() or None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip() or None

# Groq (OpenAI-compatible). Used when GROQ_API_KEY is set and LLM_BASE_URL is empty.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip() or None
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()


CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.80"))
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "").strip() or None
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
