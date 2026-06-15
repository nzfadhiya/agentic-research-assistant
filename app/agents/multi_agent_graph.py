from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import operator
import requests
import sys
sys.path.insert(0, '.')
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.memory.database import init_db, save_research, search_history

MCP_URL = "http://127.0.0.1:8000/mcp"
llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)

# ── State ─────────────────────────────────────────────────────

class MultiAgentState(TypedDict):
    query: str
    search_results: list[dict]
    wiki_result: dict
    draft_summary: str
    final_report: str
    from_cache: bool
    messages: Annotated[list, operator.add]

# ── Agents ────────────────────────────────────────────────────

def orchestrator_agent(state: MultiAgentState) -> dict:
    """
    Agent 1: Checks memory cache first.
    If cached — skip to critique with existing summary.
    If not — proceed to search + wikipedia.
    """
    print(f"[orchestrator] Query: {state['query']}")
    past = search_history(state["query"])
    if past:
        print(f"[orchestrator] Cache hit — skipping search")
        return {
            "draft_summary": past[0]["summary"],
            "from_cache": True,
            "search_results": [],
            "wiki_result": {}
        }
    print("[orchestrator] No cache — starting research")
    return {"from_cache": False}


def search_agent(state: MultiAgentState) -> dict:
    """
    Agent 2: Calls MCP web_search tool via HTTP.
    Gets 5 web results for the query.
    """
    print(f"[search_agent] Searching via MCP: {state['query']}")
    r = requests.post(f"{MCP_URL}/tools/web_search", json={
        "query": state["query"],
        "max_results": 5
    })
    results = r.json().get("results", [])
    print(f"[search_agent] Got {len(results)} results")
    return {"search_results": results}


def wikipedia_agent(state: MultiAgentState) -> dict:
    """
    Agent 3: Calls MCP wikipedia_fetch tool via HTTP.
    Gets background context from Wikipedia.
    """
    # Strip year and extra words for better Wikipedia matching
    wiki_topic = state["query"].split("202")[0].strip().rstrip("applications").strip()
    r = requests.post(f"{MCP_URL}/tools/wikipedia_fetch", json={
        "topic": wiki_topic,
        "sentences": 5
    })
    result = r.json()
    if "error" in result:
        print(f"[wikipedia_agent] Wikipedia error: {result['error']}")
        return {"wiki_result": {"summary": "No Wikipedia article found.", "url": ""}}
    print(f"[wikipedia_agent] Got Wikipedia summary ({len(result.get('summary',''))} chars)")
    return {"wiki_result": result}


def critique_agent(state: MultiAgentState) -> dict:
    """
    Agent 4: Takes web results + wikipedia, writes final polished report.
    If from cache, improves existing summary instead.
    """
    print(f"[critique_agent] Writing final report")

    if state.get("from_cache"):
        prompt = f"""You are an expert research editor. 
Improve and expand this existing research summary about: {state['query']}

Existing summary:
{state['draft_summary']}

Rewrite it to be more structured, clear, and comprehensive.
Include: Key Findings, Background, Analysis, Conclusion."""
    else:
        web_context = "\n\n".join([
            f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['body']}"
            for r in state["search_results"]
        ])
        wiki_summary = state["wiki_result"].get("summary", "Not available")
        wiki_url = state["wiki_result"].get("url", "")

        prompt = f"""You are an expert research analyst. Write a comprehensive report about: {state['query']}

WIKIPEDIA BACKGROUND:
{wiki_summary}
Source: {wiki_url}

WEB SEARCH RESULTS:
{web_context}

Write a structured report with:
1. Executive Summary (2-3 sentences)
2. Background (from Wikipedia)
3. Key Findings (5 bullet points from web results)
4. Analysis (your synthesis)
5. Conclusion
6. Sources cited

Be factual and cite all sources as clickable markdown links using this format: [Article Title](full_url)
Example: [Top AI Trends 2026](https://example.com/article)
Never write sources as plain text — always use the markdown link format."""

    response = llm.invoke([HumanMessage(content=prompt)])
    print(f"[critique_agent] Report generated ({len(response.content)} chars)")
    return {"final_report": response.content}


def save_agent(state: MultiAgentState) -> dict:
    """
    Agent 5: Saves final report to database via MCP.
    Skips if result came from cache.
    """
    if not state.get("from_cache") and state.get("final_report"):
        requests.post(f"{MCP_URL}/tools/save_memory", json={
            "query": state["query"],
            "summary": state["final_report"]
        })
        print("[save_agent] Saved to memory via MCP")
    else:
        print("[save_agent] Cache hit — skipping save")
    return {}

# ── Routing ───────────────────────────────────────────────────

def route_after_orchestrator(state: MultiAgentState) -> str:
    if state.get("from_cache"):
        return "critique"
    return "search"

# ── Build graph ───────────────────────────────────────────────

def build_multi_agent_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("orchestrator", orchestrator_agent)
    graph.add_node("search", search_agent)
    graph.add_node("wikipedia", wikipedia_agent)
    graph.add_node("critique", critique_agent)
    graph.add_node("save", save_agent)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"search": "search", "critique": "critique"}
    )

    # search and wikipedia run, then both feed into critique
    graph.add_edge("search", "wikipedia")
    graph.add_edge("wikipedia", "critique")
    graph.add_edge("critique", "save")
    graph.add_edge("save", END)

    return graph.compile()

# ── Run function ──────────────────────────────────────────────

def run_multi_agent(query: str) -> str:
    init_db()
    app = build_multi_agent_graph()

    initial_state = {
        "query": query,
        "search_results": [],
        "wiki_result": {},
        "draft_summary": "",
        "final_report": "",
        "from_cache": False,
        "messages": []
    }

    print(f"\n{'='*50}")
    print(f"Multi-agent research: {query}")
    print(f"{'='*50}\n")

    result = app.invoke(initial_state)

    print(f"\n{'='*50}")
    print("FINAL REPORT:")
    print(f"{'='*50}")
    print(result["final_report"])
    try:
        from app.memory.database import save_research
        save_research(query, result["final_report"])
    except Exception as e:
        print(f"[multi_agent] Cache save failed: {e}")

    return result["final_report"]