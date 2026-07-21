#!/bin/bash

# 1. Start local Redis server in the background
redis-server --port 6379 --daemonize yes

# 2. Start Celery worker in the background
# We use '-P solo' to minimize memory consumption on Hugging Face's free CPU tier
celery -A nyaya_ai.api.tasks worker --loglevel=info -P solo &

# 3. Start FastAPI app on the port expected by HF Spaces (7860)
uvicorn nyaya_ai.api.main:app --host 0.0.0.0 --port 7860
