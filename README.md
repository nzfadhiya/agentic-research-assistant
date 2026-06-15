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