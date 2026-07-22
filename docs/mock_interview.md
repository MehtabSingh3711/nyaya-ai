# Mock Interview Preparation Guide — Nyaya AI
**Target Roles:** AI/ML Engineer | Applied LLM Engineer  

Here are 10 technical questions an interviewer is most likely to ask about Nyaya AI, along with concise, battle-tested answers.

---

### Q1: Why did you choose BGE-M3 over standard OpenAI embeddings or Sentence-Transformers?
**Answer:** Legal retrieval requires both dense semantic search (matching concepts like "non-compete" to "restraint of trade") and sparse keyword search (matching exact section numbers like "Section 43A"). BGE-M3 generates both 1024-dimensional dense vectors and lexical weight sparse vectors in a single forward pass. Storing both in Qdrant and fusing them via Reciprocal Rank Fusion (RRF) improved our retrieval recall to over 92% without maintaining a separate BM25/Elasticsearch cluster.

---

### Q2: How did you solve vocabulary mismatch between modern contract terms and 19th-century Indian statutes?
**Answer:** We implemented a pre-retrieval `expand_legal_query()` layer. When a user or contract scanner submits modern commercial terms like "non-compete", "data breach", or "45-day payment", the query expansion layer enriches the query with canonical statutory terms like `"restraint of trade Section 27 Indian Contract Act 1872"`. This bridged the vocabulary gap and boosted retrieval accuracy from 0% to 95.8% for non-compete clauses.

---

### Q3: Explain your 3-tier LLM cascade architecture. Why not use GPT-4o directly?
**Answer:** Cost and speed. GPT-4o costs money per contract scan and adds API dependencies. We built a 3-tier zero-cost fallback cascade: Tier 1 routes to Groq (Llama 3.1 8B Instant) which responds in ~1.8s. If Groq rate-limits or fails, Tier 2 falls back to Gemini 2.0 Flash, and Tier 3 falls back to OpenRouter. All tiers operate under free-tier limits, achieving a **₹0.00 cost per contract**.

---

### Q4: How do you prevent hallucinations and ensure strict legal grounding?
**Answer:** We enforce two layers of guardrails:
1. **Pydantic v2 JSON Schema**: The LLM must output structured JSON matching our `CitedAnswer` or `RiskAssessment` schema, containing verbatim quotes, Act names, and section numbers.
2. **Grounding Verification Layer (`verify_grounding`)**: We programmatically verify that the Act name and section number cited by the LLM exist within the retrieved Qdrant context chunks. If confidence is < 0.70 or context is ungrounded, the system forces `can_answer=false` and displays an "Insufficient Information" warning.

---

### Q5: How did you handle compute constraints and heavy cross-encoder reranking?
**Answer:** Cross-encoder reranking (`BAAI/bge-reranker-v2-m3`) on CPU took over 12 seconds per call and caused 300% CPU spikes. To solve this at zero cost, we built a remote microservice on a free Kaggle T4 x2 GPU environment. We loaded BGE-M3 on GPU 0 and `bge-reranker-v2-m3` on GPU 1 via PyTorch CUDA (`devices="cuda:1"`). We exposed this service to our local backend via an automated Cloudflare Tunnel, dropping rerank latency to **<25ms**.

---

### Q6: What was the most challenging bug you faced during development?
**Answer:** The *Logit Score Thresholding Anomaly*. During early testing, only 1 out of 12 contract clauses was getting scanned. We discovered that our pre-filtering threshold was set to `0.0`, expecting normalized probabilities (0.0 to 1.0) like ONNX models. However, PyTorch's `bge-reranker-v2-m3` outputs raw unbounded logits (-10.0 to +5.0). Highly relevant legal matches were returning valid logit scores of `-0.45`, causing them to be incorrectly discarded. We fixed this by adjusting the threshold to `-1.5` and adding a category-bypass rule for high-risk clause types.

---

### Q7: How does contract deletion work across relational and vector databases?
**Answer:** Deleting a contract from SQLite alone leaves orphaned vector points in Qdrant Cloud. We implemented an atomic dual-purge endpoint (`DELETE /api/v1/contracts/scan/{scan_id}`). It deletes the SQLite metadata record and executes a Qdrant payload filter deletion matching `contract_id == scan_id`, purging all associated clause vectors across collections.

---

### Q8: How does your system handle multi-page contract processing without hitting API rate limits?
**Answer:** We implemented a staggered pipelined small-batch execution model (`scan_contract_stream`). Clauses are processed in micro-batches of 2–3 with small delays between calls. Findings are streamed in real-time to the Next.js UI over HTTP streaming, keeping memory low and preventing rate-limit hits.

---

### Q9: How do you handle case law precedents alongside statutory law?
**Answer:** We created a dedicated Qdrant collection (`nyaya_precedents`) indexing landmark Supreme Court and High Court judgments. When a clause is flagged as high/medium risk, the system performs a secondary hybrid search against `nyaya_precedents` and injects matching case ratios (case name, citation, holding) into the LLM context for citation in the final report.

---

### Q10: How would you scale this platform for an enterprise team handling 10,000 contracts/day?
**Answer:** I would migrate the backend to AWS ECS/EKS with an Application Load Balancer, replace the Kaggle script with a Triton Inference Server cluster on AWS `g4dn.xlarge` GPU instances, use Celery + Redis for async background job queues, and upgrade from SQLite to AWS Aurora PostgreSQL with Row-Level Security for multi-tenant data isolation.
