import os
import time
import logging
import asyncio
import threading
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reranker-service")

app = FastAPI(title="Nyaya AI Reranker Service")

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

MODEL_NAME = "jinaai/jina-reranker-v1-turbo-en"

class RerankRequest(BaseModel):
    query: str = Field(..., description="The search query text")
    candidates: List[str] = Field(..., description="List of document candidates to rerank")

class RankedItem(BaseModel):
    text: str
    score: float

class RerankResponse(BaseModel):
    ranked: List[RankedItem]

def load_model_background():
    global model, model_status, model_error
    try:
        logger.info(f"Initializing FastEmbed Reranker ({MODEL_NAME}) in background thread...")
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        
        # Load local cross-encoder model
        model = TextCrossEncoder(model_name=MODEL_NAME)
        model_status = "ready"
        logger.info(f"Reranker model {MODEL_NAME} successfully loaded.")
    except Exception as e:
        model_status = "failed"
        model_error = str(e)
        logger.error(f"Failed to load Reranker model: {e}", exc_info=True)

@app.on_event("startup")
def startup_event():
    # Start loading the model in a background thread to prevent port binding timeouts
    thread = threading.Thread(target=load_model_background, daemon=True)
    thread.start()

@app.get("/health")
def health_check(response: Response):
    if model_status == "ready":
        return {"status": "ready", "model": MODEL_NAME}
    elif model_status == "loading":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        response.headers["Retry-After"] = "5"
        return {"status": "loading", "message": "Model is still warming up inside container."}
    else:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "failed", "error": model_error}

def run_inference(query: str, candidates: List[str]) -> List[dict]:
    """Executes local reranking synchronously inside the thread pool."""
    results = list(model.rerank(query=query, documents=candidates))
    
    # Map scores back and format
    ranked_items = []
    for item in results:
        # fastembed returns dicts or objects depending on version; handle both robustly
        if hasattr(item, "score") and hasattr(item, "document"):
            score = float(item.score)
            text = str(item.document)
        elif isinstance(item, dict):
            score = float(item.get("score", 0.0))
            text = str(item.get("document", ""))
        else:
            score = float(item[0]) if isinstance(item, tuple) else 0.0
            text = str(item[1]) if isinstance(item, tuple) else ""
            
        ranked_items.append({"text": text, "score": score})
        
    # Sort descending by score
    ranked_items.sort(key=lambda x: x["score"], reverse=True)
    return ranked_items

@app.post("/rerank", response_model=RerankResponse)
async def rerank_endpoint(request: RerankRequest, response: Response):
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

    if not request.candidates:
        return RerankResponse(ranked=[])

    start_time = time.time()
    num_candidates = len(request.candidates)
    logger.info(f"Incoming rerank request for query '{request.query[:30]}...' with {num_candidates} candidates.")

    try:
        # Enforce 30s timeout on inference
        loop = asyncio.get_event_loop()
        ranked = await asyncio.wait_for(
            loop.run_in_executor(executor, run_inference, request.query, request.candidates),
            timeout=30.0
        )
        
        duration = time.time() - start_time
        logger.info(f"Successfully reranked {num_candidates} items in {duration:.4f} seconds.")
        return RerankResponse(ranked=ranked)
        
    except asyncio.TimeoutError:
        logger.error(f"Reranking timeout (30s exceeded) for query '{request.query[:30]}...'.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Reranking request timed out (limit: 30s)."
        )
    except Exception as e:
        logger.error(f"Reranking execution failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during reranking: {str(e)}"
        )
