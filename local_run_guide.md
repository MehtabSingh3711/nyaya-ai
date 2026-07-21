# Nyaya AI — Local Verification & Run Guide (Windows)

This guide provides step-by-step instructions to boot the complete Nyaya AI stack locally, verify database connection states, caching responses, and execute end-to-end testing of both the FastAPI backend and Next.js frontend.

---

## 🏗️ Prerequisites & Dependencies
Before starting, ensure you have the following installed on your Windows machine:
1. **Python 3.10+** (with `pip` and `virtualenv`).
2. **Node.js 18+** (with `npm`).
3. **Redis Server** (Windows native binaries, Memurai, or running inside WSL/Docker).

---

## 🚀 Step 1: Start the Backend Services (Python + Redis)

### 1.1 Start Redis Server
Open a terminal (PowerShell or Command Prompt) and start the Redis service on port `6379`:
```powershell
# If using Windows Native Redis
redis-server --port 6379

# If using Docker
docker run -d -p 6379:6379 redis:alpine
```
*Verification*: Run `redis-cli ping` in another terminal. It should respond with `PONG`.

### 1.2 Configure Backend Environment Variables
Create a `.env` file in the root workspace directory (where `requirements.txt` is located) and specify your API credentials:
```env
# Cloud LLM cascade endpoints (Free Tiers)
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# JWT Config (for session tokens)
JWT_SECRET_KEY=nyaya_dev_secret_key_change_in_prod

# Redis Cache URI
REDIS_URL=redis://localhost:6379/0
```

### 1.3 Activate Virtual Environment & Install Modules
Open a new PowerShell terminal in the project root:
```powershell
# Create & Activate Virtual Environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install Dependencies
pip install -r requirements.txt
```

### 1.4 Start Celery Worker (Critical Windows Rule)
On Windows, Celery must run in **solo pool mode** to prevent billiard-fork child process hangs. Activate your virtual environment and run:
```powershell
# Make sure venv is active
celery -A nyaya_ai.api.tasks worker --loglevel=info -P solo
```
Keep this window open. You should see logs indicating Celery is connected to `redis://localhost:6379/0`.

### 1.5 Start FastAPI Server
Open a new terminal, activate your virtual environment, and run:
```powershell
# Start Uvicorn Dev Server
uvicorn nyaya_ai.api.main:app --host 127.0.0.1 --port 8000 --reload
```
*Verification*: Open `http://127.0.0.1:8000/api/v1/health` in your browser. You should receive:
```json
{
  "status": "ok",
  "database": "healthy"
}
```

---

## 🌐 Step 2: Start the Frontend Service (Next.js)

### 2.1 Install Node Packages
Open a new terminal, change directory to `frontend/`, and run:
```powershell
cd frontend
npm install
```

### 2.2 Configure Frontend Environment
Create a `.env.local` file inside the `frontend/` folder:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2.3 Start Next.js Development Server
Start the frontend server inside the `frontend/` directory:
```powershell
npm run dev
```
*Verification*: Open your browser to `http://localhost:3000`. You should see the Landing Page featuring the new custom pillar logo!

---

## 🧪 Step 3: End-to-End Verification Protocol (Smoke Test)

Follow this workflow to verify the platform is fully operational:

### 3.1 User Onboarding & Auth Verification
1. Open `http://localhost:3000` and click **"Sign In"** (or "Enter Dashboard").
2. Since no cookie token is present, you will be redirected instantly to `/signin` without layout flashes.
3. Switch to the **"Create Account"** tab.
4. Input a Full Name, Email Address, and Password, then click **"Create Account"**.
5. *Expected Result*: The page registers your user in the local `nyaya_history.db` database, generates a JWT token, writes it to the `nyaya_token` cookie, saves metadata in `localStorage`, and routes you automatically to the `/dashboard`.

### 3.2 Dashboard Telemetry Verification
1. On the dashboard, verify the widgets display:
   * **Ingested Contracts**: `0 / 200`
   * **Risks Identified**: `0`
   * **Open RAG Chats**: `0`
   * **API Usage/Cost**: `₹0.00`
2. Keep this tab open.

### 3.3 Contract Ingestion & Scan Verification (Mode 1)
1. Click **"Upload New Contract"** in the dashboard or navigation bar.
2. Drag and drop or select a support contract document (`.pdf` or `.docx`).
3. *Expected Result*: 
   * The file is uploaded to `POST /api/v1/contracts/scan`.
   * The page routes to `/scan?id=scan_id` and shows the loading status *"Auditing contract clauses against Central Acts..."*.
   * In your Celery terminal, you will see logs indicating the scan task was received and is processing.
   * After completion, the progress skeleton is replaced with the **Compliance Scan Workstation**.
4. Inside the workstation, click on different flagged clauses in the **Clause Navigator** (left column).
5. Verify the **Statutory Analysis** (right column) renders the conflicting act details, explanations, recommended negotiation actions, and **landmark precedents** (like *Niranjan Shankar Golikari*).
6. Click **"Export Report"** at the top right and verify a PDF file downloads containing the compliance findings.

### 3.4 Statutory Grounding Chat Verification (Mode 2)
1. Click **"Ask Legal AI"** or **"Research"** in the navigation bar to open the RAG Chat workstation.
2. Click on one of the suggested topics: *"Is non-compete valid in Karnataka?"*.
3. Click **"Send"** (or hit Enter).
4. *Expected Result*:
   * The query is submitted to `POST /api/v1/chat`.
   * The system searches the statutory corpus in Qdrant and feeds it to the LLM cascade.
   * The response is rendered inside the legal memorandum area.
   * Hovering over the dashed highlights in the memorandum highlights the matching **Cited Statutory Authority** cards in the left column.
   * A new research session is appended to the **Research Sessions** sidebar on the right, and the URL updates to `/chat?session_id=session_id`.
5. Enter the *same question* a second time.
6. *Expected Result*: The backend terminal logs `[Cache] HIT for key: chat_cache:...` and responds in under 50ms without invoking the cloud LLM cascade.
7. Click the trash icon next to the session in the history sidebar to verify the session deletes and resets the view.
