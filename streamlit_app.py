import streamlit as st
import requests
import uuid

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Agentic Research Assistant", layout="wide")

# ── Session state init ────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_mode" not in st.session_state:
    st.session_state.last_mode = ""
if "sessions_list" not in st.session_state:
    st.session_state.sessions_list = []
if "history_loaded" not in st.session_state:
    st.session_state.history_loaded = False
if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None

# Load current session messages from DB on first load
if not st.session_state.history_loaded:
    st.session_state.history_loaded = True
    try:
        r = requests.get(
            API_URL + "/chat/" + st.session_state.session_id + "/history",
            timeout=5
        )
        if r.status_code == 200:
            db_msgs = r.json().get("messages", [])
            if db_msgs:
                st.session_state.messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in db_msgs
                ]
    except:
        pass

# ── Helper functions ──────────────────────────────────────────
def refresh_sessions():
    try:
        r = requests.get(API_URL + "/sessions", timeout=10)
        if r.status_code == 200:
            st.session_state.sessions_list = r.json().get("sessions", [])
    except:
        pass

def load_session_messages(sid):
    try:
        r = requests.get(API_URL + "/chat/" + sid + "/history", timeout=10)
        if r.status_code == 200:
            return [
                {"role": m["role"], "content": m["content"]}
                for m in r.json().get("messages", [])
            ]
    except:
        pass
    return []

# Load sessions list on startup
if not st.session_state.sessions_list:
    refresh_sessions()

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Research Assistant")
    
    
    st.divider()

    # New chat
    if st.button("+ New Chat", use_container_width=True, type="primary"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.last_mode = ""
        st.session_state.history_loaded = True
        st.session_state.pending_delete = None
        refresh_sessions()
        st.rerun()

    # Clear current chat
    if st.button("Clear current chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # Export
    if st.button("Export this chat", use_container_width=True):
        if not st.session_state.messages:
            st.warning("No messages to export yet.")
        else:
            try:
                r = requests.post(
                    API_URL + "/export/" + st.session_state.session_id,
                    timeout=30
                )
                if r.status_code == 200:
                    st.download_button(
                        "Download report",
                        data=r.content,
                        file_name="report.html",
                        mime="text/html",
                        use_container_width=True
                    )
                else:
                    st.error("Export failed.")
            except:
                st.error("API not reachable.")

    st.divider()

    # Mode selection with auto
    st.markdown("**Mode**")
    auto_mode = st.toggle("Auto (recommended)", value=True)
    if not auto_mode:
        mode = st.radio(
            "",
            ["chat", "multi", "simple"],
            captions=[
                "Conversational + follow-ups",
                "Deep 4-agent research",
                "Quick search"
            ],
            label_visibility="collapsed"
        )
    else:
        mode = "chat"
        st.caption("AI picks the best approach automatically.")

    st.divider()

    # Past conversations
    st.markdown("**Your conversations**")

    col_ref, col_close = st.columns(2)
    with col_ref:
        if st.button("Refresh", use_container_width=True):
            refresh_sessions()
            st.session_state.pending_delete = None
            st.rerun()

    # Confirmation dialog for delete
    if st.session_state.pending_delete:
        del_sid = st.session_state.pending_delete
        del_preview = next(
            (s["preview"][:30] for s in st.session_state.sessions_list
             if s["session_id"] == del_sid),
            del_sid[:8]
        )
        st.warning("Delete: " + del_preview + "...?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete", use_container_width=True, type="primary"):
                try:
                    requests.delete(API_URL + "/chat/" + del_sid)
                except:
                    pass
                if del_sid == st.session_state.session_id:
                    st.session_state.session_id = str(uuid.uuid4())
                    st.session_state.messages = []
                    st.session_state.history_loaded = True
                st.session_state.pending_delete = None
                refresh_sessions()
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.pending_delete = None
                st.rerun()

    # Session list
    if st.session_state.sessions_list:
        for s in st.session_state.sessions_list:
            sid = s["session_id"]
            is_current = sid == st.session_state.session_id
            preview = (s.get("preview") or "New conversation")[:30]
            msg_count = s.get("message_count", 0)
            started = s.get("started", "")[:10]

            if is_current:
                st.markdown(
                    "<div style='background:#e8f4fd;border-left:3px solid #1f77b4;"
                    "padding:8px 10px;border-radius:6px;margin:3px 0'>"
                    "<div style='font-size:10px;font-weight:700;color:#1f77b4'>CURRENT</div>"
                    "<div style='font-size:13px;color:#222'>" + preview + "...</div>"
                    "<div style='font-size:11px;color:#888'>" + str(msg_count) + " msgs · " + started + "</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
            else:
                c1, c2 = st.columns([5, 1])
                with c1:
                    if st.button(
                        preview + "...",
                        key="open_" + sid,
                        use_container_width=True,
                        help=str(msg_count) + " messages · " + started
                    ):
                        msgs = load_session_messages(sid)
                        if msgs:
                            st.session_state.session_id = sid
                            st.session_state.messages = msgs
                            st.session_state.last_mode = ""
                            st.session_state.history_loaded = True
                            st.session_state.pending_delete = None
                            st.rerun()
                        else:
                            st.warning("Could not load that conversation.")
                with c2:
                    if st.button("x", key="del_" + sid, help="Delete"):
                        st.session_state.pending_delete = sid
                        st.rerun()
    else:
        st.caption("No past conversations yet.")


# ── MAIN AREA ─────────────────────────────────────────────────
st.markdown("## Agentic Research Assistant")
st.caption("LangGraph + Groq + MCP")

mode_desc = {
    "chat": "Conversational — ask anything, ask follow-ups, full memory.",
    "multi": "Deep research — 4 agents + Wikipedia, structured report.",
    "simple": "Quick — fast single search and summary."
}
if auto_mode:
    st.info("Auto mode ON — AI picks chat, research, or quick answer based on your question.")
else:
    st.info(mode_desc[mode])

if st.session_state.last_mode:
    st.caption("Last response: " + st.session_state.last_mode + " mode")

st.divider()

# Empty state
if not st.session_state.messages:
    st.markdown(
        "<div style='text-align:center;padding:80px 0;color:#aaa'>"
        "<div style='font-size:22px;font-weight:600'>Start a conversation</div>"
        "<div style='font-size:14px;margin-top:10px'>"
        "Ask a research question, write an email, or just chat"
        "</div>"
        "<div style='font-size:13px;margin-top:6px;color:#bbb'>"
        "Tip: chat mode remembers follow-ups, multi mode gives deep reports"
        "</div></div>",
        unsafe_allow_html=True
    )

# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────
user_input = st.chat_input("Ask anything...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                if auto_mode or mode == "chat":
                    r = requests.post(
                        API_URL + "/chat",
                        json={
                            "session_id": st.session_state.session_id,
                            "message": user_input
                        },
                        timeout=120
                    )
                    if r.status_code == 200:
                        data = r.json()
                        response_text = data["response"]
                        st.session_state.last_mode = data.get("mode_used", "chat")
                    else:
                        response_text = "Error " + str(r.status_code) + ": " + r.json().get("detail", "Unknown")

                elif mode == "multi":
                    r = requests.post(
                        API_URL + "/research",
                        json={"query": user_input, "mode": "multi"},
                        timeout=120
                    )
                    if r.status_code == 200:
                        response_text = r.json()["summary"]
                        st.session_state.last_mode = "multi-agent"
                    else:
                        response_text = "Error " + str(r.status_code)

                else:
                    r = requests.post(
                        API_URL + "/research",
                        json={"query": user_input, "mode": "simple"},
                        timeout=120
                    )
                    if r.status_code == 200:
                        response_text = r.json()["summary"]
                        st.session_state.last_mode = "simple"
                    else:
                        response_text = "Error " + str(r.status_code)

            except requests.exceptions.ConnectionError:
                response_text = "Cannot connect to API. Make sure port 8000 is running."
            except requests.exceptions.Timeout:
                response_text = "Request timed out. Try a shorter query."
            except Exception as e:
                response_text = "Something went wrong: " + str(e)

        st.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})
    refresh_sessions()