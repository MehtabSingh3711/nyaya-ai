---
title: Nyaya AI Embedding Service
emoji: ⚖️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Nyaya AI — Embedding Service

A high-performance, containerized microservice for generating BGE-M3 dense and sparse lexical embeddings.

## API Endpoints

### 1. `POST /embed`
Generates BGE-M3 embeddings.

**Request Payload:**
```json
{
  "texts": ["Your clause text here"]
}
```

**Response:**
```json
{
  "dense_vectors": [[0.12, -0.45, ...]],
  "sparse_vectors": [{"101": 0.85, "2005": 1.2}]
}
```

### 2. `GET /health`
Uptime health check probe endpoint.
