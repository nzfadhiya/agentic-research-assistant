from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import requests
import sys
sys.path.insert(0, '.')
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.memory.database import save_chat_message, get_chat_history, save_research

MCP_URL = "http://127.0.0.1:8001"
llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)

SYSTEM_PROMPT = """You are a friendly, expert AI assistant with two sides that work together seamlessly.

CASUAL SIDE — for greetings, small talk, personal questions:
- Be warm, friendly, and human-like
- Short responses for simple things — don't over-explain
- Handle typos gracefully — understand what the person meant
- "u ar u" means "who are you", "hi da chatbot" gets a warm hi back
- For jokes or playful questions like "can i kill you" — respond with humour, not a formal analysis
- For time/date questions — say you cannot access real-time data directly, suggest checking their device
- NEVER do a web search for greetings or casual chat

RESEARCH AND TASK SIDE — for information, facts, topics, writing, tasks:
- You can do two things:
  1. Research topics using web search results provided to you
  2. Handle direct tasks: writing emails, explaining concepts, summarising, answering questions from conversation context
- For research queries: use web search results and structure your response with clear headers and cite sources by title
- For tasks (write email, explain X, summarise, compare from context): just do the task directly, no preamble, no mentioning of searching
- Be concise and practical, not verbose
- Match response length to question complexity — short question gets short answer, complex research gets full structured response
- Correct typos in queries before answering — cvide means covid, machne lerning means machine learning, coronaviru means coronavirus — always answer the corrected version, never search the misspelled version

MEMORY RULES — always apply without exception:
- Remember EVERYTHING mentioned in this conversation
- If user said their name, always use it naturally in responses
- Never say "you didn't mention" if they clearly did earlier in the chat
- Build on previous messages naturally — never repeat what was already established
- For follow-up questions, use conversation context first before deciding to search

TONE: Warm, helpful, occasionally witty. Never robotic or overly formal for casual chat."""

def auto_classify(user_message: str, chat_history: list) -> str:
    msg_lower = user_message.lower().strip()
    
    # Hard-coded casual patterns — never classify these as RESEARCH
    casual_patterns = [
        # Greetings
        "hi", "hello", "hey", "hii", "hiii", "hiiii", "howdy", "sup", "yo",
        "good morning", "good evening", "good night", "good afternoon",
        # Farewells  
        "bye", "goodbye", "see you", "take care", "later", "cya",
        # Acknowledgements
        "thanks", "thank you", "thanku", "thx", "ok", "okay", "sure",
        "yes", "no", "got it", "understood", "cool", "great", "nice",
        "wow", "lol", "haha", "😊", "👍",
        # About the bot
        "who are you", "what are you", "how are you", "how r u",
        "u ar u", "who r u", "what r u", "are you ai", "are you a bot",
        "what is your name", "whats ur name", "tell me about yourself",
        # Casual questions
        "what time", "what day", "what date", "what is today",
        "what is tomorrow", "what was yesterday", "what will tomorrow",
        "can i kill you", "can you die", "are you alive",
        # Short unclear inputs
        "da", "na", "ya", "nah", "yep", "nope", "hmm", "ugh",
    ]
    for pattern in casual_patterns:
        if msg_lower == pattern or msg_lower.startswith(pattern + " ") or msg_lower.startswith(pattern + ","):
            print(f"[classifier] Hard-coded CASUAL: {user_message}")
            return "CHAT"

    history_summary = ""
    if chat_history:
        history_summary = "\n".join([
            f"{m['role'].upper()}: {m['content'][:120]}"
            for m in chat_history[-3:]
        ])

    prompt = f"""Classify this message into exactly one mode.

Conversation history:
{history_summary if history_summary else "None"}

User message: "{user_message}"

RESEARCH: needs comprehensive analysis, deep report, trends (e.g. "analyze AI in healthcare 2026", "comprehensive report on climate")
SIMPLE: needs quick factual answer (e.g. "what is photosynthesis", "define blockchain", "how to cook pasta")
CHAT: casual, greeting, follow-up, writing task, short question (e.g. "hi", "explain the risks you mentioned", "write an email")

Reply ONE word only: RESEARCH, SIMPLE, or CHAT"""

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


def run_chat(session_id: str, user_message: str, username: str = "anonymous") -> tuple[str, str]:
    """Main chat function with automatic mode routing."""
    history = get_chat_history(session_id)
    save_chat_message(session_id, "user", user_message, username)

    mode = auto_classify(user_message, history)
    print(f"[chat_agent] Auto-classified as: {mode}")

    if mode == "RESEARCH":
        return _handle_research(user_message, history, session_id, username), "research"
    elif mode == "SIMPLE":
        return _handle_simple(user_message, history, session_id, username), "simple"
    else:
        return _handle_chat(user_message, history, session_id, username), "chat"


def _handle_research(user_message: str, history: list, session_id: str, username: str = "anonymous") -> str:
    print(f"[chat_agent] RESEARCH mode: searching web + Wikipedia")
    search_context = ""
    wiki_context = ""

    try:
        r = requests.post(f"{MCP_URL}/tools/web_search",
            json={"query": user_message, "max_results": 5}, timeout=15)
        results = r.json().get("results", [])
        if results:
            search_context = "\n\n".join([
                f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['body']}"
                for r in results
            ])
    except Exception as e:
        print(f"[chat_agent] Web search failed: {e}")

    try:
        topic = user_message.split("202")[0].strip()
        r2 = requests.post(f"{MCP_URL}/tools/wikipedia_fetch",
            json={"topic": topic, "sentences": 4}, timeout=15)
        wiki_data = r2.json()
        if "summary" in wiki_data:
            wiki_context = wiki_data["summary"]
    except Exception as e:
        print(f"[chat_agent] Wikipedia failed: {e}")

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history[-20:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    full_message = f"""{user_message}

WIKIPEDIA BACKGROUND:
{wiki_context if wiki_context else "Not available"}

WEB SEARCH RESULTS:
{search_context if search_context else "Not available"}

Write a detailed, in-depth research report on this topic, formatted in markdown:

# [Topic Title]

## Executive Summary
2-3 sentences giving a high-level overview.

## Key Findings
5-7 bullet points, each a specific fact or finding. Where a finding comes from
one of the web search results above, mention the source title in parentheses
at the end of that bullet.

## Analysis
At least 3-4 substantial paragraphs of in-depth discussion — context, implications,
different angles, trends, and any debates or nuances. Go beyond restating the
findings; explain why they matter and how they connect to each other.

## Conclusion
A summarizing paragraph with the key takeaways and, where relevant, an outlook
on what might come next.

Be thorough and substantive — this should read as a comprehensive report, not
a short summary."""

    messages.append(HumanMessage(content=full_message))
    response = llm.invoke(messages)
    save_chat_message(session_id, "assistant", response.content, username)
    save_research(user_message, response.content, username)
    return response.content


def _handle_simple(user_message: str, history: list, session_id: str, username: str = "anonymous") -> str:
    print(f"[chat_agent] SIMPLE mode: quick search")
    search_context = ""
    try:
        r = requests.post(f"{MCP_URL}/tools/web_search",
            json={"query": user_message, "max_results": 3}, timeout=15)
        results = r.json().get("results", [])
        if results:
            search_context = "\n\n".join([
                f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['body']}"
                for r in results
            ])
    except Exception as e:
        print(f"[chat_agent] Search failed: {e}")

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history[-20:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    if search_context:
        full_message = (
            f"{user_message}\n\n"
            f"[Web search results:]\n{search_context}\n\n"
            "Answer in short bullet points (3-5 points), each covering one key fact. "
            "Do not put links or citations inside the bullet points. "
            "After the bullet points, add a section titled 'Sources:' listing each "
            "source as a markdown link in the format [Title](URL), one per line."
        )
    else:
        full_message = user_message

    messages.append(HumanMessage(content=full_message))
    response = llm.invoke(messages)
    save_chat_message(session_id, "assistant", response.content, username)
    return response.content


def _handle_chat(user_message: str, history: list, session_id: str, username: str = "anonymous") -> str:
    print(f"[chat_agent] CHAT mode: conversational")
    search_context = ""

    if needs_web_search(user_message, history):
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
    for msg in history[-20:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    if search_context:
        full_message = f"{user_message}\n\n[Context:]\n{search_context}"
    else:
        full_message = user_message

    messages.append(HumanMessage(content=full_message))
    response = llm.invoke(messages)
    save_chat_message(session_id, "assistant", response.content, username)
    return response.content