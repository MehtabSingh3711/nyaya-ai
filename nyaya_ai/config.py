"""Centralized configuration for Nyaya AI. All constants live here."""

# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "nyaya_corpus"

# ---------------------------------------------------------------------------
# Embedding — BGE-M3 (ADR-002)
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

# ---------------------------------------------------------------------------
# LLM — Ollama / Phi-3 Mini (ADR-004)
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "phi3:3.8b"

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
