"""Kaggle Dual-GPU Microservice (BGE-M3 + PyTorch CUDA BGE-Reranker v2-m3) — Nyaya AI

This script runs inside a Kaggle Notebook (GPU T4 x2 or P100 enabled).
- GPU 0 (cuda:0): BAAI/bge-m3 (Dense + Sparse Hybrid Embedder)
- GPU 1 (cuda:1): BAAI/bge-reranker-v2-m3 (PyTorch CUDA Cross-Encoder Reranker)

Uses PyTorch CUDA on GPU 1 (or GPU 0) for ~20ms ultra-fast cross-encoder scoring,
preventing Cloudflare timeouts and CPU bottlenecks!

Usage on Kaggle:
----------------
1. Open a Kaggle Notebook with GPU T4 x2 enabled.
2. Copy-paste this script into a cell and run it.
3. Copy the generated Cloudflare URL into your local .env:
   REMOTE_EMBEDDING_URL=https://xxx.trycloudflare.com
"""

import os
import sys
import time
import subprocess
import threading
from typing import List, Dict, Any, Optional

# Install dependencies if missing inside Kaggle
try:
    import torch
    import FlagEmbedding
    import fastapi
    import uvicorn
    import nest_asyncio
except ImportError:
    print("📦 Installing required packages on Kaggle...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "FlagEmbedding", "fastapi", "uvicorn", "pydantic", "nest_asyncio", "torch"
    ])
    import torch
    import FlagEmbedding
    import fastapi
    import uvicorn
    import nest_asyncio

import nest_asyncio
nest_asyncio.apply()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from FlagEmbedding import BGEM3FlagModel, FlagReranker

# Kill any leftover process on port 8000 from previous notebook runs
try:
    subprocess.run(["fuser", "-k", "8000/tcp"], stderr=subprocess.DEVNULL)
    time.sleep(1)
except Exception:
    pass

# Detect available CUDA GPUs
if torch.cuda.is_available():
    gpu_count = torch.cuda.device_count()
    print(f"🔍 Detected {gpu_count} CUDA GPU(s):")
    for i in range(gpu_count):
        name = torch.cuda.get_device_name(i)
        mem = torch.cuda.get_device_properties(i).total_memory / (1024**3)
        print(f"   GPU {i}: {name} ({mem:.1f} GiB)")
else:
    gpu_count = 0
    print("⚠️ No CUDA GPUs detected — running on CPU (will be slow!)")

device_embed = "cuda:0" if gpu_count > 0 else "cpu"
device_rerank = "cuda:1" if gpu_count > 1 else device_embed

print(f"\n🚀 Initializing Nyaya AI Dual-GPU Microservice...")
print(f"  🔹 Hybrid Embedder : {device_embed} (BAAI/bge-m3)")
print(f"  🔹 CUDA Reranker   : {device_rerank} (BAAI/bge-reranker-v2-m3)")

# Initialize Embedder on GPU 0 (cuda:0)
# BGEM3FlagModel uses 'device' (singular)
embed_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=(device_embed != "cpu"), device=device_embed)
print(f"✅ BGE-M3 Embedder loaded on {device_embed}")

# Verify embedder is actually on GPU
if device_embed.startswith("cuda"):
    mem_used = torch.cuda.memory_allocated(int(device_embed.split(":")[1])) / (1024**3)
    print(f"   GPU memory used by embedder: {mem_used:.2f} GiB")

# Initialize PyTorch CUDA Reranker on GPU 1 (cuda:1)
# CRITICAL: FlagReranker uses 'devices' (PLURAL), not 'device'!
# Using 'device' (singular) is silently ignored → falls back to CPU.
rerank_model = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=(device_rerank != "cpu"), devices=device_rerank)
print(f"✅ BGE-Reranker v2-m3 loaded on {device_rerank}")

# Verify reranker is actually on GPU
if device_rerank.startswith("cuda"):
    gpu_idx = int(device_rerank.split(":")[1])
    mem_used = torch.cuda.memory_allocated(gpu_idx) / (1024**3)
    print(f"   GPU memory used by reranker: {mem_used:.2f} GiB")

app = FastAPI(title="Nyaya AI Dual-GPU Microservice")

class QueryRequest(BaseModel):
    text: str

class DocumentsRequest(BaseModel):
    texts: List[str]
    batch_size: Optional[int] = 32

class RerankRequest(BaseModel):
    query: str
    documents: List[str]
    top_n: Optional[int] = None

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Nyaya AI Dual-GPU Microservice",
        "embed_device": device_embed,
        "rerank_device": device_rerank,
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }

@app.get("/health")
def health_check():
    gpu_stats = []
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            gpu_stats.append({
                "gpu": i,
                "name": torch.cuda.get_device_name(i),
                "memory_allocated_gib": round(torch.cuda.memory_allocated(i) / (1024**3), 2),
                "memory_reserved_gib": round(torch.cuda.memory_reserved(i) / (1024**3), 2),
            })
    return {
        "status": "online",
        "embed_device": device_embed,
        "rerank_device": device_rerank,
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "gpu_stats": gpu_stats,
    }

@app.post("/embed_query_hybrid")
def embed_query_hybrid(req: QueryRequest):
    try:
        output = embed_model.encode(
            [req.text],
            batch_size=1,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
            verbose=False,
        )
        
        dense_vec = output["dense_vecs"][0].tolist()
        sparse_weights = output["lexical_weights"][0]
        
        converted_sparse = {}
        for key, value in sparse_weights.items():
            if isinstance(key, str):
                t_ids = embed_model.tokenizer.convert_tokens_to_ids([key])
                converted_sparse[int(t_ids[0])] = float(value)
            else:
                converted_sparse[int(key)] = float(value)
                
        return {
            "dense": dense_vec,
            "sparse": converted_sparse
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed_documents_hybrid")
def embed_documents_hybrid(req: DocumentsRequest):
    try:
        output = embed_model.encode(
            req.texts,
            batch_size=req.batch_size or 32,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
            verbose=False,
        )
        
        dense_vecs = output["dense_vecs"].tolist()
        sparse_vecs = []
        for weights_dict in output["lexical_weights"]:
            converted = {}
            for key, value in weights_dict.items():
                if isinstance(key, str):
                    t_ids = embed_model.tokenizer.convert_tokens_to_ids([key])
                    converted[int(t_ids[0])] = float(value)
                else:
                    converted[int(key)] = float(value)
            sparse_vecs.append(converted)
            
        return {
            "dense": dense_vecs,
            "sparse": sparse_vecs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rerank")
def rerank_documents(req: RerankRequest):
    try:
        if not req.documents:
            return {"results": []}

        # Pair query with each document text for CUDA PyTorch Cross-Encoder scoring
        pairs = [[req.query, doc] for doc in req.documents]
        raw_scores = rerank_model.compute_score(pairs)

        if isinstance(raw_scores, float):
            raw_scores = [raw_scores]

        results = []
        for idx, score in enumerate(raw_scores):
            results.append({
                "index": idx,
                "relevance_score": float(score)
            })

        # Sort by relevance score descending if requested
        if req.top_n and req.top_n < len(results):
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            results = results[:req.top_n]

        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_uvicorn():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

def start_cloudflare_tunnel(token: Optional[str] = None):
    if not os.path.exists("cloudflared"):
        print("📥 Downloading cloudflared Linux binary...")
        subprocess.run(["wget", "-q", "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", "-O", "cloudflared"])
        subprocess.run(["chmod", "+x", "cloudflared"])
        
    print("\n🌐 Launching Cloudflare Tunnel...")
    if token:
        print(f"🔑 Using Cloudflare Named Tunnel Token")
        cmd = ["./cloudflared", "tunnel", "run", "--token", token]
    else:
        cmd = ["./cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"]
        
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    printed_url = False
    for line in process.stdout:
        if "trycloudflare.com" in line and not printed_url:
            import re
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                url = match.group(0)
                print("\n" + "="*70)
                print(f"🎉 NYAYA AI DUAL-GPU ENDPOINT IS LIVE AT:")
                print(f"👉 {url}")
                print("="*70 + "\n")
                printed_url = True

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_uvicorn, daemon=True)
    server_thread.start()
    time.sleep(3)
    
    CLOUDFLARE_TOKEN = os.environ.get("CLOUDFLARE_TUNNEL_TOKEN", None)
    start_cloudflare_tunnel(token=CLOUDFLARE_TOKEN)
