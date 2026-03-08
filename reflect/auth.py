from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from surrealdb import Surreal

_JWT_SECRET = os.getenv("JWT_SECRET", "changeme")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Password helpers ──

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT helpers ──

def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_jwt(token: str) -> str:
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    return decode_jwt(token)


# ── User CRUD ──

def register_user(conn: Surreal, email: str, password: str) -> dict:
    email = email.strip().lower()
    existing = conn.query(
        "SELECT id FROM app_user WHERE email = $email",
        {"email": email},
    )
    if isinstance(existing, list) and existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    password_hash = hash_password(password)
    result = conn.query(
        "CREATE app_user SET email = $email, password_hash = $hash",
        {"email": email, "hash": password_hash},
    )
    user_id = str(result[0]["id"])
    token = create_jwt(user_id)
    return {"user_id": user_id, "email": email, "token": token}


def login_user(conn: Surreal, email: str, password: str) -> dict:
    email = email.strip().lower()
    rows = conn.query(
        "SELECT id, email, password_hash FROM app_user WHERE email = $email",
        {"email": email},
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    row = rows[0]
    if not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user_id = str(row["id"])
    token = create_jwt(user_id)
    return {"user_id": user_id, "email": row["email"], "token": token}


def request_password_reset(conn: Surreal, email: str) -> str:
    email = email.strip().lower()
    rows = conn.query(
        "SELECT id FROM app_user WHERE email = $email",
        {"email": email},
    )
    if not rows:
        # Don't reveal whether email exists
        return str(uuid.uuid4())
    user_id = str(rows[0]["id"])
    token = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    conn.query(
        "CREATE reset_token SET user_id = $user_id, token = $token, expires_at = $expires_at",
        {"user_id": user_id, "token": token, "expires_at": expires_at},
    )
    return token


def confirm_password_reset(conn: Surreal, token: str, new_password: str) -> bool:
    rows = conn.query(
        "SELECT user_id, expires_at FROM reset_token WHERE token = $token",
        {"token": token},
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    row = rows[0]
    expires_at = row["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        conn.query("DELETE reset_token WHERE token = $token", {"token": token})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token expired")
    new_hash = hash_password(new_password)
    conn.query(
        "UPDATE $user_id SET password_hash = $hash",
        {"user_id": row["user_id"], "hash": new_hash},
    )
    conn.query("DELETE reset_token WHERE token = $token", {"token": token})
    return True


# ── Telegram identity ──

def get_user_by_telegram_id(conn: Surreal, telegram_id: int) -> str | None:
    rows = conn.query(
        "SELECT id, created_at FROM app_user WHERE telegram_id = $tid ORDER BY created_at DESC LIMIT 1",
        {"tid": telegram_id},
    )
    if rows:
        return str(rows[0]["id"])
    return None


def link_telegram_to_user(conn: Surreal, user_id: str, telegram_id: int) -> None:
    # Enforce one Telegram ID -> one account mapping by clearing stale links first.
    conn.query(
        "UPDATE app_user SET telegram_id = NONE WHERE telegram_id = $tid",
        {"tid": telegram_id},
    )
    target = user_id.strip()
    if ":" not in target:
        target = f"app_user:{target}"
    conn.query(
        f"UPDATE {target} SET telegram_id = $tid",
        {"tid": telegram_id},
    )
    linked_user_id = get_user_by_telegram_id(conn, telegram_id)
    if not linked_user_id:
        raise RuntimeError("Telegram link failed to persist")


def register_user_from_telegram(conn: Surreal, email: str, password: str, telegram_id: int) -> dict:
    result = register_user(conn, email, password)
    link_telegram_to_user(conn, result["user_id"], telegram_id)
    return result
