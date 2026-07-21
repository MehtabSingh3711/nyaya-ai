# AI Session Log — 2026-07-20 — Documentation Updates & Precedents Plan
**Agent:** Antigravity (Gemini)
**Phase:** Week 4 — Production Polish & Delivery
**Session opened:** 1:10 PM

## Session Goal
Update all project documentation (Problem Statement, Initial Design Doc, Architecture Doc) to align with actual project implementations (FastAPI backend, cloud LLM cascade, Qdrant Cloud hybrid, and upcoming case-law precedents).

## Decisions Log

### Decision: Verified Precedent Manifest Ingestion
**Options presented:**
- **Option A**: Use online Hugging Face streaming & keyword filtering to extract judgments on-the-fly.
- **Option B**: Use a hand-curated 100-case manifest containing verified commercial/contract precedents, resolving any unverified placeholders.
**Student chose:** Option B (Ingest verified local manifest after correcting and validating all citations).
**Student's reason:** To ensure 100% legal accuracy and avoid any unverified or fabricated cases in the RAG pipeline, the manifest was updated with correct landmark precedents (e.g. *Kunwarlal*, *Subrahmanyam*, *Jai Indra Bahadur Singh*).
**Agent recommendation was:** Option B
**Student followed agent recommendation:** Yes

### Decision: Qdrant Multi-Tenancy Strategy
**Options presented:**
- **Option A**: Store all contract clauses in a single `nyaya_contracts` collection, tag each point with `user_id` in the payload, and pass a `Filter` condition in all queries.
- **Option B**: Create a distinct collection named `nyaya_contracts_{user_id}` dynamically when a user signs up.
**Student chose:** Option A (Payload Filtering).
**Student's reason:** Not stated.
**Agent recommendation was:** Option A (Payload Filtering).
**Student followed agent recommendation:** Yes

### Decision: Authentication Scheme
**Options presented:**
- **Option A**: Use JSON Web Tokens (JWT) passed in the `Authorization: Bearer <token>` header.
- **Option B**: Use cookie-based session IDs stored in a SQLite database table.
**Student chose:** Option A (JWT Stateless Auth).
**Student's reason:** Not stated.
**Agent recommendation was:** Option A (JWT Stateless Auth).
**Student followed agent recommendation:** Yes

### Decision: Database Concurrency with Celery & SQLite
**Options presented:**
- **Option A**: Enable Write-Ahead Logging (WAL) on SQLite and set a `timeout=30` in SQLAlchemy connection arguments.
- **Option B**: Replace SQLite with PostgreSQL.
**Student chose:** Option A (WAL Mode + Timeout).
**Student's reason:** Not stated.
**Agent recommendation was:** Option A (WAL Mode + Timeout).
**Student followed agent recommendation:** Yes

### Decision: Database Schema Migration Strategy
**Options presented:**
- **Option A**: Delete and recreate the database file `nyaya_history.db` to automatically initialize the new schema.
- **Option B**: Run SQL migration statements to add the missing `user_id` columns to existing tables.
**Student chose:** Option A (Delete and Recreate).
**Student's reason:** Not stated.
**Agent recommendation was:** Option A.
**Student followed agent recommendation:** Yes



### Discovery Answers Logged:
1. **Primary Target User:** Anyone who needs to understand a contract (startup founders, freelancers, MSME owners).
2. **Pain Point:** Difficult wording burying clauses that are hard to decipher and match with laws.
3. **Target Companies:** SpotDraft, Leegality, Sarvam AI, Razorpay, Swiggy.
4. **Key Technical Risks:** Hallucinations (solved by strong prompting & larger models), API latency.

## Summary
In this session, we updated the project documentation (`problem-statement.md`, `initial-design-doc.md`, and `architecture.md`) to reflect the current implementation and scope of Nyaya AI. We then designed, verified, and implemented the case-law precedents database (`nyaya_precedents`) and updated the contract risk scanning pipeline (Mode 1) to retrieve and return supporting judicial precedents. 

Following this, we implemented a production-ready backend upgrade:
1. **JWT Authentication**: Implemented direct user registration `/api/v1/auth/signup` and signin `/api/v1/auth/signin` endpoints, alongside a standard OAuth2 token endpoint `/api/v1/auth/token` for interactive Swagger UI / FastView testing.
2. **Data Isolation (Multi-Tenancy)**: Added user-owner scoping to Qdrant clauses payload, chat sessions, database scan records, and dashboard metrics.
3. **Redis Caching**: Built a session-independent query caching engine with Redis, including short-term TTL (5m) for LLM refusals, long-term TTL (2h) for verified answers, and console logs.
4. **Celery Worker & Tasks**: Integrated Celery to offload contract scans to a background worker process, configured SQLite Write-Ahead Logging (WAL) for concurrent writes, and built a local background task fallback for zero-dependency environments.
5. **Deployment Configs**: Wrote a startup `run.sh` orchestrator script and a custom `Dockerfile` to deploy the entire multi-service stack inside a single Hugging Face Spaces Docker container.

## Code / Output Produced
* **PRD**: [problem-statement.md](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/problem-statement.md)
* **Objectives / Plan**: [initial-design-doc.md](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/initial-design-doc.md)
* **System Architecture**: [architecture.md](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/architecture.md)
* **Verified Precedents Manifest**: [precedent_cases_manifest.md](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/docs/data/precedent_cases_manifest.md)
* **Local Ingestion Script**: [ingest_precedents.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/ingest_precedents.py)
* **Colab Ingestion Script**: [ingest_precedents_colab.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/ingest_precedents_colab.py)
* **Precedent Schema**: [nyaya_ai/schemas.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/schemas.py)
* **Precedent Prompts**: [nyaya_ai/llm/prompts.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/llm/prompts.py)
* **Cascade Ingestion**: [nyaya_ai/llm/cascade.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/llm/cascade.py)
* **Contract Scanner**: [nyaya_ai/contracts/scanner.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/contracts/scanner.py)
* **CLI Scan Report**: [scan_contract.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/scan_contract.py)
* **Scanner Unit Tests**: [tests/test_mode1_scanner.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/tests/test_mode1_scanner.py)
* **Test Fix & Additions**: [tests/test_api.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/tests/test_api.py)
* **FastAPI Entrypoint**: [nyaya_ai/api/main.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/api/main.py)
* **Celery Tasks & Config**: [nyaya_ai/api/tasks.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/api/tasks.py)
* **Compose File**: [docker-compose.yml](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/docker-compose.yml)
* **Deployment Guide**: [setup_and_deployment_guide.md](file:///C:/Users/mehta/.gemini/antigravity-ide/brain/9cc4cf71-fb77-4b5a-873c-02f02756dd5d/setup_and_deployment_guide.md)
* **HF Spaces Config**: [Dockerfile](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/Dockerfile) and [run.sh](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/run.sh)

## What the Student Built / Decided
* You decided to use JWT-based authentication for the FastAPI backend.
* You chose Qdrant payload filtering (`user_id` tags) to achieve secure multi-tenancy without creation overhead.
* You implemented Redis caching to store RAGChat queries session-independently and avoid redundant LLM billing.
* You configured Celery background task processing for contract scans, using SQLite WAL mode to bypass concurrent write database locks.
* You decided to deploy the entire multi-service application inside a single container on Hugging Face Spaces using a Docker setup.

## Open Questions for Next Session
* None.

## Next Session Goal
* Build the Next.js dark-themed dashboard frontend.

