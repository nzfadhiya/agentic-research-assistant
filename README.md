# Agentic Research Assistant

A production-grade multi-agent AI research system built with LangGraph, MCP, FastAPI, and Streamlit.

## Features

- Multi-agent research pipeline (LangGraph orchestration)
- MCP tool server (web search, Wikipedia, memory)
- Auto-routing: AI decides between chat, research, or quick answer
- Dual agent mode: two parallel answers, user chooses
- JWT authentication with multi-user support
- Document upload and analysis (PDF, DOCX, TXT)
- Document generation (PDF, DOCX)
- Conversation memory with SQLite
- Research cache with clear functionality
- Export conversations as HTML reports
- Full CI/CD pipeline with GitHub Actions

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph |
| LLM | Groq (llama-3.3-70b-versatile) |
| Tool protocol | MCP (Model Context Protocol) |
| API | FastAPI |
| UI | Streamlit |
| Auth | JWT (python-jose + passlib) |
| Memory | SQLite |
| Search | DuckDuckGo (free) |
| CI/CD | GitHub Actions |
| Deployment | Render |

## Architecture

User → Streamlit UI → FastAPI (port 8000)
↓
LangGraph Agents
↓
MCP Tool Server (port 8001)
├── web_search
├── wikipedia_fetch
├── save_memory
└── search_memory
↓
Groq LLM API

## Stack
- LangGraph + LangChain
- Groq (llama-3.3-70b-versatile)
- FastAPI + Uvicorn
- Streamlit
- SQLite
- Docker Compose

## Setup

```bash
git clone https://github.com/nzfadhiya/agentic-research-assistant
cd agentic-research-assistant
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

## Run locally

Terminal 1:
```bash
uvicorn app.mcp_server.server:mcp_app --reload --port 8001
```

Terminal 2:
```bash
uvicorn app.main:app --reload --port 8000
```

Terminal 3:
```bash
streamlit run streamlit_app.py
```

## Run with Docker

```bash
docker-compose up --build
```

## Project Structure
app/
├── agents/          # LangGraph agents
├── auth/            # JWT authentication
├── memory/          # SQLite database
├── mcp_server/      # MCP tool server
└── tools/           # Search, doc reader, pdf export

streamlit_app.py     # Frontend UI