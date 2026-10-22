from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import httpx
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import api_server
from reflect import auth
from reflect import service


@pytest.fixture
def client(monkeypatch):
    # No lifespan startup: the test must never initialise a remote database.
    monkeypatch.setattr(api_server, "get_db", Mock(return_value=Mock()))
    if hasattr(api_server.app.state, "limiter"):
        api_server.app.state.limiter.reset()
    return TestClient(api_server.app, raise_server_exceptions=False)


def test_reset_request_never_returns_credentials(client, monkeypatch):
    monkeypatch.setattr(api_server, "request_password_reset", Mock(return_value="leaked-token"))
    response = client.post("/api/auth/reset-request", json={"email": "person@example.com"})
    assert response.status_code == 200
    assert response.json() == {"message": "If that email exists, password reset instructions have been sent."}


def test_reset_failure_does_not_reveal_account_or_internals(client, monkeypatch):
    monkeypatch.setattr(api_server, "request_password_reset", Mock(side_effect=RuntimeError("database-secret")))
    response = client.post("/api/auth/reset-request", json={"email": "person@example.com"})
    assert response.status_code == 200
    assert response.json() == {"message": "If that email exists, password reset instructions have been sent."}


def test_password_reset_requires_eight_characters(client, monkeypatch):
    confirm = Mock()
    monkeypatch.setattr(api_server, "confirm_password_reset", confirm)
    response = client.post("/api/auth/reset-confirm", json={"token": "token", "new_password": "1234567"})
    assert response.status_code == 422
    confirm.assert_not_called()


@pytest.mark.parametrize("claims", [{"sub": "app_user:test"}, {"exp": datetime.now(timezone.utc) + timedelta(days=1)}])
def test_jwt_requires_expiry_and_subject(claims):
    token = jwt.encode(claims, auth._JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as error:
        auth.decode_jwt(token)
    assert error.value.status_code == 401


def test_expired_jwt_is_rejected():
    token = jwt.encode({"sub": "app_user:test", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, auth._JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as error:
        auth.decode_jwt(token)
    assert error.value.status_code == 401


def test_demo_jwt_expires_within_one_day(monkeypatch):
    monkeypatch.setenv("DEMO_USER_EMAIL", "demo@example.com")
    conn = Mock()
    conn.query.return_value = [{"id": "app_user:demo", "email": "demo@example.com"}]
    result = auth.demo_login(conn)
    payload = jwt.decode(result["token"], auth._JWT_SECRET, algorithms=["HS256"])
    assert 0 < payload["exp"] - datetime.now(timezone.utc).timestamp() <= 86400


def test_login_rate_limit_runs_before_database_work(client, monkeypatch):
    login = Mock(side_effect=HTTPException(status_code=401, detail="Invalid credentials"))
    monkeypatch.setattr(api_server, "login_user", login)
    responses = [client.post("/api/auth/login", json={"email": "person@example.com", "password": "wrong"}) for _ in range(11)]
    assert [r.status_code for r in responses[:10]] == [401] * 10
    assert responses[-1].status_code == 429
    assert login.call_count == 10
    assert api_server.get_db.call_count == 10


@pytest.mark.parametrize("function,path,payload", [
    ("register_user", "/api/auth/register", {"email": "x@example.com", "password": "password"}),
    ("login_user", "/api/auth/login", {"email": "x@example.com", "password": "password"}),
    ("demo_login", "/api/auth/demo-login", {}),
    ("confirm_password_reset", "/api/auth/reset-confirm", {"token": "token", "new_password": "password"}),
    ("run_chat", "/api/chat", {"message": "hello"}),
    ("run_reflection_pipeline", "/api/reflection", {"reflection_text": "hello"}),
])
def test_errors_hide_internal_details(client, monkeypatch, function, path, payload):
    monkeypatch.setattr(api_server, function, Mock(side_effect=RuntimeError("database-secret")))
    response = client.post(path, json=payload, headers={"Authorization": f"Bearer {auth.create_jwt('app_user:test')}"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error"}


def test_connection_errors_are_also_generic(client, monkeypatch):
    monkeypatch.setattr(api_server, "get_db", Mock(side_effect=RuntimeError("database-secret")))
    response = client.post("/api/auth/login", json={"email": "person@example.com", "password": "password"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error"}


@pytest.mark.parametrize("path,payload,allowed", [
    ("register", {"email": "x@example.com", "password": "password"}, 5),
    ("demo-login", {}, 30),
    ("reset-request", {"email": "x@example.com"}, 3),
    ("reset-confirm", {"token": "token", "new_password": "password"}, 10),
])
def test_all_auth_routes_are_limited(client, monkeypatch, path, payload, allowed):
    for name in ["register_user", "demo_login", "request_password_reset", "confirm_password_reset"]:
        monkeypatch.setattr(api_server, name, Mock(return_value={"user_id": "app_user:test", "email": "x@example.com", "token": "test"}))
    for _ in range(allowed):
        assert client.post(f"/api/auth/{path}", json=payload).status_code == 200
    assert client.post(f"/api/auth/{path}", json=payload).status_code == 429


@pytest.mark.parametrize("path,setup,payload", [
    ("chat", "_build_chat_agent_for_user", {"message": "hello"}),
    ("reflection", "_ensure_graph", {"reflection_text": "hello"}),
])
@pytest.mark.parametrize("during_stream", [False, True])
def test_stream_errors_are_generic(client, monkeypatch, path, setup, payload, during_stream):
    async def failing_stream(*args, **kwargs):
        yield {"event": "on_chain_start", "name": "store_reflection"}
        raise RuntimeError("database-secret")

    if during_stream:
        agent = Mock()
        agent.astream_events = failing_stream
        monkeypatch.setattr(service, setup, Mock(return_value=agent))
        monkeypatch.setattr(service, "_ensure_live_connection", Mock())
    else:
        monkeypatch.setattr(service, setup, Mock(side_effect=RuntimeError("database-secret")))
    response = client.post(f"/api/{path}/stream", json=payload, headers={"Authorization": f"Bearer {auth.create_jwt('app_user:test')}"})
    assert response.status_code == 200
    assert '"type": "error", "content": "Internal error"' in response.text
    assert "database-secret" not in response.text


def test_reset_email_is_sent_only_to_the_account(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("RESET_EMAIL_FROM", "Synapse <security@example.com>")
    post = Mock(return_value=httpx.Response(200, request=httpx.Request("POST", "https://api.resend.com/emails")))
    monkeypatch.setattr(auth.httpx, "post", post)
    auth.send_password_reset_email("person@example.com", "private-test-code")
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert post.call_args.kwargs["json"]["to"] == ["person@example.com"]
    assert "private-test-code" in post.call_args.kwargs["json"]["text"]


def test_reflection_still_initialises_and_runs(monkeypatch):
    graph = Mock()
    graph.invoke.return_value = {"insight": "example"}
    monkeypatch.setattr(service, "_ensure_graph", Mock(return_value=graph))
    connection = Mock()
    monkeypatch.setattr(service, "_ensure_live_connection", connection)
    result = service.run_reflection_pipeline("reflection", None, "thread", user_id="app_user:test")
    assert result == {"thread_id": "thread", "result": {"insight": "example"}}
    connection.assert_called_once()


@pytest.mark.parametrize("results", [
    [{"status": "OK", "result": None}, {"status": "ERR", "kind": "Query", "result": "commit failed"}],
    [{"status": "ERR", "kind": "Query", "result": "statement failed"}, {"status": "ERR", "kind": "Query", "result": "cancelled"}],
])
def test_auth_transaction_cannot_report_success_after_database_failure(results):
    conn = Mock()
    conn.query_raw.return_value = {"result": results}
    with pytest.raises(RuntimeError, match="Authentication transaction failed"):
        auth._auth_transaction(conn, "transaction", {})
