from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import sys
sys.path.insert(0, '.')
from app.memory.database import get_conn, ph

SECRET_KEY = "agentic-research-2026-secret-key"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": username, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def register_user(username: str, email: str, password: str) -> dict:
    """
    Registration rules:
    - Username must be unique
    - Email must be unique (same email cannot register twice even with different username)
    - Password minimum 6 characters
    """
    username = username.strip().lower()
    email = email.strip().lower()

    if len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters"}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters"}
    if "@" not in email:
        return {"success": False, "error": "Invalid email address"}

    conn = get_conn()
    cursor = conn.cursor()

    # Check username taken
    cursor.execute(f"SELECT id FROM users WHERE username = {ph()}", (username,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "error": "Username already taken. Choose another."}

    # Check email already registered — same email cannot register again
    cursor.execute(f"SELECT id FROM users WHERE email = {ph()}", (email,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "error": "Email already registered. Please login instead."}

    cursor.execute(f"INSERT INTO users (username, email, password_hash) VALUES ({ph()}, {ph()}, {ph()})",
        (username, email, hash_password(password))
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": "Account created successfully"}


def login_user(username: str, password: str) -> dict:
    """
    Login rules:
    - Username + correct password = success
    - Username + wrong password = fail
    - Unknown username = fail
    """
    username = username.strip().lower()
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT password_hash FROM users WHERE username = {ph()}", (username,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"success": False, "error": "Username not found"}
    if not verify_password(password, row[0]):
        return {"success": False, "error": "Incorrect password"}

    return {
        "success": True,
        "token": create_token(username),
        "username": username
    }


def get_current_user(token: str) -> Optional[str]:
    return decode_token(token)