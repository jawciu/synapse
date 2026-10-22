"""Integration checks against an explicitly configured, disposable local SurrealDB."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
from fastapi import HTTPException
from surrealdb import Surreal

from reflect import auth
from reflect.db import SCHEMA_STATEMENTS


@pytest.fixture
def store(monkeypatch):
    url = os.getenv("SYNAPSE_TEST_SURREAL_URL")
    if not url:
        pytest.skip("Set SYNAPSE_TEST_SURREAL_URL to a disposable local SurrealDB")
    if urlsplit(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Security integration tests only accept a loopback database")
    database = "reset_" + uuid.uuid4().hex

    def connect():
        conn = Surreal(url)
        conn.signin({"username": "test", "password": "test"})
        conn.use("security_tests", database)
        return conn

    conn = connect()
    for statement in SCHEMA_STATEMENTS:
        conn.query(statement)
    auth.register_user(conn, "person@example.com", "original-password")
    monkeypatch.setenv("RESEND_API_KEY", "test-resend")
    monkeypatch.setenv("RESET_EMAIL_FROM", "test@example.com")
    send = Mock()
    monkeypatch.setattr(auth, "send_password_reset_email", send)
    yield conn, send, connect
    conn.query(f"REMOVE DATABASE {database}")
    conn.close()


def assert_invalid(conn, token):
    with pytest.raises(HTTPException) as error:
        auth.confirm_password_reset(conn, token, "replacement-password")
    assert error.value.status_code == 400


def test_emailed_token_is_hashed_single_use_and_replaces_previous(store):
    conn, send, _ = store
    assert auth.request_password_reset(conn, " PERSON@example.com ") is None
    first = send.call_args.args[1]
    rows = conn.query("SELECT * FROM reset_token")
    assert len(rows) == 1
    assert rows[0]["token"] == auth._reset_token_hash(first)
    assert first not in repr(rows)
    assert_invalid(conn, rows[0]["token"])

    auth.request_password_reset(conn, "person@example.com")
    second = send.call_args.args[1]
    assert first != second
    assert len(conn.query("SELECT * FROM reset_token")) == 1
    assert_invalid(conn, first)
    assert auth.confirm_password_reset(conn, second, "replacement-password")
    assert auth.login_user(conn, "person@example.com", "replacement-password")["email"] == "person@example.com"
    assert conn.query("SELECT * FROM reset_token") == []
    assert_invalid(conn, second)
    with pytest.raises(HTTPException):
        auth.login_user(conn, "person@example.com", "original-password")


def test_legacy_and_expired_tokens_are_rejected(store):
    conn, send, _ = store
    user_id = str(conn.query("SELECT id FROM app_user")[0]["id"])
    conn.query("CREATE reset_token SET user_id = $uid, token = 'legacy-plaintext', expires_at = time::now() + 1h", {"uid": user_id})
    assert_invalid(conn, "legacy-plaintext")
    auth.request_password_reset(conn, "person@example.com")
    token = send.call_args.args[1]
    conn.query("UPDATE reset_token SET expires_at = time::now() - 1s")
    assert_invalid(conn, token)
    assert auth.login_user(conn, "person@example.com", "original-password")


def test_unknown_account_and_missing_email_configuration_issue_nothing(store, monkeypatch):
    conn, send, _ = store
    auth.request_password_reset(conn, "unknown@example.com")
    monkeypatch.delenv("RESEND_API_KEY")
    auth.request_password_reset(conn, "person@example.com")
    send.assert_not_called()
    assert conn.query("SELECT * FROM reset_token") == []


def test_failed_delivery_invalidates_the_new_token(store):
    conn, send, _ = store
    send.side_effect = RuntimeError("email failure")
    with pytest.raises(RuntimeError):
        auth.request_password_reset(conn, "person@example.com")
    assert conn.query("SELECT * FROM reset_token") == []


def test_concurrent_confirmations_cannot_reuse_token(store):
    conn, send, connect = store
    auth.request_password_reset(conn, "person@example.com")
    token = send.call_args.args[1]
    barrier = Barrier(2)

    def confirm():
        own_conn = connect()
        try:
            barrier.wait(timeout=5)
            auth.confirm_password_reset(own_conn, token, "replacement-password")
            return True
        except (HTTPException, RuntimeError):
            return False
        finally:
            own_conn.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(lambda _: confirm(), range(2))) == 1
    assert conn.query("SELECT * FROM reset_token") == []
