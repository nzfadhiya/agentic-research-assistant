from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import requests
import sys
sys.path.insert(0, '.')
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.memory.database import save_chat_message, get_chat_history, save_research

MCP_URL = "http://127.0.0.1:8001"
llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)

SYSTEM_PROMPT = """You are an expert research assistant and general AI assistant.

You can do two things:
1. Research topics using web search results provided to you
2. Handle direct tasks: writing emails, explaining concepts, summarising, answering questions from conversation context

Rules:
- For research queries: use web search results + structure your response with clear headers
- For tasks (write email, explain X, summarise, compare from context): just do the task directly
- Always maintain full conversation context - remember everything discussed
- For follow-up questions, build on what was already discussed
- Be concise and practical, not verbose
- Match response length to question complexity — short questions get short answers"""


def auto_classify(user_message: str, chat_history: list) -> str:
    """
    Automatically decides the best mode for this message.
    Returns: RESEARCH, SIMPLE, or CHAT
    
    RESEARCH — needs deep multi-agent analysis with Wikipedia + web search
    SIMPLE   — needs a quick web search summary  
    CHAT     — can be answered conversationally or from context
    """
    history_summary = ""
    if chat_history:
        history_summary = "\n".join([
            f"{m['role'].upper()}: {m['content'][:120]}"
            for m in chat_history[-3:]
        ])

    prompt = f"""You are a query router. Classify this message into exactly one mode.

Conversation history:
{history_summary if history_summary else "None — first message"}

User message: "{user_message}"

Modes:
- RESEARCH: needs comprehensive analysis, trends, comparisons, in-depth reports (e.g. "analyze AI in healthcare", "comprehensive report on climate change", "compare blockchain vs traditional finance")
- SIMPLE: needs a quick factual answer or short summary (e.g. "what is h1n1", "define machine learning", "how to catch fish")  
- CHAT: casual conversation, follow-up on previous messages, writing tasks, simple questions (e.g. "hi", "what time is it", "explain the risks you mentioned", "write me an email")

Reply with ONLY one word: RESEARCH, SIMPLE, or CHAT"""

    response = llm.invoke([HumanMessage(content=prompt)])
    result = response.content.strip().upper()
    
    if "RESEARCH" in result:
        return "RESEARCH"
    elif "SIMPLE" in result:
        return "SIMPLE"
    return "CHAT"


def needs_web_search(user_message: str, chat_history: list) -> bool:
    """For CHAT mode — decides if a quick web search would help."""
    if not chat_history:
        return True
    
    msg_lower = user_message.lower()
    no_search_signals = [
        "you mentioned", "from what you said", "the risks you",
        "what you found", "explain that", "tell me more about",
        "hi", "hello", "thanks", "write", "draft", "compose",
        "summarise", "summarize", "compare what you"
    ]
    for signal in no_search_signals:
        if signal in msg_lower:
            return False
    
    return True


def run_chat(session_id: str, user_message: str) -> tuple[str, str]:
    """
    Main chat function with automatic mode routing.
    Returns: (response_text, mode_used)
    """
    history = get_chat_history(session_id)
    save_chat_message(session_id, "user", user_message)

    # Auto-classify the message
    mode = auto_classify(user_message, history)
    print(f"[chat_agent] Auto-classified as: {mode}")

    # Route to appropriate handler
    if mode == "RESEARCH":
        return _handle_research(user_message, history, session_id), "research"
    elif mode == "SIMPLE":
        return _handle_simple(user_message, history, session_id), "simple"
    else:
        return _handle_chat(user_message, history, session_id), "chat"


def _handle_research(user_message: str, history: list, session_id: str) -> str:
    """Deep research: web search + Wikipedia + structured report."""
    print(f"[chat_agent] RESEARCH mode: searching web + Wikipedia")
    
    search_context = ""
    wiki_context = ""

    # Web search via MCP
    try:
        r = requests.post(f"{MCP_URL}/tools/web_search",
            json={"query": user_message, "max_results": 5}, timeout=15)
        results = r.json().get("results", [])
        if results:
            search_context = "\n\n".join([
                f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['body']}"
                for r in results
            ])
            print(f"[chat_agent] Got {len(results)} web results")
    except Exception as e:
        print(f"[chat_agent] Web search failed: {e}")

    # Wikipedia via MCP
    try:
        topic = user_message.split("202")[0].strip()
        r2 = requests.post(f"{MCP_URL}/tools/wikipedia_fetch",
            json={"topic": topic, "sentences": 4}, timeout=15)
        wiki_data = r2.json()
        if "summary" in wiki_data:
            wiki_context = wiki_data["summary"]
            print(f"[chat_agent] Got Wikipedia context")
    except Exception as e:
        print(f"[chat_agent] Wikipedia failed: {e}")

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history[-6:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    full_message = f"""{user_message}

WIKIPEDIA BACKGROUND:
{wiki_context if wiki_context else "Not available"}

WEB SEARCH RESULTS:
{search_context if search_context else "Not available"}

Write a comprehensive structured report with:
1. Executive Summary
2. Key Findings (5 bullet points with sources)
3. Analysis
4. Conclusion"""

    messages.append(HumanMessage(content=full_message))
    response = llm.invoke(messages)
    save_chat_message(session_id, "assistant", response.content)
    save_research(user_message, response.content)
    return response.content


def _handle_simple(user_message: str, history: list, session_id: str) -> str:
    """Quick search + concise answer."""
    print(f"[chat_agent] SIMPLE mode: quick search")

    search_context = ""
    try:
        r = requests.post(f"{MCP_URL}/tools/web_search",
            json={"query": user_message, "max_results": 3}, timeout=15)
        results = r.json().get("results", [])
        if results:
            search_context = "\n\n".join([
                f"Title: {r['title']}\nContent: {r['body']}"
                for r in results
            ])
    except Exception as e:
        print(f"[chat_agent] Search failed: {e}")

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history[-4:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    if search_context:
        full_message = f"""{user_message}

Search results:
{search_context}

Give a clear, concise answer in 3-5 sentences max. No formal report structure needed."""
    else:
        full_message = user_message

    messages.append(HumanMessage(content=full_message))
    response = llm.invoke(messages)
    save_chat_message(session_id, "assistant", response.content)
    return response.content


def _handle_chat(user_message: str, history: list, session_id: str) -> str:
    """Conversational response — context first, light search if needed."""
    print(f"[chat_agent] CHAT mode: conversational")

    do_search = needs_web_search(user_message, history)
    search_context = ""

    if do_search:
        try:
            r = requests.post(f"{MCP_URL}/tools/web_search",
                json={"query": user_message, "max_results": 3}, timeout=10)
            results = r.json().get("results", [])
            if results:
                search_context = "\n\n".join([
                    f"Title: {r['title']}\nContent: {r['body']}"
                    for r in results[:2]
                ])
        except:
            pass

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history[-6:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    if search_context:
        full_message = f"{user_message}\n\n[Context from web:]\n{search_context}"
    else:
        full_message = user_message

    messages.append(HumanMessage(content=full_message))
    response = llm.invoke(messages)
    save_chat_message(session_id, "assistant", response.content)
    return response.content