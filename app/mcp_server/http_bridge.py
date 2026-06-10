"""
HTTP bridge for MCP tools.
Agents call these HTTP endpoints.
The bridge calls the actual MCP tool functions.
This keeps FastAPI as the API layer while using real MCP tool definitions.
"""
from fastapi import FastAPI
from pydantic import BaseModel
import sys
sys.path.insert(0, '.')
from app.tools.search import web_search
from app.memory.database import save_research, search_history, get_history
import wikipedia

bridge_app = FastAPI(title="MCP Tool Bridge", version="2.0.0")

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5

class WikiRequest(BaseModel):
    topic: str
    sentences: int = 5

class SaveRequest(BaseModel):
    query: str
    summary: str

class MemoryRequest(BaseModel):
    query: str = ""
    limit: int = 5

@bridge_app.get("/")
async def root():
    return {
        "service": "MCP Tool Bridge",
        "protocol": "MCP over HTTP",
        "tools": ["web_search", "wikipedia_fetch", "save_memory", "search_memory"]
    }

@bridge_app.post("/tools/web_search")
async def tool_web_search(request: SearchRequest):
    print(f"[MCP Bridge] web_search: {request.query}")
    results = web_search(request.query, max_results=request.max_results)
    return {"tool": "web_search", "results": results}

@bridge_app.post("/tools/wikipedia_fetch")
async def tool_wikipedia(request: WikiRequest):
    print(f"[MCP Bridge] wikipedia_fetch: {request.topic}")
    try:
        summary = wikipedia.summary(request.topic, sentences=request.sentences)
        page = wikipedia.page(request.topic)
        return {"tool": "wikipedia_fetch", "summary": summary, "url": page.url, "topic": request.topic}
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            summary = wikipedia.summary(e.options[0], sentences=request.sentences)
            return {"tool": "wikipedia_fetch", "summary": summary, "url": "", "topic": e.options[0]}
        except:
            return {"tool": "wikipedia_fetch", "error": "Disambiguation failed"}
    except Exception as e:
        return {"tool": "wikipedia_fetch", "error": str(e)}

@bridge_app.post("/tools/save_memory")
async def tool_save(request: SaveRequest):
    print(f"[MCP Bridge] save_memory: {request.query[:40]}")
    save_research(request.query, request.summary)
    return {"tool": "save_memory", "status": "saved"}

@bridge_app.post("/tools/search_memory")
async def tool_search_memory(request: MemoryRequest):
    print(f"[MCP Bridge] search_memory: {request.query}")
    if request.query:
        results = search_history(request.query)
    else:
        results = get_history(limit=request.limit)
    return {"tool": "search_memory", "results": results}