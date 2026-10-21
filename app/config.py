"""Configuração lida do .env (nunca versionado)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # groq | gemini
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b" if PROVIDER == "groq" else "gemini-3.8-flash")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
TOP_K = int(os.getenv("RAG_TOP_K", "4"))

CORPUS_DIR = ROOT / "data" / "corpus"
PROMPTS_DIR = ROOT / "prompts"
RESULTS_DIR = ROOT / "resultados"
LOGS_DIR = RESULTS_DIR / "logs"

# Id interno embutido em todos os prompts: se aparecer na saída, houve vazamento de instruções.
PROMPT_CANARY = "CANARY-4417"
