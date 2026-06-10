import asyncio
import sys
sys.path.insert(0, '.')
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from app.tools.search import web_search
from app.memory.database import save_research, search_history, get_history
import wikipedia

# MCP Server package
# server.py    — real MCP SDK server (stdio protocol)
# http_bridge.py — HTTP wrapper so agents can call MCP tools via REST
# ── Create MCP server ─────────────────────────────────────────
server = Server("research-tools")

# ── Define tools ──────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Registers all available tools with the MCP server.
    When an agent connects, it sees this list and knows
    what tools it can call.
    """
    return [
        types.Tool(
            name="web_search",
            description="Search the web using DuckDuckGo. Returns titles, URLs and content snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="wikipedia_fetch",
            description="Fetch a Wikipedia summary for a topic. Good for background context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic to look up on Wikipedia"
                    },
                    "sentences": {
                        "type": "integer",
                        "description": "Number of sentences to return (default 5)",
                        "default": 5
                    }
                },
                "required": ["topic"]
            }
        ),
        types.Tool(
            name="save_memory",
            description="Save a research result to the database for future reference.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The research query"
                    },
                    "summary": {
                        "type": "string",
                        "description": "The research summary to save"
                    }
                },
                "required": ["query", "summary"]
            }
        ),
        types.Tool(
            name="search_memory",
            description="Search past research stored in the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to search for in past research"
                    }
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Handles tool calls from agents.
    Each tool is called by name with its arguments.
    Returns results as TextContent.
    """
    print(f"[MCP] Tool called: {name} with args: {arguments}")

    if name == "web_search":
        query = arguments["query"]
        max_results = arguments.get("max_results", 5)
        results = web_search(query, max_results=max_results)
        formatted = "\n\n".join([
            f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['body']}"
            for r in results
        ])
        return [types.TextContent(
            type="text",
            text=f"Web search results for '{query}':\n\n{formatted}"
        )]

    elif name == "wikipedia_fetch":
        topic = arguments["topic"]
        sentences = arguments.get("sentences", 5)
        try:
            summary = wikipedia.summary(topic, sentences=sentences)
            page = wikipedia.page(topic)
            return [types.TextContent(
                type="text",
                text=f"Wikipedia: {topic}\n\n{summary}\n\nSource: {page.url}"
            )]
        except wikipedia.exceptions.DisambiguationError as e:
            try:
                summary = wikipedia.summary(e.options[0], sentences=sentences)
                return [types.TextContent(
                    type="text",
                    text=f"Wikipedia: {e.options[0]}\n\n{summary}"
                )]
            except:
                return [types.TextContent(type="text", text="Wikipedia: No article found.")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Wikipedia error: {str(e)}")]

    elif name == "save_memory":
        query = arguments["query"]
        summary = arguments["summary"]
        save_research(query, summary)
        return [types.TextContent(
            type="text",
            text=f"Saved research for: {query}"
        )]

    elif name == "search_memory":
        query = arguments["query"]
        results = search_history(query)
        if results:
            formatted = "\n\n".join([
                f"Query: {r['query']}\nSummary: {r['summary'][:300]}..."
                for r in results
            ])
            return [types.TextContent(
                type="text",
                text=f"Past research found:\n\n{formatted}"
            )]
        return [types.TextContent(type="text", text="No past research found.")]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ── Run server ────────────────────────────────────────────────

async def main():
    print("[MCP] Starting research tools server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())