import re

file_path = "architecture.md"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace Ollama cascade references with cloud cascade
content = content.replace("LLM Cascade: Phi-3 Mini → Gemma-2-9B → OpenRouter", "LLM Cascade: Groq Llama 3.1 8B → Gemini 2.5 Flash Lite → OpenRouter")
content = content.replace("(all free — Tiers 1 & 2 via Ollama local)", "(all free — Tier 1 via Groq, Tier 2 via Gemini Cloud)")
content = content.replace("Phi-3 Mini → Gemma-2-9B → GPT-4o", "Groq Llama 3.1 8B → Gemini 2.5 Flash Lite → OpenRouter Qwen 3")

# Replace Celery/Redis references with BackgroundTasks/SQLite
content = content.replace("Celery Task Queue & Redis Broker", "FastAPI BackgroundTasks & SQLite Database")
content = content.replace("Celery Worker", "BackgroundTasks Thread Pool")
content = content.replace("enqueue Celery task", "trigger FastAPI BackgroundTask")
content = content.replace("check Redis", "query SQLite")
content = content.replace("Redis", "SQLite")
content = content.replace("Celery", "BackgroundTasks")

# Write back
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[SUCCESS] Successfully updated architecture.md!")
