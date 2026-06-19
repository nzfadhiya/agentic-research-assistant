# Agentic Research Assistant

A multi-agent AI research assistant built with LangGraph, Groq, and MCP. Supports conversational chat, deep multi-agent research, and quick search — all with persistent memory across sessions.

🌐 **Live Demo:** [agentic-research-assistant-kmljzkanipeb25cmph36id.streamlit.app](https://agentic-research-assistant-kmljzkanipeb25cmph36id.streamlit.app)  
🔗 **API:** [agentic-research-assistant-zwwf.onrender.com](https://agentic-research-assistant-zwwf.onrender.com)  
📦 **GitHub:** [nzfadhiya/agentic-research-assistant](https://github.com/nzfadhiya/agentic-research-assistant)



---

## Features

- **Auto mode** — AI automatically routes your query to the best agent (chat, research, or quick search)
- **Multi-agent research** — 4 specialized agents (search, Wikipedia, critique, save) produce comprehensive reports
- **Persistent memory** — chat history saved to Supabase PostgreSQL, survives server restarts
- **Cross-session context** — follow-up questions work across chat, multi, and simple modes
- **User authentication** — register, login, guest mode with JWT tokens
- **Dual response mode** — two agents answer in parallel, you choose the better response
- **Document tools** — upload PDF/DOCX/TXT for analysis, generate PDF/DOCX reports
- **Export** — download full chat as HTML report

---

## Architecture

```
User
 │
 ▼
Streamlit UI (Streamlit Cloud)
 │
 ▼
FastAPI Backend (Render)
 │
 ├── Chat Agent (LangChain + Groq)
 │     └── Auto-classifies: CHAT / SIMPLE / RESEARCH
 │
 ├── Multi-Agent Graph (LangGraph)
 │     ├── Search Agent → MCP web_search tool
 │     ├── Wikipedia Agent → MCP wikipedia_fetch tool
 │     ├── Critique Agent → synthesizes report
 │     └── Save Agent → MCP save_memory tool
 │
 ├── Dual Agent → parallel A/B responses
 │
 └── MCP Server (custom HTTP bridge)
       ├── web_search (DuckDuckGo)
       ├── wikipedia_fetch
       └── save_memory
 │
 ▼
Supabase PostgreSQL (persistent storage)
 ├── users
 ├── chat_sessions
 └── research_history
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI + Uvicorn |
| AI Agents | LangGraph, LangChain |
| LLM | Llama 3.1 8B via Groq API |
| Tool Protocol | MCP (Model Context Protocol) |
| Database | Supabase (PostgreSQL) |
| Auth | JWT (python-jose) + bcrypt |
| Document processing | PyMuPDF, python-docx |
| Deployment | Render (API) + Streamlit Cloud (UI) |
| CI/CD | GitHub Actions |
| Version control | GitHub (auto-deploy on push) |

---

## CI/CD Pipeline

This project uses **GitHub Actions** for continuous integration and **automatic deployment** via Render and Streamlit Cloud.

### How it works

```
git push origin master
        │
        ▼
GitHub Actions runs CI
        │
        ├── ✅ Tests pass → Render auto-deploys API
        │                 → Streamlit Cloud auto-deploys UI
        │
        └── ❌ Tests fail → Deploy blocked, email notification sent
```

### Pipeline stages

| Stage | What happens |
|---|---|
| **Checkout** | Pulls latest code from GitHub |
| **Setup Python 3.11** | Installs Python with pip cache |
| **Install dependencies** | `pip install -r requirements.txt` |
| **Run tests** | `pytest test_system.py -v` |
| **Deploy notify** | Confirms Render + Streamlit Cloud will auto-deploy |

### Workflow file

Located at `.github/workflows/ci.yml`. Triggers on every push to `master` and on pull requests.

### Setting up GitHub Actions secret

Add your Groq API key to GitHub Actions:
1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `GROQ_API_KEY`
4. Value: your Groq API key
5. Click **Add secret**

### Deployment flow

```
Developer pushes code
        │
        ▼
GitHub Actions (CI tests)
        │
        ├── Render watches master branch
        │   └── Auto-deploys FastAPI backend (~3 min)
        │
        └── Streamlit Cloud watches master branch
            └── Auto-deploys Streamlit frontend (~2 min)
```

No manual deployment steps needed — just `git push`.

---

## Agents

### Chat Agent
Handles conversational queries with full session memory. Auto-classifies each message into CHAT, SIMPLE, or RESEARCH mode and routes accordingly.

### Multi-Agent Graph (LangGraph)
Four agents work in sequence:
1. **Search Agent** — queries web via MCP
2. **Wikipedia Agent** — fetches background via MCP
3. **Critique Agent** — synthesizes a structured report
4. **Save Agent** — persists to memory via MCP

### Dual Agent
Two agents run in parallel — Agent A answers from LLM knowledge, Agent B researches with web sources. User picks the better response.

---

## MCP Server
Custom MCP-compatible HTTP tool server exposing:
- `web_search` — DuckDuckGo search
- `wikipedia_fetch` — Wikipedia summaries
- `save_memory` — persist research to database

Mounted directly on the FastAPI app at `/mcp`.

---

## Local Setup

```bash
# Clone
git clone https://github.com/nzfadhiya/agentic-research-assistant
cd agentic-research-assistant

# Install
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Add: GROQ_API_KEY, DATABASE_URL (optional — falls back to SQLite)

# Run backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run frontend (new terminal)
streamlit run streamlit_app.py
```

---

## Deployment

| Service | Purpose | URL |
|---|---|---|
| Render | FastAPI backend | [agentic-research-assistant-zwwf.onrender.com](https://agentic-research-assistant-zwwf.onrender.com) |
| Streamlit Cloud | Streamlit frontend | [streamlit.app link](https://agentic-research-assistant-kmljzkanipeb25cmph36id.streamlit.app) |
| Supabase | PostgreSQL database | Internal |
| Groq | LLM API (Llama 3.1 8B) | Internal |

All services are free tier. Push to `master` → both Render and Streamlit Cloud redeploy automatically.

---

## Environment Variables

| Variable | Description | Where |
|---|---|---|
| `GROQ_API_KEY` | Groq API key | Render environment |
| `DATABASE_URL` | Supabase PostgreSQL URI | Render environment |
| `API_URL` | Backend URL for Streamlit | Streamlit Cloud secrets |
| `GROQ_API_KEY` | Groq API key for CI tests | GitHub Actions secrets |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/chat` | Conversational chat with memory |
| POST | `/research` | Multi-agent or simple research |
| POST | `/dual` | Two parallel agent responses |
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/sessions` | List user's past sessions |
| GET | `/chat/{session_id}/history` | Full session history |
| POST | `/upload-doc` | Upload and analyze document |
| POST | `/generate-doc` | Generate PDF/DOCX on topic |
| POST | `/export/{session_id}` | Export chat as HTML |

---

## Project Structure

```
agentic-research-assistant/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI/CD
├── app/
│   ├── agents/
│   │   ├── chat_agent.py        # Auto-routing chat agent
│   │   ├── multi_agent_graph.py # LangGraph 4-agent pipeline
│   │   ├── dual_agent.py        # Parallel A/B agents
│   │   └── research_graph.py    # Simple research agent
│   ├── auth/
│   │   └── auth.py              # JWT auth
│   ├── memory/
│   │   └── database.py          # SQLite/PostgreSQL abstraction
│   ├── mcp_server/
│   │   └── http_bridge.py       # MCP HTTP tool server
│   ├── tools/
│   │   ├── doc_reader.py        # PDF/DOCX extraction
│   │   ├── doc_generator.py     # PDF/DOCX generation
│   │   └── pdf_export.py        # Chat export
│   ├── config.py
│   └── main.py                  # FastAPI app
├── streamlit_app.py             # Streamlit frontend
├── test_system.py               # System tests
├── requirements.txt
├── Procfile                     # Render start command
└── README.md
```

---

## Live URLs

- **App:** https://agentic-research-assistant-kmljzkanipeb25cmph36id.streamlit.app
- **API:** https://agentic-research-assistant-zwwf.onrender.com
- **GitHub:** https://github.com/nzfadhiya/agentic-research-assistant
