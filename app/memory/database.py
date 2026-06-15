import sqlite3
import os
import sys
sys.path.insert(0, '.')
from app.config import DB_PATH


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT DEFAULT 'anonymous',
            query TEXT NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT DEFAULT 'anonymous',
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("[db] Database ready at", DB_PATH)


def save_research(query: str, summary: str, username: str = "anonymous"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO research_history (username, query, summary) VALUES (?, ?, ?)",
        (username, query, summary)
    )
    conn.commit()
    conn.close()


def get_history(limit: int = 10, username: str = None) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if username:
        cursor.execute(
            "SELECT query, summary, created_at FROM research_history WHERE username = ? ORDER BY created_at DESC LIMIT ?",
            (username, limit)
        )
    else:
        cursor.execute(
            "SELECT query, summary, created_at FROM research_history ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
    rows = cursor.fetchall()
    conn.close()
    return [{"query": r[0], "summary": r[1], "created_at": r[2]} for r in rows]


def search_history(query: str, username: str = None) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if username:
        cursor.execute(
            "SELECT query, summary, created_at FROM research_history WHERE username = ? AND query LIKE ? ORDER BY created_at DESC LIMIT 3",
            (username, f"%{query}%")
        )
    else:
        cursor.execute(
            "SELECT query, summary, created_at FROM research_history WHERE query LIKE ? ORDER BY created_at DESC LIMIT 3",
            (f"%{query}%",)
        )
    rows = cursor.fetchall()
    conn.close()
    return [{"query": r[0], "summary": r[1], "created_at": r[2]} for r in rows]


def save_chat_message(session_id: str, role: str, content: str, username: str = "anonymous"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_sessions (username, session_id, role, content) VALUES (?, ?, ?, ?)",
        (username, session_id, role, content)
    )
    conn.commit()
    conn.close()


def get_chat_history(session_id: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, created_at FROM chat_sessions WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]


def clear_chat_session(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def get_user_sessions(username: str = None) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if username:
        cursor.execute("""
            SELECT session_id, MIN(created_at), COUNT(*),
                   MIN(CASE WHEN role='user' THEN content END)
            FROM chat_sessions WHERE username = ?
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if username:
        cursor.execute("DELETE FROM research_history WHERE username = ?", (username,))
    else:
        cursor.execute("DELETE FROM research_history")
    conn.commit()
    conn.close()


def get_cache_stats(username: str = None) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if username:
        cursor.execute(
            "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM research_history WHERE username = ?",
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