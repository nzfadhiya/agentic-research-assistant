from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import requests
import concurrent.futures
import sys
sys.path.insert(0, '.')
from app.config import GROQ_API_KEY, GROQ_MODEL
import os

MCP_URL = os.getenv(
    "MCP_URL",
    "https://agentic-research-assistant-zwwf.onrender.com/mcp"
)
llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)

FAST_SYSTEM = """You are a skilled AI assistant. Handle the task directly and completely.

For writing tasks (emails, letters, messages):
- Write the complete draft immediately
- Professional tone unless casual is requested
- Include subject line for emails

For coding tasks:
- Write complete working code
- Add clear comments
- Explain what the code does briefly after

For analysis/research:
- Give a direct, well-structured answer
- Use bullet points for clarity
- 200-300 words"""

RESEARCH_SYSTEM = """You are a research-backed AI assistant.

For writing tasks:
- Write an alternative version with a different approach or tone
- Show a different style than Agent A

For coding tasks:
- Write an alternative implementation
- Use a different approach, library, or method than Agent A
- Explain the tradeoffs

For research:
- Use the web search results provided
- Cite sources with URLs
- More comprehensive than Agent A
- 400-600 words"""


def agent_a_fast(question: str) -> dict:
    """Fast answer from LLM knowledge. No web search."""
    try:
        response = llm.invoke([
            SystemMessage(content=FAST_SYSTEM),
            HumanMessage(content=question)
        ])
        return {
            "agent": "A",
            "label": "Quick Answer",
            "description": "Direct answer from AI knowledge",
            "response": response.content,
            "sources": []
        }
    except Exception as e:
        return {
            "agent": "A",
            "label": "Quick Answer",
            "description": "Direct answer from AI knowledge",
            "response": f"Error: {str(e)}",
            "sources": []
        }


def agent_b_research(question: str) -> dict:
    """Research answer with web sources via MCP."""
    try:
        search_results = []
        try:
            r = requests.post(
                f"{MCP_URL}/tools/web_search",
                json={"query": question, "max_results": 4},
                timeout=15
            )
            search_results = r.json().get("results", [])
        except Exception as e:
            print(f"[dual_agent] MCP search failed: {e}")

        sources = [
            {"title": r["title"], "url": r["url"]}
            for r in search_results if r.get("url")
        ]

        context = "\n\n".join([
            f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['body']}"
            for r in search_results
        ]) if search_results else "No search results available."

        response = llm.invoke([
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(content=f"Question: {question}\n\nWeb Results:\n{context}\n\nGive a comprehensive sourced answer.")
        ])
        return {
            "agent": "B",
            "label": "Research Answer",
            "description": "Sourced answer from web research",
            "response": response.content,
            "sources": sources
        }
    except Exception as e:
        return {
            "agent": "B",
            "label": "Research Answer",
            "description": "Sourced answer from web research",
            "response": f"Error: {str(e)}",
            "sources": []
        }


def run_dual_agents(question: str) -> dict:
    """Runs both agents in parallel. Returns both responses."""
    print(f"[dual_agent] Running parallel agents for: {question[:50]}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(agent_a_fast, question)
        future_b = executor.submit(agent_b_research, question)
        result_a = future_a.result(timeout=60)
        result_b = future_b.result(timeout=60)
    print(f"[dual_agent] Both agents done")
    return {
        "question": question,
        "agent_a": result_a,
        "agent_b": result_b
    }
