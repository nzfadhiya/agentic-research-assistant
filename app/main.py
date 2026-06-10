from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import sqlite3
import sys
sys.path.insert(0, '.')
from app.agents.research_graph import run_research
from app.agents.multi_agent_graph import run_multi_agent
from app.agents.chat_agent import run_chat
from app.memory.database import (
    get_history, init_db, get_chat_history,
    clear_chat_session, save_chat_message
)
from app.tools.pdf_export import export_chat_to_pdf
from app.config import GROQ_API_KEY, GROQ_MODEL, DB_PATH
MCP_URL = "http://127.0.0.1:8001"

app = FastAPI(
    title="Agentic Research Assistant",
    description="Multi-agent research system using LangGraph + Groq + MCP",
    version="2.0.0"
)

# ── Request models ────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str
    mode: str = "multi"

class ResearchResponse(BaseModel):
    query: str
    summary: str
    mode: str
    status: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

# ── Startup ───────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    print("[API] Started. Database ready.")

# ── Health check ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Agentic Research Assistant",
        "version": "2.0.0"
    }

# ── Research endpoints ────────────────────────────────────────

@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    casual_signals = ["hi", "hello", "how are", "what time", "who are you", "thanks"]
    is_casual = any(request.query.lower().strip().startswith(s) for s in casual_signals)
    actual_mode = "simple" if is_casual else request.mode
    try:
        if actual_mode == "multi":
            summary = run_multi_agent(request.query)
        else:
            summary = run_research(request.query)
        return ResearchResponse(
            query=request.query,
            summary=summary,
            mode=actual_mode,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def history():
    records = get_history(limit=10)
    return {"count": len(records), "history": records}

# ── Chat endpoints ────────────────────────────────────────────

@app.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint with auto-routing."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        result = run_chat(request.session_id, request.message)
        if isinstance(result, tuple):
            response_text, mode_used = result
        else:
            response_text = result
            mode_used = "chat"
        return {
            "session_id": request.session_id,
            "message": request.message,
            "response": response_text,
            "mode_used": mode_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat — returns tokens as they arrive."""
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, AIMessage

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    llm_stream = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        streaming=True
    )
    history = get_chat_history(request.session_id)
    save_chat_message(request.session_id, "user", request.message)

    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=request.message))

    full_response = []

    async def generate():
        async for chunk in llm_stream.astream(messages):
            token = chunk.content
            if token:
                full_response.append(token)
                yield token
        save_chat_message(request.session_id, "assistant", "".join(full_response))

    return StreamingResponse(generate(), media_type="text/plain")

@app.get("/chat/{session_id}/history")
async def chat_history(session_id: str):
    history = get_chat_history(session_id)
    return {"session_id": session_id, "messages": history}

@app.delete("/chat/{session_id}")
async def clear_chat(session_id: str):
    clear_chat_session(session_id)
    return {"status": "cleared", "session_id": session_id}

# ── Sessions list ─────────────────────────────────────────────

@app.get("/sessions")
async def get_sessions():
    """Returns all unique chat sessions with preview."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id,
               MIN(created_at) as started,
               COUNT(*) as message_count,
               MIN(CASE WHEN role='user' THEN content END) as first_message,
               MAX(created_at) as last_activity
        FROM chat_sessions
        GROUP BY session_id
        ORDER BY last_activity DESC
        LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    return {
        "sessions": [
            {
                "session_id": r[0],
                "started": r[1],
                "message_count": r[2],
                "preview": r[3][:60] if r[3] else "No messages"
            }
            for r in rows
        ]
    }

# ── Export ────────────────────────────────────────────────────

@app.post("/export/{session_id}")
async def export_session(session_id: str):
    """Exports chat session as downloadable HTML report."""
    try:
        history = get_chat_history(session_id)
        if not history:
            raise HTTPException(status_code=404, detail="No messages found")
        filepath = export_chat_to_pdf(history, session_id)
        return FileResponse(
            filepath,
            media_type="text/html",
            filename=f"research_report_{session_id[:8]}.html"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))