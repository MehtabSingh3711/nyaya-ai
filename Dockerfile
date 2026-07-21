FROM python:3.10-slim

# Install system dependencies, PyMuPDF requirements, and Redis Server
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Setup permissions for Hugging Face non-root user (UID 1000)
RUN useradd -m -u 1000 user
RUN chown -R user:user /app

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

# Grant execute rights to the startup script
RUN chmod +x run.sh

USER user
ENV PORT=7860
ENV REDIS_URL=redis://localhost:6379/0
ENV DATABASE_URL=sqlite:///./nyaya_history.db

EXPOSE 7860

# Launch the all-in-one stack
CMD ["./run.sh"]
