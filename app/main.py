from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import sqlite3
import requests
import sys
import traceback
sys.path.insert(0, '.')
from app.agents.research_graph import run_research
from app.agents.multi_agent_graph import run_multi_agent
from app.agents.chat_agent import run_chat
from app.agents.dual_agent import run_dual_agents
from app.memory.database import (
    get_history, init_db, get_chat_history,
    clear_chat_session, save_chat_message,
    get_user_sessions, clear_research_cache,
    get_cache_stats,save_research
)
from app.tools.doc_reader import extract_text
from app.tools.doc_generator import create_pdf, create_docx
from app.agents.chat_agent import run_chat
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.tools.pdf_export import export_chat_to_pdf
from app.auth.auth import register_user, login_user, get_current_user
from app.config import GROQ_API_KEY, GROQ_MODEL, DB_PATH
from app.mcp_server.http_bridge import bridge_app
import os

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:" + os.environ.get("PORT", "8000") + "/mcp")
app = FastAPI(
    title="Agentic Research Assistant",
    description="Multi-agent research system using LangGraph + Groq + MCP",
    version="3.0.0"
)

app.mount("/mcp", bridge_app)

security = HTTPBearer(auto_error=False)


# ── Models ────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ResearchRequest(BaseModel):
    query: str
    mode: str = "multi"
    session_id: str = "global-research"  # add this


class ResearchResponse(BaseModel):
    query: str
    summary: str
    mode: str
    status: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class DualRequest(BaseModel):
    question: str


class DocRequest(BaseModel):
    topic: str
    format: str = "pdf"
    session_id: str = "doc-session"


# ── Auth helpers ──────────────────────────────────────────────


def get_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[str]:
    if not credentials:
        return None
    try:
        return get_current_user(credentials.credentials)
    except:
        return None


def get_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Login required")
    username = get_current_user(credentials.credentials)
    if not username:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")
    return username


# ── Startup ───────────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    init_db()
    print("[API] Started. Database ready.")


# ── Health ────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Agentic Research Assistant",
        "version": "3.0.0"
    }


# ── Auth endpoints ────────────────────────────────────────────


@app.post("/auth/register")
async def register(req: RegisterRequest):
    """
    Register new user.
    - Username must be unique
    - Email must be unique (same email cannot register with different username)
    - Password minimum 6 characters
    """
    result = register_user(req.username.strip(), req.email.strip(), req.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": result["message"]}


@app.post("/auth/login")
async def login(req: LoginRequest):
    """Login with username + password. Returns JWT token valid 24 hours."""
    result = login_user(req.username.strip(), req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return {"token": result["token"], "username": result["username"]}


# ── Research endpoints ────────────────────────────────────────

@app.post("/research", response_model=ResearchResponse)
def research(
    request: ResearchRequest,
    username: str = Depends(get_user_optional)
):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    casual_signals = ["hi", "hello", "hey", "helo", "hii", "hiii", "how are", "what time", 
                  "who are you", "thanks", "bye", "ok", "okay", "sup", "yo", "good morning",
                  "good evening", "good night","who are you","what","what happened","so what","You’re lying",
]
    is_casual = any(request.query.lower().strip().startswith(s) for s in casual_signals)
    if is_casual:
        return ResearchResponse(
            query=request.query,
            summary="Hi there! For casual chat, please use Auto mode — it handles greetings and conversation much better than research mode.",
            mode="chat",
            status="success"
        )
    actual_mode = request.mode
    print("========== RESEARCH START ==========")
    print("Query:", request.query)
    print("Mode:", actual_mode)

    # define is_memory_query FIRST
    memory_signals = [
        "what was my name", "what is my name", "my name",
        "what did i say", "what did you say", "you just said",
        "short version", "summarize what you", "summarize above",
        "give a short version", "from above", "you mentioned",
        "what we discussed", "earlier you", "previous answer",
        "who are you", "what are you", "who r u", "what r u",
        "are you ai", "are you a bot", "tell me about yourself",
        "write mail", "write a mail", "write email", "write an email",
        "generate mail", "mail template", "email template",
        "draft a mail", "draft an email", "compose a mail",
    ]
    is_memory_query = any(sig in request.query.lower() for sig in memory_signals)

    # NOW build history context
    history = get_chat_history(request.session_id)
    history_context = ""
    if history:
        history_context = "\n".join([
            f"{m['role'].upper()}: {m['content'][:300]}"
            for m in history[-6:]
        ])

    query_with_context = request.query
    if is_memory_query and history_context:
        query_with_context = f"Conversation so far:\n{history_context}\n\nNew request: {request.query}"
    #if history_context and not is_memory_query:
        #query_with_context = f"Conversation so far:\n{history_context}\n\nNew request: {request.query}"

    try:
        if is_memory_query and history_context:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage
            llm_direct = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)
            direct_response = llm_direct.invoke([
                SystemMessage(content="You are a helpful assistant. Answer using only the conversation history provided. Do not search the web."),
                HumanMessage(content=query_with_context)
            ])
            summary = direct_response.content
        elif actual_mode == "multi":
            print("Calling run_multi_agent()")
            summary = run_multi_agent(query_with_context)
        else:
            summary = run_research(query_with_context)

        try:
            save_research(query=request.query, summary=summary, username=username or "anonymous")
        except Exception as cache_err:
            print(f"[research] Cache save failed: {cache_err}")

        save_chat_message(request.session_id, "user", request.query, username or "anonymous")
        save_chat_message(request.session_id, "assistant", summary, username or "anonymous")

        return ResearchResponse(
            query=request.query,
            summary=summary,
            mode=actual_mode,
            status="success"
        )
    except Exception as e:
        print("========== ERROR ==========")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/history")
async def history(username: str = Depends(get_user_optional)):
    records = get_history(limit=10, username=username)
    return {"count": len(records), "history": records}


# ── Chat endpoints ────────────────────────────────────────────


@app.post("/chat")
def chat(
    request: ChatRequest,
    username: str = Depends(get_user_optional)
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        actual_username = username or "anonymous"
        result = run_chat(request.session_id, request.message, actual_username)
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
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, AIMessage


    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")


    llm_stream = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, streaming=True)
    history = get_chat_history(request.session_id)
    save_chat_message(request.session_id, "user", request.message)


    from app.agents.chat_agent import SYSTEM_PROMPT
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
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


# ── Sessions ──────────────────────────────────────────────────


@app.get("/sessions")
async def get_sessions(username: str = Depends(get_user_optional)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if username and username != "anonymous":
        cursor.execute("""
            SELECT session_id, MIN(created_at), COUNT(*),
                   MIN(CASE WHEN role='user' THEN content END),
                   MAX(created_at)
            FROM chat_sessions WHERE username = ?
            GROUP BY session_id ORDER BY MAX(created_at) DESC LIMIT 20
        """, (username,))
    else:
        cursor.execute("""
            SELECT session_id, MIN(created_at), COUNT(*),
                   MIN(CASE WHEN role='user' THEN content END),
                   MAX(created_at)
            FROM chat_sessions WHERE username = 'anonymous'
            AND session_id = ?
            GROUP BY session_id ORDER BY MAX(created_at) DESC LIMIT 20
        """, (username or "",))
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


# ── Dual agent ────────────────────────────────────────────────


@app.post("/dual")
def dual(req: DualRequest):
    """
    Returns two parallel responses for the same question.
    Agent A: Fast answer from LLM knowledge.
    Agent B: Research answer with web sources and links.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        result = run_dual_agents(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Cache ─────────────────────────────────────────────────────


# ── Cache ─────────────────────────────────────────────────────

@app.get("/cache/stats")
async def cache_stats(username: str = Depends(get_user_optional)):
    return get_cache_stats()


@app.delete("/cache")
async def clear_cache(username: str = Depends(get_user_optional)):
    clear_research_cache()
    return {"status": "cache cleared"}


#------------------------


@app.post("/generate-doc")
def generate_doc(req: DocRequest, username: str = Depends(get_user_optional)):
    """
    Generates a PDF or DOCX document on any topic.
    Agent researches the topic and creates a structured document.
    """
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    try:
        # Use LLM to generate structured content
        from app.config import GROQ_API_KEY, GROQ_MODEL
        llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)


        # Search for content first
        search_context = ""
        try:
            r = requests.get(f"{MCP_URL}/tools/web_search",
                json={"query": req.topic, "max_results": 4}, timeout=15)
        except:
            pass


        try:
            import requests as req_lib
            sr = req_lib.post(f"{MCP_URL}/tools/web_search",
                json={"query": req.topic, "max_results": 4}, timeout=15)
            results = sr.json().get("results", [])
            if results:
                search_context = "\n\n".join([
                    f"Title: {r['title']}\nContent: {r['body']}"
                    for r in results
                ])
        except:
            pass


        prompt = f"""Create a comprehensive, well-structured document about: {req.topic}


{f"Using these sources: {search_context}" if search_context else ""}


Structure the document with:
# {req.topic}


## Executive Summary
[2-3 sentence overview]


## Introduction
[Background and context]


## Key Points
[5-7 main points as bullet points]


## Detailed Analysis
[Comprehensive coverage of the topic]


## Conclusion
[Summary and key takeaways]


Write in a professional, informative tone. Use markdown formatting."""


        response = llm.invoke([
            SystemMessage(content="You are an expert document writer. Create comprehensive, well-structured documents."),
            HumanMessage(content=prompt)
        ])
        content = response.content


        # Generate file
        if req.format.lower() == "docx":
            filepath = create_docx(req.topic, content, req.session_id)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        else:
            filepath = create_pdf(req.topic, content, req.session_id)
            media_type = "application/pdf"
            ext = "pdf"


        filename = req.topic[:30].replace(" ", "_") + "." + ext
        return FileResponse(filepath, media_type=media_type, filename=filename)


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#reader
@app.post("/upload-doc")
async def upload_doc(
    file: UploadFile = File(...),
    question: str = Form(default="Summarize this document"),
    session_id: str = Form(default="upload-session"),
    username: str = Depends(get_user_optional)
):
    """
    Upload a PDF/DOCX/TXT file.
    Agent reads it and answers your question about it.
    """
    try:
        file_bytes = await file.read()
        text = extract_text(file_bytes, file.filename)


        if not text or len(text) < 50:
            raise HTTPException(status_code=400, detail="Could not extract text from file")


        # Truncate if too long for context window
        max_chars = 80000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Document truncated — showing first 80,000 characters]"


        from app.config import GROQ_API_KEY, GROQ_MODEL
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage


        llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)


        prompt = f"""Document content:
---
{text}
---


User question: {question}


Answer the question based on the document content above. 
Be specific, cite relevant sections where possible.
If asked to summarize, give a structured summary with key points."""


        response = llm.invoke([
            SystemMessage(content="You are a document analysis expert. Read documents carefully and answer questions accurately based on their content."),
            HumanMessage(content=prompt)
        ])


        # Save to chat history
        save_chat_message(
            session_id,
            "user",
            f"[Uploaded: {file.filename}] {question}",
            username or "anonymous"
        )
        save_chat_message(
            session_id,
            "assistant",
            response.content,
            username or "anonymous"
        )


        return {
            "filename": file.filename,
            "question": question,
            "response": response.content,
            "chars_extracted": len(text)
        }


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
