## What this is
Aradhana is a conversational astrology companion: you enter birth details, it computes a real natal chart via a real ephemeris library, and it responds with grounded warmth.
It uses LangGraph (agentic loop + tools) on FastAPI, with a Next.js frontend that streams responses and live tool activity.

## Setup
### 1) Prereqs
- Python 3.11
- Node.js 20+
- PostgreSQL 16+

### 2) Backend
```bash
python -m venv .venv
# Windows PowerShell
. .\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# flatlib==0.2.3 hard-pins an old pyswisseph version that is no longer
# published for Python 3.11 on Windows; install flatlib without deps.
pip install --no-deps flatlib==0.2.3

copy backend/.env.example backend/.env
# edit .env with your GROQ_API_KEY and DATABASE_URL

# Run from the repo root (recommended)
uvicorn backend.main:app --reload --port 8000

# If you're currently in the backend/ folder, use the launcher:
#   python run_dev.py
# Or set PYTHONPATH then run uvicorn:
#   $env:PYTHONPATH = ".."; uvicorn backend.main:app --reload --port 8000
```

### 3) Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000

### 4) Docker (optional)
```bash
docker compose up --build
```

## Architecture overview
- Backend: FastAPI provides SSE streaming at `POST /api/chat`.
- Agent: LangGraph routes message → reasons → calls tools → formats response.
- Tools:
  - `geocode_place` (Nominatim)
  - `compute_birth_chart` (flatlib)
  - `get_daily_transits` (flatlib + aspects)
  - `knowledge_lookup` (keyword-overlap RAG over a local notes file)
- DB: PostgreSQL stores chat messages by session.

## LangGraph graph

   START
     │
   router_node
     │
   ┌─┴──────────────────┬──────────────┐
   │                    │              │
  needs_details    chart/transit    off_topic
   │                    │              │
  ask_details      reasoner_node   respond_node
   │                    │              │
  END              ┌────┴────┐        END
                   │ tools?  │
                  yes        no
                   │         │
               tool_node  respond_node
                   │         │
               reasoner   END
               (loop, max 8)

## Known limitations
- Nominatim does not reliably return an IANA timezone; this project uses a best-effort mapping and may fall back to UTC.
- Transit logic is intentionally simple (conjunction/trine/square with basic orbs) and not a full professional-grade transit engine.
- The eval harness uses live geocoding which can fail without network access.

## How to run evals
```bash
python evals/run_evals.py
```
Set `GROQ_API_KEY` first to enable LLM-as-judge scoring.
