from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END # pyright: ignore[reportMissingImports]
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import operator
import sys
sys.path.insert(0, '.')
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.tools.search import web_search
from app.memory.database import init_db, save_research, search_history

# ── 1. Define state ──────────────────────────────────────────

class ResearchState(TypedDict):
    query: str
    search_results: list[dict]
    summary: str
    from_cache: bool
    messages: Annotated[list, operator.add]

# ── 2. Initialise LLM ────────────────────────────────────────

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)

# ── 3. Define nodes ──────────────────────────────────────────

def check_memory_node(state: ResearchState) -> dict:
    """
    Node 0: Checks if this topic was researched before.
    If yes, returns cached summary and skips search+summarise.
    If no, continues to search_node.
    """
    print(f"[memory_node] Checking history for: {state['query']}")
    past = search_history(state["query"])
    if past:
        print(f"[memory_node] Found cached result from: {past[0]['created_at']}")
        return {
            "summary": past[0]["summary"],
            "from_cache": True,
            "search_results": []
        }
    print("[memory_node] No cache found, proceeding to search")
    return {"from_cache": False}


def search_node(state: ResearchState) -> dict:
    """
    Node 1: Searches the web for the query.
    Skipped if result came from cache.
    """
    print(f"[search_node] Searching for: {state['query']}")
    results = web_search(state["query"], max_results=5)
    print(f"[search_node] Found {len(results)} results")
    return {"search_results": results}


def summarise_node(state: ResearchState) -> dict:
    """
    Node 2: Sends search results to Groq, gets structured summary.
    """
    print(f"[summarise_node] Summarising {len(state['search_results'])} results")

    context = "\n\n".join([
        f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['body']}"
        for r in state["search_results"]
    ])

    prompt = f"""You are a research assistant. Based on the search results below,
write a clear, structured research summary about: {state['query']}

Search Results:
{context}

Write a summary with:
1. Key findings (3-5 bullet points)
2. Main themes
3. Conclusion

Be factual and cite sources as clickable markdown links using this format: [Article Title](full_url)
Example: According to [AI Trends 2026](https://example.com/article), ..."""

    response = llm.invoke([HumanMessage(content=prompt)])
    print(f"[summarise_node] Summary generated ({len(response.content)} chars)")
    return {"summary": response.content}


def save_node(state: ResearchState) -> dict:
    """
    Node 3: Saves the summary to SQLite database.
    Skipped if result came from cache (already saved before).
    """
    if not state.get("from_cache"):
        save_research(state["query"], state["summary"])
        print("[save_node] Research saved to database")
    else:
        print("[save_node] Cache hit — skipping save")
    return {}


# ── 4. Routing function ──────────────────────────────────────

def route_after_memory(state: ResearchState) -> str:
    """
    After checking memory:
    - If cached result found → go straight to save_node
    - If not cached → go to search_node
    """
    if state.get("from_cache"):
        return "save"
    return "search"


# ── 5. Build the graph ───────────────────────────────────────

def build_research_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("check_memory", check_memory_node)
    graph.add_node("search", search_node)
    graph.add_node("summarise", summarise_node)
    graph.add_node("save", save_node)

    graph.set_entry_point("check_memory")

    # Conditional routing after memory check
    graph.add_conditional_edges(
        "check_memory",
        route_after_memory,
        {
            "search": "search",
            "save": "save"
        }
    )

    graph.add_edge("search", "summarise")
    graph.add_edge("summarise", "save")
    graph.add_edge("save", END)

    return graph.compile()


# ── 6. Run function ──────────────────────────────────────────

def run_research(query: str) -> str:
    init_db()
    app = build_research_graph()

    initial_state = {
        "query": query,
        "search_results": [],
        "summary": "",
        "from_cache": False,
        "messages": []
    }

    print(f"\n{'='*50}")
    print(f"Starting research: {query}")
    print(f"{'='*50}\n")

    result = app.invoke(initial_state)

    print(f"\n{'='*50}")
    print("FINAL SUMMARY:")
    print(f"{'='*50}")
    print(result["summary"])
    try:
        from app.memory.database import save_research
        save_research(query, result["summary"])
    except Exception as e:
        print(f"[research_graph] Cache save failed: {e}")

    return result["summary"]