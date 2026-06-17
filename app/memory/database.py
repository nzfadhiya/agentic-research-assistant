import sqlite3
import os
import sys
sys.path.insert(0, '.')
from app.config import DB_PATH

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def ph():
    """Placeholder — %s for PostgreSQL, ? for SQLite"""
    return "%s" if DATABASE_URL else "?"

def serial():
    """Primary key type"""
    return "SERIAL" if DATABASE_URL else "INTEGER"

def autoincrement():
    return "" if DATABASE_URL else "AUTOINCREMENT"

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            id {serial()} PRIMARY KEY {autoincrement()},
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS research_history (
            id {serial()} PRIMARY KEY {autoincrement()},
            username TEXT DEFAULT 'anonymous',
            query TEXT NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id {serial()} PRIMARY KEY {autoincrement()},
            username TEXT DEFAULT 'anonymous',
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("[db] Database ready at", "Supabase" if DATABASE_URL else DB_PATH)

def save_research(query: str, summary: str, username: str = "anonymous"):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO research_history (username, query, summary) VALUES ({ph()}, {ph()}, {ph()})",
        (username, query, summary)
    )
    conn.commit()
    conn.close()

def get_history(limit: int = 10, username: str = None) -> list:
    conn = get_conn()
    cursor = conn.cursor()
    if username:
        cursor.execute(
            f"SELECT query, summary, created_at FROM research_history WHERE username = {ph()} ORDER BY created_at DESC LIMIT {ph()}",
            (username, limit)
        )
    else:
        cursor.execute(
            f"SELECT query, summary, created_at FROM research_history ORDER BY created_at DESC LIMIT {ph()}",
            (limit,)
        )
    rows = cursor.fetchall()
    conn.close()
    return [{"query": r[0], "summary": r[1], "created_at": r[2]} for r in rows]

def search_history(query: str, username: str = None) -> list:
    conn = get_conn()
    cursor = conn.cursor()
    if username:
        cursor.execute(
            f"SELECT query, summary, created_at FROM research_history WHERE username = {ph()} AND query LIKE {ph()} ORDER BY created_at DESC LIMIT 3",
            (username, f"%{query}%")
        )
    else:
        cursor.execute(
            f"SELECT query, summary, created_at FROM research_history WHERE query LIKE {ph()} ORDER BY created_at DESC LIMIT 3",
            (f"%{query}%",)
        )
    rows = cursor.fetchall()
    conn.close()
    return [{"query": r[0], "summary": r[1], "created_at": r[2]} for r in rows]

def save_chat_message(session_id: str, role: str, content: str, username: str = "anonymous"):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO chat_sessions (username, session_id, role, content) VALUES ({ph()}, {ph()}, {ph()}, {ph()})",
        (username, session_id, role, content)
    )
    conn.commit()
    conn.close()

def get_chat_history(session_id: str) -> list:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT role, content, created_at FROM chat_sessions WHERE session_id = {ph()} ORDER BY created_at ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]

def clear_chat_session(session_id: str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM chat_sessions WHERE session_id = {ph()}", (session_id,))
    conn.commit()
    conn.close()

def get_user_sessions(username: str = None) -> list:
    conn = get_conn()
    cursor = conn.cursor()
    if username:
        cursor.execute(f"""
            SELECT session_id, MIN(created_at), COUNT(*),
                   MIN(CASE WHEN role='user' THEN content END)
            FROM chat_sessions WHERE username = {ph()}
            GROUP BY session_id ORDER BY MIN(created_at) DESC LIMIT 20
        """, (username,))
    else:
        cursor.execute("""
            SELECT session_id, MIN(created_at), COUNT(*),
                   MIN(CASE WHEN role='user' THEN content END)
            FROM chat_sessions
            GROUP BY session_id ORDER BY MIN(created_at) DESC LIMIT 20
        """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "session_id": r[0],
            "started": r[1],
            "message_count": r[2],
            "preview": r[3][:60] if r[3] else "No messages"
        }
        for r in rows
    ]

def clear_research_cache(username: str = None):
    conn = get_conn()
    cursor = conn.cursor()
    if username:
        cursor.execute(f"DELETE FROM research_history WHERE username = {ph()}", (username,))
    else:
        cursor.execute("DELETE FROM research_history")
    conn.commit()
    conn.close()

def get_cache_stats(username: str = None) -> dict:
    conn = get_conn()
    cursor = conn.cursor()
    if username:
        cursor.execute(
            f"SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM research_history WHERE username = {ph()}",
            (username,)
        )
    else:
        cursor.execute(
            "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM research_history"
        )
    row = cursor.fetchone()
    conn.close()
    return {
        "total_entries": row[0] or 0,
        "oldest": row[1],
        "newest": row[2]
    }