import streamlit as st
import requests
import uuid
import os
API_URL = os.environ.get("API_URL", "https://agentic-research-assistant-zwwf.onrender.com")

st.set_page_config(page_title="Agentic Research Assistant", layout="wide", initial_sidebar_state="expanded")
defaults = {

    "messages": [],

    "last_mode": "",

    "sessions_list": [],
    "pending_delete": None,

    "logged_in": False,

    "username": "",

    "token": "",

    "dual_mode": False,

    "dual_result": None,

    "doc_ready": False,

    "doc_data": None,

    "doc_name": "",

    "doc_mime": "",

    "doc_preview_content": "",

    "doc_preview_text": "",
    "show_doc_preview": False,
    "last_loaded_sid": "",       # ← add this line
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ← add this whole block below (pin session_id to URL)
if "session_id" not in st.session_state:
    sid = st.query_params.get("s", str(uuid.uuid4()))
    st.session_state.session_id = sid
st.query_params["s"] = st.session_state.session_id


def auth_headers():

    if st.session_state.token:

        return {"Authorization": "Bearer " + st.session_state.token}

    return {}



def refresh_sessions():
    try:
        r = requests.get(API_URL + "/sessions", headers=auth_headers(), timeout=10)
        if r.status_code == 200:
            st.session_state.sessions_list = r.json().get("sessions", [])
    except:
        pass
def load_session(sid):

    try:

        r = requests.get(API_URL + "/chat/" + sid + "/history", headers=auth_headers(), timeout=10)

        if r.status_code == 200:

            return [{"role": m["role"], "content": m["content"]} for m in r.json().get("messages", [])]

    except:

        pass

    return []



if st.session_state.get("last_loaded_sid") != st.session_state.session_id:
    st.session_state.last_loaded_sid = st.session_state.session_id
    try:
        r = requests.get(API_URL + "/chat/" + st.session_state.session_id + "/history", timeout=5)
        if r.status_code == 200:
            db_msgs = r.json().get("messages", [])
            if db_msgs:
                st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in db_msgs]
    except:
        pass



if not st.session_state.sessions_list and st.session_state.logged_in:

    refresh_sessions()



# -- LOGIN PAGE ------------------------------------------------

if not st.session_state.logged_in:

    st.markdown("## Agentic Research Assistant")

    st.caption("LangGraph + Groq + MCP")

    st.divider()



    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        tab1, tab2 = st.tabs(["Login", "Register"])



        with tab1:

            st.subheader("Login")

            login_user = st.text_input("Username", key="login_user")

            login_pass = st.text_input("Password", type="password", key="login_pass")



            if st.button("Login", use_container_width=True, type="primary"):

                if login_user and login_pass:

                    try:

                        r = requests.post(API_URL + "/auth/login",

                            json={"username": login_user, "password": login_pass})

                        if r.status_code == 200:

                            data = r.json()

                            st.session_state.logged_in = True

                            st.session_state.username = data["username"]

                            st.session_state.token = data["token"]

                            st.session_state.sessions_list = []

                            try:

                                rs = requests.get(API_URL + "/sessions",

                                    headers={"Authorization": "Bearer " + data["token"]}, timeout=10)

                                if rs.status_code == 200:

                                    st.session_state.sessions_list = rs.json().get("sessions", [])

                            except:

                                pass

                            st.rerun()

                        else:

                            st.error(r.json().get("detail", "Login failed"))

                    except Exception as e:

                        st.error("API not reachable: " + str(e))

                else:

                    st.warning("Enter username and password")



            st.divider()

            if st.button("Continue without login", use_container_width=True):

                st.session_state.logged_in = True

                st.session_state.username = "guest"

                st.session_state.token = ""

                st.session_state.sessions_list = []

                refresh_sessions()

                st.rerun()



        with tab2:

            st.subheader("Create Account")

            with st.form("register_form"):

                reg_user = st.text_input("Username (min 3 chars)")

                reg_email = st.text_input("Email address")

                reg_pass = st.text_input("Password (min 6 chars)", type="password")

                reg_pass2 = st.text_input("Confirm password", type="password")

                submitted = st.form_submit_button("Create Account", use_container_width=True)



            if submitted:

                if not reg_user or not reg_email or not reg_pass:

                    st.warning("Please fill all fields")

                elif "@" not in reg_email:

                    st.error("Enter a valid email address")

                elif len(reg_pass) < 6:

                    st.error("Password must be at least 6 characters")

                elif reg_pass != reg_pass2:

                    st.error("Passwords do not match")

                else:

                    try:

                        r = requests.post(API_URL + "/auth/register",

                            json={"username": reg_user, "email": reg_email, "password": reg_pass})

                        if r.status_code == 200:

                            st.success("Account created successfully. Please login.")

                        else:

                            st.error(r.json().get("detail", "Registration failed"))

                    except Exception as e:

                        st.error("API not reachable: " + str(e))

    st.stop()



# -- SIDEBAR ---------------------------------------------------

with st.sidebar:

    st.markdown("### Research Assistant")

    st.caption("User: " + st.session_state.username)

    st.caption("Session: " + st.session_state.session_id[:8] + "...")

    st.divider()



    auto_mode = st.toggle("Auto mode (recommended)", value=True)

    if not auto_mode:

        mode = st.radio("Mode", ["chat", "multi", "simple"], label_visibility="collapsed",

            captions=["Conversational", "Deep 4-agent research", "Quick search"])

    else:

        mode = "chat"

        st.caption("Recommended — AI picks chat, research, or quick answer automatically.")



    dual_mode = st.toggle("Dual response mode", value=False,

        help="Two agents answer in parallel. You choose which response to keep.")

    st.session_state.dual_mode = dual_mode



    st.divider()



    if st.button("+ New Chat", use_container_width=True, type="primary"):
        new_sid = str(uuid.uuid4())
        st.session_state.session_id = new_sid
        st.session_state.messages = []
        st.session_state.last_mode = ""
        st.session_state.last_loaded_sid = new_sid   # ← replaces history_loaded
        st.session_state.pending_delete = None
        st.session_state.dual_result = None
        st.session_state.doc_ready = False
        st.session_state.doc_data = None
        st.session_state.doc_preview_content = ""
        st.query_params["s"] = new_sid               # ← pin to URL
        refresh_sessions()
        st.rerun()



    if st.button("Clear screen", use_container_width=True):

        st.session_state.messages = []

        st.session_state.dual_result = None

        st.rerun()



    if st.button("Export chat", use_container_width=True):

        if not st.session_state.messages:

            st.warning("No messages to export yet.")

        else:

            try:

                r = requests.post(API_URL + "/export/" + st.session_state.session_id,

                    headers=auth_headers(), timeout=30)

                if r.status_code == 200:

                    st.download_button("Download report", data=r.content,

                        file_name="report.html", mime="text/html", use_container_width=True)

                else:

                    st.error("Export failed.")

            except:

                st.error("API not reachable.")



    st.divider()



    # -- Documents section -------------------------------------

    st.markdown("**Documents**")

    with st.popover("+ Upload / Generate", use_container_width=True):

        tab_up, tab_gen = st.tabs(["Upload & Analyze", "Generate"])



        with tab_up:

            uploaded_file = st.file_uploader("PDF, DOCX or TXT",

                type=["pdf", "docx", "txt"], label_visibility="collapsed")

            doc_question = st.text_input("What do you want to know?",

                value="Summarize this document", key="doc_question")

            if st.button("Analyze", type="primary", key="analyze_doc", use_container_width=True):

                if not uploaded_file:

                    st.warning("Upload a file first.")

                else:

                    with st.spinner("Analyzing..."):

                        try:

                            r = requests.post(API_URL + "/upload-doc",

                                files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},

                                data={"question": doc_question, "session_id": st.session_state.session_id},

                                headers=auth_headers(), timeout=120)

                            if r.status_code == 200:

                                data = r.json()

                                st.session_state.messages.append({"role": "user",

                                    "content": "Uploaded: **" + uploaded_file.name + "**\n\n" + doc_question})

                                st.session_state.messages.append({"role": "assistant",

                                    "content": data["response"]})

                                refresh_sessions()

                                st.rerun()

                            else:

                                st.error("Error: " + r.json().get("detail", "Failed"))

                        except Exception as e:

                            st.error("Error: " + str(e))



        with tab_gen:

            doc_topic = st.text_input("Topic", placeholder="e.g. AI in Healthcare 2026", key="doc_topic")

            doc_format = st.radio("Format", ["pdf", "docx"], horizontal=True, key="doc_format")



            if st.button("Generate", type="primary", key="gen_doc", use_container_width=True):

                if not doc_topic.strip():

                    st.warning("Enter a topic first.")

                else:

                    with st.spinner("Generating " + doc_format.upper() + "..."):

                        try:

                            r = requests.post(API_URL + "/generate-doc",

                                json={"topic": doc_topic, "format": doc_format,

                                      "session_id": st.session_state.session_id},

                                headers=auth_headers(), timeout=120)

                            if r.status_code == 200:

                                mime = "application/pdf" if doc_format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                                st.session_state.doc_data = r.content

                                st.session_state.doc_name = doc_topic[:30].replace(" ", "_") + "." + doc_format

                                st.session_state.doc_mime = mime

                                st.session_state.doc_ready = True

                                # Store topic for preview

                                st.session_state.doc_preview_content = doc_topic

                                st.session_state.messages.append({"role": "user",

                                    "content": "Generate a " + doc_format.upper() + " about: " + doc_topic})

                                st.session_state.messages.append({"role": "assistant",

                                    "content": "Your **" + doc_format.upper() + "** document on *" + doc_topic + "* is ready. Use the ??? / ?? / ?? / ??? buttons in the sidebar — ??? shows a preview here in the chat, ?? downloads it."})

                                refresh_sessions()

                            else:

                                st.error("Error: " + r.json().get("detail", "Failed"))

                        except Exception as e:

                            st.error("Error: " + str(e))



            if st.session_state.get("doc_ready") and st.session_state.get("doc_data"):

                st.success("Ready: " + st.session_state.get("doc_name", "document"))



                ic1, ic2, ic3, ic4 = st.columns(4)

                with ic1:

                    if st.button("???", key="doc_preview_icon", help="Preview", use_container_width=True):

                        st.session_state.show_doc_preview = not st.session_state.get("show_doc_preview", False)

                with ic2:

                    st.download_button(

                        "??",

                        data=st.session_state["doc_data"],

                        file_name=st.session_state["doc_name"],

                        mime=st.session_state["doc_mime"],

                        help="Download",

                        use_container_width=True,

                        key="doc_dl_icon"

                    )

                with ic3:

                    if st.button("??", key="doc_regen_icon", help="Regenerate", use_container_width=True):

                        st.session_state.doc_ready = False

                        st.session_state.doc_data = None

                        st.session_state.doc_preview_content = ""

                        st.session_state.doc_preview_text = ""

                        st.session_state.show_doc_preview = False

                        st.rerun()

                with ic4:

                    if st.button("???", key="doc_dismiss_icon", help="Dismiss", use_container_width=True):

                        st.session_state.doc_ready = False

                        st.session_state.doc_data = None

                        st.session_state.doc_preview_content = ""

                        st.session_state.doc_preview_text = ""

                        st.session_state.show_doc_preview = False

                        st.rerun()

    st.divider()

    st.markdown("**Research Cache**")

    cache_count = 0

    try:

        cs = requests.get(API_URL + "/cache/stats", headers=auth_headers(), timeout=5).json()

        cache_count = int(cs.get("total_entries", 0))

        last_saved = cs.get("newest")

        st.caption("Saved entries: " + str(cache_count))

        if last_saved:

            st.caption("Last saved: " + str(last_saved)[:16])

        if cache_count == 0:

            st.caption("No research saved yet.")

    except:

        st.caption("Cache: unavailable")



    if st.button("Clear cache", use_container_width=True, key="clear_cache_btn_main"):

        if cache_count == 0:

            st.caption("Nothing to clear.")

        else:

            try:

                r = requests.delete(API_URL + "/cache", headers=auth_headers(), timeout=10)

                if r.status_code == 200:

                    st.success("Cleared " + str(cache_count) + " entries.")

                    st.rerun()

                else:

                    st.error("Failed: " + str(r.status_code))

            except Exception as e:

                st.error("Error: " + str(e))



    st.divider()



    st.markdown("**Session info**")

    st.caption("Messages this session: " + str(len(st.session_state.messages)))

    st.caption("Mode: " + str(st.session_state.get("last_mode", "none")))

    st.caption("Model: llama-3.3-70b-versatile")



    st.divider()

    # -- Past conversations ------------------------------------

    st.markdown("**Past conversations**")

    col_r, col_l = st.columns(2)

    with col_r:

        if st.button("Refresh", use_container_width=True):

            refresh_sessions()

            st.session_state.pending_delete = None

            st.rerun()

    with col_l:

        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.token = ""
            st.session_state.messages = []
            st.session_state.sessions_list = []
            new_sid = str(uuid.uuid4())
            st.session_state.session_id = new_sid
            st.session_state.last_loaded_sid = ""
            st.session_state.doc_ready = False
            st.session_state.doc_data = None
            st.session_state.doc_preview_content = ""
            st.query_params["s"] = new_sid
            st.rerun()
    # Session list with inline delete confirmation

    for s in st.session_state.sessions_list:

        sid = s["session_id"]

        is_cur = sid == st.session_state.session_id

        preview = (s.get("preview") or "New chat")[:26]

        info = str(s.get("message_count", 0)) + " msgs"



        if is_cur:

            st.markdown(

                "<div style='padding:8px 10px;background:#e8f4fd;border-left:3px solid #1f77b4;"

                "border-radius:6px;margin:2px 0'>"

                "<span style='font-size:10px;color:#1f77b4;font-weight:700'>NOW  </span>"

                "<span style='font-size:13px'>" + preview + "</span>"

                "<br><span style='font-size:11px;color:#888'>" + info + "</span></div>",

                unsafe_allow_html=True

            )

        else:

            c1, c2 = st.columns([6, 1])

            with c1:

               if st.button(preview, key="open_" + sid, use_container_width=True, help=info):
                    msgs = load_session(sid)
                    if msgs:
                        st.session_state.session_id = sid
                        st.session_state.messages = msgs
                        st.session_state.last_mode = ""
                        st.session_state.last_loaded_sid = sid    # ← replaces history_loaded
                        st.session_state.pending_delete = None
                        st.session_state.dual_result = None
                        st.query_params["s"] = sid                # ← pin to URL
                        st.rerun()

                    else:

                        st.warning("Could not load conversation.")

            with c2:

                if st.button("x", key="del_" + sid, help="Delete"):

                    st.session_state.pending_delete = sid

                    st.rerun()



            # Inline confirmation right below this session

            if st.session_state.pending_delete == sid:

                st.markdown(

                    "<div style='background:#fff3cd;border:1px solid #ffc107;"

                    "border-radius:6px;padding:6px 10px;margin:2px 0 6px 0;font-size:12px'>"

                    "Delete <b>" + preview[:20] + "</b>?</div>",

                    unsafe_allow_html=True

                )

                dy1, dy2 = st.columns(2)

                with dy1:

                    if st.button("Yes", key="yes_" + sid, use_container_width=True):

                        try:

                            requests.delete(API_URL + "/chat/" + sid, headers=auth_headers())

                        except:

                            pass

                        if sid == st.session_state.session_id:
                            new_sid = str(uuid.uuid4())
                            st.session_state.session_id = new_sid
                            st.session_state.messages = []
                            st.session_state.last_loaded_sid = new_sid  # ← replaces history_loaded
                            st.query_params["s"] = new_sid              # ← pin to URL
                            st.session_state.pending_delete = None

                        refresh_sessions()

                        st.rerun()

                with dy2:

                    if st.button("No", key="no_" + sid, use_container_width=True):

                        st.session_state.pending_delete = None

                        st.rerun()



# -- MAIN AREA -------------------------------------------------

st.markdown("## Agentic Research Assistant")

st.caption("LangGraph + Groq + MCP | Logged in as: **" + st.session_state.username + "**")



if st.session_state.dual_mode:

    st.info("Dual mode ON — two agents answer in parallel. Choose the response you prefer.")

elif auto_mode:

    st.info("Auto mode ON — AI decides: quick chat, deep research, or fast answer.")

else:

    mode_desc = {

        "chat": "Conversational — full memory, follow-ups, comparisons.",

        "multi": "Deep research — 4 agents + Wikipedia for comprehensive reports.",

        "simple": "Quick — fast single search and summary."

    }

    st.info(mode_desc[mode])



if st.session_state.last_mode:

    st.caption("Last response: **" + st.session_state.last_mode + "** mode")



st.divider()



# Empty state

if not st.session_state.messages and not st.session_state.dual_result:

    st.markdown(

        "<div style='text-align:center;padding:60px 0;color:#aaa'>"

        "<div style='font-size:22px;font-weight:600'>Start a conversation</div>"

        "<div style='font-size:14px;margin-top:8px'>Ask anything — research, follow-ups, comparisons</div>"

        "<div style='font-size:12px;margin-top:6px;color:#bbb'>"

        "Dual mode for two parallel answers | Use sidebar to upload or generate documents"

        "</div></div>",

        unsafe_allow_html=True

    )



# Conversation history

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])



# -- DOCUMENT PREVIEW (shown here, toggled from the sidebar) ----

if st.session_state.get("doc_ready") and st.session_state.get("doc_data") and st.session_state.get("show_doc_preview"):

    st.divider()

    st.markdown("#### Preview: " + st.session_state.get("doc_name", "document"))

    if st.session_state.get("doc_preview_content"):

        try:

            from app.config import GROQ_API_KEY, GROQ_MODEL

            from langchain_groq import ChatGroq

            from langchain_core.messages import HumanMessage, SystemMessage

            if not st.session_state.get("doc_preview_text"):

                llm_prev = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)

                prev_resp = llm_prev.invoke([

                    SystemMessage(content="You are a document writer. Generate the content preview for this document topic in structured markdown format with sections and bullet points."),

                    HumanMessage(content="Generate a structured preview of a document about: " + st.session_state["doc_preview_content"])

                ])

                st.session_state["doc_preview_text"] = prev_resp.content

            st.markdown(st.session_state["doc_preview_text"])

        except Exception as e:

            st.info("Preview not available — but your document is ready to download.")

    else:

        st.info("Document is ready. Use the sidebar to download it.")



# -- DUAL RESPONSE UI ------------------------------------------

if st.session_state.dual_result:

    dr = st.session_state.dual_result

    st.markdown("---")

    st.markdown("### Two answers for: *" + dr["question"] + "*")

    st.caption("Choose one to add to your conversation.")



    col_a, col_b = st.columns(2)

    with col_a:

        st.markdown("#### Agent A — " + dr["agent_a"]["label"])

        st.caption(dr["agent_a"]["description"])

        st.markdown(dr["agent_a"]["response"])

        if st.button("Use Agent A", key="pick_a", use_container_width=True, type="primary"):

            st.session_state.messages.append({"role": "user", "content": dr["question"]})

            st.session_state.messages.append({"role": "assistant",

                "content": "**[Agent A]** " + dr["agent_a"]["response"]})

            st.session_state.dual_result = None

            refresh_sessions()

            st.rerun()



    with col_b:

        st.markdown("#### Agent B — " + dr["agent_b"]["label"])

        st.caption(dr["agent_b"]["description"])

        st.markdown(dr["agent_b"]["response"])

        if dr["agent_b"]["sources"]:

            st.markdown("**Sources:**")

            for src in dr["agent_b"]["sources"]:

                st.markdown("- [" + src["title"][:55] + "](" + src["url"] + ")")

        if st.button("Use Agent B", key="pick_b", use_container_width=True, type="primary"):

            st.session_state.messages.append({"role": "user", "content": dr["question"]})

            st.session_state.messages.append({"role": "assistant",

                "content": "**[Agent B]** " + dr["agent_b"]["response"]})

            st.session_state.dual_result = None

            refresh_sessions()

            st.rerun()



    col_d, col_e, col_f = st.columns([1, 1, 1])

    with col_e:

        if st.button("Discard both", use_container_width=True):

            st.session_state.dual_result = None

            st.rerun()



# -- CHAT INPUT ------------------------------------------------

user_input = st.chat_input("Ask anything — research, follow-ups, definitions, comparisons...")



if user_input:

    if st.session_state.dual_mode:

        with st.spinner("Two agents thinking in parallel..."):

            try:

                r = requests.post(API_URL + "/dual", json={"question": user_input},

                    headers=auth_headers(), timeout=120)

                if r.status_code == 200:

                    st.session_state.dual_result = r.json()

                    st.rerun()

                else:

                    st.error("Dual agent error " + str(r.status_code) + ": " + r.json().get("detail", ""))

            except requests.exceptions.Timeout:

                st.error("Request timed out.")

            except Exception as e:

                st.error("Error: " + str(e))

    else:

        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):

            st.markdown(user_input)



        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                try:

                    if auto_mode or mode == "chat":

                        r = requests.post(API_URL + "/chat",

                            json={"session_id": st.session_state.session_id, "message": user_input},

                            headers=auth_headers(), timeout=120)

                        if r.status_code == 200:

                            data = r.json()

                            response_text = data["response"]

                            st.session_state.last_mode = data.get("mode_used", "chat")

                        else:

                            response_text = "Error " + str(r.status_code) + ": " + r.json().get("detail", "Unknown")

                    elif mode == "multi":
                        r = requests.post(API_URL + "/research",
                            json={"query": user_input, "mode": "multi",
                                  "session_id": st.session_state.session_id},  # ← add this
                            headers=auth_headers(), timeout=120)
                        if r.status_code == 200:
                            response_text = r.json()["summary"]
                            st.session_state.last_mode = "multi-agent"
                        else:
                            response_text = "Error " + str(r.status_code)
                    else:
                        r = requests.post(API_URL + "/research",
                            json={"query": user_input, "mode": "simple",
                                  "session_id": st.session_state.session_id},  # ← add this
                            headers=auth_headers(), timeout=120)
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