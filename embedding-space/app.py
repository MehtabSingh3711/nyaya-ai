import os
import time
import logging
import asyncio
import threading
from typing import List, Union
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("embedding-service")

app = FastAPI(title="Nyaya AI Embedding Service")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_origins_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model state
model = None
model_status = "loading"
model_error = None
executor = ThreadPoolExecutor(max_workers=2)

class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., description="List of strings to embed")

class EmbedResponse(BaseModel):
    dense_vectors: List[List[float]]
    sparse_vectors: List[dict]

def load_model_background():
    global model, model_status, model_error
    try:
        logger.info("Initializing BGE-M3 (BAAI/bge-m3) in background thread...")
        # Local imports inside thread to avoid blockages
        from FlagEmbedding import BGEM3FlagModel
        
        # CPU-only configuration
        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
        model_status = "ready"
        logger.info("BGE-M3 model successfully loaded and ready for inference.")
    except Exception as e:
        model_status = "failed"
        model_error = str(e)
        logger.error(f"Failed to load BGE-M3 model: {e}", exc_info=True)

@app.on_event("startup")
def startup_event():
    # Start loading the model in a background thread to prevent Uvicorn port binding timeouts
    thread = threading.Thread(target=load_model_background, daemon=True)
    thread.start()

@app.get("/health")
def health_check(response: Response):
    if model_status == "ready":
        return {"status": "ready", "model": "BAAI/bge-m3"}
    elif model_status == "loading":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        response.headers["Retry-After"] = "5"
        return {"status": "loading", "message": "Model is still warming up inside container."}
    else:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "failed", "error": model_error}

def run_inference(texts: List[str]) -> tuple:
    """Executes BGE-M3 encoding synchronously (called inside thread pool executor)."""
    output = model.encode(
        texts,
        batch_size=len(texts),
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
        verbose=False,
    )
    
    dense_vecs = output["dense_vecs"].tolist()
    
    # Convert lexical weights keys to standard string/int token IDs
    sparse_vecs = []
    for weights_dict in output["lexical_weights"]:
        converted = {}
        for key, value in weights_dict.items():
            if isinstance(key, str):
                token_ids = model.tokenizer.convert_tokens_to_ids([key])
                converted[str(token_ids[0])] = float(value)
            else:
                converted[str(key)] = float(value)
        sparse_vecs.append(converted)
        
    return dense_vecs, sparse_vecs

@app.post("/embed", response_model=EmbedResponse)
async def embed_endpoint(request: EmbedRequest, response: Response):
    # check model readiness
    if model_status == "loading":
        response.headers["Retry-After"] = "10"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is currently loading. Please retry shortly."
        )
    elif model_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model initialization failed: {model_error}"
        )

    start_time = time.time()
    num_items = len(request.texts)
    logger.info(f"Incoming embedding request for {num_items} items.")

    try:
        # Enforce 30s timeout on CPU inference
        loop = asyncio.get_event_loop()
        dense, sparse = await asyncio.wait_for(
            loop.run_in_executor(executor, run_inference, request.texts),
            timeout=30.0
        )
        
        duration = time.time() - start_time
        logger.info(f"Successfully processed {num_items} items in {duration:.4f} seconds.")
        return EmbedResponse(dense_vectors=dense, sparse_vectors=sparse)
        
    except asyncio.TimeoutError:
        logger.error(f"Inference timeout (30s exceeded) for request of size {num_items}.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Inference request timed out (limit: 30s)."
        )
    except Exception as e:
        logger.error(f"Inference execution failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during inference: {str(e)}"
        )
