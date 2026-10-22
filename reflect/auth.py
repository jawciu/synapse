from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta

import bcrypt
import httpx
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from surrealdb import Surreal

load_dotenv()

_jwt_env = os.getenv("JWT_SECRET", "").strip()
if not _jwt_env:
    raise RuntimeError(
        "JWT_SECRET environment variable is not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )
if len(_jwt_env) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 characters for adequate security.")
_JWT_SECRET = _jwt_env
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_DAYS = 7
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Password helpers ──

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT helpers ──

def create_jwt(user_id: str, expires_days: int = _JWT_EXPIRY_DAYS) -> str:
    if expires_days <= 0:
        raise ValueError("JWT lifetime must be positive")
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=expires_days)}
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_jwt(token: str) -> str:
    try:
        payload = jwt.decode(
            token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
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


def demo_login(conn: Surreal) -> dict:
    demo_email = os.getenv("DEMO_USER_EMAIL", "").strip().lower()
    if not demo_email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo mode is not enabled")
    rows = conn.query(
        "SELECT id, email FROM app_user WHERE email = $email",
        {"email": demo_email},
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo account not found")
    row = rows[0]
    user_id = str(row["id"])
    token = create_jwt(user_id, expires_days=1)
    return {"user_id": user_id, "email": row["email"], "token": token}


def _reset_token_hash(token: str) -> str:
    # Versioning makes every legacy plaintext token unusable without a DB migration.
    # Passing a stored hash to reset-confirm cannot work: it is hashed again.
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()


def _auth_transaction(conn: Surreal, statement: str, params: dict) -> None:
    # The SDK's query() returns only the first statement and can miss transaction
    # errors. Inspect every result, including failures at COMMIT.
    response = conn.query_raw(statement, params)
    if response.get("error"):
        raise RuntimeError("Authentication transaction failed")
    errors = [result for result in response["result"] if result["status"] == "ERR"]
    if any(
        result.get("kind") == "Thrown"
        and result.get("result") == "An error occurred: Invalid or expired reset token"
        for result in errors
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if errors:
        raise RuntimeError("Authentication transaction failed")


def send_password_reset_email(email: str, token: str) -> None:
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
        json={
            "from": os.environ["RESET_EMAIL_FROM"],
            "to": [email],
            "subject": "Reset your Synapse password",
            "text": (
                "Paste this code into the Synapse password reset form:\n\n"
                f"{token}\n\n"
                "It expires in one hour and can only be used once. "
                "If you did not request this, you can ignore this email."
            ),
        },
        timeout=10,
    )
    response.raise_for_status()


def request_password_reset(conn: Surreal, email: str) -> None:
    if not os.getenv("RESEND_API_KEY", "").strip() or not os.getenv("RESET_EMAIL_FROM", "").strip():
        logger.error("Password reset email is not configured")
        return
    email = email.strip().lower()
    rows = conn.query(
        "SELECT id FROM app_user WHERE email = $email",
        {"email": email},
    )
    if not rows:
        return
    user_id = str(rows[0]["id"])
    token = secrets.token_urlsafe(32)
    token_hash = _reset_token_hash(token)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    _auth_transaction(conn,
        """BEGIN TRANSACTION;
        DELETE reset_token WHERE user_id = $user_id;
        UPSERT type::record('reset_token', $user_id)
            SET user_id = $user_id, token = $reset_token, expires_at = <datetime>$expires_at;
        COMMIT TRANSACTION;""",
        {"user_id": user_id, "reset_token": token_hash, "expires_at": expires_at},
    )
    try:
        send_password_reset_email(email, token)
    except Exception:
        conn.query("DELETE reset_token WHERE token = $reset_token", {"reset_token": token_hash})
        raise


def confirm_password_reset(conn: Surreal, token: str, new_password: str) -> bool:
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    new_hash = hash_password(new_password)
    # Consume and update atomically so concurrent requests cannot reuse a token.
    _auth_transaction(conn,
        """BEGIN TRANSACTION;
        LET $reset = (SELECT user_id FROM reset_token
            WHERE token = $reset_token AND expires_at > time::now() LIMIT 1)[0];
        IF $reset = NONE { THROW 'Invalid or expired reset token'; };
        UPDATE type::record($reset.user_id) SET password_hash = $hash;
        DELETE reset_token WHERE user_id = $reset.user_id;
        RETURN true;
        COMMIT TRANSACTION;""",
        {"reset_token": _reset_token_hash(token), "hash": new_hash},
    )
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
