# DataMind: Autonomous Agentic Text-to-SQL Analyst

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.0+-purple.svg)](https://vitejs.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_State_Machine-orange.svg)](https://langchain.com)

DataMind is a production-grade **Autonomous Text-to-SQL AI Analyst** that translates natural language questions into safe, executable SQL queries, runs them against PostgreSQL or CSV databases, generates statistical and trend insights, visualizes results via interactive charts, and streams live agent thinking steps in real-time over WebSockets.

---

## Architecture Overview

```mermaid
graph TD
    User([User / Browser]) <-->|WebSocket & REST| FE[React + Vite Frontend]
    FE <-->|FastAPI Gateway| BE[FastAPI Backend]

    subgraph Agentic LangGraph State Machine
        BE --> S1[1. Intent Check & Memory Disambiguation\nGroq Qwen 3.8 27B / Llama 3]
        S1 --> S2[2. Schema Linking & RAG\nGemini 768-dim Embeddings + pgvector]
        S2 --> S3[3. SQL Generation & Caching\nGemini 2.5 Flash + Semantic Cache]
        S3 --> S4[4. AST Safety Validator\nsqlglot AST inspection + allow-lists]
        S4 -->|Rejected / Error| S5[5. Autonomous Self-Correction Loop]
        S5 -->|Retry with Hint| S3
        S4 -->|Safe Read-Only SQL| S6[6. Read-Only Query Executor\nTimeout Enforcement + Limit Guard]
        S6 --> S7[7. Statistical & Trend Analyzer\nPandas / SciPy regression & outliers]
        S7 --> S8[8. Executive Result Explainer\nGroq Synthesis & Dynamic Charts]
    end

    S8 --> BE
```

---

## Key Features

1. **Autonomous LangGraph State Machine**:
   - Multi-node pipeline: `Intent Check` &rarr; `Schema Linker` &rarr; `SQL Generator` &rarr; `Safety Validator` &rarr; `Self Correction` &rarr; `Executor` &rarr; `Data Analysis` &rarr; `Result Explainer`.
2. **Dual-LLM Power & Resilience**:
   - **Google Gemini 2.5 Flash**: Complex SQL generation strictly constrained to schema definitions.
   - **Gemini Embeddings (`gemini-embedding-001`)**: 768-dimensional normalized vector embeddings for semantic schema search and similarity caching.
   - **Groq AI (`qwen/qwen3.8-27b`)**: Ultra-fast intent classification, conversational context resolution, and executive business summaries.
   - **Multi-Model Fallbacks**: Automatic graceful degradation protects against API spikes and service unavailability.
3. **Enterprise SQL Safety & AST Validation**:
   - Comprehensive `sqlglot` AST parsing.
   - Blocks multi-statement stacked attacks (`; DROP TABLE`), comments (`--`, `/* */`), destructive DDL/DML (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`), and system catalog access (`pg_shadow`, `information_schema`).
   - Strict table allow-listing and automatic `LIMIT 100` enforcement.
4. **Multi-Turn Conversational Memory**:
   - Retains context across drill-down questions (e.g. *"What is our revenue in 2023?"* &rarr; *"Why did it drop in August?"* &rarr; *"Now just show me Mumbai."*).
5. **Real-time Live WebSocket Streaming**:
   - Streams granular agent execution traces (node name, latency in ms, intermediate SQL, schema reasoning) live to the UI.
6. **Smart Analytics & Visualizations**:
   - Automatic chart type selection (`bar`, `line`, `pie`, `stat_card`).
   - Statistical trend detection, percentage changes, and anomaly detection.
7. **Production Extras**:
   - Semantic query caching (sub-millisecond repeat queries).
   - Custom dashboard widgets and pinned bookmarks.
   - LLM token usage and cost estimation analytics.
   - Direct CSV spreadsheet upload with instant auto-table creation.

---

## Quickstart: Running Locally

### Option 1: Docker Compose (Recommended)

Start the App Database (PostgreSQL + pgvector), Backend, and Frontend in one command:

```bash
docker compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **PostgreSQL Database**: localhost:5433 (user: `app_user`, password: `app_password`, db: `app_db`)

---

### Option 2: Running Directly on Windows / Local Machine

#### 1. Start the Database
Ensure PostgreSQL is running locally or start only the database container:
```bash
docker compose up -d app_db
```

#### 2. Backend Setup
```powershell
cd backend

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if needed)
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup
```powershell
cd frontend

# Install packages
npm install

# Start Vite development server
npm run dev
```
Open **http://localhost:3000** in your browser.

---

## Environment Variables (`.env`)

```env
# LLM API Keys
GEMINI_API_KEY=AQ.Ab8...
GROQ_API_KEY=gsk_i6n...
EMBEDDING_MODEL=gemini-embedding-001

# Databases
DATABASE_URL=postgresql://app_user:app_password@localhost:5433/app_db
TARGET_DB_URL=postgresql://readonly_agent:readonly_secure_pass@localhost:5433/ecommerce_db

# JWT & Security
JWT_SECRET_KEY=antigravity_secret_key_jwt_text_to_sql_analyst_2026_secure
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Server Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
QUERY_TIMEOUT_SECONDS=10
MAX_QUERY_RETRIES=2
DEFAULT_ROW_LIMIT=100
```

---

## Running Test Suites

### 1. Full Backend Test Suite (40 Tests)
```powershell
.\backend\.venv\Scripts\pytest.exe backend\tests -v
```

### 2. Standalone Adversarial & SQL Injection Test Suite (24 Tests)
```powershell
.\backend\.venv\Scripts\python.exe scripts\run_adversarial_suite.py
```

### 3. Full 6-Query Evaluation Benchmark
```powershell
.\backend\.venv\Scripts\python.exe backend\evaluation\benchmark_runner.py
```

### 4. Frontend Production Build Check
```powershell
cd frontend
npm run build
```

---

## License
MIT License. Built with ❤️ for autonomous data analytics.
