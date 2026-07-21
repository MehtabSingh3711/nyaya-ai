FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/tmp/huggingface \
    TORCH_HOME=/tmp/torch

# Create user with UID 1000
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install torch CPU-only first to save space
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=user:user . .

# Set permissions for Hugging Face cache directories
RUN mkdir -p /tmp/huggingface /tmp/torch && chown -R user:user /tmp/huggingface /tmp/torch

USER user

# Expose HF Space port
EXPOSE 7860

# Run FastAPI app with 2 workers (conforms to 2 vCPU resource constraint)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2"]
