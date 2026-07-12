"""Centralized configuration for Nyaya AI. All constants live here."""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Qdrant — local file-based storage (no Docker needed)
# Switch to QDRANT_URL = "http://localhost:6333" when using Docker
# ---------------------------------------------------------------------------
QDRANT_PATH = "./qdrant_data"    # persistent local storage
QDRANT_URL = os.getenv("QDRANT_URL", None)  # e.g. "http://localhost:6333" for Docker mode
COLLECTION_NAME = "nyaya_corpus"

# ---------------------------------------------------------------------------
# Embedding — BGE-M3 (ADR-002)
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

# ---------------------------------------------------------------------------
# LLM — 3-Tier Cloud Cascade (ADR-004)
#   Tier 1: Groq (Llama 3.3 70B) — fast, free tier
#   Tier 2: Gemini 1.5 Flash — Google AI, generous free tier
#   Tier 3: OpenRouter — free-tier models (GLM/Qwen/Kimi)
# ---------------------------------------------------------------------------


# Tier 1 — Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.1-8b-instant"

# Tier 2 — Gemini (via OpenAI-compatible endpoint)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-3.1-flash-lite"

# Tier 3 — OpenRouter free tier
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"  # free-tier model

# Ollama (local fallback — kept for offline dev)
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "llama3.2:3b"

# ---------------------------------------------------------------------------
# Cascade thresholds (ADR-004)
# ---------------------------------------------------------------------------
CONFIDENCE_THRESHOLD = 0.7
MAX_RETRIES = 1          # retries at same tier before escalation

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
TOP_K = 5                # chunks passed to LLM after retrieval

# ---------------------------------------------------------------------------
# Corpus versioning
# ---------------------------------------------------------------------------
CORPUS_VERSION = "v1"

# ---------------------------------------------------------------------------
# HuggingFace dataset identifiers (Layer1-IndianLaw.txt)
# ---------------------------------------------------------------------------
HF_DATASETS = {
    "primary": "mratanusarkar/Indian-Laws",          # pre-sectioned
    "secondary": "geekyrakshit/indian-legal-acts",   # raw text, needs chunking
    "optional": "Sahi19/IndianLawComplete",           # may not exist
}

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
MAX_CHUNK_TOKENS = 1000   # split sections longer than this
MIN_CHUNK_TOKENS = 50     # merge sections shorter than this

# ---------------------------------------------------------------------------
# Contract Intelligence (Mode 1)
# ---------------------------------------------------------------------------
CONTRACT_RELEVANCE_THRESHOLD = 0.50
CONTRACT_RISK_TOP_K = 10