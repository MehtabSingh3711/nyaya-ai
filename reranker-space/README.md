---
title: Nyaya AI Reranker Service
emoji: 🚀
colorFrom: red
colorTo: orange
sdk: docker
app_port: 7860
pinned: false
---

# Nyaya AI — Reranker Service

A high-performance, containerized microservice wrapping `jinaai/jina-reranker-v1-turbo-en` cross-encoder for semantic reranking.

## API Endpoints

### 1. `POST /rerank`
Reranks a list of candidate documents relative to a query.

**Request Payload:**
```json
{
  "query": "non-compete clause enforceability",
  "candidates": [
    "Agreement terms of employee non-compete clause",
    "Random payment details",
    "Section 27 of ICA void restraint of trade"
  ]
}
```

**Response:**
```json
{
  "ranked": [
    { "text": "Section 27 of ICA void restraint of trade", "score": 0.92 },
    { "text": "Agreement terms of employee non-compete clause", "score": 0.81 },
    { "text": "Random payment details", "score": 0.05 }
  ]
}
```

### 2. `GET /health`
Uptime health check probe endpoint.
